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

# Create Application.
app = FastAPI(root_path="/")

# Register Start/Stop application event handler to setup/stop the database connection
@app.on_event("startup")
async def startup_event():
    """Application startup: register the database connection and create table list."""
    await connect_to_db(app)
    await register_table_catalog(app)


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown: de-register the database connection."""
    await close_db_connection(app)


app.state.function_catalog = FunctionRegistry()

app.add_middleware(CompressionMiddleware, minimum_size=0)

# Register endpoints.
mvt_tiler = VectorTilerFactory(
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

app.include_router(mvt_tiler.router, tags=["Tiles"])

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", include_in_schema=False)
async def index(request: Request):
    """DEMO."""
    return JSONResponse({"message": "Hello World!"})
