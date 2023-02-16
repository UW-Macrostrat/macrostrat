from timvt.db import close_db_connection, connect_to_db, register_table_catalog
from timvt.factory import VectorTilerFactory
from fastapi import FastAPI, Request
from starlette_cramjam.middleware import CompressionMiddleware
from starlette.responses import JSONResponse
from timvt.layer import FunctionRegistry
from timvt.factory import TILE_RESPONSE_PARAMS, queryparams_to_kwargs
from .function_layer import StoredFunction
from timvt.dependencies import TileParams
from fastapi import Depends
from starlette.responses import Response
from timvt.resources.enums import MimeTypes
from morecantile import tms
from fastapi.middleware.cors import CORSMiddleware
from fastapi_utils.timing import add_timing_middleware
from .image_tiles import mapnik_layers, build_layer_cache
from macrostrat.utils import setup_stderr_logs
from morecantile import Tile, TileMatrixSet
from fastapi import BackgroundTasks
from .utils import prepared_statement
from buildpg import render
from macrostrat.utils import get_logger
from macrostrat.utils.timer import Timer

log = get_logger(__name__)

# Create Application.
app = FastAPI(root_path="/tiles/")


# Register Start/Stop application event handler to setup/stop the database connection
@app.on_event("startup")
async def startup_event():
    """Application startup: register the database connection and create table list."""
    setup_stderr_logs("macrostrat_tileserver")
    await connect_to_db(app)
    await register_table_catalog(app)
    build_layer_cache()


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown: de-register the database connection."""
    await close_db_connection(app)


app.state.function_catalog = FunctionRegistry()

app.add_middleware(CompressionMiddleware, minimum_size=0)


class CachedVectorTilerFactory(VectorTilerFactory):
    async def get_tile_from_cache(self, pool, layer, tile, tms):
        """Get tile data from cache."""
        # Get the tile from the tile_cache.tile table
        async with pool.acquire() as conn:
            q, p = render(
                prepared_statement("get-cached-tile"),
                x=tile.x,
                y=tile.y,
                z=tile.z,
                tms=None,
                layer=layer.id,
            )

            return await conn.fetchval(q, *p)

    async def set_cached_tile(self, pool, layer, tile, content):
        async with pool.acquire() as conn:
            q, p = render(
                prepared_statement("set-cached-tile"),
                x=tile.x,
                y=tile.y,
                z=tile.z,
                tile=content,
                layers=[layer.id],
                profile=layer.id,
            )
            await conn.execute(q, *p)

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
                content = await self.get_tile_from_cache(pool, layer, tile, tms)
                timer._add_step("check_cache")
                if content is not None:
                    return Response(
                        content,
                        media_type=MimeTypes.pbf.value,
                        headers={
                            "X-Tile-Cache": "hit",
                            "Server-Timing": timer.server_timings(),
                        },
                    )

            content = await layer.get_tile(pool, tile, tms, **kwargs)
            timer._add_step("get_tile")

            if should_cache:
                background_tasks.add_task(
                    self.set_cached_tile, pool, layer, tile, content
                )

            return Response(
                content,
                media_type=MimeTypes.pbf.value,
                headers={
                    "X-Tile-Cache": "miss",
                    "Server-Timing": timer.server_timings(),
                },
            )


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

app.state.function_catalog.register(
    StoredFunction(
        type="StoredFunction",
        sql="",
        id="carto-slim-rotated",
        function_name="corelle_macrostrat.carto_slim_rotated",
    )
)

app.mount("/image-layers", mapnik_layers)

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
