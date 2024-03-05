"""
Functions for implementing a pipeline for integrating maps into Macrostrat.
"""

import datetime
import hashlib
import pathlib
from typing import Optional

import magic
import minio
from macrostrat.core.schemas import (  # type: ignore[import-untyped]
    IngestProcess,
    Object,
    ObjectGroup,
    SchemeEnum,
)
from sqlalchemy import and_, insert, select, update
from sqlalchemy.orm import Session

from macrostrat.map_integration import config
from macrostrat.map_integration.database import db as DB


def get_db_session(expire_on_commit=False) -> Session:
    # NOTE: By default, let ORM objects persist past commits, and let
    # consumers manage concurrent updates.
    return Session(DB.engine, expire_on_commit=expire_on_commit)


def get_object_loc(file: pathlib.Path) -> tuple[str, str]:
    """
    Return the bucket and key corresponding to the given local file.
    """
    bucket = config.S3_BUCKET
    key = f"{config.S3_PREFIX}/{file.name}"
    return (bucket, key)


def get_object_by_id(id_: int) -> Optional[Object]:
    with get_db_session() as session:
        obj = session.scalar(
            select(Object).where(
                and_(
                    Object.id == id_,
                    Object.deleted_on == None,
                )
            )
        )
    return obj


def get_object_by_loc(bucket: str, key: str) -> Optional[Object]:
    with get_db_session() as session:
        obj = session.scalar(
            select(Object).where(
                and_(
                    Object.scheme == SchemeEnum.s3,
                    Object.host == config.S3_HOST,
                    Object.bucket == bucket,
                    Object.key == key,
                    Object.deleted_on == None,
                )
            )
        )
    return obj


def create_object(**data) -> Object:
    data = data.copy()
    data["created_on"] = datetime.datetime.utcnow()
    with get_db_session() as session:
        new_obj = session.scalar(insert(Object).values(**data).returning(Object))
        session.commit()
    return new_obj


def update_object(id_: int, **data) -> Object:
    data = data.copy()
    data["updated_on"] = datetime.datetime.utcnow()
    with get_db_session() as session:
        new_obj = session.scalar(
            update(Object).values(**data).where(Object.id == id_).returning(Object)
        )
        session.commit()
    return new_obj


def get_ingest_process_by_object_group_id(id_: int) -> Optional[IngestProcess]:
    with get_db_session() as session:
        ingest_process = session.scalar(
            select(IngestProcess).where(IngestProcess.object_group_id == id_)
        )
    return ingest_process


def create_ingest_process(**data) -> IngestProcess:
    with get_db_session() as session:
        object_group = session.scalar(
            insert(ObjectGroup).values(**data).returning(ObjectGroup)
        )
        if not object_group:
            raise RuntimeError("Failed to create a new object group")
        ingest_process = session.scalar(
            insert(IngestProcess)
            .values(object_group_id=object_group.id)
            .returning(IngestProcess)
        )
        session.commit()
    return ingest_process


# --------------------------------------------------------------------------


def upload_file(local_file: pathlib.Path) -> None:
    """
    Upload a local file to the object store.
    """
    s3 = minio.Minio(
        config.S3_HOST,
        access_key=config.S3_ACCESS_KEY,
        secret_key=config.S3_SECRET_KEY,
    )
    (bucket, key) = get_object_loc(local_file)
    s3.fput_object(bucket, key, str(local_file))


def register_file(local_file: pathlib.Path, replace: bool = False) -> Object:
    """
    Register a local file as an object in Macrostrat.
    """

    # Step 1: Calculate the object's metadata.

    mime_type = magic.Magic(mime=True).from_file(local_file)
    hasher = hashlib.sha256()
    with open(local_file, mode="rb") as fp:
        while data := fp.read(config.CHUNK_SIZE):
            hasher.update(data)
    sha256_hash = hasher.hexdigest()

    bucket, key = get_object_loc(local_file)

    # Step 2: Create or retrieve the object's ingest process.

    if obj := get_object_by_loc(bucket, key):
        if not replace and obj.sha256_hash != sha256_hash:
            raise RuntimeError(
                "Attempting to upload a different version of an already-registered object"
            )
        ingest_process = get_ingest_process_by_object_group_id(obj.object_group_id)
    else:
        ingest_process = create_ingest_process()

    if not ingest_process:
        raise RuntimeError("Failed to create or retrieve the object's ingest process")

    # Step 3: Create or update the object's DB entry.

    payload = {
        "object_group_id": ingest_process.object_group_id,
        "scheme": SchemeEnum.s3,
        "host": config.S3_HOST,
        "bucket": bucket,
        "key": key,
        # FIXME: Add missing "source" information.
        "mime_type": mime_type,
        "sha256_hash": sha256_hash,
    }
    return update_object(obj.id, **payload) if obj else create_object(**payload)
