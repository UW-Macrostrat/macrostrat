from enum import Enum
from functools import lru_cache
from os import environ
from pathlib import Path

from buildpg import render
from buildpg.asyncpg import create_pool_b
from fastapi import BackgroundTasks, Depends, FastAPI, Request
from morecantile import Tile
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import HTMLResponse

from macrostrat.database import Database
from macrostrat.tileserver_utils import (
    CachedTileArgs,
    CacheMode,
    MimeTypes,
    TileParams,
    handle_cached_tile_request,
)
from macrostrat.utils import get_logger, setup_stderr_logs

from .image_tiles import MapnikMapPool, get_image_tile

log = get_logger(__name__)

app = FastAPI(prefix="/", middleware=[Middleware(CORSMiddleware, allow_origins=["*"])])


# Register Start/Stop application event handler to setup/stop the database connection
@app.on_event("startup")
async def startup_event():
    """Application startup: register the database connection and create table list."""
    setup_stderr_logs("macrostrat.legacy_tileserver")

    url = environ["DATABASE_URL"]

    # Tile rendering map pool size
    # This controls how many image tiles can be concurrently rendered.
    # Database access is somewhat inefficient, so we may need to adjust this.
    mapnik_pool_size = int(environ.get("MAPNIK_POOL_SIZE", "64"))
    log.info(f"Setting up Mapnik map pool with size {mapnik_pool_size}")

    app.state.pool = await create_pool_b(url)
    db = Database(url)
    app.state.map_pool = MapnikMapPool(mapnik_pool_size)
    await app.state.map_pool.setup(db)


class MapCompilation(Enum):
    Carto = "carto"
    CartoSlim = "carto-slim"

    def __str__(self):
        return self.value


@app.get("/carto/{z}/{x}/{y}.png")
async def tile(
    request: Request,
    background_tasks: BackgroundTasks,
    tile: Tile = Depends(TileParams),
    *,
    cache: CacheMode = CacheMode.prefer,
):
    """Raster tiles. Only available for Carto compilation (carto-slim would be the same)."""

    args = CachedTileArgs(
        layer="carto-image",
        tile=tile,
        media_type="image/png",
        mode=cache,
    )

    return await handle_cached_tile_request(
        request, request.app.state.pool, background_tasks, get_image_tile, args
    )


@app.get("/{layer}/{z}/{x}/{y}.mvt")
async def tile(
    request: Request,
    layer: MapCompilation,
    background_tasks: BackgroundTasks,
    tile: Tile = Depends(TileParams),
    *,
    cache: CacheMode = CacheMode.prefer,
):
    """Return vector tile."""
    args = CachedTileArgs(
        layer=str(layer),
        tile=tile,
        media_type=MimeTypes.mvt,
        mode=cache,
    )

    return await handle_cached_tile_request(
        request,
        request.app.state.pool,
        background_tasks,
        vector_tile_handler(layer),
        args,
    )


# Cached function to get a handler for a specific vector tile layer
@lru_cache(10)
def vector_tile_handler(compilation: MapCompilation):
    function_name: str = "tile_layers.carto"
    if compilation == MapCompilation.CartoSlim:
        function_name = "tile_layers.carto_slim"

    async def get_vector_tile(req, args):
        """Get vector tile."""
        # This is a placeholder for the actual function to get the vector tile
        # You would replace this with the actual implementation
        q, p = render(
            f"SELECT {function_name}(:x, :y, :z)",
            x=args.tile.x,
            y=args.tile.y,
            z=args.tile.z,
        )
        async with req.app.state.pool.acquire() as conn:
            return await conn.fetchval(q, *p)

    return get_vector_tile


@app.get("/", include_in_schema=False)
def index():
    """Return index page"""
    return get_page("index")


@app.get("/preview", include_in_schema=False)
def preview():
    """Return preview page"""
    return get_page("preview")


def get_page(key):
    file = Path(__file__).parent / "pages" / (key + ".html")
    return HTMLResponse(file.read_text("utf-8"))
