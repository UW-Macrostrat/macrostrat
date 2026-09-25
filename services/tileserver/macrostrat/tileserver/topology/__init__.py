import json
from pathlib import Path
from typing import Any

from buildpg import render
from fastapi import APIRouter, HTTPException, Request

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
async def get_tile(
    request: Request,
    z: int,
    x: int,
    y: int,
    map_layer: str = None,
    level: str = "member",
):
    """Solved faces for a compilation.

    `map_layer` is any source slug -- `bc-surface` is as addressable as
    `carto-large`. Faces are attributed to the member of the compilation they
    belong to (`level=member`, the default) or to the map that actually owns them
    (`level=map`).
    """
    _check_level(level)
    sql = get_query("map-faces")
    if map_layer is None:
        sql = get_query("map-face-primitives")
        return await _render_tile(request, sql, z=z, x=x, y=y, map_layer=map_layer)

    return await _render_tile(
        request, sql, z=z, x=x, y=y, map_layer=map_layer, level=level
    )


@router.get("/maps/{z}/{x}/{y}")
@router.get("/maps/{map_layer}/{z}/{x}/{y}")
async def get_tile(
    request: Request,
    z: int,
    x: int,
    y: int,
    map_layer: str = None,
    level: str = "member",
):
    """Bounds of a compilation's members.

    The members the compilation presents (`level=member`, the default), or the
    maps at the bottom that it ultimately resolves to (`level=map`).
    """
    _check_level(level)
    if map_layer is None:
        return await _render_tile(
            request, get_query("all-maps"), z=z, x=x, y=y, map_layer=map_layer
        )
    return await _render_tile(
        request, get_query("maps"), z=z, x=x, y=y, map_layer=map_layer, level=level
    )


def _check_level(level: str):
    if level not in ("member", "map"):
        raise HTTPException(400, "level must be 'member' or 'map'")


async def _render_tile(request: Request, sql: str, **query_params: Any):
    pool = request.app.state.pool
    query, params = render(sql, **query_params)
    async with pool.acquire() as con:
        data = await con.fetchval(query, *params)
        return VectorTileResponse(data, headers={"cache-control": "no-cache"})


GET_MAP_LAYERS = """
SELECT ml.id,
    ml.name,
    ml.description,
    ml.parent,
    map_bounds.composite_layer_members(ml.id) AS composited_from,
    ml.slug,
    ml.min_zoom,
    ml.max_zoom
FROM map_bounds.map_layer ml
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

    Returns one row per source of the membership tree covering the point --
    every compilation *and* every member, whether or not the compilation has been
    materialized -- ordered by descending priority within each registered
    compilation. Nothing is chosen server-side; flags describe each row so a
    client can filter or build the tree as it needs:

    - ``is_compilation`` -- has members.
    - ``is_materialized`` -- holds polygons of its own: an ordinary map, or a
      compilation once materialized (or, as SGMC, holding them as originals).
    - ``is_derived`` -- those polygons are a cache cut from its members'. This is
      the row to mark in a UI. False for SGMC, whose polygons are originals.
    - ``member_id`` -- the member of the registered compilation this row belongs
      to; the level the ``maps`` and ``faces`` tiles draw by default, so the row
      whose ``member_id`` is its own ``source_id`` matches a clicked feature.

    ``map_face_id`` is that row's own solved face, null where the location isn't
    covered by a built face (as for the members of a materialized compilation,
    which are no longer in the topology).
    """
    sql = get_query("info")
    # ``::layer_filter`` is a raw template slot filled in here, before buildpg
    # renders the value parameters (:lng, :lat, :map_layer) below. It prunes the
    # walk at its roots rather than filtering the results.
    if map_layer is None:
        sql = sql.replace("::layer_filter", "true")
    else:
        sql = sql.replace("::layer_filter", "ml.slug = :map_layer")

    query, params = render(sql, lng=lng, lat=lat, map_layer=map_layer)
    async with request.app.state.pool.acquire() as con:
        rows = await con.fetch(query, *params)
        return [dict(row) for row in rows]


@router.get("/errors")
async def get_errors(request: Request, map_layer: str = None):
    """Topology-solving errors as a GeoJSON FeatureCollection.

    Each feature is a `map_topo` face whose insertion into the topology failed
    (``topology_error`` is set); properties carry the source map id/name/slug
    and the error text. Optionally filtered to a single map layer by slug.
    """
    sql = get_query("errors")
    # ``::map_layer_filter`` is a raw template slot filled before buildpg renders
    # the value parameters.
    if map_layer is None:
        sql = sql.replace("::map_layer_filter", "true")
    else:
        sql = sql.replace("::map_layer_filter", "ml.slug = :map_layer")

    query, params = render(sql, map_layer=map_layer)
    async with request.app.state.pool.acquire() as con:
        data = await con.fetchval(query, *params)
    # asyncpg may hand back json as text depending on codec config.
    if isinstance(data, str):
        data = json.loads(data)
    return data
