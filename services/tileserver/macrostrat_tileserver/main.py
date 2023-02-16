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
from .utils import TileResponse
from fastapi_utils.tasks import repeat_every
from buildpg import render

log = get_logger(__name__)

app = FastAPI(root_path="/tiles/")


# Register Start/Stop application event handler to setup/stop the database connection
@app.on_event("startup")
async def startup_event():
    """Application startup: register the database connection and create table list."""
    setup_stderr_logs("macrostrat_tileserver")
    await connect_to_db(app)
    await register_table_catalog(app)
    build_layer_cache()


@app.on_event("startup")
@repeat_every(seconds=600)  # 10 minutes
async def truncate_tile_cache_if_needed() -> None:
    """Truncate the tile cache if it's too big."""
    pool = app.state.pool
    async with pool.acquire() as conn:
        max_size = 1e10

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
            "/tiles/{layer}/{z}/{x}/{y}.pbf",
            **TILE_RESPONSE_PARAMS,
            tags=["Tiles"],
            deprecated=True,
        )
        @self.router.get(
            "/tiles/{TileMatrixSetId}/{layer}/{z}/{x}/{y}.pbf",
            **TILE_RESPONSE_PARAMS,
            tags=["Tiles"],
            deprecated=True,
        )
        @self.router.get(
            "/tiles/{layer}/{z}/{x}/{y}",
            **TILE_RESPONSE_PARAMS,
            tags=["Tiles"],
        )
        @self.router.get(
            "/tiles/{TileMatrixSetId}/{layer}/{z}/{x}/{y}",
            **TILE_RESPONSE_PARAMS,
            tags=["Tiles"],
        )
        async def tile(
            request: Request,
            background_tasks: BackgroundTasks,
            tile: Tile = Depends(TileParams),
            tms: TileMatrixSet = Depends(self.tms_dependency),
            layer=Depends(self.layer_dependency),
        ):
            """Return vector tile."""
            pool = request.app.state.pool

            timer = Timer()

            kwargs = queryparams_to_kwargs(
                request.query_params, ignore_keys=["tilematrixsetid"]
            )

            should_cache = isinstance(layer, StoredFunction)

            if should_cache:
                content = await get_tile_from_cache(pool, layer.id, tile, None)
                timer._add_step("check_cache")
                if content is not None:
                    return TileResponse(content, timer, cache_hit=True)

            content = await layer.get_tile(pool, tile, tms, **kwargs)
            timer._add_step("get_tile")

            if should_cache:
                background_tasks.add_task(
                    set_cached_tile, pool, layer.id, tile, content
                )

            return TileResponse(content, timer, cache_hit=False)


# Register endpoints.
mvt_tiler = CachedVectorTilerFactory(
    with_tables_metadata=True,
    with_functions_metadata=True,  # add Functions metadata endpoints (/functions.json, /{function_name}.json)
    with_viewer=True,
)


for layer in ["carto-slim", "carto"]:
    lyr = StoredFunction(
        type="StoredFunction",
        sql="",
        id=layer,
        function_name="tile_layers." + layer.replace("-", "_"),
    )
    app.state.function_catalog.register(lyr)

MapnikLayerFactory(app)

app.state.function_catalog.register(
    StoredFunction(
        type="StoredFunction",
        sql="",
        id="carto-slim-rotated",
        function_name="corelle_macrostrat.carto_slim_rotated",
    )
)

app.include_router(mvt_tiler.router, tags=["Tiles"])

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )


@app.get("/", include_in_schema=False)
async def index(request: Request):
    """DEMO."""
    return JSONResponse({"message": "Hello World!"})
