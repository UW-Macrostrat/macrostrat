from fastapi import BackgroundTasks, Depends, FastAPI, Request
from macrostrat.utils import get_logger, setup_stderr_logs
from macrostrat.utils.timer import Timer
from morecantile import Tile, TileMatrixSet
from starlette.responses import JSONResponse
from starlette_cramjam.middleware import CompressionMiddleware
from timvt.db import close_db_connection, connect_to_db, register_table_catalog
from timvt.dependencies import TileParams
from timvt.factory import (
    TILE_RESPONSE_PARAMS,
    VectorTilerFactory,
    queryparams_to_kwargs,
)
from timvt.layer import FunctionRegistry

from .cache import get_tile_from_cache, set_cached_tile
from .function_layer import StoredFunction
from .image_tiles import build_layer_cache, MapnikLayerFactory
from .utils import TileResponse, CacheMode, CacheStatus
from fastapi_utils.tasks import repeat_every
from buildpg import render
from fastapi import HTTPException
from pydantic import BaseModel

log = get_logger(__name__)

app = FastAPI(prefix="/tiles")


# Register Start/Stop application event handler to setup/stop the database connection
@app.on_event("startup")
async def startup_event():
    """Application startup: register the database connection and create table list."""
    setup_stderr_logs("macrostrat_tileserver")
    await connect_to_db(app)
    # await register_table_catalog(app)
    build_layer_cache()


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


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown: de-register the database connection."""
    await close_db_connection(app)


app.state.function_catalog = FunctionRegistry()

app.add_middleware(CompressionMiddleware, minimum_size=0)


class CachedVectorTilerFactory(VectorTilerFactory):
    def register_tiles(self):
        """Register /tiles endpoints."""
        # super().register_tiles()

        @self.router.get(
            "/{layer}/{z}/{x}/{y}.pbf",
            **TILE_RESPONSE_PARAMS,
            tags=["Tiles"],
            deprecated=True,
        )
        @self.router.get(
            "/{layer}/{z}/{x}/{y}.mvt",
            **TILE_RESPONSE_PARAMS,
            tags=["Tiles"],
            deprecated=True,
        )
        @self.router.get(
            "/{TileMatrixSetId}/{layer}/{z}/{x}/{y}.pbf",
            **TILE_RESPONSE_PARAMS,
            tags=["Tiles"],
            deprecated=True,
        )
        @self.router.get(
            "/{layer}/{z}/{x}/{y}",
            **TILE_RESPONSE_PARAMS,
            tags=["Tiles"],
        )
        @self.router.get(
            "/{TileMatrixSetId}/{layer}/{z}/{x}/{y}",
            **TILE_RESPONSE_PARAMS,
            tags=["Tiles"],
        )
        async def tile(
            request: Request,
            background_tasks: BackgroundTasks,
            tile: Tile = Depends(TileParams),
            tms: TileMatrixSet = Depends(self.tms_dependency),
            layer=Depends(self.layer_dependency),
            cache: CacheMode = CacheMode.prefer,
            # If cache query arg is set, don't cache the tile
        ):
            """Return vector tile."""
            pool = request.app.state.pool

            timer = Timer()

            kwargs = queryparams_to_kwargs(
                request.query_params, ignore_keys=["tilematrixsetid"]
            )

            should_cache = (
                isinstance(layer, CachedStoredFunction) and cache != CacheMode.bypass
            )

            if should_cache:
                content = await get_tile_from_cache(pool, layer.id, tile, None)
                timer._add_step("check_cache")
                if content is not None:
                    return TileResponse(content, timer, cache_status=CacheStatus.hit)

            if cache == CacheMode.force:
                raise HTTPException(
                    status_code=404,
                    detail="Tile not found in cache",
                    header={
                        "Server-Timing": timer.server_timings(),
                        "X-Tile-Cache": CacheStatus.miss,
                    },
                )

            content = await layer.get_tile(pool, tile, tms, **kwargs)
            timer._add_step("get_tile")

            cache_status = CacheStatus.bypass
            if should_cache:
                background_tasks.add_task(
                    set_cached_tile, pool, layer.id, tile, content
                )
                cache_status = CacheStatus.miss

            return TileResponse(content, timer, cache_status=cache_status)


# Register endpoints.
mvt_tiler = CachedVectorTilerFactory(
    with_tables_metadata=True,
    with_functions_metadata=True,  # add Functions metadata endpoints (/functions.json, /{function_name}.json)
    with_viewer=False,
)


class CachedStoredFunction(StoredFunction):
    ...


# Tile layer definitions start here.
# Note: these are defined somewhat redundantly.
# Our eventual goal will be to store these configurations in the database.

for layer in ["carto-slim", "carto"]:
    lyr = CachedStoredFunction(
        type="StoredFunction",
        sql="",
        id=layer,
        function_name="tile_layers." + layer.replace("-", "_"),
    )
    app.state.function_catalog.register(lyr)

MapnikLayerFactory(app)

# Corelle-macrostrat layers
for layer in ["carto_slim_rotated", "igcp_orogens", "igcp_orogens_rotated"]:
    app.state.function_catalog.register(
        StoredFunction(
            type="StoredFunction",
            sql="",
            id=layer.replace("_", "-"),
            function_name="corelle_macrostrat." + layer,
        )
    )

# Weaver point-data management system
app.state.function_catalog.register(
    StoredFunction(
        type="StoredFunction",
        sql="",
        id="weaver-tile",
        function_name="weaver_api.weaver_tile",
    )
)

# Individual macrostrat maps
app.state.function_catalog.register(
    StoredFunction(
        type="StoredFunction",
        sql="",
        id="map",
        function_name="tile_layers.map",
    )
)

app.include_router(mvt_tiler.router, tags=["Tiles"])

# def MapLayerDepends():
#     pass


# single_map_tiler = VectorTilerFactory(
#     with_tables_metadata=False,
#     with_functions_metadata=False,  # add Functions metadata endpoints (/functions.json, /{function_name}.json)
#     with_viewer=False,
#     layer_dependency=MapLayerDepends(),
# )

# class MapParams(BaseModel):
#     map_id: int

# app.include_router(
#     single_map_tiler.router,
#     prefix="/map/{map_id}",
#     tags=["map"],
#     dependencies=[Depends(MapParams)],
# )


@app.get("/", include_in_schema=False)
async def index(request: Request):
    """DEMO."""
    return JSONResponse({"message": "Macrostrat Tileserver"})
