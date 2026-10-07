"""The on-disk format of a Macrostrat map package, and the codec between Postgres
rows and GeoPackage layers.

A package is an ordinary GeoPackage -- it opens in QGIS -- with three extra
attribute tables that make it self-describing:

- `macrostrat_package`: `key`/`value` metadata; `format` identifies the file.
- `macrostrat_package_layers`: one row per exported table -- the Postgres table
  it came from, its geometry column and SRID, and the staging-table owner.
- `macrostrat_package_columns`: every exported column with its Postgres type.

Integers, floats, booleans and text are stored natively so the layers are
readable as they are. Every other type (arrays, `jsonb`, enums, timestamps,
secondary geometry columns) is stored as its Postgres text form, which casts
back exactly. Import casts each value to the *target* column's type, so a
package survives modest schema drift between environments.
"""

import json
import re
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator, Optional

import numpy as N
import pandas as P
import pyogrio
import shapely
from sqlalchemy import text

from macrostrat.map_utils.slugs import STAGING_KINDS, slugify, staging_table

FORMAT_NAME = "macrostrat-map-package"
# The newest version this code reads. Full packages are still written as 1, so
# older readers load them; partial packages (version 2) must be refused there.
FORMAT_VERSION = 2
FULL_FORMAT_VERSION = 1

META_TABLE = "macrostrat_package"
LAYERS_TABLE = "macrostrat_package_layers"
COLUMNS_TABLE = "macrostrat_package_columns"

CHUNK_SIZE = 5000
# Export fetches small batches and writes once either limit is reached, so a
# table of dense geometries never arrives as one enormous fetch
CHUNK_BYTES = 32 * 1024 * 1024
FETCH_SIZE = 200

_INTEGER = {"int2", "int4", "int8"}
_FLOAT = {"float4", "float8", "numeric"}
_TEXT = {"text", "varchar", "bpchar", "name"}


def quote(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def qualified(table: str) -> str:
    """Quote a `schema.table` name; packages from before kebab slugs have hyphens."""
    schema, name = table.split(".", 1)
    return quote(schema) + "." + quote(name)


@dataclass
class Column:
    name: str
    type: str  # format_type(), e.g. "character varying(255)"
    encoding: str  # integer | float | boolean | text | geometry
    generated: bool = False
    default: Optional[str] = None


@dataclass
class Layer:
    """An exported table as recorded in the package manifest."""

    name: str
    table: str
    columns: list[Column]
    geometry_column: Optional[str] = None
    srid: int = 0
    row_count: int = 0
    # The slug whose staging table this is; None for shared or non-staging tables
    owner: Optional[str] = None

    def column(self, name: str) -> Optional[Column]:
        return next((c for c in self.columns if c.name == name), None)


def _encoding(typname: str) -> str:
    if typname == "geometry":
        return "geometry"
    if typname in _INTEGER:
        return "integer"
    if typname in _FLOAT:
        return "float"
    if typname == "bool":
        return "boolean"
    return "text"


def table_columns(conn, table: str) -> Optional[list[Column]]:
    """Columns of a Postgres table, or None if it does not exist."""
    if conn.execute(text("SELECT to_regclass(:t)"), dict(t=qualified(table))).scalar():
        rows = conn.execute(
            text(
                """
                SELECT a.attname AS name,
                       format_type(a.atttypid, a.atttypmod) AS type,
                       t.typname,
                       a.attgenerated <> '' OR a.attidentity <> '' AS generated,
                       pg_get_expr(d.adbin, d.adrelid) AS "default"
                FROM pg_attribute a
                JOIN pg_type t ON t.oid = a.atttypid
                LEFT JOIN pg_attrdef d ON d.adrelid = a.attrelid AND d.adnum = a.attnum
                WHERE a.attrelid = CAST(:t AS regclass)
                  AND a.attnum > 0 AND NOT a.attisdropped
                ORDER BY a.attnum
                """
            ),
            dict(t=qualified(table)),
        ).all()
        return [
            Column(r.name, r.type, _encoding(r.typname), r.generated, r.default)
            for r in rows
        ]
    return None


def _select_expression(col: Column, primary_geometry: bool) -> str:
    q = "t." + quote(col.name)
    if primary_geometry:
        return f"ST_AsBinary({q})"
    if col.encoding == "float":
        return f"CAST({q} AS double precision)"
    if col.encoding in ("text", "geometry"):
        # geometry::text is hex EWKB, which casts straight back
        return f"CAST({q} AS text)"
    return q


def _frame(rows, layer: Layer) -> P.DataFrame:
    names = [c.name for c in layer.columns]
    df = P.DataFrame.from_records(rows, columns=names)
    for col in layer.columns:
        if col.name == layer.geometry_column:
            continue
        if col.encoding == "integer":
            df[col.name] = P.array(df[col.name], dtype="Int64")
        elif col.encoding == "boolean":
            df[col.name] = P.array(df[col.name], dtype="boolean")
        elif col.encoding == "float":
            df[col.name] = df[col.name].astype("float64")
        else:
            df[col.name] = df[col.name].astype(object)
    if layer.geometry_column is None:
        return df
    import geopandas as G

    name = layer.geometry_column
    df[name] = shapely.from_wkb([None if v is None else bytes(v) for v in df[name]])
    return G.GeoDataFrame(df, geometry=name, crs=layer.srid or None)


def dump_table(
    conn,
    path: Path,
    layer: Layer,
    where: str,
    params: dict,
    *,
    order_by: Optional[str] = None,
    extra: Optional[dict[str, str]] = None,
) -> Layer:
    """Stream the rows of `layer.table` matching `where` into a package layer.

    `layer.columns` is the export's column list; `extra` adds computed text
    columns (e.g. a slug standing in for a database-specific id).
    """
    extra = extra or {}
    geoms = [c for c in layer.columns if c.encoding == "geometry"]
    if geoms:
        layer.geometry_column = geoms[0].name
        m = re.search(r"geometry\(\w+,\s*(\d+)\)", geoms[0].type)
        layer.srid = int(m.group(1)) if m else 0
        if not layer.srid:
            layer.srid = (
                conn.execute(
                    text(
                        f"SELECT ST_SRID({quote(layer.geometry_column)}) FROM"
                        f" {qualified(layer.table)} t WHERE {where} LIMIT 1"
                    ),
                    params,
                ).scalar()
                or 0
            )

    exprs = [
        _select_expression(c, c.name == layer.geometry_column) for c in layer.columns
    ]
    exprs += list(extra.values())
    layer.columns = layer.columns + [Column(k, "text", "text") for k in extra]
    sql = f"SELECT {', '.join(exprs)} FROM {qualified(layer.table)} t WHERE {where}"
    if order_by:
        sql += f" ORDER BY {order_by}"

    # A binary-format server-side cursor: in text format `bytea` arrives as hex,
    # doubling the transfer of every geometry. SQLAlchemy can't request binary
    # results, so the cursor is opened on the driver connection, in the same
    # transaction. Every selected column is an integer, double, boolean, text or
    # bytea, which decode to the same Python values in either format.
    compiled = text(sql).compile(dialect=conn.dialect)
    layer.row_count = 0
    rows, size = [], 0
    with conn.connection.driver_connection.cursor(
        name="map_package_export", binary=True
    ) as cursor:
        cursor.execute(compiled.string, compiled.construct_params(params))
        while batch := cursor.fetchmany(FETCH_SIZE):
            rows += batch
            size += sum(_row_bytes(r) for r in batch)
            if len(rows) >= CHUNK_SIZE or size >= CHUNK_BYTES:
                _write_rows(path, layer, rows)
                rows, size = [], 0
    if rows:
        _write_rows(path, layer, rows)
    return layer


def _row_bytes(row) -> int:
    return sum(len(v) for v in row if isinstance(v, (bytes, str)))


def _write_rows(path: Path, layer: Layer, rows: list):
    df = _frame(rows, layer)
    opts = {}
    if layer.geometry_column is not None:
        opts = dict(
            promote_to_multi=False,
            geometry_type="Unknown",
            layer_options={"GEOMETRY_NAME": layer.geometry_column},
        )
    pyogrio.write_dataframe(
        df,
        path,
        layer=layer.name,
        driver="GPKG",
        append=layer.row_count > 0,
        **opts,
    )
    layer.row_count += len(df)


def insert_rows(conn, table: str, columns: list[Column], rows: list[dict], suffix=""):
    """Insert `rows`, casting each value to its target column's type."""
    if not rows:
        return
    names = ", ".join(quote(c.name) for c in columns)
    values = ", ".join(f"CAST(:p{i} AS {c.type})" for i, c in enumerate(columns))
    sql = f"INSERT INTO {qualified(table)} ({names}) VALUES ({values}) {suffix}"
    conn.execute(
        text(sql),
        [{f"p{i}": r.get(c.name) for i, c in enumerate(columns)} for r in rows],
    )


def write_manifest(
    path: Path, meta: dict, layers: list[Layer], version: int = FULL_FORMAT_VERSION
):
    with sqlite3.connect(path) as db:
        db.executescript(
            f"""
            CREATE TABLE {META_TABLE} (key TEXT PRIMARY KEY, value TEXT);
            CREATE TABLE {LAYERS_TABLE} (
              layer TEXT PRIMARY KEY, pg_table TEXT NOT NULL, geometry_column TEXT,
              srid INTEGER, row_count INTEGER, owner TEXT);
            CREATE TABLE {COLUMNS_TABLE} (
              layer TEXT NOT NULL, position INTEGER NOT NULL, name TEXT NOT NULL,
              pg_type TEXT NOT NULL, encoding TEXT NOT NULL,
              PRIMARY KEY (layer, position));
            """
        )
        meta = {"format": FORMAT_NAME, "format_version": version, **meta}
        db.executemany(
            f"INSERT INTO {META_TABLE} VALUES (?, ?)",
            [(k, v if isinstance(v, str) else json.dumps(v)) for k, v in meta.items()],
        )
        for l in layers:
            db.execute(
                f"INSERT INTO {LAYERS_TABLE} VALUES (?, ?, ?, ?, ?, ?)",
                (l.name, l.table, l.geometry_column, l.srid, l.row_count, l.owner),
            )
            db.executemany(
                f"INSERT INTO {COLUMNS_TABLE} VALUES (?, ?, ?, ?, ?)",
                [
                    (l.name, i, c.name, c.type, c.encoding)
                    for i, c in enumerate(l.columns)
                ],
            )


def is_map_package(path) -> bool:
    """Whether `path` is a GeoPackage written by `macrostrat maps export`."""
    path = Path(path)
    if path.suffix.lower() != ".gpkg" or not path.is_file():
        return False
    try:
        with sqlite3.connect(f"file:{path}?mode=ro", uri=True) as db:
            row = db.execute(
                f"SELECT value FROM {META_TABLE} WHERE key = 'format'"
            ).fetchone()
    except sqlite3.DatabaseError:
        return False
    return row is not None and row[0] == FORMAT_NAME


@dataclass
class Package:
    path: Path
    meta: dict
    layers: dict[str, Layer] = field(default_factory=dict)

    @property
    def format_version(self) -> int:
        return int(self.meta.get("format_version", 0))

    @property
    def elements(self) -> Optional[list[str]]:
        """The patch elements of a partial package; None for a whole one."""
        value = self.meta.get("elements")
        return None if value is None else json.loads(value)

    def rows(self, name: str) -> Iterator[list[dict]]:
        """Yield a layer's rows in chunks, decoded to plain Python values.

        Geometry comes back as hex EWKB, the form `CAST(... AS geometry)` takes.
        A layer in the manifest but absent from the file was exported empty.
        """
        layer = self.layers.get(name)
        if layer is None or layer.row_count == 0:
            return
        for skip in range(0, layer.row_count, CHUNK_SIZE):
            df = pyogrio.read_dataframe(
                self.path, layer=name, skip_features=skip, max_features=CHUNK_SIZE
            )
            yield [_kebab(row) for row in _decode(df, layer)]

    def all_rows(self, name: str) -> list[dict]:
        return [row for chunk in self.rows(name) for row in chunk]

    def distinct(self, name: str, column: str) -> set:
        """The distinct values of one column, read without decoding the layer."""
        layer = self.layers.get(name)
        if layer is None or layer.row_count == 0 or layer.column(column) is None:
            return set()
        with sqlite3.connect(f"file:{self.path}?mode=ro", uri=True) as db:
            return {
                v
                for (v,) in db.execute(
                    f"SELECT DISTINCT {quote(column)} FROM {quote(name)}"
                )
            }


# Packages written before slugs were kebab-case carry the old forms.
SLUG_COLUMNS = ("slug", "superseded_by_slug", "compilation_slug", "member_slug")


def _kebab(row: dict) -> dict:
    for col in SLUG_COLUMNS:
        if row.get(col) is not None:
            row[col] = slugify(row[col])
    return row


def _staging_layer(table: str, owner: Optional[str]) -> tuple[str, Optional[str]]:
    """An owned staging table, renamed to the prefix its kebab slug derives."""
    if owner is None:
        return table, None
    slug = slugify(owner)
    for kind in STAGING_KINDS:
        if table == f"sources.{owner}_{kind}":
            return f"sources.{staging_table(slug, kind)}", slug
    return table, slug


def _decode(df: P.DataFrame, layer: Layer) -> list[dict]:
    out = {}
    for col in layer.columns:
        if col.name == layer.geometry_column:
            geom = N.asarray(df.geometry.values, dtype=object)
            if layer.srid:
                geom = shapely.set_srid(geom, layer.srid)
            out[col.name] = shapely.to_wkb(geom, hex=True, include_srid=True)
            continue
        values = df[col.name].to_numpy(dtype=object)
        out[col.name] = [_value(v, col.encoding) for v in values]
    names = list(out)
    return [dict(zip(names, vals)) for vals in zip(*out.values())]


def _value(v, encoding):
    if v is None or (isinstance(v, float) and v != v) or v is P.NA:
        return None
    if encoding == "integer":
        return int(v)
    if encoding == "float":
        return float(v)
    if encoding == "boolean":
        return v if isinstance(v, bool) else str(v).lower() in ("1", "1.0", "true")
    return str(v)


def read_package(path) -> Package:
    path = Path(path)
    if not is_map_package(path):
        raise ValueError(f"{path} is not a Macrostrat map package")
    with sqlite3.connect(f"file:{path}?mode=ro", uri=True) as db:
        meta = dict(db.execute(f"SELECT key, value FROM {META_TABLE}").fetchall())
        pkg = Package(path, meta)
        for name, table, geom, srid, count, owner in db.execute(
            f"SELECT * FROM {LAYERS_TABLE}"
        ):
            columns = [
                Column(n, t, e)
                for n, t, e in db.execute(
                    f"SELECT name, pg_type, encoding FROM {COLUMNS_TABLE}"
                    " WHERE layer = ? ORDER BY position",
                    (name,),
                )
            ]
            table, owner = _staging_layer(table, owner)
            pkg.layers[name] = Layer(
                name, table, columns, geom, srid or 0, count, owner
            )
    if pkg.format_version > FORMAT_VERSION:
        raise ValueError(
            f"{path} is format version {pkg.format_version}; this version of"
            f" Macrostrat reads up to {FORMAT_VERSION}"
        )
    return pkg
