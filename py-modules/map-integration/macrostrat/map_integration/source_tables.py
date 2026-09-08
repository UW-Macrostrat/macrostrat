"""Create `sources.*` staging tables carrying Macrostrat's standard columns.

`prepare_fields` brings a table that *already exists* -- one `ogr2ogr` built from
a GIS file -- up to the current standard. Data that arrives any other way (out of
another database, an API, a hand-built extract) needs the same table with no file
to derive it from, and there was no way to get one.

The column specs live here rather than beside the updaters so that both paths --
create-from-nothing and bring-up-to-standard -- read a single definition.
"""

from typing import Iterable, Mapping

from psycopg.sql import SQL, Identifier

__all__ = [
    "COLUMN_SPECS",
    "GEOMETRY_TYPES",
    "LINE_COLUMNS",
    "POINT_COLUMNS",
    "POLYGON_COLUMNS",
    "common_columns",
    "create_source_table",
    "create_source_tables",
]

common_columns = {
    "source_id": "integer",
    "orig_id": "integer",
    "omit": "boolean",
}

POLYGON_COLUMNS = {
    **common_columns,
    "name": "text",
    "strat_name": "text",
    "age": "text",
    "lith": "text",
    "descrip": "text",
    "comments": "text",
    "t_interval": "integer",
    "b_interval": "integer",
    "color": "text",
    "unit_label": "text",
    "fill_pattern": "text",
}

LINE_COLUMNS = {
    **common_columns,
    "descrip": "text",
    "comments": "text",
    "name": "character varying(255)",
    "type": "character varying(100)",
    "direction": "character varying(20)",
    "certainty": "character varying(100)",
}

POINT_COLUMNS = {
    **common_columns,
    "descrip": "text",
    "comments": "text",
    "strike": "integer",
    "dip": "integer",
    "dip_dir": "integer",
    "point_type": "character varying(100)",
    "certainty": "character varying(100)",
}

COLUMN_SPECS = {
    "polygons": POLYGON_COLUMNS,
    "lines": LINE_COLUMNS,
    "points": POINT_COLUMNS,
}

# `maps.polygons`, `maps.lines` and `maps.points` are single-geometry-type
# tables, so a staging table that admits both a POLYGON and a MULTIPOLYGON just
# defers the cast. Stage as multi and let the loader call `ST_Multi`.
GEOMETRY_TYPES = {
    "polygons": "MultiPolygon",
    "lines": "MultiLineString",
    "points": "Point",
}


def create_source_table(
    db,
    slug: str,
    kind: str,
    *,
    schema: str = "sources",
    extra_columns: Mapping[str, str] | None = None,
    srid: int = 4326,
) -> str:
    """Create one `<schema>.<slug>_<kind>` table at the current standard.

    `kind` is `polygons`, `lines` or `points`. `extra_columns` adds
    source-specific fields the standard has no home for -- an ingestion should
    keep what the source shipped rather than discard it at the staging boundary,
    even where the `maps` schema has nowhere to put it yet.

    An `extra_columns` name that collides with a standard one overrides its type,
    which is how a source with a wider `orig_id` is accommodated. Creation is not
    guarded: staging over a table that already exists is a mistake worth hearing
    about.
    """
    if kind not in COLUMN_SPECS:
        raise ValueError(
            f"Unknown table kind {kind!r}; expected one of {', '.join(COLUMN_SPECS)}"
        )

    table_name = f"{slug}_{kind}"
    table = Identifier(schema, table_name)
    columns = {**COLUMN_SPECS[kind], **(extra_columns or {})}

    definitions = [SQL("_pkid serial PRIMARY KEY")]
    for name, type_ in columns.items():
        definitions.append(SQL(" ").join([Identifier(name), SQL(type_)]))
    definitions.append(
        SQL("geom geometry({}, {})").format(SQL(GEOMETRY_TYPES[kind]), SQL(str(srid)))
    )

    db.run_sql(
        "CREATE TABLE {table} ({definitions})",
        dict(table=table, definitions=SQL(", ").join(definitions)),
    )
    # The two indexes every consumer of a staging table needs: `copy_to_maps`
    # filters on `source_id`, and anything spatial wants the geometry index.
    db.run_sql(
        "CREATE INDEX ON {table} USING GIST (geom)",
        dict(table=table),
    )
    db.run_sql(
        "CREATE INDEX ON {table} (source_id)",
        dict(table=table),
    )
    return f"{schema}.{table_name}"


def create_source_tables(
    db,
    slug: str,
    *,
    kinds: Iterable[str] = ("polygons", "lines", "points"),
    schema: str = "sources",
    extra_columns: Mapping[str, Mapping[str, str]] | None = None,
    srid: int = 4326,
) -> list[str]:
    """Create the staging tables for a source, returning their qualified names.

    `extra_columns` is keyed by kind, so one call can give polygons and lines
    different source-specific fields.
    """
    extra = extra_columns or {}
    return [
        create_source_table(
            db,
            slug,
            kind,
            schema=schema,
            extra_columns=extra.get(kind),
            srid=srid,
        )
        for kind in kinds
    ]
