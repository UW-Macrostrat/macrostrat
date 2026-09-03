from os import environ
from pathlib import Path
from typing import Optional

from buildpg import asyncpg, render
from fastapi import FastAPI
from pydantic_settings import SettingsConfigDict
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette_cramjam.middleware import CompressionMiddleware
from titiler.core.errors import DEFAULT_STATUS_CODES, add_exception_handlers
from titiler.core.factory import TilerFactory

from macrostrat.tileserver_utils import DecimalJSONResponse
from macrostrat.utils import get_logger, setup_stderr_logs

from .map_ingestion import register_map_ingestion_routes
from .paleogeography import PaleoGeographyLayer
from .vector_tiles import (
    FunctionRegistry,
    PostgresSettings,
    StoredFunction,
    VectorTileFactory,
    close_db_connection,
    connect_to_db,
)
from .vendor.repeat_every import repeat_every

# Wire up legacy postgres database
if not environ.get("DATABASE_URL") and "POSTGRES_DB" in environ:
    environ["DATABASE_URL"] = environ["POSTGRES_DB"]

# We need to provide the Rockd database URL or else the whole thing doesn't start up


log = get_logger(__name__)

__here__ = Path(__file__).parent

app = FastAPI(
    prefix="/",
    middleware=[
        Middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_methods=["*"],
            allow_headers=["*"],
        )
    ],
)


class TileServerSettings(PostgresSettings):
    # XDD embedding service URL
    xdd_embedding_service_url: Optional[str] = None
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="allow",
    )


# Read once at import for callers that only need static configuration (e.g. the
# xDD embedding service URL). The database connection re-reads at startup, so
# the URL can be set after import — which is what the test fixtures do.
db_settings = TileServerSettings()

# Every vector-tile layer this application serves, resolved by name at request
# time (see `vector_tiles.layer_dependency`).
app.state.function_catalog = FunctionRegistry()


# Register Start/Stop application event handler to setup/stop the database connection
@app.on_event("startup")
async def startup_event():
    """Application startup: register the database connection and create table list."""
    # Don't rely on poort TimVT handling of database connections
    setup_stderr_logs("macrostrat_tileserver")
    await connect_to_db(
        app,
        TileServerSettings(),
        server_settings={"application_name": "tileserver"},
    )


# Budget for the L2 tile cache, in bytes of tile payload. This is a *logical* size
# (mean tile length times row count), not the relation's on-disk size -- see
# `tile_cache.remove_excess_tiles`. Sized against the database volume: the cache is
# the largest discretionary consumer on it, and an unbounded one filled the volume and
# took production down in September 2026.
TILE_CACHE_MAX_BYTES = 20_000_000_000  # 20 GB


@app.on_event("startup")
@repeat_every(seconds=600)  # 10 minutes
async def trim_tile_cache_if_needed() -> None:
    """Evict least-recently-used tiles until the cache fits its byte budget."""
    pool = app.state.pool
    async with pool.acquire() as conn:
        q, p = render(
            "SELECT tile_cache.remove_excess_tiles(:max_bytes)",
            max_bytes=TILE_CACHE_MAX_BYTES,
        )

        deleted = await conn.fetchval(q, *p)

    if deleted:
        log.info("Evicted %s tiles from the L2 cache", deleted)


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown: de-register the database connection."""
    await close_db_connection(app)


# `minimum_size=1`, not 0: compressing a *zero-length* body produces a gzip
# header with a real `content-length`, and attaching that to a 204 (which must
# carry no body) makes caching proxies fail the fetch — an empty raster tile
# came back to clients as a 503 from Varnish. Everything with actual content is
# still compressed.
app.add_middleware(CompressionMiddleware, minimum_size=1)

# Map ingestion
register_map_ingestion_routes(app)

cog = TilerFactory()

app.include_router(cog.router, prefix="/cog", tags=["Cloud Optimized GeoTIFF"])
add_exception_handlers(app, DEFAULT_STATUS_CODES)


# Register endpoints.
mvt_tiler = VectorTileFactory()

# Tile layer definitions start here.
# Note: these are defined somewhat redundantly.
# Our eventual goal will be to store these configurations in the database.

functions = [
    "corelle_macrostrat.igcp_orogens",
    "corelle_macrostrat.igcp_orogens_rotated",
    "weaver_api.weaver_tile",
    "tile_layers.map",
    "tile_layers.all_maps",
]

# Register the layers, setting appropriate cache profiles
layers = [StoredFunction(l) for l in functions]

layer = StoredFunction("tile_layers.carto")
layer.profile_id = "carto"
layers.append(layer)

layer = StoredFunction("tile_layers.carto_slim")
layer.profile_id = "carto-slim"
layers.append(layer)

paleo_layer = PaleoGeographyLayer()
paleo_layer.profile_id = "carto-slim-rotated"
layers.append(paleo_layer)

for layer in layers:
    app.state.function_catalog.register(layer)

# Mounted at the app root, so its `/{layer}/{z}/{x}/{y}` route is the widest
# thing in the table — see `VectorTileFactory.register_tiles` for why its path
# converters are typed.
#
# NOTE: the comment that used to sit here claimed `.mvt`-suffixed legacy routes
# were registered. None are, and none work (`/layer/1/2/3.mvt` is a 404) — the
# claim was stale rather than a regression.
app.include_router(mvt_tiler.router, tags=["Tiles"])

from .filterable import router as filterable_router

app.include_router(filterable_router, tags=["Filterable"], prefix="/v2")

from .map_bounds import router as map_bounds_router

app.include_router(map_bounds_router, tags=["Maps"], prefix="/maps")

from .vector_search import router as search_router

app.include_router(search_router, tags=["Vector search"], prefix="/search")

from .fossils import router as fossils_router

app.include_router(fossils_router, tags=["PBDB"], prefix="/pbdb")

from .measurements import router as measurements_router

app.include_router(measurements_router, tags=["Measurements"], prefix="/measurements")

from .integrations import router as integrations_router

app.include_router(integrations_router, tags=["Integrations"], prefix="/integrations")


from .stats import stats_router

app.include_router(stats_router, tags=["Stats"], prefix="/stats")

from .carto_new import router as carto_router

app.include_router(carto_router, tags=["Carto new"], prefix="/dev/carto")

from .topology import router as topo_router

app.include_router(topo_router, tags=["Topology"], prefix="/dev/topology")

from .cache_management import router as cache_router

app.include_router(cache_router, tags=["Cache"], prefix="/cache")

from .rasters import register_raster_routes

# Mosaicked COG layers from the `raster_layers` index. Optional: the raster
# libraries are still developed against local checkouts.
register_raster_routes(app)


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
