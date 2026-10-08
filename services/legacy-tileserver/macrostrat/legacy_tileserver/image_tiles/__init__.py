from os import environ
from typing import Optional

from fastapi import Request
from mapnik import Box2d, Image, render
from morecantile import tms

from macrostrat.tileserver_utils import CachedTileArgs
from macrostrat.utils import get_logger

from .pool import MapnikMapPool

log = get_logger(__name__)

db_url = environ.get("DATABASE_URL")


# The maps a raster tile draws, as the vector route names them in
# `X-Macrostrat-Sources`: resolved maps whose faces meet the tile envelope.
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


async def tile_sources(request: Request, tile) -> Optional[str]:
    """The `X-Macrostrat-Sources` header value for a tile, or None."""
    bands = request.app.state.bands
    layer_id = bands.layer_for_zoom(tile.z)
    if layer_id is None:
        return None
    async with request.app.state.pool.acquire() as conn:
        ids = await conn.fetchval(SOURCES_QUERY, layer_id, tile.x, tile.y, tile.z)
    if not ids:
        return None
    return ",".join(str(i) for i in ids)


async def get_image_tile(request: Request, args: CachedTileArgs) -> bytes:
    pool: MapnikMapPool = request.app.state.map_pool
    tile = args.tile
    scale = request.app.state.bands.scale_for_zoom(tile.z)

    # TODO: tune PostGIS data sources
    # https://github.com/mapnik/mapnik/wiki/PostGIS

    async with pool.map_context(scale) as _map:
        return render_tile(_map, tile)


def render_tile(_map, tile) -> bytes:
    """Draw one Web Mercator tile of a Mapnik map as a 512 px PNG."""
    quad = tms.get("WebMercatorQuad")
    bbox = quad.xy_bounds(tile)
    _map.zoom_to_box(Box2d(bbox.left, bbox.top, bbox.right, bbox.bottom))

    im = Image(512, 512)
    render(_map, im, 2)
    return im.tostring("png")
