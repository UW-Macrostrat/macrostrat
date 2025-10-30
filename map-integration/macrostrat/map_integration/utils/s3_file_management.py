import json
import pathlib
import subprocess
import tempfile
from os import path
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


# upload, delete, list all files for a map.
# upload a directory
# object group id...store a set of objects related to a map....
# get list of objects.
# page through objects and ingest them.
# single ingestion....
# file to be stored in the storage schema and objects table...object group...
# change object group table into an intersection table that ties  the objects with the maps_metadata.ingest_process table.
# delete the object group id from all the tables.
# super standardized upload
# specify the bucket name
def staging_upload_dir(slug: str, data_path: pathlib.Path) -> dict:
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
        "prefix": f"{slug}/",
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
        slug: Remote key prefix (folder) in the bucket, e.g. "myprefix_region"
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
