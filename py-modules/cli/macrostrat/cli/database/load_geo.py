"""Load geospatial files into the database, inferring a table structure.

The geospatial counterpart to [cyan]load-csv[/], with the same semantics: the
destination table is created to match the file, named after it, and placed in
the [cyan]temp[/] schema by default.

Reading is done with [cyan]pyogrio[/], a direct GDAL/OGR binding — so this
handles the same formats [cyan]ogr2ogr[/] does (Shapefile, GeoPackage, GeoJSON,
FileGDB, KML, …) without shelling out to it or putting database credentials on a
command line. Attributes are handed to the same Polars-based type inference and
[cyan]COPY[/] path used by [cyan]load-csv[/]; geometry travels as hex EWKB.
"""

from pathlib import Path
from sys import stderr
from typing import Optional

import polars as pl
import typer
from psycopg.sql import SQL, Identifier
from rich import print
from sqlalchemy.engine import Engine
from typer import Argument, Option

from macrostrat.database.utils import run_sql
from macrostrat.utils import get_logger

from .load_utils import (
    check_target,
    comment_original_names,
    copy_dataframe,
    create_table,
    dedupe,
    identifier,
    pg_type,
    polars_from_pandas,
    render_ddl,
)
from .utils import engine_for_db_name

log = get_logger(__name__)

# Macrostrat stores geometry in WGS84 unless told otherwise
DEFAULT_SRID = 4326

# OGR geometry type names -> PostGIS typmod names. Anything absent (or mixed
# within a layer) falls back to the unconstrained 'Geometry'.
_GEOM_TYPES = {
    "Point": "Point",
    "LineString": "LineString",
    "Polygon": "Polygon",
    "MultiPoint": "MultiPoint",
    "MultiLineString": "MultiLineString",
    "MultiPolygon": "MultiPolygon",
    "GeometryCollection": "GeometryCollection",
    "LinearRing": "LineString",
}

_PROMOTE_TO_MULTI = {
    "Point": "MultiPoint",
    "LineString": "MultiLineString",
    "Polygon": "MultiPolygon",
}


def load_geo(
    files: list[Path] = Argument(..., help="Geospatial file(s) to load"),
    schema: str = Option("temp", "--schema", "-n", help="Schema to create tables in"),
    table: Optional[str] = Option(
        None,
        "--table",
        "-t",
        help="Table name (defaults to the file name). Only valid for a single layer.",
    ),
    layer: Optional[str] = Option(
        None,
        "--layer",
        "-l",
        help="Layer to load. Defaults to every layer in the file, each into its own table.",
    ),
    database: Optional[str] = Option(None, "--database", help="Database to connect to"),
    srid: Optional[int] = Option(
        None,
        "--srid",
        help=f"Target SRID to reproject to (default: {DEFAULT_SRID})",
    ),
    keep_srid: bool = Option(
        False,
        "--keep-srid",
        help="Keep the file's own CRS instead of reprojecting to EPSG:4326",
    ),
    source_srid: Optional[int] = Option(
        None,
        "--source-srid",
        help=(
            "Declare the source CRS for a file that has none (or override a wrong "
            "one). Reprojection to the target SRID still applies unless --keep-srid."
        ),
    ),
    geometry_column: str = Option(
        "geom", "--geometry-column", "-g", help="Name of the geometry column"
    ),
    promote_to_multi: bool = Option(
        False,
        "--multi",
        help="Promote single geometries to their Multi* equivalent, so mixed layers share one type",
    ),
    no_index: bool = Option(
        False, "--no-index", help="Skip creating the GIST index on the geometry column"
    ),
    where: Optional[str] = Option(
        None, "--where", help="OGR attribute filter applied while reading"
    ),
    replace: bool = Option(
        False, "--replace", help="Drop and recreate the table if it already exists"
    ),
    append: bool = Option(
        False, "--append", help="Append to an existing table instead of creating it"
    ),
    dry_run: bool = Option(
        False,
        "--dry-run",
        help="Print the inferred table structure without touching the database",
    ),
):
    """Load geospatial files into the database, creating tables to match the data.

    The geospatial counterpart to [cyan]load-csv[/]. Reads anything GDAL/OGR can
    (Shapefile, GeoPackage, GeoJSON, FileGDB, …), creating one table per layer in
    the [cyan]temp[/] schema and reprojecting to EPSG:4326 by default.
    """
    from pyogrio import list_layers

    if replace and append:
        raise typer.BadParameter("--replace and --append are mutually exclusive")
    if keep_srid and srid is not None:
        raise typer.BadParameter(
            "--keep-srid and --srid are mutually exclusive: one keeps the file's "
            "CRS, the other reprojects away from it"
        )

    engine = engine_for_db_name(database)

    for file in files:
        if not file.exists():
            raise typer.BadParameter(f"File {file} does not exist")

        if layer is not None:
            layers = [layer]
        else:
            layers = [str(name) for name, _ in list_layers(file)]
            if not layers:
                raise typer.BadParameter(f"No layers found in {file}")

        if table is not None and (len(layers) > 1 or len(files) > 1):
            raise typer.BadParameter(
                "--table cannot be used with multiple files or layers; "
                "use --layer to pick one"
            )

        for name in layers:
            _load_layer(
                engine,
                file,
                name,
                schema=schema,
                table=table,
                single_layer=len(layers) == 1,
                srid=srid,
                keep_srid=keep_srid,
                source_srid=source_srid,
                geometry_column=geometry_column,
                promote_to_multi=promote_to_multi,
                no_index=no_index,
                where=where,
                replace=replace,
                append=append,
                dry_run=dry_run,
            )


def _load_layer(
    engine: Engine,
    file: Path,
    layer: str,
    *,
    schema: str,
    table: Optional[str] = None,
    single_layer: bool = True,
    srid: Optional[int] = None,
    keep_srid: bool = False,
    source_srid: Optional[int] = None,
    geometry_column: str = "geom",
    promote_to_multi: bool = False,
    no_index: bool = False,
    where: Optional[str] = None,
    replace: bool = False,
    append: bool = False,
    dry_run: bool = False,
):
    import geopandas as gpd

    if table is None:
        table = _table_name(file, layer, single_layer=single_layer)

    gdf = gpd.read_file(file, layer=layer, engine="pyogrio", where=where)

    if gdf.geometry.name is None or gdf.geometry.isna().all():
        log.warning("Layer %s has no usable geometry", layer)

    gdf, srid = _resolve_crs(
        gdf,
        srid=srid,
        keep_srid=keep_srid,
        source_srid=source_srid,
        label=f"{file}:{layer}",
    )

    if promote_to_multi:
        gdf = _promote(gdf)

    geom_type = _geometry_type(gdf, promote_to_multi=promote_to_multi)

    # Split geometry off, then run the attributes through exactly the same
    # inference and COPY path as load-csv.
    source_columns = [c for c in gdf.columns if c != gdf.geometry.name]
    attrs = polars_from_pandas(gdf.drop(columns=[gdf.geometry.name]))
    columns = dedupe([identifier(c) for c in source_columns])
    attrs.columns = columns

    types = [pg_type(dtype) for dtype in attrs.schema.values()]

    geom_col = identifier(geometry_column, fallback="geom")
    if geom_col in columns:
        raise typer.BadParameter(
            f"Attribute column '{geom_col}' collides with the geometry column; "
            "pass --geometry-column to rename it"
        )

    geom_declared = f"geometry({geom_type}, {srid})"

    if dry_run:
        print(
            render_ddl(
                engine,
                schema,
                table,
                columns + [geom_col],
                types + [geom_declared],
            )
        )
        return

    print(
        f"[dim]Loading[/] [bold cyan]{file}[/][dim]:[/][cyan]{layer}[/] [dim]→[/] "
        f"[bold green]{schema}.{table}[/] "
        f"[dim]({len(gdf)} features, {len(columns)} attributes, "
        f"{geom_type} @ {srid})[/]",
        file=stderr,
    )

    check_target(engine, schema, table, replace=replace, append=append)

    if not append:
        # The geometry column is created untyped, then constrained after the
        # COPY: hex WKB carries no SRID, so inserting straight into a
        # geometry(<type>, <srid>) column would fail the SRID check.
        create_table(
            engine,
            schema,
            table,
            columns + [geom_col],
            types + ["geometry"],
            replace=replace,
        )
        comment_original_names(engine, schema, table, source_columns, columns)

    # Hex WKB goes into the geometry column as text; PostGIS parses it on input.
    # Build the WKB column as a plain list: this sidesteps the pyarrow
    # requirement for pandas -> Polars, and lets us normalize missing
    # geometries, which to_wkb reports as a float NaN that pandas' own
    # notna() does not flag on its str dtype.
    wkb = [v if isinstance(v, str) else None for v in gdf.geometry.to_wkb(hex=True)]
    attrs = attrs.with_columns(pl.Series(geom_col, wkb, dtype=pl.String))

    n = copy_dataframe(engine, attrs, schema, table, columns + [geom_col])

    if not append:
        _apply_srid(engine, schema, table, geom_col, geom_type, srid)
        if not no_index:
            _create_index(engine, schema, table, geom_col)

    print(f"[dim]Copied[/] [bold green]{n}[/] [dim]features[/]", file=stderr)


def _table_name(file: Path, layer: str, *, single_layer: bool) -> str:
    """Name the table after the file, disambiguating by layer when needed"""
    stem = identifier(file.name.split(".")[0], fallback="table")
    layer_name = identifier(layer, fallback="layer")
    # A single-layer file usually names its layer after itself; don't stutter
    if single_layer or layer_name == stem:
        return stem
    return f"{stem}_{layer_name}"[:63]


def _resolve_crs(
    gdf,
    *,
    srid: Optional[int],
    keep_srid: bool,
    source_srid: Optional[int],
    label: str,
):
    """Settle the layer's CRS, reprojecting unless asked to keep it.

    Returns the frame together with the SRID its geometry is actually in, which
    is what the geometry column gets declared as.
    """
    if gdf.crs is None:
        if keep_srid and source_srid is None:
            raise typer.BadParameter(
                f"{label} has no CRS of its own to keep; "
                "pass --source-srid to declare one"
            )
        assumed = source_srid or srid or DEFAULT_SRID
        log.warning("%s has no CRS; assuming EPSG:%s", label, assumed)
        gdf = gdf.set_crs(epsg=assumed)
    elif source_srid is not None:
        gdf = gdf.set_crs(epsg=source_srid, allow_override=True)

    current = gdf.crs.to_epsg()

    if keep_srid:
        if current is None:
            raise typer.BadParameter(
                f"{label} has a CRS with no EPSG code, so it cannot be stored as "
                "a PostGIS SRID; drop --keep-srid to reproject, or pass "
                "--source-srid if you know the equivalent code"
            )
        return gdf, current

    target = srid or DEFAULT_SRID
    if current != target:
        log.info("Reprojecting %s from EPSG:%s to EPSG:%s", label, current, target)
        gdf = gdf.to_crs(epsg=target)
    return gdf, target


def _promote(gdf):
    """Promote single geometries to their Multi* equivalent"""
    from shapely.geometry import MultiLineString, MultiPoint, MultiPolygon

    wrappers = {
        "Point": MultiPoint,
        "LineString": MultiLineString,
        "Polygon": MultiPolygon,
    }

    def _wrap(geom):
        if geom is None:
            return None
        wrapper = wrappers.get(geom.geom_type)
        return wrapper([geom]) if wrapper else geom

    return gdf.set_geometry(gdf.geometry.map(_wrap), crs=gdf.crs)


def _geometry_type(gdf, *, promote_to_multi: bool) -> str:
    """Pick the narrowest PostGIS type that covers every feature in the layer"""
    present = {t for t in gdf.geom_type.dropna().unique()}
    if not present:
        return "Geometry"

    mapped = set()
    for t in present:
        name = _GEOM_TYPES.get(t)
        if name is None:
            return "Geometry"
        if promote_to_multi:
            name = _PROMOTE_TO_MULTI.get(name, name)
        mapped.add(name)

    if len(mapped) != 1:
        return "Geometry"

    geom_type = mapped.pop()
    # Preserve a Z dimension if every geometry carries one
    has_z = gdf.geometry.dropna().has_z
    if len(has_z) and bool(has_z.all()):
        geom_type += "Z"
    return geom_type


def _apply_srid(
    engine: Engine, schema: str, table: str, column: str, geom_type: str, srid: int
):
    """Constrain the geometry column and stamp the SRID onto its contents"""
    run_sql(
        engine,
        "ALTER TABLE {table} ALTER COLUMN {column} "
        "TYPE geometry(" + geom_type + ", " + str(srid) + ") "
        "USING ST_SetSRID({column}, " + str(srid) + ")",
        dict(
            table=Identifier(schema, table),
            column=Identifier(column),
        ),
        raise_errors=True,
    )


def _create_index(engine: Engine, schema: str, table: str, column: str):
    index = identifier(f"{table}_{column}_idx")
    run_sql(
        engine,
        "CREATE INDEX {index} ON {table} USING GIST ({column})",
        dict(
            index=Identifier(index),
            table=Identifier(schema, table),
            column=Identifier(column),
        ),
        raise_errors=True,
    )
