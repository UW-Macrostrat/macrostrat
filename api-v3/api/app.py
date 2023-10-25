import uvicorn

from contextlib import asynccontextmanager
from typing import List

from fastapi import FastAPI

from api.models import PolygonModel
from api.database import get_engine, connect_engine, dispose_engine, select_table


@asynccontextmanager
async def setup_engine(a: FastAPI):
    """Return database client instance."""
    await connect_engine()
    yield
    await dispose_engine()


app = FastAPI(lifespan=setup_engine)


@app.get("/sources/{table}/polygons", response_model=List[PolygonModel])
async def get_sources(table: str, offset: int = 0, page_size: int = 100):
    result = await select_table(engine=get_engine(), table=table, offset=offset, page_size=page_size)
    return result.to_dict()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)