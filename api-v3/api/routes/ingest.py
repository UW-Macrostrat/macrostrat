import os

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import insert, select, update, and_
from sqlalchemy.orm import selectinload, joinedload, defer
import minio

from api.database import (
    get_async_session,
    get_engine,
    results_to_model
)
from api.routes.security import has_access
import api.models.ingest as IngestProcessModel
import api.models.object as Object
from api.schemas import IngestProcess as IngestProcessSchema, ObjectGroup, Sources
from api.query_parser import get_filter_query_params, QueryParser

router = APIRouter(
    prefix="/ingest-process",
    tags=["ingest-process"],
    responses={404: {"description": "Not found"}},
)


@router.get("", response_model=list[IngestProcessModel.Get])
async def get_multiple_ingest_process(page: int = 0, page_size: int = 50, filter_query_params=Depends(get_filter_query_params)):
    """Get all ingestion processes"""

    engine = get_engine()
    async_session = get_async_session(engine)

    query_parser = QueryParser(columns=IngestProcessSchema.__table__.c, query_params=filter_query_params)

    async with async_session() as session:

        # TODO: This flow should likely be refactored into a function, lets see it used once more before making the move
        select_stmt = select(IngestProcessSchema)\
            .limit(page_size)\
            .offset(page_size * page)\
            .where(and_(query_parser.where_expressions()))\
            .options(joinedload(IngestProcessSchema.source).defer(Sources.rgeom).defer(Sources.web_geom))

        results = await session.execute(select_stmt)

        return map(lambda x: x[0], results.all())


@router.get("/{id}", response_model=IngestProcessModel.Get)
async def get_ingest_process(id: int):
    """Get a single object"""

    engine = get_engine()
    async_session = get_async_session(engine)

    async with async_session() as session:

        select_stmt = select(IngestProcessSchema).where(and_(IngestProcessSchema.id == id))\
            .options(joinedload(IngestProcessSchema.source).defer(Sources.rgeom).defer(Sources.web_geom))

        result = await session.scalar(select_stmt)

        if result is None:
            raise HTTPException(status_code=404, detail=f"IngestProcess with id ({id}) not found")

        return result


@router.post("", response_model=IngestProcessModel.Get)
async def create_ingest_process(object: IngestProcessModel.Post, user_has_access: bool = Depends(has_access)):
    """Create/Register a new object"""

    if not user_has_access:
        raise HTTPException(status_code=403, detail="User does not have access to create an object")

    engine = get_engine()
    async_session = get_async_session(engine,  expire_on_commit=False)

    async with async_session() as session:

        object_group_stmt = insert(ObjectGroup).values().returning(ObjectGroup)
        object_group = await session.scalar(object_group_stmt)

        stmt = insert(IngestProcessSchema).values(**object.model_dump(), object_group_id=object_group.id).returning(IngestProcessSchema)

        server_object = await session.scalar(stmt)

        server_object.source = await session.scalar(select(Sources).where(Sources.source_id == server_object.source_id))

        await session.commit()

    return server_object


@router.patch("/{id}", response_model=IngestProcessModel.Get)
async def patch_ingest_process(
        id: int,
        object: IngestProcessModel.Patch,
        user_has_access: bool = Depends(has_access)
):
    """Update a object"""

    if not user_has_access:
        raise HTTPException(status_code=403, detail="User does not have access to create an object")

    engine = get_engine()
    async_session = get_async_session(engine)

    async with async_session() as session:

        update_stmt = update(IngestProcessSchema)\
            .where(IngestProcessSchema.id == id)\
            .values(**object.model_dump(exclude_unset=True))\
            .returning(IngestProcessSchema)

        server_object = await session.scalar(update_stmt)

        response = IngestProcessModel.Get(**server_object.__dict__)
        await session.commit()
        return response


@router.get("/{id}/objects", response_model=list[Object.GetSecureURL])
async def get_ingest_process_objects(id: int):
    """Get all objects for an ingestion process"""

    engine = get_engine()
    async_session = get_async_session(engine)

    async with async_session() as session:

        select_stmt = select(IngestProcessSchema).where(and_(IngestProcessSchema.id == id))
        ingest_process = await session.scalar(select_stmt)

        object_stmt = select(ObjectGroup).where(ObjectGroup.id == ingest_process.object_group_id).options(selectinload(ObjectGroup.objects))
        objects_iterator = await session.execute(object_stmt)
        schema_objects = objects_iterator.scalar().objects

    if len(schema_objects) == 0:
        return []

    try:
        # Attach the secure url
        first_object = schema_objects[0]
        m = minio.Minio(endpoint=first_object.host, access_key=os.environ['access_key'], secret_key=os.environ['secret_key'], secure=True)

        for obj in schema_objects:
            obj.pre_signed_url = m.presigned_get_object(bucket_name=obj.bucket, object_name=obj.key)

        return schema_objects

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get secure url for object: {e}"
        )
