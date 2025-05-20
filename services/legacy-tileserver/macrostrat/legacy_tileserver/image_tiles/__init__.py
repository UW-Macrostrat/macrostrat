from fastapi import Depends, BackgroundTasks, Request
from macrostrat.utils import get_logger
from morecantile import Tile

from .utils import TileParams

log = get_logger(__name__)

image_tiler = None
from .core import ImageTileSubsystem

image_tiler = ImageTileSubsystem()


def prepare_image_tile_subsystem():
    image_tiler.build_layer_cache()


def MapnikLayerFactory(app):
    @app.get("/carto/{z}/{x}/{y}.png")
    @app.get("/carto-slim/{z}/{x}/{y}.png")
    async def tile(
        request: Request,
        background_tasks: BackgroundTasks,
        tile: Tile = Depends(TileParams),
    ):
        """Return vector tile."""
        log.info(tile)
        return await image_tiler.handle_tile_request(request, background_tasks, tile)
