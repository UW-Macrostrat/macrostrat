import secrets
import urllib.parse
from contextlib import asynccontextmanager
from typing import List

import starlette.requests
import uvicorn
from fastapi import FastAPI, HTTPException, Response, status, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import NoResultFound, NoSuchTableError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from starlette.authentication import requires

import dotenv
dotenv.load_dotenv()

import api.routes.security
import api.database as db
from api.database import (
    connect_engine,
    dispose_engine,
    get_async_session,
    get_engine,
    patch_sources_sub_table,
    select_sources_sub_table,
)
from api.models import PolygonModel, Sources, CopyColumnRequest
from api.query_parser import ParserException
from api.routes.security import TokenData, get_groups

@asynccontextmanager
async def setup_engine(a: FastAPI):
    """Return database client instance."""
    await connect_engine()
    yield
    await dispose_engine()


app = FastAPI(
    lifespan=setup_engine
)

origins = [
    "http://localhost:8000",
    "http://localhost:3000",
    "http://localhost:3000/",
    "http://localhost:6006"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api.routes.security.router)


@app.get("/sources")
async def get_sources(response: Response, page: int = 0, page_size: int = 100, include_geom: bool = False) -> List[Sources]:
    async_session = get_async_session(get_engine())
    sources = await db.get_sources(async_session, page, page_size)

    # Delete the geom if not required
    if not include_geom:
        for source in sources:
            del source.rgeom
            del source.web_geom

    # Add the appropriate headers
    response.headers["Link"] = "/sources" + urllib.parse.urlencode({page: page + 1, page_size: page_size})

    return sources


@app.get("/sources/{table_id}/polygons", response_model=List[PolygonModel])
async def get_sub_sources(
        response: Response,
        request: starlette.requests.Request,
        table_id: int,
        page: int = 0,
        page_size: int = 100
):

    try:
        # Get the query results
        filter_query_params = [*filter(lambda x: x[0] not in ["page", "page_size"], request.query_params.items())]
        result = await select_sources_sub_table(
            engine=get_engine(),
            table_id=table_id,
            page=page,
            page_size=page_size,
            query_params=filter_query_params
        )

        # Add metadata to the response
        response.headers["X-Total-Count"] = str(await db.get_sources_sub_table_count(engine=get_engine(), table_id=table_id))

        return result.to_dict()

    except ParserException as e:
        raise HTTPException(status_code=400, detail=e)

    except NoSuchTableError:
        raise HTTPException(status_code=400, detail=f"Source table with id ({table_id}) not found")


@app.patch("/sources/{table_id}/polygons", response_model=List[PolygonModel])
async def patch_sub_sources(
        request: starlette.requests.Request,
        table_id: int,
        polygon_updates: PolygonModel,
        groups: list[int] = Depends(get_groups)
):

    if 1 not in groups:
        raise HTTPException(status_code=401, detail="User is not in admin group")

    try:
        result = await patch_sources_sub_table(
            engine=get_engine(),
            table_id=table_id,
            update_values=polygon_updates.model_dump(exclude_none=True),
            query_params=request.query_params.items()
        )

    except ParserException as e:
        raise HTTPException(status_code=400, detail=e)

    except NoSuchTableError:
        raise HTTPException(status_code=400, detail=f"Source table with id ({table_id}) not found")

    if result.rowcount == 0:
        raise HTTPException(status_code=400, detail="No rows patched, if this is unexpected please report as bug")

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.patch("/sources/{table_id}/polygons/{target_column}", response_model=List[PolygonModel])
async def patch_sub_sources(
        request: starlette.requests.Request,
        target_column: str,
        copy_column: CopyColumnRequest,
        groups: list[int] = Depends(get_groups)
):

    if 1 not in groups:
        raise HTTPException(status_code=401, detail="User is not in admin group")

    try:
        result = await db.patch_sources_sub_table_set_columns_equal(
            engine=get_engine(),
            table_id=copy_column.table_id,
            source_column=copy_column.source_column,
            target_column=target_column,
            query_params=request.query_params.items()
        )

    except ParserException as e:
        raise HTTPException(status_code=400, detail=e)

    except NoSuchTableError:
        raise HTTPException(status_code=400, detail=f"Source table with id ({copy_column.table_id}) not found")

    if result.rowcount == 0:
        raise HTTPException(status_code=400, detail="No rows patched, if this is unexpected please report as bug")

    return Response(status_code=status.HTTP_204_NO_CONTENT)



if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, headers=[("Access-Control-Expose-Headers", "X-Total-Count")])
