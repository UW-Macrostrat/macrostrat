from os import environ
from typing import Optional

from fastapi import Request
from mapnik import Box2d, Image, render
from morecantile import tms

from macrostrat.tileserver_utils import CachedTileArgs, RenderedTile
from macrostrat.utils import get_logger

from .pool import MapnikMapPool

log = get_logger(__name__)

db_url = environ.get("DATABASE_URL")


# The maps a raster tile draws, as the vector route names them in
# `X-Macrostrat-Sources`: resolved maps whose faces meet the tile envelope.
# Asked once per render; the cache keeps the answer beside the tile.
SOURCES_QUERY = """
SELECT array_agg(m.map_id ORDER BY m.map_id)
FROM (
  SELECT DISTINCT mf.map_id
  FROM map_bounds_topology.map_face mf
  WHERE mf.map_layer = $1
    AND ST_Intersects(mf.geometry, tile_layers.geographic_envelope($2, $3, $4, 0.01))
) m
WHERE map_bounds.has_content(m.map_id)
"""


async def tile_sources(request: Request, tile) -> Optional[list]:
    """The maps a tile draws, or None for a band carto has no member for."""
    layer_id = request.app.state.bands.layer_for_zoom(tile.z)
    if layer_id is None:
        return None
    async with request.app.state.pool.acquire() as conn:
        return await conn.fetchval(SOURCES_QUERY, layer_id, tile.x, tile.y, tile.z)


async def get_image_tile(request: Request, args: CachedTileArgs) -> RenderedTile:
    pool: MapnikMapPool = request.app.state.map_pool
    tile = args.tile
    scale = request.app.state.bands.scale_for_zoom(tile.z)

    # TODO: tune PostGIS data sources
    # https://github.com/mapnik/mapnik/wiki/PostGIS

    async with pool.map_context(scale) as _map:
        content = render_tile(_map, tile)
    return RenderedTile(content, await tile_sources(request, tile))


def render_tile(_map, tile) -> bytes:
    """Draw one Web Mercator tile of a Mapnik map as a 512 px PNG."""
    quad = tms.get("WebMercatorQuad")
    bbox = quad.xy_bounds(tile)
    _map.zoom_to_box(Box2d(bbox.left, bbox.top, bbox.right, bbox.bottom))

    im = Image(512, 512)
    render(_map, im, 2)
    return im.tostring("png")
