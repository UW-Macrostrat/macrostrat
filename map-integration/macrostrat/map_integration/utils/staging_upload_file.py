import subprocess
import tempfile
from os import path
from textwrap import dedent
import pathlib
from macrostrat.core.schemas import (  # type: ignore[import-untyped]
    IngestProcess,
    IngestProcessTag,
    IngestState,
    Object,
    ObjectGroup,
    SchemeEnum,
    Sources,
)
from macrostrat.core.exc import MacrostratError

from macrostrat.core import app as app_

settings = app_.settings

#upload, delete, list all files for a map.
#upload a directory
#object group id...store a set of objects related to a map....
#get list of objects.
#page through objects and ingest them.
#single ingestion....
#file to be stored in the storage schema and objects table...object group...
#change object group table into an intersection table that ties  the objects with the maps_metadata.ingest_process table.
#delete the object group id from all the tables.
#super standardized upload
#specify the bucket name
def staging_upload_file(slug: str, data_path: pathlib.Path) -> dict:
    endpoint = settings.get("storage.endpoint")
    b_access = settings.get("storage.access_key")
    b_secret = settings.get("storage.secret_key")
    bucket_name = settings.get("storage.bucket_name")

    missing = [k for k, v in {
        "storage.endpoint": endpoint,
        "storage.bucket_name": bucket_name,
        "storage.*_access": b_access,
        "storage.*_secret": b_secret,
    }.items() if not v]
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
            "rclone", "copy",
            str(data_path),
            dst,
            "--config", tf.name,
            "--checksum",
            "--metadata",
            "--transfers", "8",
            "--log-level", "NOTICE",
            "--stats-log-level", "NOTICE",
            "--stats=1s",
            "--stats-one-line",
            "--s3-no-check-bucket",
        ]

        try:
            subprocess.run(cmd, check=True)
        except FileNotFoundError:
            conf_dir, conf_name = path.dirname(tf.name), path.basename(tf.name)
            docker_cmd = [
                "docker", "run", "--rm",
                "-v", f"{conf_dir}:/cfg:ro",
                "-v", f"{data_path}:/src:ro",
                "rclone/rclone:latest",
                "copy",
                "/src",
                f"{dst}",
                "--config", f"/cfg/{conf_name}",
                "--checksum",
                "--metadata",
                "--transfers", "8",
                "--log-level", "NOTICE",
                "--stats-log-level", "NOTICE",
                "--stats=1s",
                "--stats-one-line",
                "--s3-no-check-bucket",
            ]
            subprocess.run(docker_cmd, check=True)

    return {
        "bucket_name": bucket_name,
        "prefix": f"{slug}/",
        "endpoint": endpoint,
        "destination": f"s3://{bucket_name}/{slug}/",
    }