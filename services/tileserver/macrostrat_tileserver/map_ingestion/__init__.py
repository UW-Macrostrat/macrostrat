from pathlib import Path

from buildpg import render, Renderer
from fastapi import APIRouter, Request, Response
from timvt.resources.enums import MimeTypes
from titiler.core.models.mapbox import TileJSON
from pydantic import BaseModel
from enum import Enum
from macrostrat.utils import get_logger
from typing import Optional

router = APIRouter()
log = get_logger("uvicorn.error")

__here__ = Path(__file__).parent


class FeatureType(str, Enum):
    """Feature types."""

    polygons = "polygons"
    lines = "lines"
    points = "points"


class ColumnNameInformation(BaseModel):
    polygon_columns: Optional[list[str]]
    line_columns: Optional[list[str]]
    point_columns: Optional[list[str]]


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

    sql = get_bounds(f"SELECT * FROM sources.{slug}_polygons", geometry_column="geom")
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


async def get_column_name_information(pool, slug) -> ColumnNameInformation:
    polygon_table = f"{slug}_polygons"
    line_table = f"{slug}_lines"
    point_table = f"{slug}_points"
    names = await get_column_names(
        pool, polygon_table, line_table, point_table, schema="sources"
    )
    return ColumnNameInformation(
        polygon_columns=names[polygon_table],
        line_columns=names[line_table],
        point_columns=names[point_table],
    )


def get_bounds(base_query, geometry_column="geometry"):
    return f"""WITH b AS (
        SELECT ST_Union(a.{geometry_column}::box2d)::box2d env
        FROM ({base_query}) a
    )
    SELECT ARRAY[ST_XMin(env), ST_YMin(env), ST_XMax(env), ST_YMax(env)]
    FROM b;
    """


async def get_column_names(pool, *tables, schema="sources"):
    base_sql = f"""
    SELECT array_agg(column_name)
    FROM information_schema.columns
    WHERE table_name = :table
    AND table_schema = :schema;
    """

    res = {}
    async with pool.acquire() as con:
        for table in tables:
            q, p = render(base_sql, table=table, schema=schema)
            columns = await con.fetchval(q, *p)
            res[table] = columns
    return res


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

    column_names = await get_column_name_information(pool, slug)

    async with pool.acquire() as con:
        data = await run_layer_query(
            con,
            slug,
            column_names,
            z=z,
            x=x,
            y=y,
        )
    kwargs = {}
    kwargs.setdefault("media_type", MimeTypes.pbf.value)
    return Response(data, **kwargs)


async def run_layer_query(con, slug, column_names: ColumnNameInformation, **params):
    layer_name = "polygons"

    cols = [_wrap_with_quotes(i) for i in column_names.polygon_columns if i != "geom"]
    cols.append("tile_layers.tile_geom(geom, :envelope) AS geometry")
    cols = ", ".join(cols)
    query = f"SELECT :cols FROM sources.{slug}_polygons".replace(":cols", cols)
    query = extend_sql(query, layer_name)

    q, p = render(query, layer_name=layer_name, **params)

    log.info(q, p)

    return await con.fetchval(q, *p)


def _wrap_with_quotes(col):
    if col[0] == '"' and col[-1] == '"':
        col = col[1:-1]
    if '"' in col:
        col = col.replace('"', '""')
    return '"' + col + '"'


def extend_sql(sql, layer_name):
    q = sql.strip()
    if q.endswith(";"):
        q = q[:-1]

    # Replace the envelope with the function call. Kind of awkward.
    q = q.replace(":envelope", "tile_utils.envelope(:x, :y, :z)")

    # Wrap with MVT creation
    return f"WITH feature_query AS ({q}) SELECT ST_AsMVT(feature_query, :layer_name, 4096, 'geometry') FROM feature_query"


def register_map_ingestion_routes(app):
    app.include_router(router, tags=["Map ingestion"], prefix="/ingestion")
