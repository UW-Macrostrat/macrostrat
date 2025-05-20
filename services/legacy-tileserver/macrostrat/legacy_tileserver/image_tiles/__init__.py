from fastapi import Depends, BackgroundTasks, Request, Path
from macrostrat.utils import get_logger
from morecantile import Tile


def TileParams(
    z: int = Path(..., ge=0, le=30, description="Tiles's zoom level"),
    x: int = Path(..., description="Tiles's column"),
    y: int = Path(..., description="Tiles's row"),
) -> Tile:
    """Tile parameters."""
    return Tile(x, y, z)


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
        if image_tiler is None:
            return "Mapnik not available", 404
        return await image_tiler.handle_tile_request(request, background_tasks, tile)
