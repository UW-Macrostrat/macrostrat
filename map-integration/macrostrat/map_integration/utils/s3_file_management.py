import hashlib
import json
import pathlib
import shutil
import subprocess
import tempfile
from os import path
from pathlib import Path
from textwrap import dedent

from rich.progress import Progress

from macrostrat.core import app as app_
from macrostrat.core.exc import MacrostratError
from macrostrat.core.schemas import (  # type: ignore[import-untyped]
    IngestProcess,
    IngestProcessTag,
    IngestState,
    Object,
    ObjectGroup,
    SchemeEnum,
    Sources,
)

settings = app_.settings


# object group id...store a set of objects related to a map....
# page through objects and ingest them.
# single ingestion....
# file to be stored in the storage schema and objects table...object group...
# change object group table into an intersection table that ties  the objects with the maps_metadata.ingest_process table.
# delete the object group id from all the tables.
# super standardized upload
# specify the bucket name
def staging_upload_dir(slug: str, data_path: pathlib.Path, ext: str) -> dict:
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

    dst = f"dev:{bucket_name}/{slug}"
    # If a FileGDB directory, zip it to slug.gdb.zip and upload that file
    if ext == ".gdb":
        archive_base = path.join(tempfile.gettempdir(), f"{slug}.gdb")
        archive_path = shutil.make_archive(
            archive_base, "zip", root_dir=data_path.parent, base_dir=data_path.name
        )
        data_path = pathlib.Path(archive_path)

    with tempfile.NamedTemporaryFile("w+", delete=False) as tf:
        tf.write(cfg)
        tf.flush()

        cmd = [
            "rclone",
            "copy",
            str(data_path),
            dst,
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
            conf_dir, conf_name = path.dirname(tf.name), path.basename(tf.name)
            docker_cmd = [
                "docker",
                "run",
                "--rm",
                "-v",
                f"{conf_dir}:/cfg:ro",
                "-v",
                f"{data_path}:/src:ro",
                "rclone/rclone:latest",
                "copy",
                "/src",
                f"{dst}",
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
        "filename": f"{slug}/",
        "endpoint": endpoint,
        "destination": f"s3://{bucket_name}/{slug}/",
    }


def staging_delete_dir(slug: str, file_name: str | None = None) -> None:
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

    target = f"dev:{bucket_name}/{slug}" + (f"/{file_name}" if file_name else "")

    with tempfile.NamedTemporaryFile("w+", delete=False) as tf:
        tf.write(cfg)
        tf.flush()
        cmd = [
            "rclone",
            "deletefile" if file_name else "purge",
            target,
            "--config",
            tf.name,
            "--s3-no-check-bucket",
        ]
        try:
            subprocess.run(cmd, check=True)
        except FileNotFoundError:
            conf_dir, conf_name = path.dirname(tf.name), path.basename(tf.name)
            subprocess.run(
                [
                    "docker",
                    "run",
                    "--rm",
                    "-v",
                    f"{conf_dir}:/cfg:ro",
                    "rclone/rclone:latest",
                    "deletefile" if file_name else "purge",
                    target,
                    "--config",
                    f"/cfg/{conf_name}",
                    "--s3-no-check-bucket",
                ],
                check=True,
            )


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


def upload_files_db(db, slug: str, data_path: Path):
    """
    Insert metadata files into storage.object, **only if not already inserted**.
    """
    bucket = settings.get("storage.bucket_name")
    host = settings.get("storage.endpoint")

    # Fetch the original map source URL
    source_url = db.run_query(
        "SELECT url FROM maps.sources WHERE slug = :slug",
        dict(slug=slug),
    ).scalar()

    metadata_files = (
        list(data_path.glob("*.json"))
        + list(data_path.glob("*.csv"))
        + list(data_path.glob("*.txt"))
        + list(data_path.glob("*.xml"))
        + list(data_path.glob("*.zip"))
        + list(data_path.glob("*.xlsx"))
        + list(data_path.glob("*.tsv"))
        + list(data_path.glob("*.xls"))
        + list(data_path.glob("*.gpkg"))
        + list(data_path.glob("*.shp"))
    )

    inserted = []
    skipped = []

    for f in metadata_files:
        # MIME detection
        mime_type = "application/octet-stream"
        if f.suffix == ".json":
            mime_type = "application/json"
        elif f.suffix == ".csv":
            mime_type = "text/csv"
        elif f.suffix in [".txt", ".tsv"]:
            mime_type = "text/plain"
        elif f.suffix == ".xml":
            mime_type = "application/xml"

        record_key = f"{slug}/{f.name}"
        sha256 = sha256_of_file(f)

        # --- NEW: Check if row already exists ---
        exists = db.run_query(
            """
            SELECT 1
            FROM storage.object
            WHERE scheme = 's3'
              AND host = :host
              AND bucket = :bucket
              AND key = :key
            """,
            dict(host=host, bucket=bucket, key=record_key),
        ).scalar()

        if exists:
            skipped.append(record_key)
            continue

        # Insert only when not present
        db.run_sql(
            """
            INSERT INTO storage.object (scheme, host, bucket, key, source, mime_type, sha256_hash)
            VALUES ('s3', :host, :bucket, :key, :source, :mime_type, :sha256_hash)
            """,
            dict(
                host=host,
                bucket=bucket,
                key=record_key,
                source=json.dumps({"local_path": str(f), "map_source_url": source_url}),
                mime_type=mime_type,
                sha256_hash=sha256,
            ),
        )

        inserted.append(record_key)

    return {"inserted": inserted, "skipped": skipped}
