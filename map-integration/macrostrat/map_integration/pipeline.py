"""
Functions for implementing a pipeline for integrating maps into Macrostrat.
"""

import datetime
import hashlib
import pathlib
import tempfile
import zipfile
from typing import Optional

import magic
import minio
from macrostrat.core.schemas import (  # type: ignore[import-untyped]
    IngestProcess,
    Object,
    ObjectGroup,
    SchemeEnum,
    Sources,
)
from sqlalchemy import and_, insert, select, update
from sqlalchemy.orm import Session

from macrostrat.map_integration import config
from macrostrat.map_integration.commands.ingest import ingest_map
from macrostrat.map_integration.commands.prepare_fields import prepare_fields
from macrostrat.map_integration.database import db as DB
from macrostrat.map_integration.process.geometry import create_rgeom, create_webgeom
from macrostrat.map_integration.utils.map_info import get_map_info


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
            .values(
                object_group_id=object_group.id,
                created_on=datetime.datetime.utcnow(),
            )
            .returning(IngestProcess)
        )
        session.commit()
    return ingest_process


def update_ingest_process(id_: int, **data) -> IngestProcess:
    with get_db_session() as session:
        new_ingest_process = session.scalar(
            update(IngestProcess)
            .values(**data)
            .where(IngestProcess.id == id_)
            .returning(IngestProcess)
        )
        session.commit()
    return new_ingest_process


def update_source(id_: int, **data) -> Sources:
    with get_db_session() as session:
        new_source = session.scalar(
            update(Sources)
            .values(**data)
            .where(Sources.source_id == id_)
            .returning(Sources)
        )
        session.commit()
    return new_source


# --------------------------------------------------------------------------


def run_pipeline(
    local_file: pathlib.Path,
    slug: str,
    replace_object: bool = False,
) -> Object:

    # Step 1: Calculate the object's metadata.

    mime_type = magic.Magic(mime=True).from_file(local_file)
    hasher = hashlib.sha256()
    with open(local_file, mode="rb") as fp:
        while data := fp.read(config.CHUNK_SIZE):
            hasher.update(data)
    sha256_hash = hasher.hexdigest()

    # Step 2: Upload the file.

    bucket, key = get_object_loc(local_file)

    if obj := get_object_by_loc(bucket, key):
        if not replace_object and obj.sha256_hash != sha256_hash:
            raise RuntimeError(
                "Attempting to upload a different version of this object"
            )

    if not obj or obj.sha256_hash != sha256_hash:
        s3 = minio.Minio(
            config.S3_HOST,
            access_key=config.S3_ACCESS_KEY,
            secret_key=config.S3_SECRET_KEY,
        )
        s3.fput_object(bucket, key, str(local_file))

    # Step 3: Create or retrieve the object's ingest process.

    if obj:
        ingest_process = get_ingest_process_by_object_group_id(obj.object_group_id)
    else:
        ingest_process = create_ingest_process()
    if not ingest_process:
        raise RuntimeError("Failed to create or retrieve the object's ingest process")
    if ingest_process.state == "ingested":
        return obj

    # Step 4: Create or update the object's DB entry.

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

    if obj:
        obj = update_object(obj.id, **payload)
    else:
        obj = create_object(**payload)

    # Step 5: Locate and ingest files.

    if local_file.name.endswith(".zip"):
        tmp_dir_obj = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        tmp_dir = pathlib.Path(tmp_dir_obj.name)

        with zipfile.ZipFile(local_file) as zf:
            zf.extractall(path=tmp_dir)
        shapefiles = list(tmp_dir.glob("**/*.shp"))

        ingest_map(slug, shapefiles)

        macrostrat_map = get_map_info(DB, slug)

        prepare_fields(macrostrat_map, recover=False)
        create_rgeom(macrostrat_map)
        create_webgeom(macrostrat_map)

        update_source(
            macrostrat_map.id,
            scale="large",
        )
        update_ingest_process(
            ingest_process.id, state="ingested", source_id=macrostrat_map.id
        )

    else:
        raise RuntimeError("Unrecognized file format")
