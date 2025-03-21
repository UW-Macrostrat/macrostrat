import datetime
import os
from typing import Union

import api.models.object as Object
import api.schemas as schemas
import minio
import starlette.requests
from api.database import get_async_session, get_engine, results_to_model
from api.query_parser import QueryParser, get_filter_query_params
from api.routes.security import has_access
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import and_, insert, select, update
from starlette.datastructures import UploadFile as StarletteUploadFile

router = APIRouter(
    prefix="/object",
    tags=["file"],
    responses={404: {"description": "Not found"}},
)


@router.get("", response_model=list[Object.Get])
async def get_objects(
    page: int = 0,
    page_size: int = 50,
    filter_query_params=Depends(get_filter_query_params),
):
    """Get all objects"""

    engine = get_engine()
    async_session = get_async_session(engine)

    query_parser = QueryParser(
        columns=schemas.Object.__table__.c, query_params=filter_query_params
    )

    async with async_session() as session:

        # TODO: This flow should likely be refactored into a function, lets see it used once more before making the move
        select_stmt = (
            select(*query_parser.get_select_columns())
            .limit(page_size)
            .offset(page_size * page)
            .where(
                and_(
                    schemas.Object.deleted_on == None, query_parser.where_expressions()
                )
            )
        )

        # Add grouping
        if query_parser.get_group_by_column() is not None:
            select_stmt = select_stmt.group_by(
                query_parser.get_group_by_column()
            ).order_by(query_parser.get_group_by_column())

        if (
            query_parser.get_order_by_columns() is not None
            and query_parser.get_group_by_column() is None
        ):
            select_stmt = select_stmt.order_by(*query_parser.get_order_by_columns())

        results = await session.execute(select_stmt)

        return results_to_model(results, Object.Get)


@router.get("/{id}", response_model=Object.Get)
async def get_object(id: int):
    """Get a single object"""

    engine = get_engine()
    async_session = get_async_session(engine)

    async with async_session() as session:
        select_stmt = select(schemas.Object).where(
            and_(schemas.Object.id == id, schemas.Object.deleted_on == None)
        )

        result = await session.scalar(select_stmt)

        if result is None:
            raise HTTPException(
                status_code=404, detail=f"Object with id ({id}) not found"
            )

        response = Object.Get(**result.__dict__)
        return response


@router.post("", response_model=Object.Get)
async def create_object(
    request: starlette.requests.Request,
    object: Union[Object.Post, list[UploadFile], UploadFile],
    user_has_access: bool = Depends(has_access),
):
    """Create/Register a new object"""

    if not user_has_access:
        raise HTTPException(
            status_code=403, detail="User does not have access to create object"
        )

    if "multipart/form-data" in request.headers["content-type"]:

        files = (await request.form()).getlist("object")
        for upload_file in files:

            m = minio.Minio(
                endpoint=os.environ["S3_HOST"],
                access_key=os.environ["access_key"],
                secret_key=os.environ["secret_key"],
                secure=True,
            )

            m.put_object(
                bucket_name=os.environ["S3_BUCKET"],
                object_name=upload_file.filename,
                data=upload_file.file,
                content_type=upload_file.content_type,
                length=upload_file.size,
            )

            object = Object.Post(
                mime_type=upload_file.content_type,
                key=upload_file.filename,
                bucket=os.environ["S3_BUCKET"],
                host=os.environ["S3_HOST"],
                scheme=schemas.SchemeEnum.s3,
            )

    engine = get_engine()
    async_session = get_async_session(engine)

    async with async_session() as session:
        insert_stmt = (
            insert(schemas.Object)
            .values(**object.model_dump())
            .returning(schemas.Object)
        )
        server_object = await session.scalar(insert_stmt)

        response = Object.Get(**server_object.__dict__)
        await session.commit()
        return response


@router.patch("/{id}", response_model=Object.Get)
async def patch_object(
    id: int, object: Object.Patch, user_has_access: bool = Depends(has_access)
):
    """Update a object"""

    if not user_has_access:
        raise HTTPException(
            status_code=403, detail="User does not have access to update object"
        )

    engine = get_engine()
    async_session = get_async_session(engine)

    async with async_session() as session:
        update_stmt = (
            update(schemas.Object)
            .where(schemas.Object.id == id)
            .values(**object.model_dump(exclude_unset=True))
            .returning(schemas.Object)
        )

        server_object = await session.scalar(update_stmt)

        response = Object.Get(**server_object.__dict__)
        await session.commit()
        return response


@router.delete("/{id}", response_model=Object.Get)
async def delete_object(id: int, has_access: bool = Depends(has_access)):
    """Delete a object"""

    if not has_access:
        raise HTTPException(
            status_code=403, detail="User does not have access to delete object"
        )

    engine = get_engine()
    async_session = get_async_session(engine)

    async with async_session() as session:
        delete_stmt = (
            update(schemas.Object)
            .where(schemas.Object.id == id)
            .values(deleted_on=datetime.datetime.utcnow())
            .returning(schemas.Object)
        )

        server_object = await session.scalar(delete_stmt)

        response = Object.Get(**server_object.__dict__)
        await session.commit()
        return response
