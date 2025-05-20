from os import environ
from pathlib import Path

from fastapi import FastAPI
from macrostrat.utils import get_logger, setup_stderr_logs
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from .image_tiles import MapnikLayerFactory, prepare_image_tile_subsystem

# Wire up legacy postgres database
if not environ.get("DATABASE_URL") and "POSTGRES_DB" in environ:
    environ["DATABASE_URL"] = environ["POSTGRES_DB"]

# We need to provide the Rockd database URL or else the whole thing doesn't start up


log = get_logger(__name__)

__here__ = Path(__file__).parent

app = FastAPI(prefix="/", middleware=[Middleware(CORSMiddleware, allow_origins=["*"])])


# Register Start/Stop application event handler to setup/stop the database connection
@app.on_event("startup")
async def startup_event():
    """Application startup: register the database connection and create table list."""
    # Don't rely on poort TimVT handling of database connections
    setup_stderr_logs("macrostrat.legacy_tileserver")

    # Apply fixtures
    # apply_fixtures(db_settings.database_url)
    # await register_table_catalog(app, schemas=["sources"])
    prepare_image_tile_subsystem()


MapnikLayerFactory(app)


@app.get("/", include_in_schema=False)
async def index(request: Request):
    """DEMO."""
    return JSONResponse({"message": "Macrostrat legacy tileserver"})
