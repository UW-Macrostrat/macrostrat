import os
from typing import Union

import api.models.ingest as IngestProcessModel
import api.models.object as Object
import api.schemas as schemas
import minio
import starlette.requests
from api.celery_app import celery_app
from api.database import EngineDep, get_async_session
from api.query_parser import QueryParser, get_filter_query_params
from api.routes.security import has_access
from api.schemas import IngestProcess as IngestProcessSchema
from api.schemas import IngestProcessTag, MapFiles
from api.schemas import Object as ObjectORM
from api.schemas import Sources
from celery.exceptions import TimeoutError as CeleryTimeoutError
from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel
from sqlalchemy import and_, delete, func, insert, select, update
from sqlalchemy.orm import defer, joinedload, selectinload
from starlette.responses import Response

router = APIRouter(
    prefix="/ingest-process",
    tags=["ingest-process"],
    responses={404: {"description": "Not found"}},
)


class DeleteMapRequest(BaseModel):
    slug: str


# How long the API waits for the Celery delete task to finish before giving up.
# Override with the DELETE_TASK_TIMEOUT env var (seconds).
DELETE_TASK_TIMEOUT = float(os.environ.get("DELETE_TASK_TIMEOUT", "30"))


@router.post("/delete-map")
async def delete_map(
    request: DeleteMapRequest, user_has_access: bool = Depends(has_access)
):
    """Delete a staged map via the Celery worker, surfacing any failure.

    The task runs in the `celery_worker` container (calling `macrostrat.map_utils`).
    We enqueue it and wait for the result so errors can be returned to the caller
    for debugging rather than failing silently:

    * 403 — caller lacks access
    * 503 — task couldn't be enqueued (broker / Celery container unreachable)
    * 504 — no worker finished it within DELETE_TASK_TIMEOUT (worker down, or
            nothing consuming the `maps` queue)
    * 502 — error talking to the result backend while waiting
    * 500 — the task itself raised in the worker (includes the worker-side error
            message and traceback from map_utils / the DB / etc.)
    """
    if not user_has_access:
        raise HTTPException(
            status_code=403, detail="User does not have access to delete a map"
        )

    # Enqueue. A failure here means the broker (Redis / Celery container) is
    # unreachable.
    try:
        task = celery_app.send_task("macrostrat.maps.delete", args=[request.slug])
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Could not enqueue delete task — is the Celery broker reachable? {e}",
        )

    # Wait for the worker to finish within DELETE_TASK_TIMEOUT timeframe.
    try:
        result = await run_in_threadpool(
            task.get, timeout=DELETE_TASK_TIMEOUT, propagate=False
        )
    except CeleryTimeoutError:
        raise HTTPException(
            status_code=504,
            detail=(
                f"Delete task {task.id} for slug '{request.slug}' did not finish "
                f"within {DELETE_TASK_TIMEOUT:.0f}s. It may still be running, or no "
                f"worker is consuming the 'maps' queue (check the celery_worker "
                f"container)."
            ),
        )
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=f"Error while waiting for delete task {task.id}: {e}",
        )

    # The task ran but error raised inside the map_utils function
    if task.failed():
        raise HTTPException(
            status_code=500,
            detail={
                "message": f"Delete task failed for slug '{request.slug}'",
                "task_id": task.id,
                "error": str(task.result),
                "traceback": task.traceback,
            },
        )

    return {"task_id": task.id, "slug": request.slug, "result": result}


@router.get("", response_model=list[IngestProcessModel.Get])
async def get_multiple_ingest_process(
    response: Response,
    engine: EngineDep,
    page: int = 0,
    page_size: int = 50,
    filter_query_params=Depends(get_filter_query_params),
):
    """Get all ingestion processes"""

    async_session = get_async_session(engine)

    query_parser = QueryParser(
        columns=IngestProcessSchema.__table__.c, query_params=filter_query_params
    )

    async with async_session() as session:

        select_stmt = (
            select(IngestProcessSchema)
            .limit(page_size)
            .offset(page_size * page)
            .where(and_(query_parser.where_expressions()))
            .order_by(*query_parser.get_order_by_columns())
            .options(
                joinedload(IngestProcessSchema.source)
                .defer(Sources.rgeom)
                .defer(Sources.web_geom)
            )
            .options(selectinload(IngestProcessSchema.tags))
        )

        # If there is a filter based on tags
        if query_parser.decomposed_query_params.get("tags") is not None:
            query_param = query_parser.decomposed_query_params.get("tags")
            query_param.column = IngestProcessTag.tag
            operation_expression = query_param.get_operator_expression()
            select_stmt = select_stmt.filter(
                IngestProcessSchema.tags.any(operation_expression)
            )

        results = await session.execute(select_stmt)

        response.headers["X-Total-Count"] = str(
            await session.scalar(
                select(func.count("*")).select_from(select_stmt.subquery())
            )
        )

        return map(lambda x: x[0], results.all())


@router.get("/tags", response_model=list[str])
async def get_all_tags(engine: EngineDep):
    """Get all tags"""

    async_session = get_async_session(engine)

    async with async_session() as session:
        select_stmt = select(IngestProcessTag.tag).distinct()
        results = await session.execute(select_stmt)

        return [result[0] for result in results.all()]


@router.get("/{id}", response_model=IngestProcessModel.Get)
async def get_ingest_process(id: int, engine: EngineDep):
    """Get a single object"""

    async_session = get_async_session(engine)

    async with async_session() as session:
        select_stmt = (
            select(IngestProcessSchema)
            .where(and_(IngestProcessSchema.id == id))
            .options(
                joinedload(IngestProcessSchema.source)
                .defer(Sources.rgeom)
                .defer(Sources.web_geom)
            )
            .options(selectinload(IngestProcessSchema.tags))
        )

        result = await session.scalar(select_stmt)

        if result is None:
            raise HTTPException(
                status_code=404, detail=f"IngestProcess with id ({id}) not found"
            )

        return result


@router.post("", response_model=IngestProcessModel.Get)
async def create_ingest_process(
    object: IngestProcessModel.Post,
    engine: EngineDep,
    user_has_access: bool = Depends(has_access),
):
    """Create/Register a new object"""

    if not user_has_access:
        raise HTTPException(
            status_code=403, detail="User does not have access to create an object"
        )

    async_session = get_async_session(engine, expire_on_commit=False)

    async with async_session() as session:

        if object.tags is None:
            object.tags = []

        tags = [IngestProcessTag(tag=tag.strip()) for tag in object.tags]
        del object.tags
        ingest_process = IngestProcessSchema(**object.model_dump(), tags=tags)

        session.add(ingest_process)
        await session.commit()

        ingest_process.source = await session.get(Sources, object.source_id)

    return ingest_process


@router.patch("/{id}", response_model=IngestProcessModel.Get)
async def patch_ingest_process(
    id: int,
    object: IngestProcessModel.Patch,
    engine: EngineDep,
    user_has_access: bool = Depends(has_access),
):
    """Update a object"""

    if not user_has_access:
        raise HTTPException(
            status_code=403, detail="User does not have access to create an object"
        )

    async_session = get_async_session(engine)

    async with async_session() as session:
        update_stmt = (
            update(IngestProcessSchema)
            .where(IngestProcessSchema.id == id)
            .values(**object.model_dump(exclude_unset=True))
            .returning(IngestProcessSchema)
        )

        server_object = await session.scalar(update_stmt)

        response = IngestProcessModel.Get(**server_object.__dict__)
        await session.commit()
        return response


@router.post("/{id}/tags", response_model=list[str])
async def add_ingest_process_tag(
    id: int,
    tag: IngestProcessModel.Tag,
    engine: EngineDep,
    user_has_access: bool = Depends(has_access),
):
    """Add a tag to an ingest process"""

    if not user_has_access:
        raise HTTPException(
            status_code=403, detail="User does not have access to create an object"
        )

    async_session = get_async_session(engine)

    async with async_session() as session:

        ingest_process = await session.get(IngestProcessSchema, id)

        if ingest_process is None:
            raise HTTPException(
                status_code=404, detail=f"IngestProcess with id ({id}) not found"
            )

        ingest_process.tags.append(IngestProcessTag(tag=tag.tag.strip()))
        await session.commit()

        ingest_process = await session.get(IngestProcessSchema, id)
        return [tag.tag for tag in ingest_process.tags]

    return None


@router.delete("/{id}/tags/{tag}", response_model=list[str])
async def delete_ingest_process_tag(
    id: int,
    tag: str,
    engine: EngineDep,
    user_has_access: bool = Depends(has_access),
):
    """Delete a tag from an ingest process"""

    if not user_has_access:
        raise HTTPException(
            status_code=403, detail="User does not have access to create an object"
        )

    async_session = get_async_session(engine)

    async with async_session() as session:

        ingest_process = await session.get(IngestProcessSchema, id)

        if ingest_process is None:
            raise HTTPException(
                status_code=404, detail=f"IngestProcess with id ({id}) not found"
            )

        tag_stmt = delete(IngestProcessTag).where(
            and_(IngestProcessTag.ingest_process_id == id, IngestProcessTag.tag == tag)
        )
        await session.execute(tag_stmt)
        await session.commit()

        ingest_process = await session.get(IngestProcessSchema, id)

        return [tag.tag for tag in ingest_process.tags]

    return ingest_process


@router.get("/{id}/objects", response_model=list[Object.GetSecureURL])
async def get_ingest_process_objects(id: int, engine: EngineDep):
    """Get all objects for an ingestion process"""

    async_session = get_async_session(engine)

    async with async_session() as session:

        select_stmt = select(IngestProcessSchema).where(
            and_(IngestProcessSchema.id == id)
        )
        ingest_process = await session.scalar(select_stmt)
        object_ids_stmt = select(MapFiles.object_id).where(
            MapFiles.ingest_process_id == id
        )
        object_ids = (await session.execute(object_ids_stmt)).scalars().all()

        if not object_ids:
            return []

        objects_stmt = select(ObjectORM).where(ObjectORM.id.in_(object_ids))
        schema_objects = (await session.execute(objects_stmt)).scalars().all()

    if len(schema_objects) == 0:
        return []

    try:
        # Attach the secure url
        first_object = schema_objects[0]
        m = minio.Minio(
            endpoint=first_object.host,
            access_key=os.environ["access_key"],
            secret_key=os.environ["secret_key"],
            secure=True,
        )

        for obj in schema_objects:
            obj.pre_signed_url = m.presigned_get_object(
                bucket_name=obj.bucket, object_name=obj.key
            )

        return schema_objects

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get secure url for object: {e}"
        )


@router.post("/{id}/objects", response_model=list[Object.Get])
async def create_object(
    request: starlette.requests.Request,
    id: int,
    object: list[UploadFile],
    engine: EngineDep,
    user_has_access: bool = Depends(has_access),
):
    """Create/Register a new object"""

    if not user_has_access:
        raise HTTPException(
            status_code=403, detail="User does not have access to create object"
        )

    async_session = get_async_session(engine)

    response_objects = []

    async with async_session() as session:

        ingest_stmt = select(IngestProcessSchema).where(IngestProcessSchema.id == id)
        ingest_process = await session.scalar(ingest_stmt)

        if "multipart/form-data" in request.headers["content-type"]:

            files = (await request.form()).getlist("object")
            for upload_file in files:

                m = minio.Minio(
                    endpoint=os.environ["S3_HOST"],
                    access_key=os.environ["access_key"],
                    secret_key=os.environ["secret_key"],
                    secure=True,
                )

                object_file_name = f"{ingest_process.id}/{upload_file.filename}"

                m.put_object(
                    bucket_name=os.environ["S3_BUCKET"],
                    object_name=object_file_name,
                    data=upload_file.file,
                    content_type=upload_file.content_type,
                    length=upload_file.size,
                )

                object = Object.Post(
                    mime_type=upload_file.content_type,
                    key=object_file_name,
                    bucket=os.environ["S3_BUCKET"],
                    host=os.environ["S3_HOST"],
                    scheme=schemas.SchemeEnum.s3,
                )

                insert_stmt = (
                    insert(schemas.Object)
                    .values(**object.model_dump())
                    .returning(schemas.Object)
                )
                server_object = await session.scalar(insert_stmt)
                await session.execute(
                    insert(MapFiles).values(
                        ingest_process_id=id, object_id=server_object.id
                    )
                )

                response_objects.append(Object.Get(**server_object.__dict__))

            await session.commit()

    return response_objects
