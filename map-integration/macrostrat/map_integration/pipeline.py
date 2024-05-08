"""
A pipeline for ingesting maps into Macrostrat.
"""

import csv
import datetime
import hashlib
import os
import pathlib
import re
import tarfile
import tempfile
import time
import zipfile
from typing import Annotated, NoReturn, Optional

import magic
import minio
import requests
from macrostrat.core.schemas import (  # type: ignore[import-untyped]
    IngestProcess,
    IngestProcessTag,
    IngestState,
    Object,
    ObjectGroup,
    SchemeEnum,
    Sources,
)
from rich.console import Console
from sqlalchemy import and_, insert, select, update
from sqlalchemy.orm import Session
from typer import Argument, Context, Option

from macrostrat.map_integration import config
from macrostrat.map_integration.commands.ingest import ingest_map
from macrostrat.map_integration.commands.prepare_fields import prepare_fields
from macrostrat.map_integration.database import db as DB
from macrostrat.map_integration.errors import IngestError
from macrostrat.map_integration.process.geometry import create_rgeom, create_webgeom
from macrostrat.map_integration.utils.map_info import get_map_info

DOWNLOAD_ROOT_DIR = pathlib.Path("./tmp")
FIELDS = [
    "slug",
    "tag",
    "filter",
    "name",
    "ref_title",
    "ref_authors",
    "ref_year",
    "ref_source",
    "ref_isbn_or_doi",
    "scale",
    "archive_url",
    "website_url",
    "raster_url",
    "s3_bucket",
    "s3_prefix",
]

console = Console()


# --------------------------------------------------------------------------


def record_ingest_error(
    ingest_process: IngestProcess,
    message: str,
) -> None:
    update_ingest_process(
        ingest_process.id,
        state=IngestState.failed,
        comments=message,
    )


def raise_ingest_error(
    ingest_process: IngestProcess,
    message: str,
    source_exn: Optional[Exception] = None,
) -> NoReturn:
    record_ingest_error(ingest_process, message)
    raise IngestError(message) from source_exn


# --------------------------------------------------------------------------


def truncate_str(data: str, *, limit: int = 255) -> str:
    if len(data) > limit:
        data = data[: limit - 3] + "..."
    return data


def extract_archive(
    archive_file: pathlib.Path,
    target_dir: pathlib.Path,
    *,
    ingest_process: Optional[IngestProcess] = None,
    extract_subarchives: bool = True,
) -> None:
    """
    Extract an archive into a directory.

    By default, any sub-archives will be extracted into the same directory.
    This might not result in the expected layout for some archives.

    If provided, the ingest process will be used to report any errors.
    """
    if archive_file.name.endswith((".tgz", ".tar.gz")):
        with tarfile.open(archive_file) as tf:
            tf.extractall(path=target_dir, filter="data")
    elif archive_file.name.endswith(".zip"):
        with zipfile.ZipFile(archive_file) as zf:
            zf.extractall(path=target_dir)
    else:
        if ingest_process:
            raise_ingest_error(ingest_process, "Unrecognized file format")

    if extract_subarchives:
        sub_archives = set(
            list(target_dir.glob("**/*.tar.gz"))
            + list(target_dir.glob("**/*.tgz"))
            + list(target_dir.glob("**/*.zip"))
        )
        for sub_archive in sub_archives - set([archive_file]):
            extract_archive(
                sub_archive,
                target_dir,
                ingest_process=ingest_process,
                extract_subarchives=False,
            )


def set_alaska_metadata(source: Sources, data_dir: pathlib.Path) -> None:
    metadata: dict[str, str] = {}
    metadata_files = list(data_dir.glob("metadata/*.txt"))

    if len(metadata_files) != 1:
        return
    with open(metadata_files[0], encoding="utf-8") as fp:
        raw_metadata = fp.readlines()

    ## NOTE: The metadata file looks like it could be parsed as YAML,
    ## but alas, it is not YAML. Some hashes define a key multiple times,
    ## and some values confuse PyYAMLs parser.

    ## Skip the first line ("Identification_Information:").

    raw_metadata.pop(0)

    ## Scan for interesting lines until we reach the next section.

    for line in raw_metadata:
        if not line.startswith(" ") or "Description:" in line:
            break
        line = line.strip()

        if line.startswith("Originator:"):
            author = line.replace("Originator:", "").strip()
            if "authors" in metadata:
                metadata["authors"] += f"; {author}"
            else:
                metadata["authors"] = author
        elif line.startswith("Publication_Date:"):
            year = line.replace("Publication_Date:", "").strip()
            metadata["ref_year"] = year
        elif line.startswith("Title:"):
            title = line.replace("Title:", "").strip()
            metadata["name"] = title
            metadata["ref_title"] = title
        elif line.startswith("Publisher:"):
            publisher = line.replace("Publisher:", "").strip()
            metadata["ref_source"] = publisher
        elif line.startswith("Online_Linkage:"):
            doi = line.replace("Online_Linkage:", "").strip()
            metadata["isbn_doi"] = doi

    ## Update the map's metadata.

    if metadata:
        update_source(source.source_id, **metadata)


# --------------------------------------------------------------------------


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
        ingest_process = session.scalar(
            select(IngestProcess).where(IngestProcess.id == id_),
        )
    return ingest_process


def get_ingest_process_by_object_group_id(id_: int) -> Optional[IngestProcess]:
    with get_db_session() as session:
        ingest_process = session.scalar(
            select(IngestProcess).where(IngestProcess.object_group_id == id_),
        )
    return ingest_process


def create_ingest_process() -> IngestProcess:
    with get_db_session() as session:
        object_group = session.scalar(insert(ObjectGroup).returning(ObjectGroup))
        if not object_group:
            raise RuntimeError("Failed to create a new object group")
        new_ingest_process = session.scalar(
            insert(IngestProcess)
            .values(
                object_group_id=object_group.id,
                created_on=datetime.datetime.utcnow(),
            )
            .returning(IngestProcess)
        )
        session.commit()
    return new_ingest_process


def create_ingest_process_tag(
    ingest_process_id: int,
    tag: str,
) -> IngestProcessTag:
    with get_db_session() as session:
        new_ingest_process_tag = session.scalar(
            insert(IngestProcessTag)
            .values(
                ingest_process_id=ingest_process_id,
                tag=tag,
            )
            .returning(IngestProcessTag)
        )
        session.commit()
    return new_ingest_process_tag


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


def get_source_by_id(id_: int) -> Optional[Sources]:
    with get_db_session() as session:
        source = session.scalar(select(Sources).where(Sources.source_id == id_))
    return source


def get_source_by_slug(slug: str) -> Optional[Sources]:
    with get_db_session() as session:
        source = session.scalar(select(Sources).where(Sources.slug == slug))
    return source


def create_source(**data) -> Sources:
    with get_db_session() as session:
        new_source = session.scalar(
            insert(Sources).values(**data).returning(Sources),
        )
        session.commit()
    return new_source


def update_source(id_: int, **data) -> Sources:
    data = data.copy()
    for col in ["name", "url", "authors", "ref_source"]:
        if col in data:
            data[col] = truncate_str(data[col], limit=255)
    for col in ["isbn_doi", "licence"]:
        if col in data:
            data[col] = truncate_str(data[col], limit=100)
    with get_db_session() as session:
        new_source = session.scalar(
            update(Sources).values(**data).where(Sources.source_id == id_).returning(Sources),
        )
        session.commit()
    return new_source


# --------------------------------------------------------------------------


def ingest_file(
    local_file: Annotated[
        pathlib.Path,
        Argument(help="Local file to ingest"),
    ],
    slug: Annotated[
        str,
        Argument(help="The slug to use for this map"),
    ],
    tag: Annotated[
        Optional[list[str]],
        Option(help="A tag to apply to the map"),
    ] = None,
    filter: Annotated[
        Optional[str],
        Option(help="How to interpret the contents of the provided file"),
    ] = None,
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
    archive_url: Annotated[
        Optional[str],
        Option(help="The URL for the map's archive file"),
    ] = None,
    website_url: Annotated[
        Optional[str],
        Option(help="The URL for the map's canonical landing page"),
    ] = None,
    raster_url: Annotated[
        Optional[str],
        Option(help="The URL for the map's raster file"),
    ] = None,
    s3_bucket: Annotated[
        str,
        Option(help="The S3 bucket to upload this object to"),
    ] = config.S3_BUCKET,
    s3_prefix: Annotated[
        str,
        Option(help="The prefix, sans trailing slash, to use for this object's S3 key"),
    ] = config.S3_PREFIX,
    append_data: Annotated[
        bool,
        Option(help="Whether to append data to the map when it already exists"),
    ] = False,
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
    console.print(f"Normalized the provided slug to {slug}")

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
        console.print(f"Uploading {local_file} to S3 as {bucket}/{key}")
        s3 = minio.Minio(
            config.S3_HOST,
            access_key=config.S3_ACCESS_KEY,
            secret_key=config.S3_SECRET_KEY,
        )
        s3.fput_object(bucket, key, str(local_file))
        uploaded_obj = True
        console.print("Finished upload")

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
    if tag:
        if isinstance(tag, list):
            for t in tag:
                create_ingest_process_tag(ingest_process.id, t)
        else:
            create_ingest_process_tag(ingest_process.id, tag)
    console.print(f"Created or updated ingest process ID {ingest_process.id}")

    ## Create or update the object's DB entry.

    source_info = {}
    if archive_url:
        source_info["archive_url"] = archive_url
    if raster_url:
        source_info["raster_url"] = raster_url
    if website_url:
        source_info["website_url"] = website_url

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
    console.print(f"Created or updated object ID {obj.id}")

    ## Create the "sources" record.

    metadata = {
        "slug": slug,
        "primary_table": f"{slug}_polygons",
        "scale": scale,
    }
    if name:
        metadata["name"] = name
    if website_url:
        metadata["url"] = website_url
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
    if raster_url:
        metadata["raster_url"] = raster_url

    if source := get_source_by_slug(slug):
        source = update_source(source.source_id, **metadata)
    else:
        source = create_source(**metadata)
    ingest_process = update_ingest_process(ingest_process.id, source_id=source.source_id)
    console.print(f"Created or updated source ID {source.source_id}")

    return ingest_object(obj.bucket, obj.key, filter=filter, append_data=append_data)


def ingest_object(
    bucket: Annotated[
        str,
        Argument(help="The object's bucket"),
    ],
    key: Annotated[
        str,
        Argument(help="The object's key"),
    ],
    *,
    filter: Annotated[
        Optional[str],
        Option(help="How to interpret the contents of the specified object"),
    ] = None,
    append_data: Annotated[
        bool,
        Option(help="Whether to append data to the map when it already exists"),
    ] = False,
) -> Object:
    """
    Ingest an object in S3 containing a map into Macrostrat.

    This command/function assumes that database records for the "ingest
    process" and "sources" tables have already been created. (The web UI's
    upload form creates the required records.)
    """
    obj = get_object_by_loc(bucket, key)
    if not obj:
        raise IngestError(f"No such object in the database: {bucket}/{key}")

    ingest_process = get_ingest_process_by_object_group_id(obj.object_group_id)
    if not ingest_process:
        raise IngestError("No ingest process in the database for object ID {obj.id}")

    source = get_source_by_id(ingest_process.source_id)
    if not source:
        raise_ingest_error(
            ingest_process,
            "No source ID in the database for ingest process ID {ingest_process.id}",
        )

    ## Normalize the filter.

    if filter:
        filter = filter.lower()

    ## Download the object to a local, temporary file.

    s3 = minio.Minio(
        config.S3_HOST,
        access_key=config.S3_ACCESS_KEY,
        secret_key=config.S3_SECRET_KEY,
    )
    obj_basename = key.split("/")[-1]
    fd, local_filename = tempfile.mkstemp(suffix=f"-{obj_basename}")
    os.close(fd)
    local_file = pathlib.Path(local_filename)

    console.print(f"Downloading archive into {local_file}")
    s3.fget_object(bucket, key, str(local_file))
    console.print("Finished downloading archive")

    ## Process anything that might have points, lines, and polygons.

    try:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as td:
            tmp_dir = pathlib.Path(td)
            console.print(f"Extracting archive into {tmp_dir}")

            ## Extract the archive.

            extract_archive(local_file, tmp_dir, ingest_process=ingest_process)

            ## Locate files of interest.

            gis_files = (
                list(tmp_dir.glob("**/*.shp"))
                + list(tmp_dir.glob("**/*.geojson"))
                + list(tmp_dir.glob("**/*.gpkg"))
            )
            gis_data = []
            excluded_data = []

            for gis_file in gis_files:
                if filter == "ta1":
                    if "_bbox" not in gis_file.name and "_legend" not in gis_file.name:
                        gis_data.append(gis_file)
                    else:
                        excluded_data.append(gis_file)
                else:
                    gis_data.append(gis_file)
            if not gis_data:
                raise_ingest_error(ingest_process, "Failed to locate GIS data")

            ## Process the GIS files.

            console.print(f"NOT ingesting {excluded_data}")
            console.print(f"Ingesting {source.slug} from {gis_data}")
            try:
                ingest_map(
                    source.slug,
                    gis_data,
                    if_exists="append" if append_data else "replace",
                )
            except Exception as exn:
                raise_ingest_error(ingest_process, str(exn), exn)

            ## Process any other data of interest.

            try:
                if filter == "alaska":
                    set_alaska_metadata(source, tmp_dir)
            except Exception as exn:
                raise_ingest_error(ingest_process, str(exn), exn)
    finally:
        local_file.unlink()

    ## Prepare tables for human review.

    macrostrat_map = get_map_info(DB, source.slug)
    console.print(f"Macrostrat map object: {macrostrat_map}")

    try:
        prepare_fields(macrostrat_map)
        ingest_process = update_ingest_process(ingest_process.id, state=IngestState.prepared)
        create_rgeom(macrostrat_map)
        create_webgeom(macrostrat_map)
        ingest_process = update_ingest_process(ingest_process.id, state=IngestState.ingested)
    except Exception as exn:
        raise_ingest_error(ingest_process, str(exn), exn)

    return obj


def ingest_from_csv(
    ctx: Context,
    csv_file: Annotated[
        pathlib.Path,
        Argument(help="CSV file containing arguments for ingest-file"),
    ],
) -> None:
    """
    Ingest multiple maps as specified in a CSV file.

    This command/function enables the bulk ingest of maps by specifying
    values for arguments and options to the ingest-file command/function,
    with each row in the CSV file corresponding to one map/invocation.

    The first row of the CSV file should be a header listing the names of
    arguments and options to the ingest-file subcommand, with hyphens being
    replaced by underscores.

    Instead of the "local_file" argument, there must be a column for
    "archive_url", which is where to download the map's archive file from.

    There must also be a column for "slug".

    Options for the ingest-file subcommand can be provided *after* the CSV
    file, in which case they will override whatever is specified in the CSV
    file itself. Note that mistyped options will result in verbose errors.
    """
    slugs_seen = []

    with open(csv_file, mode="r", encoding="utf-8", newline="") as input_fp:
        reader = csv.DictReader(input_fp)

        for row in reader:
            url = row["archive_url"]
            prefix = row.get("s3_prefix") or "ingest_from_csv"

            download_dir = DOWNLOAD_ROOT_DIR / prefix
            download_dir.mkdir(parents=True, exist_ok=True)

            filename = url.split("/")[-1]
            partial_local_file = download_dir / (filename + ".partial")
            local_file = download_dir / filename

            if not local_file.exists():
                response = requests.get(url, stream=True, timeout=config.TIMEOUT)

                if not response.ok:
                    console.print(f"Failed to download {url}")
                    continue

                with open(partial_local_file, mode="wb") as local_fp:
                    for chunk in response.iter_content(chunk_size=config.CHUNK_SIZE):
                        local_fp.write(chunk)
                partial_local_file.rename(local_file)

            kwargs = {}
            for f in FIELDS:
                if row.get(f):
                    kwargs[f] = row[f]
            for i in range(0, len(ctx.args), 2):
                k = ctx.args[i][2:].replace("-", "_")
                v = ctx.args[i + 1]
                kwargs[k] = v

            kwargs["append_data"] = row["slug"] in slugs_seen
            slugs_seen.append(row["slug"])

            try:
                ingest_file(local_file, **kwargs)
            except Exception as exn:
                console.print(f"Exception: {exn}")


# --------------------------------------------------------------------------


def run_polling_loop(
    polling_interval: Annotated[
        int,
        Argument(help="How often to poll, in seconds"),
    ] = 30,
) -> None:
    """
    Poll for and process pending ingest processes.
    """
    while True:
        console.print("Starting iteration of polling loop")
        with get_db_session() as session:
            for ingest_process in session.scalars(
                select(IngestProcess).where(
                    IngestProcess.state == IngestState.pending,
                )
            ).unique():
                console.print(f"Examining ingest process ID {ingest_process.id}")
                for obj in session.scalars(
                    select(Object).where(
                        Object.object_group_id == ingest_process.object_group_id,
                    )
                ):
                    console.print(f"Processing object ID {obj.id} ({obj.bucket}/{obj.key})")
                    try:
                        ingest_object(obj.bucket, obj.key)
                    except Exception as exn:
                        record_ingest_error(ingest_process, str(exn))

        console.print("Finished iteration of polling loop")
        time.sleep(polling_interval)
