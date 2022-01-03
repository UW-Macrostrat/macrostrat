from timvt.db import close_db_connection, connect_to_db
from timvt.factory import VectorTilerFactory
from fastapi import FastAPI, Request
from starlette_cramjam.middleware import CompressionMiddleware
from starlette.responses import JSONResponse

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
app.include_router(mvt_tiler.router, tags=["Tiles"])


@app.get("/", include_in_schema=False)
async def index(request: Request):
    """DEMO."""
    return JSONResponse(request.app.state.table_catalog)
