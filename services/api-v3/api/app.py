from contextlib import asynccontextmanager

import dotenv
import uvicorn
from api.routes.dev_routes.convert import convert_router
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

dotenv.load_dotenv()

import api.routes.security
from api.database import connect_engine, dispose_engine
from api.map import router as map_router
from api.match import router as match_router
from api.routes.ingest import router as ingest_router
from api.routes.object import router as object_router
from api.routes.sources import router as sources_router


@asynccontextmanager
async def setup_engine(app: FastAPI):
    """Return database client instance."""
    app.state.engine = await connect_engine()
    yield
    await dispose_engine()


app = FastAPI(
    lifespan=setup_engine,
    root_path="./",
)

origins = [
    "http://localhost:8000",
    "http://localhost:3000",
    "http://localhost:3000/",
    "http://localhost:6006",
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
