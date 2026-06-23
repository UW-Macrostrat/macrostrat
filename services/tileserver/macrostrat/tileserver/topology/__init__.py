from pathlib import Path
from typing import Any

from buildpg import render
from fastapi import APIRouter, Request

from macrostrat.tileserver_utils import VectorTileResponse

from ..utils import get_sql


__here__ = Path(__file__).parent

router = APIRouter()


def get_query(name):
    return get_sql(__here__ / "queries" / (name + ".sql"))


@router.get("/elements/{z}/{x}/{y}")
@router.get("/elements/{map_layer}/{z}/{x}/{y}")
async def get_tile(request: Request, z: int, x: int, y: int, map_layer: str = None):
    """Get a tile from the tileserver."""
    name = "topo-primitives"
    if map_layer is not None:
        name += "-by-map-layer"

    sql = get_query(name)
    return await _render_tile(request, sql, z=z, x=x, y=y, map_layer=map_layer)


@router.get("/faces/{z}/{x}/{y}")
@router.get("/faces/{map_layer}/{z}/{x}/{y}")
async def get_tile(request: Request, z: int, x: int, y: int, map_layer: str = None):
    """Get a tile from the tileserver."""
    sql = get_query("map-faces")
    if map_layer is None:
        sql = get_query("map-face-primitives")

    return await _render_tile(request, sql, z=z, x=x, y=y, map_layer=map_layer)


@router.get("/maps/{z}/{x}/{y}")
@router.get("/maps/{map_layer}/{z}/{x}/{y}")
async def get_tile(request: Request, z: int, x: int, y: int, map_layer: str = None):
    """All maps associated with the map layer"""
    query = "maps"
    if map_layer is None:
        query = "all-maps"
    sql = get_query(query)
    return await _render_tile(request, sql, z=z, x=x, y=y, map_layer=map_layer)


async def _render_tile(request: Request, sql: str, **query_params: Any):
    pool = request.app.state.pool
    query, params = render(sql, **query_params)
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


@router.get("/info")
async def get_info(
    request: Request,
    lng: float,
    lat: float,
    map_layer: str = None,
):
    """Get information about the maps and topological faces at a location.

    Returns one row per map covering the point, ordered by descending priority.
    ``map_face_id`` is null where the location isn't covered by a built
    topological face for the corresponding layer.
    """
    sql = get_query("info")
    # ``::where_clauses`` is a raw template slot filled in here, before buildpg
    # renders the value parameters (:lng, :lat, :map_layer) below.
    if map_layer is None:
        sql = sql.replace("::where_clauses", "true")
    else:
        sql = sql.replace("::where_clauses", "ml.slug = :map_layer")

    query, params = render(sql, lng=lng, lat=lat, map_layer=map_layer)
    async with request.app.state.pool.acquire() as con:
        rows = await con.fetch(query, *params)
        return [dict(row) for row in rows]
