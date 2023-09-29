from typing import Any, Callable, Dict, List, Literal, Optional
from os import environ
from buildpg import render
from fastapi import (BackgroundTasks, Depends, FastAPI, HTTPException, Path,
                     Query, Request)
from fastapi_utils.tasks import repeat_every
from macrostrat.utils import get_logger, setup_stderr_logs
from macrostrat.utils.timer import Timer
from morecantile import Tile, TileMatrixSet
from pydantic import BaseModel
from starlette.responses import JSONResponse, Response
from starlette_cramjam.middleware import CompressionMiddleware
from timvt.db import close_db_connection, connect_to_db, register_table_catalog
from timvt.dependencies import TileParams
from timvt.factory import (TILE_RESPONSE_PARAMS, VectorTilerFactory,
                           queryparams_to_kwargs)
from timvt.layer import FunctionRegistry
from timvt.resources.enums import MimeTypes

from .cache import get_tile_from_cache, set_cached_tile
from .function_layer import StoredFunction
from .utils import CacheMode, CacheStatus, TileResponse

"""timvt.endpoints.factory: router factories."""

from typing import Any, Callable, Dict, List, Literal, Optional
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, FastAPI, Path, Query
from morecantile import Tile
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from timvt.dependencies import LayerParams, TileParams
from timvt.layer import Function, Layer, Table
from timvt.models.mapbox import TileJSON
from timvt.models.OGC import TileMatrixSetList
from timvt.resources.enums import MimeTypes
from titiler.core.errors import DEFAULT_STATUS_CODES, add_exception_handlers
from titiler.core.factory import TilerFactory

from .image_tiles import MapnikLayerFactory, prepare_image_tile_subsystem

# Wire up legacy postgres database
if not environ.get("DATABASE_URL") and "POSTGRES_DB" in environ:
    environ["DATABASE_URL"] = environ["POSTGRES_DB"]


def _first_value(values: List[Any], default: Any = None):
    """Return the first not None value."""
    return next(filter(lambda x: x is not None, values), default)


log = get_logger(__name__)

app = FastAPI(prefix="/")

app.state.timvt_function_catalog = FunctionRegistry()


# Register Start/Stop application event handler to setup/stop the database connection
@app.on_event("startup")
async def startup_event():
    """Application startup: register the database connection and create table list."""
    setup_stderr_logs("macrostrat_tileserver", "timvt")
    await connect_to_db(app)
    # await register_table_catalog(app)
    prepare_image_tile_subsystem()


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


MapnikLayerFactory(app)

cog = TilerFactory()

app.include_router(cog.router, prefix="/cog", tags=["Cloud Optimized GeoTIFF"])
add_exception_handlers(app, DEFAULT_STATUS_CODES)


class CachedVectorTilerFactory(VectorTilerFactory):
    def register_tiles(self):
        """Register /tiles endpoints."""

        @self.router.get(
            "/{TileMatrixSetId}/{layer}/{z}/{x}/{y}", **TILE_RESPONSE_PARAMS
        )
        @self.router.get("/{layer}/{z}/{x}/{y}", **TILE_RESPONSE_PARAMS)
        async def tile(
            request: Request,
            background_tasks: BackgroundTasks,
            tile: Tile = Depends(TileParams),
            TileMatrixSetId: Literal[tuple(self.supported_tms.list())] = self.default_tms,
            layer=Depends(self.layer_dependency),
            cache: CacheMode = CacheMode.prefer,
            # If cache query arg is set, don't cache the tile
        ):
            """Return vector tile."""
            pool = request.app.state.pool
            tms = self.supported_tms.get(TileMatrixSetId)

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

        @self.router.get(
            "/{TileMatrixSetId}/{layer}/tilejson.json",
            response_model=TileJSON,
            responses={200: {"description": "Return a tilejson"}},
            response_model_exclude_none=True,
        )
        @self.router.get(
            "/{layer}/tilejson.json",
            response_model=TileJSON,
            responses={200: {"description": "Return a tilejson"}},
            response_model_exclude_none=True,
        )
        async def tilejson(
            request: Request,
            layer=Depends(self.layer_dependency),
            TileMatrixSetId: Literal[tuple(self.supported_tms.list())] = self.default_tms,
            minzoom: Optional[int] = Query(
                None, description="Overwrite default minzoom."
            ),
            maxzoom: Optional[int] = Query(
                None, description="Overwrite default maxzoom."
            ),
        ):
            """Return TileJSON document."""
            tms = self.supported_tms.get(TileMatrixSetId)

            path_params: Dict[str, Any] = {
                "TileMatrixSetId": tms.identifier,
                "layer": layer.id,
                "z": "{z}",
                "x": "{x}",
                "y": "{y}",
            }
            tile_endpoint = self.url_for(request, "tile", **path_params)

            qs_key_to_remove = ["tilematrixsetid", "minzoom", "maxzoom"]
            query_params = [
                (key, value)
                for (key, value) in request.query_params._list
                if key.lower() not in qs_key_to_remove
            ]

            if query_params:
                tile_endpoint += f"?{urlencode(query_params)}"

            # Get Min/Max zoom from layer settings if tms is the default tms
            if tms.identifier == layer.default_tms:
                minzoom = _first_value([minzoom, layer.minzoom])
                maxzoom = _first_value([maxzoom, layer.maxzoom])

            minzoom = minzoom if minzoom is not None else tms.minzoom
            maxzoom = maxzoom if maxzoom is not None else tms.maxzoom

            return {
                "minzoom": minzoom,
                "maxzoom": maxzoom,
                "name": layer.id,
                "bounds": layer.bounds,
                "tiles": [tile_endpoint],
            }


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

# Core macrostrat layers
for layer in ["carto-slim", "carto"]:
    lyr = CachedStoredFunction(
        type="StoredFunction",
        sql="",
        id=layer,
        function_name="tile_layers." + layer.replace("-", "_"),
    )
    app.state.function_catalog.register(lyr)

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

# Serve a single macrostrat map
app.state.function_catalog.register(
    StoredFunction(
        type="StoredFunction",
        sql="",
        id="map",
        function_name="tile_layers.map",
    )
)

# All maps from the 'maps' schema.
# Note: this is likely to be inefficient and should only be used
# for internal purposes, and not cached
app.state.function_catalog.register(
    StoredFunction(
        type="StoredFunction",
        sql="",
        id="all-maps",
        function_name="tile_layers.all_maps",
    )
)

# Legacy routes postfixed with ".mvt"
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


# Open CORS policy
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
)

