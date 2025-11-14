from os import environ

from fastapi import Request
from mapnik import Box2d, Image, render
from morecantile import tms

from macrostrat.database import Database
from macrostrat.tileserver_utils import CachedTileArgs
from macrostrat.utils import get_logger

from .config import scale_for_zoom, scales
from .mapnik_styles import make_mapnik_xml
from .pool import MapnikMapPool

log = get_logger(__name__)

db_url = environ.get("DATABASE_URL")

db = Database(db_url)


async def get_image_tile(request: Request, args: CachedTileArgs) -> bytes:
    pool: MapnikMapPool = request.app.state.map_pool
    tile = args.tile

    quad = tms.get("WebMercatorQuad")
    bbox = quad.xy_bounds(tile)

    # Get map scale for this zoom level
    # For some reason, the scale is one less than expected
    scale = scale_for_zoom(tile.z)
    box = Box2d(bbox.left, bbox.top, bbox.right, bbox.bottom)

    # TODO: tune PostGIS data sources
    # https://github.com/mapnik/mapnik/wiki/PostGIS

    async with pool.map_context(scale) as _map:

        _map.zoom_to_box(box)

        # Render map to image
        im = Image(512, 512)
        render(_map, im, 2)

        # Return image as binary
        res = im.tostring("png")
        return res
