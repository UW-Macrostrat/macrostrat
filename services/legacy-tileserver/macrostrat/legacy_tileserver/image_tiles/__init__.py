from os import environ

import buildpg
from fastapi import Depends, BackgroundTasks, HTTPException
from fastapi import Request
from macrostrat.database import Database
from macrostrat.utils import get_logger
from macrostrat.utils.timer import Timer
from mapnik import Map, load_map_from_string, Image, render, Box2d
from morecantile import Tile, tms

from .config import scales, scale_for_zoom
from .mapnik_styles import make_mapnik_xml
from .pool import MapnikMapPool
from ..cache import get_tile_from_cache, set_cached_tile
from ..utils import TileParams, TileResponse, CacheStatus, CacheMode

log = get_logger(__name__)

db_url = environ.get("DATABASE_URL")

db = Database(db_url)


class ImageTileSubsystem:
    """Macrostrat's image tile subsystem allows image tiles to be generated using Mapnik.
    It is considered a legacy feature, and is not recommended for new applications.
    The Mapnik dependency is difficult to build, and is available in the Docker image
    but not for Poetry-based installations.

    This "v2" implementation of the image tile system replaces the much less efficient "v1" version
    that was implemented in NodeJS.
    """

    layer_cache = {}
    layer_name: str = "carto-tile"
    cache_profile_id: int = None

    async def get_tile(self, pool: MapnikMapPool, tile: Tile, tms) -> bytes:
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

    async def get_cache_profile_id(self, pool):
        if self.cache_profile_id is not None:
            return self.cache_profile_id
        # Set the cache profile id from the database
        async with pool.acquire() as conn:
            q, p = buildpg.render(
                "SELECT id FROM tile_cache.profile WHERE name = :layer",
                layer=self.layer_name,
            )
            res = await conn.fetchval(q, *p)
            self.cache_profile_id = res
            return res

    async def handle_tile_request(
        self,
        request: Request,
        background_tasks: BackgroundTasks,
        tile: Tile = Depends(TileParams),
        cache: CacheMode = CacheMode.prefer,
    ):
        """Return vector tile."""
        pool = request.app.state.pool

        timer = Timer()

        cache_id = await self.get_cache_profile_id(pool)

        # If cache is not bypassed and the tile is in the cache, return it
        if cache != CacheMode.bypass:
            content = await get_tile_from_cache(pool, cache_id, None, tile)
            timer._add_step("check_cache")
            if content is not None:
                return TileResponse(
                    content, timer, cache_status=CacheStatus.hit, media_type="image/png"
                )

        # If the cache is forced and the tile is not in the cache, return a 404
        if cache == CacheMode.force:
            raise HTTPException(
                status_code=404,
                detail="Tile not found in cache",
                header={
                    "Server-Timing": timer.server_timings(),
                    "X-Tile-Cache": CacheStatus.miss,
                },
            )

        map_pool = request.app.state.map_pool
        content = await self.get_tile(map_pool, tile, tms)
        timer._add_step("get_tile")

        if cache != CacheMode.bypass:
            background_tasks.add_task(
                set_cached_tile, pool, cache_id, None, tile, content
            )

        return TileResponse(
            content, timer, cache_status=CacheStatus.miss, media_type="image/png"
        )
