"""
A pipeline for ingesting maps into Macrostrat.
"""

import datetime
import hashlib
import pathlib
import re
import tempfile
import zipfile
from typing import Annotated, Optional

import magic
import minio
import psycopg2.errors  # type: ignore[import-untyped]
from macrostrat.core.schemas import (  # type: ignore[import-untyped]
    IngestProcess,
    IngestState,
    Object,
    ObjectGroup,
    SchemeEnum,
    Sources,
)
from rich.console import Console
from sqlalchemy import and_, insert, select, update
from sqlalchemy.orm import Session
from typer import Argument, Option

from macrostrat.map_integration import config
from macrostrat.map_integration.commands.ingest import ingest_map
from macrostrat.map_integration.commands.prepare_fields import prepare_fields
from macrostrat.map_integration.database import db as DB
from macrostrat.map_integration.errors import IngestError
from macrostrat.map_integration.process.geometry import create_rgeom, create_webgeom
from macrostrat.map_integration.utils.map_info import get_map_info

console = Console()


def raise_ingest_error(
    ingest_process: IngestProcess,
    message: str,
    source_exn=None,
) -> None:
    update_ingest_process(
        ingest_process.id,
        state=IngestState.failed,
        comments=message,
    )
    raise IngestError(message) from source_exn


def get_db_session(expire_on_commit=False) -> Session:
    # NOTE: By default, let ORM objects persist past commits, and let
    # consumers manage concurrent updates.
    return Session(DB.engine, expire_on_commit=expire_on_commit)


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


def get_ingest_process_by_id(id_: int) -> Optional[IngestProcess]:
    with get_db_session() as session:
        ingest_process = session.scalar(select(IngestProcess).where(IngestProcess.id == id_))
    return ingest_process


def get_ingest_process_by_object_group_id(id_: int) -> Optional[IngestProcess]:
    with get_db_session() as session:
        ingest_process = session.scalar(
            select(IngestProcess).where(IngestProcess.object_group_id == id_)
        )
    return ingest_process


def create_ingest_process() -> IngestProcess:
    with get_db_session() as session:
        object_group = session.scalar(insert(ObjectGroup).returning(ObjectGroup))
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


def get_source_by_slug(slug: str) -> Sources:
    return get_map_info(DB, slug)


def update_source(id_: int, **data) -> Sources:
    with get_db_session() as session:
        new_source = session.scalar(
            update(Sources).values(**data).where(Sources.source_id == id_).returning(Sources)
        )
        session.commit()
    return new_source


# --------------------------------------------------------------------------


def run_pipeline(
    local_file: Annotated[
        pathlib.Path,
        Argument(help="Local file to ingest"),
    ],
    slug: Annotated[
        str,
        Argument(help="Macrostrat slug to use for this map"),
    ],
    name: Annotated[
        Optional[str],
        Option(help="The map's name"),
    ] = None,
    ref_title: Annotated[
        Optional[str],
        Option(help="The map's report's title"),
    ] = None,
    ref_authors: Annotated[
        Optional[str],
        Option(help="The map's report's authors"),
    ] = None,
    ref_year: Annotated[
        Optional[str],
        Option(help="The map's report's year"),
    ] = None,
    ref_source: Annotated[
        Optional[str],
        Option(help="The map's report's source"),
    ] = None,
    ref_isbn_or_doi: Annotated[
        Optional[str],
        Option(help="The map's report's ISBN or DOI"),
    ] = None,
    scale: Annotated[
        str,
        Option(help="The map's scale"),
    ] = "large",
    url: Annotated[
        Optional[str],
        Option(help="The map's download URL"),
    ] = None,
    website: Annotated[
        Optional[str],
        Option(help="The map's website"),
    ] = None,
    s3_bucket: Annotated[
        str,
        Option(help="The S3 bucket to upload this object to"),
    ] = config.S3_BUCKET,
    s3_prefix: Annotated[
        str,
        Option(help="The prefix, sans trailing slash, to use for this object's S3 key"),
    ] = config.S3_PREFIX,
    replace_object: Annotated[
        bool,
        Option(help="Replace the current version of this object"),
    ] = False,
) -> Object:
    """
    Ingest a local file containing a map into Macrostrat.
    """

    ## Normalize identifiers.

    slug = re.sub(r"\W", "_", slug).lower()

    ## Collect metadata.

    mime_type = magic.Magic(mime=True).from_file(local_file)
    hasher = hashlib.sha256()
    with open(local_file, mode="rb") as fp:
        while data := fp.read(config.CHUNK_SIZE):
            hasher.update(data)
    sha256_hash = hasher.hexdigest()
    console.print(f"Detected {mime_type} with SHA-256 {sha256_hash}")

    ## Upload the file.

    bucket = s3_bucket
    key = f"{s3_prefix}/{local_file.name}"
    uploaded_obj = False

    if obj := get_object_by_loc(bucket, key):
        if not replace_object and obj.sha256_hash != sha256_hash:
            raise IngestError("Attempting to upload a different version of this object")

    if not obj or obj.sha256_hash != sha256_hash or replace_object:
        console.print(f"Uploading file to S3 ({bucket}/{key})")
        s3 = minio.Minio(
            config.S3_HOST,
            access_key=config.S3_ACCESS_KEY,
            secret_key=config.S3_SECRET_KEY,
        )
        s3.fput_object(bucket, key, str(local_file))
        uploaded_obj = True

    ## Create or retrieve the ingest process.

    if obj:
        ingest_process = get_ingest_process_by_object_group_id(obj.object_group_id)
    else:
        ingest_process = create_ingest_process()
    if not ingest_process:
        raise IngestError("Failed to create or retrieve the object's ingest process")
    if uploaded_obj:
        ingest_process = update_ingest_process(ingest_process.id, state=None, comments=None)
    if ingest_process.state == IngestState.ingested:
        console.print("Ingest pipeline has already been completed")
        return obj
    console.print(f"Found or created ingest process ID {ingest_process.id}")

    ## Create or update the object's DB entry.

    source_info = {}
    if url:
        source_info["url"] = url
    if website:
        source_info["website"] = website

    payload = {
        "object_group_id": ingest_process.object_group_id,
        "scheme": SchemeEnum.s3,
        "host": config.S3_HOST,
        "bucket": bucket,
        "key": key,
        "source": source_info,
        "mime_type": mime_type,
        "sha256_hash": sha256_hash,
    }

    if obj:
        obj = update_object(obj.id, **payload)
    else:
        obj = create_object(**payload)
    ingest_process = update_ingest_process(
        ingest_process.id,
        state=IngestState.pending,
        comments=None,
    )
    console.print(f"Found or created object ID {obj.id}")

    ## Process anything that might have points, lines, and polygons.

    if local_file.name.endswith(".zip"):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as td:
            tmp_dir = pathlib.Path(td)
            console.print(f"Extracting zip archive into\n{tmp_dir}")

            with zipfile.ZipFile(local_file) as zf:
                zf.extractall(path=tmp_dir)
            shapefiles = list(tmp_dir.glob("**/*.shp"))

            if not shapefiles:
                raise_ingest_error(ingest_process, "Failed to locate any shapefiles")

            shapefiles_str = "\n".join(str(x) for x in shapefiles)
            console.print(f"Ingesting {slug} from\n{shapefiles_str}")
            try:
                ingest_map(slug, shapefiles)
            except IngestError as exn:
                raise_ingest_error(ingest_process, str(exn), exn)
            except psycopg2.errors.InvalidTextRepresentation as exn:
                raise_ingest_error(ingest_process, str(exn), exn)
        macrostrat_map = get_source_by_slug(slug)
    else:
        raise_ingest_error(ingest_process, "Unrecognized file format")

    ## Prepare tables for human review.

    console.print(f"Found or created source ID {macrostrat_map.id}")

    metadata = {"scale": scale}
    if name:
        metadata["name"] = name
    if ref_title:
        metadata["ref_title"] = ref_title
    if ref_authors:
        metadata["authors"] = ref_authors
    if ref_year:
        metadata["ref_year"] = ref_year
    if ref_source:
        metadata["ref_source"] = ref_source
    if ref_isbn_or_doi:
        metadata["isbn_doi"] = ref_isbn_or_doi

    update_source(macrostrat_map.id, **metadata)
    ingest_process = update_ingest_process(
        ingest_process.id,
        source_id=macrostrat_map.id,
        comments="created tables",
    )
    prepare_fields(macrostrat_map)
    ingest_process = update_ingest_process(
        ingest_process.id,
        state=IngestState.prepared,
        comments=None,
    )
    create_rgeom(macrostrat_map)
    create_webgeom(macrostrat_map)
    ingest_process = update_ingest_process(
        ingest_process.id,
        state=IngestState.ingested,
        comments=None,
    )
    console.print("Finished running ingest pipeline")

    return obj
