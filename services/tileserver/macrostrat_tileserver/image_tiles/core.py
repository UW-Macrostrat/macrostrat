from fastapi import Request
from morecantile import Tile, tms
from mapnik import Map, load_map_from_string, Image, render, Box2d
from timvt.dependencies import TileParams
from timvt.settings import TileSettings
import time
from .mapnik_styles import make_mapnik_xml
from .config import scales, scale_for_zoom
from fastapi import Depends, BackgroundTasks
from macrostrat.utils.timer import Timer
from timvt.resources.enums import MimeTypes
from ..cache import get_tile_from_cache, set_cached_tile
from ..utils import TileResponse

tile_settings = TileSettings()


class ImageTileSubsystem:
    """Macrostrat's image tile subsystem allows image tiles to be generated using Mapnik.
    It is considered a legacy feature, and is not recommended for new applications.
    The Mapnik dependency is difficult to build, and is available in the Docker image
    but not for Poetry-based installations.

    This "v2" implementation of the image tile system replaces the much less efficient "v1" version
    that was implemented in NodeJS.
    """

    layer_cache = {}

    def build_layer_cache(self):
        ## Generate mapnik XML files
        for scale in scales:
            # Log timings
            t = time.time()
            self.layer_cache[scale] = make_mapnik_xml(scale)
            print(
                f"Generated mapnik XML for scale {scale} in {time.time() - t} seconds"
            )

    def get_tile(self, tile: Tile, tms) -> bytes:
        quad = tms.get("WebMercatorQuad")
        bbox = quad.xy_bounds(tile)

        # Get map scale for this zoom level
        scale = scale_for_zoom(tile.z)

        # Path to mapnik XML file

        # Load mapnik XML
        map = Map(512, 512)
        load_map_from_string(map, self.layer_cache[scale])
        # Set bbox of map

        # map.zoom_all()

        box = Box2d(bbox.left, bbox.top, bbox.right, bbox.bottom)
        map.zoom_to_box(box)

        # Render map to image
        im = Image(512, 512)
        render(map, im)
        # Return image as binary
        return im.tostring("png")

    async def handle_tile_request(
        self,
        request: Request,
        background_tasks: BackgroundTasks,
        tile: Tile = Depends(TileParams),
    ):
        """Return vector tile."""
        pool = request.app.state.pool

        timer = Timer()

        should_cache = True

        if should_cache:
            content = await get_tile_from_cache(pool, "carto-image", tile, None)
            timer._add_step("check_cache")
            if content is not None:
                return TileResponse(
                    content, timer, cache_hit=True, media_type="image/png"
                )

        content = self.get_tile(tile, tms)
        timer._add_step("get_tile")

        if should_cache:
            background_tasks.add_task(
                set_cached_tile, pool, "carto-image", tile, content
            )

        return TileResponse(content, timer, cache_hit=False, media_type="image/png")
