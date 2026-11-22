"""Tile routes: vector, map, raster and elevation tiles, formerly the tileserver.

`register_tile_routes` mounts them on API v3's app, at its root, and
`tile_lifespan` owns the asyncpg pool they share.
"""

import asyncio
import re
from contextlib import asynccontextmanager, suppress
from enum import Enum
from typing import Optional
from urllib.parse import parse_qsl, urlencode

from buildpg import render
from fastapi import FastAPI
from pydantic_settings import SettingsConfigDict
from starlette.requests import Request
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

log = get_logger(__name__)


class CartoBuild(str, Enum):
    legacy = "legacy"
    compilation = "compilation"


class TileServerSettings(PostgresSettings):
    # XDD embedding service URL
    xdd_embedding_service_url: Optional[str] = None
    #: Which build answers `/carto-slim` and `/carto`: `compilation` serves them
    #: from `/map/carto`. Shared with the legacy tileserver and API v2; legacy
    #: until an environment is ready to change what its public clients receive.
    carto_build: CartoBuild = CartoBuild.legacy
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="allow",
    )

    @property
    def carto_from_compilation(self) -> bool:
        return self.carto_build == CartoBuild.compilation


# Read once at import for callers that only need static configuration (e.g. the
# xDD embedding service URL). The pool takes its URL from `tile_lifespan`.
db_settings = TileServerSettings()


# Budgets for the L2 tile cache, on disk. Sized against the database volume: the
# cache is the largest discretionary consumer on it, and an unbounded one filled the
# volume and took production down in September 2026.
TILE_CACHE_MAX_BYTES = 20_000_000_000  # 20 GB across the rotating generations
TILE_CACHE_MAX_PINNED_BYTES = 2_000_000_000  # 2 GB of pinned tiles
TILE_CACHE_ROTATION_SECONDS = 600


async def rotate_tile_cache(app: FastAPI) -> None:
    """Advance the cache's generation ring when the current one is full."""
    try:
        async with app.state.pool.acquire() as conn:
            q, p = render(
                "SELECT * FROM tile_cache.rotate(:max_bytes, :max_pinned_bytes)",
                max_bytes=TILE_CACHE_MAX_BYTES,
                max_pinned_bytes=TILE_CACHE_MAX_PINNED_BYTES,
            )
            row = await conn.fetchrow(q, *p)
    except Exception:
        # Includes a TRUNCATE that hit its lock timeout; the next call retries.
        log.warning("Tile cache rotation failed", exc_info=True)
        return

    if row is not None and row["rotated_to"] is not None:
        log.info("Tile cache rotated to generation %s", row["rotated_to"])
    if row is not None and row["pinned_evicted"]:
        log.info("Evicted %s pinned tiles from the L2 cache", row["pinned_evicted"])


async def _rotate_periodically(app: FastAPI) -> None:
    while True:
        await rotate_tile_cache(app)
        await asyncio.sleep(TILE_CACHE_ROTATION_SECONDS)


@asynccontextmanager
async def tile_lifespan(app: FastAPI, database_url: str):
    """Open the tile pool and run cache rotation for the app's lifetime."""
    setup_stderr_logs("macrostrat_tileserver")
    await connect_to_db(
        app,
        TileServerSettings(database_url=database_url),
        server_settings={"application_name": "tileserver"},
    )
    rotation = asyncio.create_task(_rotate_periodically(app))
    try:
        yield
    finally:
        rotation.cancel()
        with suppress(asyncio.CancelledError):
            await rotation
        await close_db_connection(app)


# `/carto-slim/{z}/{x}/{y}` and `/carto/{z}/{x}/{y}` are the legacy build's
# tiles. With `carto_build=compilation`, both are answered by `/map/carto`
# under their own addresses: `carto-slim`'s properties are `/map/carto`'s, and
# `/carto`'s are its `detail=full` ones. Any query string is kept. Rewritten in
# process rather than redirected, so clients, Varnish and the access log see one
# request under the address they have always used.
_LEGACY_CARTO_TILE = re.compile(r"^/(carto|carto-slim)/(\d+)/(\d+)/(\d+)$")


def rewrite_legacy_carto(path: str, query: str) -> Optional[tuple[str, str]]:
    """The `/map/carto` address a legacy carto tile request is served from."""
    match = _LEGACY_CARTO_TILE.match(path)
    if match is None:
        return None
    layer, z, x, y = match.groups()
    params = parse_qsl(query, keep_blank_values=True)
    if layer == "carto":
        params.append(("detail", "full"))
    return f"/map/carto/{z}/{x}/{y}", urlencode(params)


async def carto_from_compilation(request: Request, call_next):
    if db_settings.carto_from_compilation:
        rewritten = rewrite_legacy_carto(
            request.scope["path"], request.scope["query_string"].decode()
        )
        if rewritten is not None:
            path, query = rewritten
            # The scope is what the router reads, and the request shares it.
            request.scope["path"] = path
            request.scope["raw_path"] = path.encode()
            request.scope["query_string"] = query.encode()
    return await call_next(request)


def register_tile_routes(app: FastAPI, database_url: Optional[str] = None) -> None:
    """Mount every tile route on `app`, after the app's own routes.

    `database_url` is needed at registration only by the raster and elevation
    routes, which build their index then; without it they are skipped.
    """
    app.middleware("http")(carto_from_compilation)

    register_map_ingestion_routes(app)

    cog = TilerFactory()
    app.include_router(cog.router, prefix="/cog", tags=["Cloud Optimized GeoTIFF"])
    add_exception_handlers(app, DEFAULT_STATUS_CODES)

    # Every vector-tile layer, resolved by name at request time (see
    # `vector_tiles.layer_dependency`).
    app.state.function_catalog = FunctionRegistry()
    for layer in _stored_function_layers():
        app.state.function_catalog.register(layer)

    # Its `/{layer}/{z}/{x}/{y}` route is the widest in the table, so it comes
    # after the app's own routes; its typed path converters keep it from
    # matching anything without three integer segments.
    mvt_tiler = VectorTileFactory()
    app.include_router(mvt_tiler.router, tags=["Tiles"])

    from .filterable import router as filterable_router
    from .fossils import router as fossils_router
    from .integrations import router as integrations_router
    from .map_bounds import router as map_bounds_router
    from .map_tiles import legacy_router as carto_alias_router
    from .map_tiles import router as map_tiles_router
    from .measurements import router as measurements_router
    from .regions import router as regions_router
    from .stats import stats_router
    from .topology import router as topo_router
    from .vector_search import router as search_router

    app.include_router(filterable_router, tags=["Filterable"], prefix="/v2")
    app.include_router(map_bounds_router, tags=["Maps"], prefix="/maps")
    app.include_router(search_router, tags=["Vector search"], prefix="/search")
    app.include_router(fossils_router, tags=["PBDB"], prefix="/pbdb")
    app.include_router(
        measurements_router, tags=["Measurements"], prefix="/measurements"
    )
    app.include_router(
        integrations_router, tags=["Integrations"], prefix="/integrations"
    )
    app.include_router(regions_router, tags=["Regions"], prefix="/regions")
    app.include_router(stats_router, tags=["Stats"], prefix="/stats")

    # Any source by slug, `carto` included: `/map/{slug}/{z}/{x}/{y}`. Five
    # segments, so it never collides with the catalog's `/map/{z}/{x}/{y}?source_id=`,
    # which stays as the v2 alias.
    app.include_router(map_tiles_router, tags=["Map tiles"], prefix="/map")
    app.include_router(
        carto_alias_router, tags=["Map tiles"], prefix="/dev/carto", deprecated=True
    )
    app.include_router(topo_router, tags=["Topology"], prefix="/dev/topology")

    from .rasters import register_raster_routes

    # Mosaicked COG layers from the `raster_layers` index.
    register_raster_routes(app, database_url)

    from .elevation import register_elevation_routes

    # Terrain height and bathymetry at a point or along a line, read from the same
    # index. Mounted only when the installed raster libraries carry the sampling
    # primitives (`macrostrat.raster_layers` >= 0.4).
    register_elevation_routes(app, database_url)

    app.add_api_route("/carto/rotation-models", rotation_models, methods=["GET"])


def _stored_function_layers():
    functions = [
        "corelle_macrostrat.igcp_orogens",
        "corelle_macrostrat.igcp_orogens_rotated",
        "weaver_api.weaver_tile",
        "tile_layers.map",
        "tile_layers.all_maps",
    ]
    layers = [StoredFunction(l) for l in functions]

    # Cache profiles for the layers whose tiles are kept in L2.
    layer = StoredFunction("tile_layers.carto")
    layer.profile_id = "carto"
    layers.append(layer)

    layer = StoredFunction("tile_layers.carto_slim")
    layer.profile_id = "carto-slim"
    layers.append(layer)

    paleo_layer = PaleoGeographyLayer()
    paleo_layer.profile_id = "carto-slim-rotated"
    layers.append(paleo_layer)
    return layers


async def rotation_models(request: Request):
    """Return a list of rotation models."""
    q, p = render("SELECT * FROM corelle.model")
    rows = await request.app.state.pool.fetch(q, *p)
    return DecimalJSONResponse([dict(row) for row in rows])
