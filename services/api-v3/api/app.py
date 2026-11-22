from contextlib import asynccontextmanager

import dotenv
import uvicorn
from fastapi import FastAPI
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
from sqlalchemy.engine import make_url
from starlette_cramjam.middleware import CompressionMiddleware

from api.cors import CREDENTIALED_ORIGINS, TwoTierCORSMiddleware
from api.routes.dev_routes.api import convert_router
from api.tiles import register_tile_routes, tile_lifespan

dotenv.load_dotenv()

import api.routes.security
from api.compilations import router as compilations_router
from api.database import AppDatabase, get_db_url
from api.map import router as map_router
from api.map_bounds import router as map_bounds_router
from api.match import router as match_router
from api.refs import router as refs_router
from api.regions import router as regions_router
from api.routes.cache import router as cache_router
from api.routes.column_geometry import router as column_geometry_router
from api.routes.columns import router as columns_router
from api.routes.ingest import router as ingest_router
from api.routes.nearby_columns import router as nearby_columns_router
from api.routes.object import router as object_router
from api.routes.sources import router as sources_router
from api.routes.status import router as status_router
from api.routes.tasks import router as tasks_router
from api.routes.usage_stats import router as usage_stats_router


@asynccontextmanager
async def setup_engine(app: FastAPI, url: str | None = None):
    """Create the shared database connection pools for the app's lifetime.

    The unified ``Database`` owns both the async and sync connection pools, so it
    is built exactly once here and shared across all requests via ``app.state.db``
    (see api/database.py dependencies). It is disposed on shutdown so its
    connections are returned to Postgres rather than leaked.
    """
    app.state.db = AppDatabase(url or get_db_url())
    api.routes.security.accounts.sessionmaker = app.state.db.async_sessionmaker
    yield
    await app.state.db.dispose()


def _optional_db_url() -> str | None:
    try:
        return get_db_url()
    except ValueError:
        return None


@asynccontextmanager
async def lifespan(app: FastAPI):
    url = get_db_url()
    async with setup_engine(app, url), tile_lifespan(app, _asyncpg_url(url)):
        yield


def _asyncpg_url(url: str) -> str:
    # asyncpg rejects SQLAlchemy's `postgresql+driver` schemes.
    return make_url(url).set(drivername="postgresql").render_as_string(False)


# No `root_path`: it would enter every absolute URL the tile routes build. The
# relative server and docs URLs resolve under whichever prefix the proxy serves.
app = FastAPI(
    lifespan=lifespan,
    servers=[{"url": "./"}],
    docs_url=None,
    redoc_url=None,
)


@app.get("/docs", include_in_schema=False)
def docs():
    return get_swagger_ui_html(openapi_url="openapi.json", title="Macrostrat API")


@app.get("/redoc", include_in_schema=False)
def redoc():
    return get_redoc_html(openapi_url="openapi.json", title="Macrostrat API")


app.add_middleware(
    CompressionMiddleware,
    # Not 0: a gzip header on an empty 204 makes Varnish fail the fetch.
    minimum_size=1,
    # Matched exactly against Content-Type, which Starlette gives a charset.
    exclude_mediatype={"text/event-stream", "text/event-stream; charset=utf-8"},
)
app.add_middleware(TwoTierCORSMiddleware, credentialed_origins=CREDENTIALED_ORIGINS)

app.include_router(status_router)
app.include_router(api.routes.security.router)
app.include_router(object_router)
app.include_router(ingest_router)
app.include_router(columns_router)
app.include_router(column_geometry_router)
app.include_router(nearby_columns_router)
app.include_router(sources_router)
app.include_router(compilations_router)
app.include_router(map_bounds_router)
app.include_router(refs_router)
app.include_router(regions_router)
app.include_router(map_router, prefix="/map")
app.include_router(cache_router, prefix="/cache")
app.include_router(tasks_router)
app.include_router(usage_stats_router)

app.include_router(convert_router, prefix="/dev")
app.include_router(match_router, prefix="/dev/match")

# Last: the tile catalog's `/{layer}/{z}/{x}/{y}` must not shadow the routes above.
register_tile_routes(app, _optional_db_url())


if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        headers=[("Access-Control-Expose-Headers", "X-Total-Count")],
    )
