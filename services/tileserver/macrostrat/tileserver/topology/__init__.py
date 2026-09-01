import json
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
async def get_tile(
    request: Request,
    z: int,
    x: int,
    y: int,
    map_layer: str = None,
    expand: bool = False,
):
    """Solved faces for a compilation.

    `map_layer` is any compilation slug, not only a served layer -- `bc-surface`
    is as addressable as `carto-large`. Faces are attributed to the direct member
    they are reached through; `expand=true` attributes them to the map that
    actually owns them.
    """
    sql = get_query("map-faces")
    if map_layer is None:
        sql = get_query("map-face-primitives")
        return await _render_tile(request, sql, z=z, x=x, y=y, map_layer=map_layer)

    return await _render_tile(
        request, sql, z=z, x=x, y=y, map_layer=map_layer, expand=expand
    )


@router.get("/maps/{z}/{x}/{y}")
@router.get("/maps/{map_layer}/{z}/{x}/{y}")
async def get_tile(
    request: Request,
    z: int,
    x: int,
    y: int,
    map_layer: str = None,
    expand: bool = False,
):
    """Footprints of a compilation's members.

    Direct members by default -- what the compilation is assembled from --
    or, with `expand=true`, the maps it ultimately resolves to.
    """
    if map_layer is None:
        return await _render_tile(
            request, get_query("all-maps"), z=z, x=x, y=y, map_layer=map_layer
        )
    return await _render_tile(
        request, get_query("maps"), z=z, x=x, y=y, map_layer=map_layer, expand=expand
    )


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

    Returns one row per node of the compilation hierarchy covering the point --
    every compilation *and* every constituent, whether or not the compilation has
    been materialized -- ordered by descending priority within each layer. Nothing
    is chosen server-side; flags describe each row so a client can filter or build
    the tree as it needs:

    - ``is_composite`` -- the map is assembled from members.
    - ``holds_polygons`` -- the map has polygons of its own, so resolution stops
      here. True for an ordinary map, and for a compilation once it is solved.
    - ``is_materialized`` -- a composite that holds polygons: the compilation that
      *replaced* its constituents. This is the row to mark in a UI.
    - ``is_unit`` -- the level the ``maps`` and ``faces`` tiles are drawn at by
      default, so this is the row matching a clicked feature.
    - ``is_constituent`` -- the map is presented as some compilation above it.

    ``map_face_id`` is that row's own solved face, null where the location isn't
    covered by a built face for the layer (as for the constituents of a
    materialized compilation, which are no longer in the topology).
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
