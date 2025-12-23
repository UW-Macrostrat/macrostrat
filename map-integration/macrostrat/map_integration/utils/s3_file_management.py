import hashlib
import json
import pathlib
import shutil
import subprocess
import tempfile
from os import path
from pathlib import Path
from textwrap import dedent
from rich.console import Console
from rich.table import Table
from rich.progress import Progress
from macrostrat.core import app as app_
from macrostrat.core.exc import MacrostratError
from macrostrat.core.schemas import (
    SchemeEnum,
)
from minio import Minio

def get_minio_client():
    return Minio(
        endpoint=settings.get("storage.endpoint"),
        access_key=settings.get("storage.access_key"),
        secret_key=settings.get("storage.secret_key"),
        secure=True,
    )

settings = app_.settings
console = Console()

def print_objects(objects: list[dict]) -> None:
    table = Table(title="Objects staged for deletion")

    table.add_column("#", justify="right")
    table.add_column("Object ID", justify="right")
    table.add_column("Key")

    for i, obj in enumerate(objects, start=1):
        table.add_row(str(i), str(obj["id"]), obj["key"])

    console.print(table)



#--------------UPLOADS---------------

def get_existing_object_id(db, *, host: str, bucket: str, key: str) -> int | None:
    return db.run_query(
        """
        SELECT id
        FROM storage.object
        WHERE scheme = 's3'
          AND host = :host
          AND bucket = :bucket
          AND key = :key
        """,
        dict(host=host, bucket=bucket, key=key),
    ).scalar()


def insert_storage_object(
    db,
    *,
    host: str,
    bucket: str,
    key: str,
    sha256: str,) -> int:
    db.run_sql(
        """
        INSERT INTO storage.object
          (scheme, host, bucket, key, sha256_hash)
        VALUES
          ('s3', :host, :bucket, :key, :sha256)
        """,
        dict(
            host=host,
            bucket=bucket,
            key=key,
            sha256=sha256,
        ),
    )
    object_id = get_existing_object_id(db, host=host, bucket=bucket, key=key)
    if object_id is None:
        raise RuntimeError("Failed to retrieve storage.object id after insert")
    return object_id


def link_object_to_ingest(
    db,
    *,
    ingest_process_id: int,
    object_id: int,
) -> None:
    db.run_sql(
        """
        INSERT INTO maps_metadata.map_files (ingest_process_id, object_id)
        VALUES (:ingest_process_id, :object_id)
        ON CONFLICT DO NOTHING
        """,
        dict(
            ingest_process_id=ingest_process_id,
            object_id=object_id,
        ),
    )


def upload_file_to_minio(
    minio_client: Minio,
    *,
    bucket: str,
    object_key: str,
    local_path: Path,
    sha256: str,
    content_type: str | None = None,) -> None:
    with open(local_path, "rb") as f:
        minio_client.put_object(
            bucket_name=bucket,
            object_name=object_key,
            data=f,
            length=local_path.stat().st_size,
            content_type=content_type,
            metadata={"sha256": sha256},
        )

def staging_upload_dir(
    slug: str,
    data_path: Path,
    ext: str,
    db,
    ingest_process_id: int,
) -> dict:
    """
    Upload local files to S3 via MinIO and register them in storage.object.
    """
    if ingest_process_id is None:
        raise ValueError("ingest_process_id is required to link uploaded files")

    bucket = settings.get("storage.bucket_name")
    host = settings.get("storage.endpoint")
    minio_client = get_minio_client()

    files_to_upload: list[tuple[Path, str]] = []

    if ext == ".gdb":
        archive_base = path.join(tempfile.gettempdir(), f"{slug}.gdb")
        archive_path = shutil.make_archive(
            archive_base, "zip", root_dir=data_path.parent, base_dir=data_path.name
        )
        files_to_upload.append((Path(archive_path), Path(archive_path).name))

    elif data_path.is_dir():
        for f in data_path.rglob("*"):
            if f.is_file():
                files_to_upload.append((f, str(f.relative_to(data_path))))

    elif data_path.is_file():
        files_to_upload.append((data_path, data_path.name))

    uploaded_object_ids: list[int] = []

    for local_path, rel_key in files_to_upload:
        object_key = f"{slug}/{rel_key}"

        existing_id = get_existing_object_id(
            db,
            host=host,
            bucket=bucket,
            key=object_key,
        )
        if existing_id:
            continue

        sha256 = sha256_of_file(local_path)

        upload_file_to_minio(
            minio_client,
            bucket=bucket,
            object_key=object_key,
            local_path=local_path,
            sha256=sha256,
        )

        object_id = insert_storage_object(
            db,
            host=host,
            bucket=bucket,
            key=object_key,
            sha256=sha256,
        )

        link_object_to_ingest(
            db,
            ingest_process_id=ingest_process_id,
            object_id=object_id,
        )

        uploaded_object_ids.append(object_id)

    return {
        "bucket_name": bucket,
        "slug": slug,
        "endpoint": host,
        "destination": f"s3://{bucket}/{slug}/",
        "objects_created": uploaded_object_ids,
    }




# --------------------DELETIONS-------------------
def get_objects_for_slug(db, *, host: str, bucket: str, slug: str) -> list[dict]:
    return db.run_query(
        """
        SELECT id, key
        FROM storage.object
        WHERE scheme = 's3'
          AND host = :host
          AND bucket = :bucket
          AND key LIKE :prefix
        """,
        dict(
            host=host,
            bucket=bucket,
            prefix=f"{slug}/%",
        ),
    ).mappings().all()

def unlink_object_from_ingests(db, *, object_id: int) -> None:
    db.run_sql(
        """
        DELETE FROM maps_metadata.map_files
        WHERE object_id = :object_id
        """,
        dict(object_id=object_id),
    )

def delete_storage_object(db, *, object_id: int) -> None:
    db.run_sql(
        """
        DELETE FROM storage.object
        WHERE id = :id
        """,
        dict(id=object_id),
    )

def delete_object_from_minio(
    minio_client: Minio,
    *,
    bucket: str,
    object_key: str,
) -> None:
    minio_client.remove_object(bucket, object_key)


def staging_delete_dir(slug: str, db) -> dict:
    """
    Delete all staged objects under a slug using DB as the source of truth.
    """
    bucket = settings.get("storage.bucket_name")
    host = settings.get("storage.endpoint")
    minio_client = get_minio_client()

    objects = get_objects_for_slug(
        db,
        host=host,
        bucket=bucket,
        slug=slug,
    )

    deleted = []

    for obj in objects:
        object_id = obj["id"]
        object_key = obj["key"]

        #Remove ingest links
        unlink_object_from_ingests(db, object_id=object_id)

        #Remove DB object record
        delete_storage_object(db, object_id=object_id)

        #Remove from MinIO
        delete_object_from_minio(
            minio_client,
            bucket=bucket,
            object_key=object_key,
        )

        deleted.append(object_key)

    return {
        "bucket": bucket,
        "slug": slug,
        "objects_deleted": len(deleted),
        "keys": deleted,
    }








def staging_list_dir(slug: str, page_token: int = 0, page_size: int = 20) -> dict:
    endpoint = settings.get("storage.endpoint")
    b_access = settings.get("storage.access_key")
    b_secret = settings.get("storage.secret_key")
    bucket_name = settings.get("storage.bucket_name")

    cfg = dedent(
        f"""
        [dev]
        type = s3
        provider = Minio
        endpoint = {endpoint}
        access_key_id = {b_access}
        secret_access_key = {b_secret}
        acl = private
    """
    )

    list_dirs = slug == "all"
    dst = f"dev:{bucket_name}" if list_dirs else f"dev:{bucket_name}/{slug}"

    with tempfile.NamedTemporaryFile("w+", delete=False) as tf:
        tf.write(cfg)
        tf.flush()

        try:
            args = ["rclone", "lsjson", dst, "--config", tf.name]
            if list_dirs:
                args += ["--dirs-only", "--max-depth", "1"]
            else:
                args += ["--recursive", "--files-only"]
            out = subprocess.run(
                args, check=True, capture_output=True, text=True
            ).stdout

        except FileNotFoundError:
            conf_dir, conf_name = path.dirname(tf.name), path.basename(tf.name)
            args = [
                "docker",
                "run",
                "--rm",
                "-v",
                f"{conf_dir}:/cfg:ro",
                "rclone/rclone:latest",
                "lsjson",
                dst,
                "--config",
                f"/cfg/{conf_name}",
            ]
            if list_dirs:
                args += ["--dirs-only", "--max-depth", "1"]
            else:
                args += ["--recursive", "--files-only"]
            out = subprocess.run(
                args, check=True, capture_output=True, text=True
            ).stdout

    entries = json.loads(out) if out.strip() else []

    if list_dirs:
        items = []
        for o in entries:
            if o.get("IsDir"):
                p = (o.get("Path") or o.get("Name") or "").strip("/")
                if p:
                    items.append(f"{p}/")
    else:
        items = [f"{slug}/{o['Path']}" for o in entries]
    end = page_token + page_size
    next_token = end if end < len(items) else None
    return {
        "files": items[page_token:end],
        "next_page_token": next_token,
        "total": len(items),
    }


def staging_download_dir(slug: str, dest_path: pathlib.Path) -> dict:
    """
    Download a directory from the staging bucket to a local path.
    Args:
        slug: Remote key filename (folder) in the bucket, e.g. "myprefix_region"
        dest_path: Local directory to download into (created if missing)
    Returns:
        dict with details about the download source/destination.
    """
    endpoint = settings.get("storage.endpoint")
    b_access = settings.get("storage.access_key")
    b_secret = settings.get("storage.secret_key")
    bucket_name = settings.get("storage.bucket_name")

    missing = [
        k
        for k, v in {
            "storage.endpoint": endpoint,
            "storage.bucket_name": bucket_name,
            "storage.*_access": b_access,
            "storage.*_secret": b_secret,
        }.items()
        if not v
    ]
    if missing:
        print("These are missing ", missing)
    dest_path.mkdir(parents=True, exist_ok=True)

    cfg = dedent(
        f"""
        [dev]
        type = s3
        provider = Minio
        endpoint = {endpoint}
        access_key_id = {b_access}
        secret_access_key = {b_secret}
        acl = private
        """
    )
    src = f"dev:{bucket_name}/{slug}"

    with tempfile.NamedTemporaryFile("w+", delete=False) as tf:
        tf.write(cfg)
        tf.flush()
        cmd = [
            "rclone",
            "copy",
            src,
            str(dest_path),
            "--config",
            tf.name,
            "--checksum",
            "--metadata",
            "--transfers",
            "8",
            "--log-level",
            "ERROR",
            "--s3-no-check-bucket",
            "--progress",
        ]

        try:
            subprocess.run(cmd, check=True)
        except FileNotFoundError:
            # Fallback to Dockerized rclone
            conf_dir, conf_name = path.dirname(tf.name), path.basename(tf.name)
            docker_cmd = [
                "docker",
                "run",
                "--rm",
                "-v",
                f"{conf_dir}:/cfg:ro",
                "-v",
                f"{dest_path}:/dst",
                "rclone/rclone:latest",
                "copy",
                src,
                "/dst",
                "--config",
                f"/cfg/{conf_name}",
                "--checksum",
                "--metadata",
                "--transfers",
                "8",
                "--log-level",
                "ERROR",
                "--s3-no-check-bucket",
                "--progress",
            ]
            subprocess.run(docker_cmd, check=True)

    return {
        "bucket_name": bucket_name,
        "slug": slug,
        "endpoint": endpoint,
        "source": f"s3://{bucket_name}/{slug}/",
        "downloaded_to": str(dest_path.resolve()),
    }


def sha256_of_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    # DB stores hex, so return hexdigest()
    return h.hexdigest()


def insert_local_files_into_db(
    db, slug: str, data_path: Path, gdb_zip_path: Path | None, ext
):
    """
    Insert DB rows for files exactly as they will be uploaded to S3.
    - If ext == ".gdb": insert only the .gdb.zip
    - Otherwise: recursively list all files with full relative path
    """
    bucket = settings.get("storage.bucket_name")
    host = settings.get("storage.endpoint")
    files_to_insert = []

    # GDB upload → use only the zip
    if ext == ".gdb":
        if gdb_zip_path and gdb_zip_path.exists():
            files_to_insert.append((gdb_zip_path, gdb_zip_path.name))

    # normal directory upload → keep nested structure
    elif data_path.is_dir():
        for f in data_path.rglob("*"):
            if f.is_file():
                # compute relative path WITH directories preserved
                rel_key = f.relative_to(data_path)
                files_to_insert.append((f, str(rel_key)))

    # single file upload
    elif data_path.is_file():
        files_to_insert.append((data_path, data_path.name))

    inserted = []

    for f, rel_key in files_to_insert:
        record_key = f"{slug}/{rel_key}"
        exists = db.run_query(
            """
            SELECT 1
            FROM storage.object
            WHERE scheme='s3'
              AND host=:host AND bucket=:bucket AND key=:key
            """,
            dict(host=host, bucket=bucket, key=record_key),
        ).scalar()

        if exists:
            continue

        db.run_sql(
            """
            INSERT INTO storage.object (scheme, host, bucket, key)
            VALUES ('s3', :host, :bucket, :key)
            """,
            dict(host=host, bucket=bucket, key=record_key),
        )
        object_id = db.run_query(
            """
            SELECT id
            FROM storage.object
            WHERE scheme='s3'
              AND host=:host AND bucket=:bucket AND key=:key
            """,
            dict(host=host, bucket=bucket, key=record_key),
        ).scalar()
        inserted.append(object_id)

    return inserted
