from timvt.db import close_db_connection, connect_to_db
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

# Create Application.
app = FastAPI(root_path="/tiles")

# Register Start/Stop application event handler to setup/stop the database connection
@app.on_event("startup")
async def startup_event():
    """Application startup: register the database connection and create table list."""
    await connect_to_db(app)


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown: de-register the database connection."""
    await close_db_connection(app)


app.add_middleware(CompressionMiddleware, minimum_size=0)

# Register endpoints.
mvt_tiler = VectorTilerFactory(
    with_tables_metadata=True,
    with_functions_metadata=True,  # add Functions metadata endpoints (/functions.json, /{function_name}.json)
    with_viewer=True,
)

carto_layer = StoredFunction(
    type="StoredFunction", sql="", id="carto", function_name="tile_layers.carto"
)


@app.get(
    "/tiles/carto/{z}/{x}/{y}",
    **TILE_RESPONSE_PARAMS,
    tags=["Tiles"],
)
async def tile(
    request: Request,
    tile=Depends(TileParams),
):
    """Return vector tile."""
    pool = request.app.state.pool

    kwargs = queryparams_to_kwargs(
        request.query_params, ignore_keys=["tilematrixsetid"]
    )
    _tms = tms.get("WebMercatorQuad")
    content = await carto_layer.get_tile(pool, tile, _tms, **kwargs)

    return Response(bytes(content), media_type=MimeTypes.pbf.value)


app.include_router(mvt_tiler.router, tags=["Tiles"])


@app.get("/", include_in_schema=False)
async def index(request: Request):
    """DEMO."""
    return JSONResponse(request.app.state.table_catalog)
