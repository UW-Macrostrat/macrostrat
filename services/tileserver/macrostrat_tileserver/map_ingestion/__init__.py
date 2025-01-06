from pathlib import Path

from buildpg import render, Renderer
from fastapi import APIRouter, Request, Response
from timvt.resources.enums import MimeTypes
from titiler.core.models.mapbox import TileJSON
from asyncpg import UndefinedTableError
from enum import Enum
from macrostrat.utils import get_logger
from macrostrat.database.utils import format as format_sql

print_sql_statements = False

router = APIRouter()
log = get_logger("uvicorn.error")

__here__ = Path(__file__).parent


class FeatureType(str, Enum):
    """Feature types."""

    polygons = "polygons"
    lines = "lines"
    points = "points"


@router.get(
    "/{slug}/tilejson.json",
    response_model=TileJSON,
    responses={200: {"description": "Return a tilejson"}},
    response_model_exclude_none=True,
)
async def tilejson(
    request: Request,
    slug: str,
):
    """Return TileJSON document."""
    url_path = request.url_for(
        "tile", **{"slug": slug, "z": "{z}", "x": "{x}", "y": "{y}"}
    )

    tile_endpoint = str(url_path)

    bounds_query = f"""
    SELECT geom FROM sources.{slug}_polygons
    UNION
    SELECT geom FROM sources.{slug}_lines
    UNION
    SELECT geom FROM sources.{slug}_points
    """

    sql = get_bounds(bounds_query, geometry_column="geom")
    pool = request.app.state.pool
    async with pool.acquire() as con:
        bounds = await con.fetchval(sql)

    return {
        "minzoom": 0,
        "maxzoom": 18,
        "name": slug,
        "bounds": bounds,
        "tiles": [tile_endpoint],
    }


@router.get("/{slug}/{z}/{x}/{y}")
async def tile(
    request: Request,
    slug: str,
    z: int,
    x: int,
    y: int,
):

    # if feature_type != FeatureType.polygons:
    #    return Response(status_code=404, content="Only polygons are supported for now")

    """Get a tile from the tileserver."""
    pool = request.app.state.pool

    data = b""
    success = False
    for layer in FeatureType:
        try:
            data += await get_layer(pool, slug, layer, z=z, x=x, y=y)
            success = True
        except UndefinedTableError:
            pass
    if not success:
        return Response(status_code=404, content=f"No tables found for {slug}")

    kwargs = {}
    kwargs.setdefault("media_type", MimeTypes.pbf.value)
    return Response(data, **kwargs)


async def get_layer(pool, slug, layer: FeatureType, **params):
    async with pool.acquire() as con:
        table_name = f"{slug}_{layer}"
        alias = "s"
        column_names = await get_table_columns(con, table_name, schema="sources")
        columns = [
            alias + "." + _wrap_with_quotes(i) for i in column_names if i != "geom"
        ]
        columns.append("tile_layers.tile_geom(s.geom, :envelope) AS geometry")

        joins = None
        if layer == FeatureType.polygons:
            joins = [
                "LEFT JOIN macrostrat.intervals i0 ON s.b_interval = i0.id",
                "LEFT JOIN macrostrat.intervals i1 ON s.t_interval = i1.id",
            ]

            b_age = "i0.age_bottom"
            t_age = "i1.age_top"
            # Eventually we will allow b_age and t_age to be set directly
            # b_age = "coalesce(s.b_age, i0.age_bottom)"
            # t_age = "coalesce(s.t_age, i1.age_top)"
            columns += [
                b_age + " AS b_age",
                t_age + " AS t_age",
                _color_subquery(b_age, t_age, "color"),
            ]

        return await run_layer_query(
            con,
            f"sources.{table_name}",
            columns,
            joins=joins,
            table_alias=alias,
            layer_name=f"{layer}",
            **params,
        )


def _color_subquery(b_age, t_age, alias):
    return f"""(
    SELECT interval_color
      FROM macrostrat.intervals
      WHERE age_top <= {t_age} AND age_bottom >= {b_age}
      ORDER BY age_bottom - age_top
      LIMIT 1
    ) AS {alias}"""


async def run_layer_query(
    con,
    table_name,
    columns,
    *,
    joins=None,
    layer_name="default",
    table_alias=None,
    **params,
):
    _cols = ", ".join(columns)
    query = f"SELECT {_cols} FROM {table_name}"
    if table_alias:
        query += f" AS {table_alias}"

    if joins:
        query += "\n" + "\n".join(joins)

    query = extend_sql(query)
    params = dict(layer_name=layer_name, **params)

    if print_sql_statements:
        log.debug(
            "Running query:\n%s\nParameters: %s",
            format_sql(query, reindent=True),
            params,
        )

    q, p = render(query, **params)

    return await con.fetchval(q, *p)


def _wrap_with_quotes(col):
    if col[0] == '"' and col[-1] == '"':
        col = col[1:-1]
    if '"' in col:
        col = col.replace('"', '""')
    return '"' + col + '"'


def extend_sql(sql):
    q = sql.strip()
    if q.endswith(";"):
        q = q[:-1]

    # Replace the envelope with the function call. Kind of awkward.
    q = q.replace(":envelope", "tile_utils.envelope(:x, :y, :z)")

    # Wrap with MVT creation
    return f"WITH feature_query AS ({q}) SELECT ST_AsMVT(feature_query, :layer_name, 4096, 'geometry') FROM feature_query"


def get_bounds(base_query, geometry_column="geometry"):
    return f"""WITH b AS (
        SELECT ST_Union(a.{geometry_column}::box2d)::box2d env
        FROM ({base_query}) a
    )
    SELECT ARRAY[ST_XMin(env), ST_YMin(env), ST_XMax(env), ST_YMax(env)]
    FROM b;
    """


async def get_table_columns(con, table, schema="sources"):
    base_sql = f"""
    SELECT array_agg(column_name)
    FROM information_schema.columns
    WHERE table_name = :table
    AND table_schema = :schema;
    """

    q, p = render(base_sql, table=table, schema=schema)
    res = await con.fetchval(q, *p)
    if res is None:
        raise UndefinedTableError(f"Table {schema}.{table} not found")

    return res


def register_map_ingestion_routes(app):
    app.include_router(router, tags=["Map ingestion"], prefix="/ingestion")
