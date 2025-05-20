from fastapi import Request
from morecantile import Tile
from timvt.dependencies import TileParams
from fastapi import Depends, BackgroundTasks
from macrostrat.utils import get_logger

log = get_logger(__name__)

image_tiler = None
try:
    from .core import ImageTileSubsystem

    image_tiler = ImageTileSubsystem()
except ImportError:
    log.info("Mapnik not available; image tile subsystem disabled")


def prepare_image_tile_subsystem():
    if image_tiler is not None:
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
        if image_tiler is None:
            return "Mapnik not available", 404
        return await image_tiler.handle_tile_request(request, background_tasks, tile)
