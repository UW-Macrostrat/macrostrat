from os import environ

from buildpg.asyncpg import create_pool_b
from fastapi import Depends, BackgroundTasks, Request
from fastapi import FastAPI
from macrostrat.database import Database
from macrostrat.utils import get_logger
from macrostrat.utils import setup_stderr_logs
from morecantile import Tile
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse

from .image_tiles import ImageTileSubsystem, MapnikMapPool
from .utils import TileParams, CacheMode

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
    app.state.map_pool = MapnikMapPool(db, 4)


image_tiler = ImageTileSubsystem()


@app.get("/carto/{z}/{x}/{y}.png")
@app.get("/carto-slim/{z}/{x}/{y}.png")
async def tile(
    request: Request,
    background_tasks: BackgroundTasks,
    tile: Tile = Depends(TileParams),
    *,
    cache: CacheMode = CacheMode.prefer,
):
    """Return vector tile."""
    return await image_tiler.handle_tile_request(
        request, background_tasks, tile, cache=cache
    )


@app.get("/", include_in_schema=False)
async def index(request: Request):
    """DEMO."""
    return JSONResponse({"message": "Macrostrat legacy tileserver"})
