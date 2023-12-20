import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import insert, select, update, and_

from api.database import (
    get_async_session,
    get_engine,
    results_to_model
)
from api.routes.security import get_groups
from api.models.object import Object, ResponseObject
from api.schemas import Objects
from api.query_parser import get_filter_query_params, QueryParser

router = APIRouter(
    prefix="/object",
    tags=["file"],
    responses={404: {"description": "Not found"}},
)


@router.get("/", response_model=list[ResponseObject])
async def get_objects(page: int = 0, page_size: int = 50, filter_query_params=Depends(get_filter_query_params), groups: list[str] = Depends(get_groups)):
    """Get all objects"""

    engine = get_engine()
    async_session = get_async_session(engine)

    query_parser = QueryParser(columns=Objects.__table__.c, query_params=filter_query_params)

    async with async_session() as session:

        # TODO: This flow should likely be refactored into a function, lets see it used once more before making the move
        select_stmt = select(*query_parser.get_select_columns())\
            .limit(page_size)\
            .offset(page_size * page)\
            .where(and_(Objects.deleted_on == None, query_parser.where_expressions()))

        # Add grouping
        if query_parser.get_group_by_column() is not None:
            select_stmt = select_stmt.group_by(query_parser.get_group_by_column()).order_by(
                query_parser.get_group_by_column()
            )

        if query_parser.get_order_by_columns() is not None and \
                query_parser.get_group_by_column() is None:
            select_stmt = select_stmt.order_by(*query_parser.get_order_by_columns())

        results = await session.execute(select_stmt)

        return results_to_model(results, ResponseObject)


@router.get("/{id}", response_model=ResponseObject)
async def get_object(id: int, groups: list[str] = Depends(get_groups)):
    """Get a single object"""

    engine = get_engine()
    async_session = get_async_session(engine)

    async with async_session() as session:

        select_stmt = select(Objects).where(and_(Objects.id == id, Objects.deleted_on == None))

        result = await session.scalar(select_stmt)

        if result is None:
            raise HTTPException(status_code=404, detail=f"Object with id ({id}) not found")

        response = ResponseObject(**result.__dict__)
        return response


@router.post("/", response_model=ResponseObject)
async def create_file(object: Object, groups: list[str] = Depends(get_groups)):
    """Create/Register a new object"""

    engine = get_engine()
    async_session = get_async_session(engine)

    async with async_session() as session:

        insert_stmt = insert(Objects).values(**object.dict()).returning(Objects)
        server_object = await session.scalar(insert_stmt)

        response = ResponseObject(**server_object.__dict__)
        await session.commit()
        return response


@router.patch("/{id}", response_model=ResponseObject)
async def patch_object(id: int, object: Object, groups: list[str] = Depends(get_groups)) -> ResponseObject:
    """Update a object"""

    engine = get_engine()
    async_session = get_async_session(engine)

    async with async_session() as session:

        update_stmt = update(Objects)\
            .where(Objects.id == id)\
            .values(**object.dict())\
            .returning(Objects)

        server_object = await session.scalar(update_stmt)

        response = ResponseObject(**server_object.__dict__)
        await session.commit()
        return response


@router.delete("/{id}")
async def delete_object(id: int, groups: list[str] = Depends(get_groups)) -> ResponseObject:
    """Delete a object"""

    engine = get_engine()
    async_session = get_async_session(engine)

    async with async_session() as session:

        delete_stmt = update(Objects)\
            .where(Objects.id == id)\
            .values(deleted_on=datetime.datetime.utcnow())\
            .returning(Objects)

        server_object = await session.scalar(delete_stmt)

        response = ResponseObject(**server_object.__dict__)
        await session.commit()
        return response