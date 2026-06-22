from pathlib import Path

from buildpg import render
from fastapi import APIRouter, Request

from macrostrat.tileserver_utils import VectorTileResponse

from ..utils import get_sql


__here__ = Path(__file__).parent

router = APIRouter()


@router.get("/elements/{z}/{x}/{y}")
@router.get("/elements/{map_layer}/{z}/{x}/{y}")
async def get_tile(request: Request, z: int, x: int, y: int, map_layer: str = None):
    """Get a tile from the tileserver."""
    pool = request.app.state.pool

    sql_file = "topo-primitives.sql"
    if map_layer is not None:
        sql_file = "topo-primitives-by-map-layer.sql"

    sql = get_sql(__here__ / sql_file)
    query, params = render(sql, z=z, x=x, y=y, map_layer=map_layer)

    async with pool.acquire() as con:
        data = await con.fetchval(query, *params)
        return VectorTileResponse(data, headers={"cache-control": "no-cache"})


@router.get("/faces/{map_layer}/{z}/{x}/{y}")
async def get_tile(request: Request, z: int, x: int, y: int, map_layer: str = None):
    """Get a tile from the tileserver."""
    pool = request.app.state.pool

    sql = get_sql(__here__ / "map-faces.sql")
    query, params = render(sql, z=z, x=x, y=y, map_layer=map_layer)

    async with pool.acquire() as con:
        data = await con.fetchval(query, *params)
        return VectorTileResponse(data, headers={"cache-control": "no-cache"})


@router.get("/maps/{z}/{x}/{y}")
@router.get("/maps/{map_layer}/{z}/{x}/{y}")
async def get_tile(request: Request, z: int, x: int, y: int, map_layer: str = None):
    """All maps associated with the map layer"""
    pool = request.app.state.pool

    sql_file = "all-maps.sql"
    if map_layer is not None:
        sql_file = "maps.sql"

    sql = get_sql(__here__ / sql_file)
    query, params = render(sql, z=z, x=x, y=y, map_layer=map_layer)

    async with pool.acquire() as con:
        data = await con.fetchval(query, *params)
        return VectorTileResponse(data, headers={"cache-control": "no-cache"})


GET_MAP_LAYERS = """
SELECT id,
    name,
    description,
    parent,
    composited_from,
    slug,
    min_zoom,
    max_zoom
FROM map_bounds.map_layer
"""


@router.get("/layers")
async def get_layers(request: Request):
    """Get a list of all map layers"""
    pool = request.app.state.pool
    async with pool.acquire() as con:
        data = await con.fetch(GET_MAP_LAYERS)
        # Kind of silly to not do better with conversion
        return [dict(row) for row in data]
