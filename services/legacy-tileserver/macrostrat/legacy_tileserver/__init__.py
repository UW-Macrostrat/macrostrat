from os import environ

from buildpg import render
from buildpg.asyncpg import create_pool_b
from enum import Enum
from fastapi import FastAPI, Depends, BackgroundTasks, Request
from functools import lru_cache
from macrostrat.database import Database
from macrostrat.tileserver_utils import (
    CacheMode,
    TileParams,
    MimeTypes,
    handle_cached_tile_request,
    CachedTileArgs,
)
from macrostrat.utils import get_logger
from macrostrat.utils import setup_stderr_logs
from morecantile import Tile
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse

from .image_tiles import get_image_tile, MapnikMapPool

log = get_logger(__name__)

app = FastAPI(prefix="/", middleware=[Middleware(CORSMiddleware, allow_origins=["*"])])


# Register Start/Stop application event handler to setup/stop the database connection
@app.on_event("startup")
async def startup_event():
    """Application startup: register the database connection and create table list."""
    # Don't rely on poort TimVT handling of database connections
    setup_stderr_logs("macrostrat.legacy_tileserver")

    url = environ["DATABASE_URL"]
    app.state.pool = await create_pool_b(url)
    db = Database(url)
    app.state.map_pool = MapnikMapPool(8)
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
async def index(request: Request):
    """DEMO."""
    return JSONResponse({"message": "Macrostrat legacy tileserver"})
