from contextlib import asynccontextmanager

import dotenv
import uvicorn
from api.routes.dev_routes.api import convert_router
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

dotenv.load_dotenv()

import api.routes.security
from api.database import AppDatabase, get_db_url
from api.map import router as map_router
from api.match import router as match_router
from api.routes.ingest import router as ingest_router
from api.routes.object import router as object_router
from api.routes.sources import router as sources_router


@asynccontextmanager
async def setup_engine(app: FastAPI, url: str | None = None):
    """Create the shared database connection pools for the app's lifetime.

    The unified ``Database`` owns both the async and sync connection pools, so it
    is built exactly once here and shared across all requests via ``app.state.db``
    (see api/database.py dependencies). It is disposed on shutdown so its
    connections are returned to Postgres rather than leaked.
    """
    app.state.db = AppDatabase(url or get_db_url())
    yield
    await app.state.db.dispose()


app = FastAPI(
    lifespan=setup_engine,
    root_path="./",
)

origins = [
    "http://localhost:8000",
    "http://localhost:3000",
    "http://localhost:3000/",
    "http://localhost:6006",
    "https://dev.rockd.org",
    "https://staging.rockd.org",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api.routes.security.router)
app.include_router(object_router)
app.include_router(ingest_router)
app.include_router(sources_router)
app.include_router(map_router, prefix="/map")

app.include_router(convert_router, prefix="/dev")
app.include_router(match_router, prefix="/dev/match")


if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        headers=[("Access-Control-Expose-Headers", "X-Total-Count")],
    )
