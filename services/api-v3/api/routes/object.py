# api/routes/object.py

import hashlib
import json
import mimetypes
import os
from datetime import datetime
from pathlib import Path
from typing import Any

import starlette.requests
from api.database import get_async_session, get_engine
from api.routes.security import has_access
from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Request,
    Response,
    UploadFile,
)
from minio import Minio
from sqlalchemy import text
from starlette.datastructures import UploadFile as StarletteUploadFile

router = APIRouter(
    prefix="/object",
    tags=["file"],
    responses={404: {"description": "Not found"}},
)


def guess_mime_type(filename: str) -> str:
    mime, _ = mimetypes.guess_type(filename)
    return mime or "application/octet-stream"


def sha256_of_uploadfile(
    upload: StarletteUploadFile, chunk_size: int = 1024 * 1024
) -> str:
    """
    Compute sha256 while reading the upload stream.
    IMPORTANT: resets file pointer back to 0 afterwards so MinIO upload works.
    """
    h = hashlib.sha256()
    upload.file.seek(0)
    while True:
        chunk = upload.file.read(chunk_size)
        if not chunk:
            break
        h.update(chunk)
    upload.file.seek(0)
    return h.hexdigest()


def get_minio_client() -> Minio:
    return Minio(
        # TODO need to add or configure these envs within kubernetets
        endpoint=os.environ["storage_host"],
        access_key=os.environ["maps_access_key"],
        secret_key=os.environ["maps_secret_key"],
        secure=True,
    )


def get_storage_host_bucket() -> tuple[str, str]:
    """
    Keep host/bucket consistent everywhere.
    Also ensures host has no port (hostname only) if storage_host ever includes one.
    """
    import urllib.parse

    raw_host = os.environ["storage_host"]
    parsed = urllib.parse.urlparse(
        raw_host if "://" in raw_host else f"https://{raw_host}"
    )
    host = parsed.hostname or raw_host.split(":")[0]
    bucket = os.environ["maps_bucket_name"]
    return host, bucket


# TODO move queries to database.py functions
SQL_LIST_OBJECTS = """
SELECT
  id,
  scheme,
  host,
  bucket,
  key,
  sha256_hash,
  mime_type,
  source,
  created_on,
  updated_on
FROM storage.object
WHERE scheme = 's3'
  AND host = :host
  AND bucket = :bucket
  AND (:prefix IS NULL OR key LIKE :prefix)
  AND (:include_deleted = TRUE OR deleted_on IS NULL)
ORDER BY id DESC
LIMIT :limit
OFFSET :offset
"""

SQL_GET_OBJECT_BY_ID = """
SELECT
  id,
  scheme,
  host,
  bucket,
  key,
  sha256_hash,
  mime_type,
  source,
  created_on,
  updated_on,
  deleted_on
FROM storage.object
WHERE id = :id
"""

SQL_FIND_EXISTING = """
SELECT id
FROM storage.object
WHERE scheme = 's3'
  AND host = :host
  AND bucket = :bucket
  AND key = :key
  AND deleted_on IS NULL
"""

SQL_INSERT_OBJECT = """
INSERT INTO storage.object
  (scheme, host, bucket, key, source, sha256_hash, mime_type)
VALUES
  ('s3', :host, :bucket, :key, :source, :sha256, :mime_type)
RETURNING
  id, scheme, host, bucket, key, sha256_hash, mime_type, source, created_on, updated_on
"""

SQL_PATCH_OBJECT = """
UPDATE storage.object
SET
  key = COALESCE(:key, key),
  mime_type = COALESCE(:mime_type, mime_type),
  source = COALESCE(:source, source),
  updated_on = NOW()
WHERE id = :id
RETURNING
  id, scheme, host, bucket, key, sha256_hash, mime_type, source, created_on, updated_on
"""

SQL_SOFT_DELETE_OBJECT = """
UPDATE storage.object
SET deleted_on = NOW(), updated_on = NOW()
WHERE id = :id
RETURNING
  id, scheme, host, bucket, key, sha256_hash, mime_type, source, created_on, updated_on, deleted_on
"""

SQL_HARD_DELETE_OBJECT = """
DELETE FROM storage.object
WHERE id = :id
RETURNING id
"""


def _row_to_dict(row) -> dict[str, Any]:
    d = dict(row)
    if "source" in d and isinstance(d["source"], str):
        try:
            d["source"] = json.loads(d["source"])
        except Exception:
            pass
    return d


@router.get("")
async def list_objects(
    page: int = 0,
    page_size: int = 50,
    slug: str | None = None,
    include_deleted: bool = False,
):
    host, bucket = get_storage_host_bucket()

    where = ["scheme = 's3'", "host = :host", "bucket = :bucket"]
    params: dict[str, Any] = {
        "host": host,
        "bucket": bucket,
        "include_deleted": include_deleted,
        "limit": page_size,
        "offset": page * page_size,
    }

    if slug:
        where.append("key LIKE :prefix")
        params["prefix"] = f"{slug}/%"

    if not include_deleted:
        where.append("deleted_on IS NULL")

    sql = f"""
    SELECT id, scheme, host, bucket, key, sha256_hash, mime_type, source, created_on, updated_on
    FROM storage.object
    WHERE {' AND '.join(where)}
    ORDER BY id DESC
    LIMIT :limit
    OFFSET :offset
    """

    engine = get_engine()
    async_session = get_async_session(engine)
    async with async_session() as session:
        res = await session.execute(text(sql), params)
        return [_row_to_dict(r) for r in res.mappings().all()]


@router.get("/{id}")
async def get_object(id: int):
    engine = get_engine()
    async_session = get_async_session(engine)

    async with async_session() as session:
        res = await session.execute(text(SQL_GET_OBJECT_BY_ID), dict(id=id))
        row = res.mappings().first()

        if row is None:
            raise HTTPException(
                status_code=404, detail=f"Object with id ({id}) not found"
            )

        return _row_to_dict(row)


@router.post("")
async def create_object(
    request: starlette.requests.Request,
    user_has_access: bool = Depends(has_access),
    object: UploadFile | None = File(default=None),
):
    """
    Upload to MinIO and register in storage.object.

    - Accepts multipart/form-data with one or many files under field name "object".
    - Uses DB to prevent duplicates (same host/bucket/key).
    """
    if not user_has_access:
        raise HTTPException(
            status_code=403, detail="User does not have access to create object"
        )

    if "multipart/form-data" not in (request.headers.get("content-type") or ""):
        raise HTTPException(status_code=400, detail="Expected multipart/form-data")

    form = await request.form()
    uploads = form.getlist("object")
    if not uploads:
        raise HTTPException(
            status_code=400, detail="No files provided under field name 'object'"
        )

    host, bucket = get_storage_host_bucket()
    minio_client = get_minio_client()

    engine = get_engine()
    async_session = get_async_session(engine)

    created: list[dict[str, Any]] = []

    async with async_session() as session:
        for upload in uploads:
            if not isinstance(upload, StarletteUploadFile):
                continue
            object_key = upload.filename
            existing = await session.execute(
                text(SQL_FIND_EXISTING),
                dict(host=host, bucket=bucket, key=object_key),
            )
            existing_id = existing.scalar_one_or_none()
            if existing_id is not None:
                continue

            sha256 = sha256_of_uploadfile(upload)
            mime_type = upload.content_type or guess_mime_type(upload.filename)
            try:
                minio_client.put_object(
                    bucket_name=bucket,
                    object_name=object_key,
                    data=upload.file,
                    length=upload.size if upload.size is not None else -1,
                    content_type=mime_type,
                    metadata={"sha256": sha256},
                )
            except Exception as e:
                raise HTTPException(
                    status_code=500, detail=f"Failed to upload to S3: {e}"
                )

            res = await session.execute(
                text(SQL_INSERT_OBJECT),
                dict(
                    host=host,
                    bucket=bucket,
                    key=object_key,
                    source=json.dumps({}),
                    sha256=sha256,
                    mime_type=mime_type,
                ),
            )
            row = res.mappings().first()
            if row is None:
                raise HTTPException(
                    status_code=500, detail="Failed to insert storage.object record"
                )

            created.append(_row_to_dict(row))
        await session.commit()

    return {
        "bucket": bucket,
        "host": host,
        "objects_created": created,
    }


@router.patch("/{id}")
async def patch_object(
    id: int,
    body: dict[str, Any],
    user_has_access: bool = Depends(has_access),
):
    """
    Update DB fields only (does not rename objects in MinIO).
    Supported keys: key, mime_type, source
    """
    if not user_has_access:
        raise HTTPException(
            status_code=403, detail="User does not have access to update object"
        )

    key = body.get("key")
    mime_type = body.get("mime_type")
    source = body.get("source")
    if isinstance(source, dict):
        source = json.dumps(source)

    engine = get_engine()
    async_session = get_async_session(engine)

    async with async_session() as session:
        res = await session.execute(
            text(SQL_PATCH_OBJECT),
            dict(id=id, key=key, mime_type=mime_type, source=source),
        )
        row = res.mappings().first()
        if row is None:
            raise HTTPException(
                status_code=404, detail=f"Object with id ({id}) not found"
            )

        await session.commit()
        return _row_to_dict(row)


@router.delete("/{id}")
async def delete_object(
    id: int,
    hard: bool = True,
    user_has_access: bool = Depends(has_access),
):
    """
    Delete an object:
    - hard=True (default): delete from MinIO + delete DB row
    - hard=False: soft delete (sets deleted_on) and keeps object in MinIO
    """
    if not user_has_access:
        raise HTTPException(
            status_code=403, detail="User does not have access to delete object"
        )

    minio_client = get_minio_client()

    engine = get_engine()
    async_session = get_async_session(engine)

    async with async_session() as session:
        # fetch the object row first (source of truth for bucket/key)
        res = await session.execute(text(SQL_GET_OBJECT_BY_ID), dict(id=id))
        obj = res.mappings().first()
        if obj is None:
            raise HTTPException(
                status_code=404, detail=f"Object with id ({id}) not found"
            )

        objd = _row_to_dict(obj)
        object_key = objd.get("key")
        object_bucket = objd.get("bucket")

        # hard delete. remove from MinIO first, then delete DB row
        if hard:
            if object_bucket and object_key:
                try:
                    minio_client.remove_object(object_bucket, object_key)
                except Exception as e:
                    # Do NOT delete DB row if MinIO deletion failed
                    raise HTTPException(
                        status_code=502,
                        detail=f"Failed to delete object from S3 (bucket={object_bucket}, key={object_key}): {e}",
                    )

            res2 = await session.execute(text(SQL_HARD_DELETE_OBJECT), dict(id=id))
            deleted_id = res2.scalar_one_or_none()
            if deleted_id is None:
                raise HTTPException(
                    status_code=500, detail="Failed to delete DB record"
                )

            await session.commit()
            return {"status": "deleted", "id": id, "hard": True}

        # soft delete: only mark deleted in DB; keep MinIO object
        res2 = await session.execute(text(SQL_SOFT_DELETE_OBJECT), dict(id=id))
        row2 = res2.mappings().first()
        if row2 is None:
            raise HTTPException(
                status_code=500, detail="Failed to soft-delete DB record"
            )

        await session.commit()
        return {"status": "deleted", "hard": False, "object": _row_to_dict(row2)}
