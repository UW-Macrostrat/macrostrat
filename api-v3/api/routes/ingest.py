import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import insert, select, update, and_
from sqlalchemy.orm import selectinload, joinedload
from pydantic import parse_obj_as

from api.database import (
    get_async_session,
    get_engine,
    results_to_model
)
from api.routes.security import get_groups
from api.models.ingest import IngestProcess, ResponseIngestProcess, ResponseIngestProcessWithObject, IngestProcessPatch
from api.schemas import IngestProcess as IngestProcessSchema
from api.query_parser import get_filter_query_params, QueryParser

router = APIRouter(
    prefix="/ingest-process",
    tags=["ingest-process"],
    responses={404: {"description": "Not found"}},
)


@router.get("", response_model=list[ResponseIngestProcess])
async def get_multiple_ingest_process(page: int = 0, page_size: int = 50, filter_query_params=Depends(get_filter_query_params), groups: list[str] = Depends(get_groups)):
    """Get all ingestion processes"""

    engine = get_engine()
    async_session = get_async_session(engine)

    query_parser = QueryParser(columns=IngestProcessSchema.__table__.c, query_params=filter_query_params)

    async with async_session() as session:

        # TODO: This flow should likely be refactored into a function, lets see it used once more before making the move
        select_stmt = select(*query_parser.get_select_columns())\
            .limit(page_size)\
            .offset(page_size * page)\
            .where(and_(query_parser.where_expressions()))

        # Add grouping
        if query_parser.get_group_by_column() is not None:
            select_stmt = select_stmt.group_by(query_parser.get_group_by_column()).order_by(
                query_parser.get_group_by_column()
            )

        if query_parser.get_order_by_columns() is not None and \
                query_parser.get_group_by_column() is None:
            select_stmt = select_stmt.order_by(*query_parser.get_order_by_columns())

        results = await session.execute(select_stmt)

        return results.all()


@router.get("/{id}", response_model=ResponseIngestProcess)
async def get_ingest_process(id: int, groups: list[str] = Depends(get_groups)):
    """Get a single object"""

    engine = get_engine()
    async_session = get_async_session(engine)

    async with async_session() as session:

        select_stmt = select(IngestProcessSchema).where(and_(IngestProcessSchema.id == id))

        result = await session.scalar(select_stmt)

        if result is None:
            raise HTTPException(status_code=404, detail=f"IngestProcess with id ({id}) not found")

        response = ResponseIngestProcess(**result.__dict__)
        return response


@router.post("", response_model=ResponseIngestProcessWithObject)
async def create_ingest_process(object: IngestProcess, groups: list[str] = Depends(get_groups)):
    """Create/Register a new object"""

    engine = get_engine()
    async_session = get_async_session(engine,  expire_on_commit=False)

    async with async_session() as session:

        stmt = insert(IngestProcessSchema).values(**object.dict()).returning(IngestProcessSchema).options(selectinload(IngestProcessSchema.object))
        server_object = await session.scalar(stmt)

        await session.commit()

    return server_object


@router.patch("/{id}", response_model=ResponseIngestProcess)
async def patch_ingest_process(id: int, object: IngestProcessPatch, groups: list[str] = Depends(get_groups)) -> ResponseIngestProcess:
    """Update a object"""

    engine = get_engine()
    async_session = get_async_session(engine)

    async with async_session() as session:

        update_stmt = update(IngestProcessSchema)\
            .where(IngestProcessSchema.id == id)\
            .values(**object.dict())\
            .returning(IngestProcessSchema)

        server_object = await session.scalar(update_stmt)

        response = ResponseIngestProcess(**server_object.__dict__)
        await session.commit()
        return response


@router.delete("/{id}")
async def delete_ingest_process(id: int, groups: list[str] = Depends(get_groups)) -> ResponseIngestProcess:
    """Delete a object"""

    engine = get_engine()
    async_session = get_async_session(engine)

    async with async_session() as session:

        delete_stmt = update(IngestProcessSchema)\
            .where(IngestProcessSchema.id == id)\
            .values(deleted_on=datetime.datetime.utcnow())\
            .returning(IngestProcessSchema)

        server_object = await session.scalar(delete_stmt)

        response = ResponseIngestProcess(**server_object.__dict__)
        await session.commit()
        return response