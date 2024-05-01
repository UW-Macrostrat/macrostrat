import re
import urllib.parse
from typing import List, Literal, Union

from slugify import slugify
import starlette.requests
from fastapi import APIRouter, HTTPException, Response, status, Depends
from sqlalchemy import select, func, update, insert
from sqlalchemy.exc import NoResultFound, NoSuchTableError

import dotenv

dotenv.load_dotenv()

import api.routes.security
import api.database as db
from api.database import (
    get_table,
    get_async_session,
    get_engine,
    patch_sources_sub_table,
    select_sources_sub_table,
)
from api.models.geometries import (
    PolygonModel, PolygonRequestModel, PolygonResponseModel, CopyColumnRequest, LineStringModel, PointModel
)
import api.models.source as Sources
from api.query_parser import ParserException
from api.routes.security import has_access

import api.schemas as schemas

router = APIRouter(
    prefix="/sources",
    tags=["sources"],
    responses={
        404: {
            "description": "Not found"
        }
    },
)


@router.get("")
async def get_sources(response: Response, page: int = 0, page_size: int = 100, include_geom: bool = False) -> List[
    Sources.Get]:
    async_session = get_async_session(get_engine())
    sources = await db.get_sources(async_session, page, page_size)

    # Delete the geom if not required
    if not include_geom:
        for source in sources:
            del source.rgeom
            del source.web_geom

    # Add the appropriate headers
    response.headers["Link"] = "/sources" + urllib.parse.urlencode({
                                                                       page: page + 1,
                                                                       page_size: page_size
                                                                   })

    return sources


@router.get("/{source_id}")
async def get_source(source_id: int) -> Sources.Get:
    """Get a single object"""

    engine = get_engine()
    async_session = get_async_session(engine)

    async with async_session() as session:
        select_stmt = select(
            *[c for c in schemas.Sources.__table__.c if c.name not in ['rgeom', 'web_geom']]
        ).where(schemas.Sources.source_id == source_id)

        results = await session.execute(select_stmt)

        if results is None:
            raise HTTPException(status_code=404, detail=f"Object with id ({id}) not found")

        return db.results_to_model(results, Sources.Get)[0]


@router.patch("/{source_id}")
async def patch_source(source_id: int, source: Sources.Patch, user_has_access: bool = Depends(has_access)) -> Sources.Get:
    """Patch a source"""

    if not user_has_access:
        raise HTTPException(status_code=401, detail="User does not have access to patch object")

    engine = get_engine()
    async_session = get_async_session(engine)

    async with async_session() as session:
        update_stmt = update(schemas.Sources)\
            .where(schemas.Sources.source_id == source_id)\
            .values(**source.model_dump(exclude_none=True))\
            .returning(schemas.Sources)

        server_object = await session.scalar(update_stmt)

        response = Sources.Get(**server_object.__dict__)
        await session.commit()
        return response


@router.post("")
async def post_source(source: Sources.Post, user_has_access: bool = Depends(has_access)) -> Sources.Get:
    """Post a source"""

    if not user_has_access:
        raise HTTPException(status_code=401, detail="User does not have access to post object")

    engine = get_engine()
    async_session = get_async_session(engine)

    if source.slug is None:
        source.slug = re.sub(r"\W", "_", slugify(source.name, max_length=10))
    source.primary_table = source.slug + "_polygons"

    async with async_session() as session:
        insert_stmt = insert(schemas.Sources).values(**source.model_dump()).returning(schemas.Sources)
        server_object = await session.scalar(insert_stmt)

        response = Sources.Get(**server_object.__dict__)
        await session.commit()
        return response


@router.get("/{table_id}/geometries")
async def get_sub_sources_geometries(
        table_id: int
):
    result = {}

    engine = get_engine()
    async with engine.begin() as conn:

        for geometry in ["polygons", "linestrings", "points"]:

            try:
                table = await get_table(conn, table_id, geometry)
                result[geometry] = True

            except:
                result[geometry] = False

    return result


async def get_sub_sources_helper(
        response: Response,
        request: starlette.requests.Request,
        table_id: int,
        geometry_type: Literal["polygons", "linestrings", "points"],
        page: int = 0,
        page_size: int = 100
) -> List[Union[PolygonResponseModel, LineStringModel, PointModel]]:
    try:
        # Get the query results
        filter_query_params = [*filter(lambda x: x[0] not in ["page", "page_size"], request.query_params.multi_items())]
        result = await select_sources_sub_table(
            engine=get_engine(),
            table_id=table_id,
            geometry_type=geometry_type,
            page=page,
            page_size=page_size,
            query_params=filter_query_params
        )

        # Add metadata to the response
        response.headers["X-Total-Count"] = str(
            await db.get_sources_sub_table_count(
                engine=get_engine(),
                query_params=filter_query_params,
                table_id=table_id,
                geometry_type=geometry_type
            )
        )

        return result.to_dict()

    except ParserException as e:
        raise HTTPException(status_code=400, detail=e)

    except NoSuchTableError:
        raise HTTPException(status_code=400, detail=f"Source table with id ({table_id}) not found")


@router.get("/{table_id}/polygons", response_model=List[PolygonResponseModel])
async def get_sub_sources(
        response: Response,
        request: starlette.requests.Request,
        table_id: int,
        page: int = 0,
        page_size: int = 100
):
    return await get_sub_sources_helper(response, request, table_id, "polygons", page, page_size)


@router.get("/{table_id}/points", response_model=List[PointModel])
async def get_sub_sources(
        response: Response,
        request: starlette.requests.Request,
        table_id: int,
        page: int = 0,
        page_size: int = 100
):
    return await get_sub_sources_helper(response, request, table_id, "points", page, page_size)


@router.get("/{table_id}/linestrings", response_model=List[LineStringModel])
async def get_sub_sources(
        response: Response,
        request: starlette.requests.Request,
        table_id: int,
        page: int = 0,
        page_size: int = 100
):
    return await get_sub_sources_helper(response, request, table_id, "linestrings", page, page_size)


@router.patch("/{table_id}/{geometry_type}")
async def patch_sub_sources(
        request: starlette.requests.Request,
        table_id: int,
        geometry_type: Literal["polygons", "linestrings", "points"],
        updates: Union[PolygonRequestModel, LineStringModel, PointModel],
        user_has_access: bool = Depends(has_access)
) -> List[Union[PolygonResponseModel, LineStringModel, PointModel]]:
    if not user_has_access:
        raise HTTPException(status_code=401, detail="User does not have access to patch object")

    try:
        result = await patch_sources_sub_table(
            engine=get_engine(),
            table_id=table_id,
            geometry_type=geometry_type,
            update_values=updates.model_dump(exclude_none=True),
            query_params=request.query_params.multi_items()
        )

    except ParserException as e:
        raise HTTPException(status_code=400, detail=e)

    except NoSuchTableError:
        raise HTTPException(status_code=400, detail=f"Source table with id ({table_id}) not found")

    if result.rowcount == 0:
        raise HTTPException(status_code=400, detail="No rows patched, if this is unexpected please report as bug")

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.patch("/{table_id}/{geometry_type}/{target_column}",
              response_model=List[Union[PolygonResponseModel, LineStringModel, PointModel]])
async def patch_sub_sources(
        request: starlette.requests.Request,
        target_column: str,
        table_id: int,
        geometry_type: Literal["polygons", "linestrings", "points"],
        copy_column: CopyColumnRequest,
        user_has_access: bool = Depends(has_access),
):
    if not user_has_access:
        raise HTTPException(status_code=401, detail="User does not have access to patch object")

    try:
        result = await db.patch_sources_sub_table_set_columns_equal(
            engine=get_engine(),
            table_id=table_id,
            geometry_type=geometry_type,
            source_column=copy_column.source_column,
            target_column=target_column,
            query_params=request.query_params.multi_items()
        )

    except ParserException as e:
        raise HTTPException(status_code=400, detail=e)

    except NoSuchTableError:
        raise HTTPException(status_code=400, detail=f"Source table with id ({copy_column.table_id}) not found")

    if result.rowcount == 0:
        raise HTTPException(status_code=400, detail="No rows patched, if this is unexpected please report as bug")

    return Response(status_code=status.HTTP_204_NO_CONTENT)
