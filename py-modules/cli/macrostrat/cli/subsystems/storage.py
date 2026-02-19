"""
Storage system management
"""

import re
import subprocess
import tempfile
from os import environ, path
from subprocess import run
from textwrap import dedent
from typing import List, Optional

from rich import print
from typer import Argument, Option, Typer

from macrostrat.core import app as app_
from macrostrat.utils import get_logger

from ...core.exc import MacrostratError
from ..kubernetes import _kubectl, get_secret

settings = app_.settings

log = get_logger(__name__)


app = Typer(no_args_is_help=True)

if admin := settings.get("storage.admin", None):
    host = settings.get("storage.endpoint", None)

    if getattr(admin, "type") == "ceph-object-storage":
        access_key = getattr(admin, "access_key")
        secret_key = getattr(admin, "secret_key")

        # Set up the radosgw-admin command

        @app.command("admin", add_help_option=False)
        def storage_admin(args: List[str] = Argument(None)):
            """
            Run the Ceph Object Storage admin command.
            """
            import sys
            from os import environ

            from htpheno.radosgw_admin_client.cli import UserError, main

            environ["RADOSGW_ACCESS_KEY"] = access_key
            environ["RADOSGW_SECRET_KEY"] = secret_key
            environ["RADOSGW_HOST"] = re.sub("^https?://", "", host)

            if args is None:
                args = ["--help"]

            sys.argv = ["radosgw-admin", *args]
            try:
                main()
            except UserError as e:
                # raise MacrostratError(e)
                print("[red bold]Error:[/] [red]" + str(e))


def _s3_users():
    res = _kubectl(
        settings,
        ["get", "secrets", "-o", "jsonpath={.items[*].metadata.name}"],
        capture_output=True,
        text=True,
    )
    prefix = "s3-user-"
    return [
        r.replace(prefix, "") for r in res.stdout.split(" ") if r.startswith(prefix)
    ]


@app.command()
def s3_bucket_migration(
    dry_run: bool = Option(False, "--dry-run", "-n", help="Do everything except write"),
    show_cmd: bool = Option(False, help="Print the rclone command for debugging"),
    src: str = Option("rockd-photo-backup", help="Source bucket that contains photos"),
    dst: str = Option(
        "rockd-photo-prod", help="Destination bucket to copy photos into"
    ),
):
    """Must be in the development env to run this command."""
    endpoint = settings.get("storage.endpoint")
    b_access = settings.get("storage.rockd_backup_access")
    b_secret = settings.get("storage.rockd_backup_secret")
    p_access = settings.get("storage.rockd_prod_access")
    p_secret = settings.get("storage.rockd_prod_secret")

    cfg = dedent(
        f"""
        [rockd-backup]
        type = s3
        provider = Minio
        endpoint = {endpoint}
        access_key_id = {b_access}
        secret_access_key = {b_secret}
        acl = private

        [rockd-prod]
        type = s3
        provider = Minio
        endpoint = {endpoint}
        access_key_id = {p_access}
        secret_access_key = {p_secret}
        acl = private
    """
    )

    with tempfile.NamedTemporaryFile("w+", delete=False) as tf:
        tf.write(cfg)
        tf.flush()

        # local rclone cmd
        cmd = [
            "rclone",
            "copy",
            f"rockd-backup:{src}",
            f"rockd-prod:{dst}",
            "--config",
            tf.name,
            "--checksum",
            "--metadata",
            "--transfers",
            "8",
            "--log-level",
            "NOTICE",
            "--stats-log-level",
            "NOTICE",
            "--stats=1s",
            "--stats-one-line",
            "--s3-no-check-bucket",
            "--ignore-existing",
        ]
        if dry_run:
            cmd.append("--dry-run")
        if show_cmd:
            print(" ".join(cmd))

        try:
            subprocess.run(cmd, check=True)
        except FileNotFoundError:
            # use rclone docker image
            conf_dir, conf_name = path.dirname(tf.name), path.basename(tf.name)
            docker_cmd = [
                "docker",
                "run",
                "--rm",
                "-v",
                f"{conf_dir}:/cfg:ro",
                "rclone/rclone:latest",
                "copy",
                f"rockd-backup:{src}",
                f"rockd-prod:{dst}",
                "--config",
                f"/cfg/{conf_name}",
                "--checksum",
                "--metadata",
                "--transfers",
                "8",
                "--log-level",
                "NOTICE",
                "--stats-log-level",
                "NOTICE",
                "--stats=1s",
                "--stats-one-line",
                "--s3-no-check-bucket",
                "--ignore-existing",
            ]
            if dry_run:
                docker_cmd.append("--dry-run")
            if show_cmd:
                print(" ".join(docker_cmd))
            subprocess.run(docker_cmd, check=True)

        print("[green]Backup complete[/green]")


@app.command()
def users():
    """
    List available S3 users.
    """
    print(_s3_users())


@app.command(
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
    add_help_option=False,
)
def mc(args: List[str] = Argument(None)):
    """
    Run the Minio client in a Docker container.
    """

    script = "mc"
    if args is not None:
        script += " " + " ".join(args)

    _mc(script)


def _mc(command: str, **kwargs):
    """
    Run the Minio client in a Docker container.
    """
    _script = []
    for user in _s3_users():
        cfg = get_secret(settings, "s3-user-" + user)
        if cfg is None:
            raise Exception(f"No secret found for S3 user {user}.")

        access_key = cfg["access_key"]
        secret_key = cfg["secret_key"]
        endpoint = getattr(settings, "s3_endpoint")

        _script.append(
            f"mc alias set {user} {endpoint} {access_key} {secret_key} --api s3v4 > /dev/null 2>&1"
        )

    # Delete common aliases
    for alias in ["gcs", "local", "play", "s3"]:
        _script.append(f"mc alias remove {alias} > /dev/null 2>&1")

    _script.append(command)
    script = "\n".join(_script)

    host = getattr(settings, "docker_base_url", "unix://var/run/docker.sock")

    log.info(f"Running Minio client in Docker host {host}")

    return run(
        [
            "docker",
            "run",
            "--rm",
            "-it",
            "--entrypoint=/bin/sh",
            "minio/mc:latest",
            "-c",
            script,
        ],
        env={
            "DOCKER_HOST": host,
            **environ,
        },
        **kwargs,
    )


@app.command()
def mirror(
    src: Optional[str] = Argument(None),
    dst: Optional[str] = Argument(None),
    overwrite=Option(False, help="Overwrite existing files"),
):
    """
    Mirror two buckets using a worker
    """
    # Build and run a Docker container with mc

    if src is None or dst is None:
        raise Exception("Both source and destination buckets must be specified.")

    flags = ""
    if overwrite:
        flags = "--overwrite"

    script = "\n".join([f"mc mb {dst}", f"mc mirror {flags} {src} {dst}"])

    _mc(script)
