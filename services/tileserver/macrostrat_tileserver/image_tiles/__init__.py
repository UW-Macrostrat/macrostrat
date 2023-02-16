from fastapi import FastAPI, Request, Response
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

layer_cache = {}


def build_layer_cache():
    ## Generate mapnik XML files
    for scale in scales:
        # Log timings
        t = time.time()
        layer_cache[scale] = make_mapnik_xml(scale)
        print(f"Generated mapnik XML for scale {scale} in {time.time() - t} seconds")


def MapnikLayerFactory(app):
    @app.get("/image-layers/carto-image/{z}/{x}/{y}.png")
    async def tile(
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

        content = get_tile(tile, tms)
        timer._add_step("get_tile")

        if should_cache:
            background_tasks.add_task(
                set_cached_tile, pool, "carto-image", tile, content
            )

        return TileResponse(content, timer, cache_hit=False, media_type="image/png")


def get_tile(tile: Tile, tms) -> bytes:
    quad = tms.get("WebMercatorQuad")
    bbox = quad.xy_bounds(tile)

    # Get map scale for this zoom level
    scale = scale_for_zoom(tile.z)

    # Path to mapnik XML file

    # Load mapnik XML
    map = Map(512, 512)
    load_map_from_string(map, layer_cache[scale])
    # Set bbox of map

    # map.zoom_all()

    box = Box2d(bbox.left, bbox.top, bbox.right, bbox.bottom)
    map.zoom_to_box(box)

    # Render map to image
    im = Image(512, 512)
    render(map, im)
    # Return image as binary
    return im.tostring("png")
