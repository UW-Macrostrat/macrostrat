from os import environ
from typing import Callable, Awaitable

from fastapi import BackgroundTasks, HTTPException
from fastapi import Request
from macrostrat.database import Database
from macrostrat.tileserver_utils import (
    get_cached_tile,
    set_cached_tile,
    TileParams,
    TileResponse,
    CacheStatus,
    CacheMode,
    CacheArgs,
)
from macrostrat.utils import get_logger
from macrostrat.utils.timer import Timer
from mapnik import Map, load_map_from_string, Image, render, Box2d
from morecantile import tms

from .config import scales, scale_for_zoom
from .mapnik_styles import make_mapnik_xml
from .pool import MapnikMapPool

log = get_logger(__name__)

db_url = environ.get("DATABASE_URL")

db = Database(db_url)


async def get_image_tile(request: Request, args: CacheArgs) -> bytes:
    pool: MapnikMapPool = request.app.state.map_pool
    tile = args.tile

    quad = tms.get("WebMercatorQuad")
    bbox = quad.xy_bounds(tile)

    # Get map scale for this zoom level
    # For some reason, the scale is one less than expected
    scale = scale_for_zoom(tile.z)
    box = Box2d(bbox.left, bbox.top, bbox.right, bbox.bottom)

    async with pool.map_context(scale) as _map:

        _map.zoom_to_box(box)

        # Render map to image
        im = Image(512, 512)
        render(_map, im, 2)
        # Return image as binary
        return im.tostring("png")


async def handle_tile_request(
    request: Request,
    background_tasks: BackgroundTasks,
    get_tile: Callable[[Request, CacheArgs], Awaitable[bytes]],
    args: CacheArgs,
) -> TileResponse:
    """Return vector tile."""
    pool = request.app.state.pool

    timer = Timer()

    # If cache is not bypassed and the tile is in the cache, return it
    if args.mode != CacheMode.bypass:
        content = await get_cached_tile(pool, args)
        timer._add_step("check_cache")
        if content is not None:
            return TileResponse(
                content, timer, cache_status=CacheStatus.hit, media_type=args.media_type
            )

    # If the cache is forced and the tile is not in the cache, return a 404
    if args.mode == CacheMode.force:
        raise HTTPException(
            status_code=404,
            detail="Tile not found in cache",
            header={
                "Server-Timing": timer.server_timings(),
                "X-Tile-Cache": CacheStatus.miss,
            },
        )

    content = await get_tile(request, args)
    timer._add_step("get_tile")

    if args.mode != CacheMode.bypass:
        background_tasks.add_task(set_cached_tile, pool, args, content)

    return TileResponse(
        content, timer, cache_status=CacheStatus.miss, media_type=args.media_type
    )
