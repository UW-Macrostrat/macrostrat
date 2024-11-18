from os import environ
from typing import Any, List, Optional

from buildpg import render
from fastapi import FastAPI, Request
from macrostrat.utils import get_logger, setup_stderr_logs
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware import Middleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette_cramjam.middleware import CompressionMiddleware
from timvt.db import close_db_connection, connect_to_db, connect_to_rockd_db, register_table_catalog
from timvt.settings import PostgresSettings
from timvt.layer import FunctionRegistry
from titiler.core.errors import DEFAULT_STATUS_CODES, add_exception_handlers
from titiler.core.factory import TilerFactory
from pydantic_settings import SettingsConfigDict

from .cached_tiler import CachedStoredFunction, CachedVectorTilerFactory
from .function_layer import StoredFunction
from .image_tiles import MapnikLayerFactory, prepare_image_tile_subsystem
from .utils import DecimalJSONResponse
from .vendor.repeat_every import repeat_every
from .paleogeography import PaleoGeographyLayer
from macrostrat.database import Database
from pathlib import Path
from time import time


# Wire up legacy postgres database
if not environ.get("DATABASE_URL") and "POSTGRES_DB" in environ:
    environ["DATABASE_URL"] = environ["POSTGRES_DB"]


log = get_logger(__name__)

__here__ = Path(__file__).parent

app = FastAPI(prefix="/", middleware=[Middleware(CORSMiddleware, allow_origins=["*"])])


class TileServerSettings(PostgresSettings):
    # XDD embedding service URL
    xdd_embedding_service_url: Optional[str] = None
    rockd_database_url: Optional[str] = None
    model_config = SettingsConfigDict(
        extra="allow",
    )

db_settings = TileServerSettings()
db_settings.rockd_database_url

app.state.timvt_function_catalog = FunctionRegistry()
app.state.function_catalog = FunctionRegistry()


# Register Start/Stop application event handler to setup/stop the database connection
@app.on_event("startup")
async def startup_event():
    """Application startup: register the database connection and create table list."""
    # Don't rely on poort TimVT handling of database connections
    setup_stderr_logs("macrostrat_tileserver", "timvt")
    await connect_to_db(app, db_settings)
    await connect_to_rockd_db(app, db_settings)

    # Apply fixtures
    # apply_fixtures(db_settings.database_url)
    await register_table_catalog(app, schemas=["sources"])
    prepare_image_tile_subsystem()

    print("Application started.")


@app.on_event("startup")
@repeat_every(seconds=600)  # 10 minutes
async def truncate_tile_cache_if_needed() -> None:
    """Truncate the tile cache if it's too big."""
    pool = app.state.pool
    async with pool.acquire() as conn:
        max_size = 1e6

        q, p = render(
            "SELECT tile_cache.remove_excess_tiles(:max_size)",
            max_size=max_size,
        )

        await conn.execute(q, *p)


def apply_fixtures(url: str):
    """Apply fixtures."""
    start = time()
    db = Database(url)
    db.run_fixtures(__here__ / "fixtures")
    end = time()
    log.info(f"Fixtures applied in {end-start:.2f} seconds.")


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown: de-register the database connection."""
    await close_db_connection(app)



app.add_middleware(CompressionMiddleware, minimum_size=0)

MapnikLayerFactory(app)

cog = TilerFactory()

app.include_router(cog.router, prefix="/cog", tags=["Cloud Optimized GeoTIFF"])
add_exception_handlers(app, DEFAULT_STATUS_CODES)


# Register endpoints.
mvt_tiler = CachedVectorTilerFactory(
    with_tables_metadata=True,
    with_functions_metadata=True,  # add Functions metadata endpoints (/functions.json, /{function_name}.json)
    with_viewer=False,
)

# Tile layer definitions start here.
# Note: these are defined somewhat redundantly.
# Our eventual goal will be to store these configurations in the database.

cached_functions = [
    "tile_layers.carto",
    "tile_layers.carto_slim",
]


functions = [
    "corelle_macrostrat.igcp_orogens",
    "corelle_macrostrat.igcp_orogens_rotated",
    "weaver_api.weaver_tile",
    "tile_layers.map",
    "tile_layers.all_maps",

]

layers = [CachedStoredFunction(l) for l in cached_functions] + [
    StoredFunction(l) for l in functions
]

if hasattr(app.state, 'rockd_pool'):
    checkins_tile_layer = StoredFunction("public.checkins_tile", connection=app.state.rockd_pool)
    app.state.function_catalog.register(checkins_tile_layer)

layers.append(PaleoGeographyLayer())

for layer in layers:
    app.state.function_catalog.register(layer)


# Legacy routes postfixed with ".mvt"
app.include_router(mvt_tiler.router, tags=["Tiles"])

from .filterable import router as filterable_router

app.include_router(filterable_router, tags=["Filterable"], prefix="/v2")

from .map_bounds import router as map_bounds_router

app.include_router(map_bounds_router, tags=["Maps"], prefix="/maps")

from .vector_search import router as search_router

app.include_router(search_router, tags=["Vector search"], prefix="/search")

from .rockd_checkins import router as checkins_router

app.include_router(checkins_router, tags=["checkins"], prefix="/checkins")


@app.get("/carto/rotation-models")
async def rotation_models():
    """Return a list of rotation models."""
    pool = app.state.pool
    q, p = render("SELECT * FROM corelle.model")
    rows = await pool.fetch(q, *p)
    data = [dict(row) for row in rows]
    return DecimalJSONResponse(data)


@app.get("/", include_in_schema=False)
async def index(request: Request):
    """DEMO."""
    return JSONResponse({"message": "Macrostrat Tileserver"})


@app.get("/refresh", include_in_schema=False)
async def refresh(request: Request):
    """Refresh the table catalog."""
    await register_table_catalog(app, schemas=["sources"])
    return JSONResponse({"message": "Table catalog refreshed."})
