from os import environ

from buildpg.asyncpg import create_pool_b
from fastapi import FastAPI
from macrostrat.utils import get_logger, setup_stderr_logs
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from .image_tiles import MapnikLayerFactory, prepare_image_tile_subsystem

log = get_logger(__name__)

app = FastAPI(prefix="/", middleware=[Middleware(CORSMiddleware, allow_origins=["*"])])


# Register Start/Stop application event handler to setup/stop the database connection
@app.on_event("startup")
async def startup_event():
    """Application startup: register the database connection and create table list."""
    # Don't rely on poort TimVT handling of database connections
    setup_stderr_logs("macrostrat.legacy_tileserver")

    app.state.pool = await create_pool_b(environ["DATABASE_URL"])

    prepare_image_tile_subsystem()


MapnikLayerFactory(app)


@app.get("/", include_in_schema=False)
async def index(request: Request):
    """DEMO."""
    return JSONResponse({"message": "Macrostrat legacy tileserver"})
