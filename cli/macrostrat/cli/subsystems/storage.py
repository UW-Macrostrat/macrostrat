"""
Storage system management
"""

from os import environ
from subprocess import run
from typing import Optional, List

from macrostrat.utils import get_logger
from rich import print
from typer import Argument, Option, Typer

from macrostrat.core import app as app_
from ..kubernetes import get_secret, _kubectl

settings = app_.settings

log = get_logger(__name__)


app = Typer(no_args_is_help=True)


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
