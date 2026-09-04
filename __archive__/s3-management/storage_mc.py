"""Minio-client (`mc`) based S3 management — ARCHIVED, not wired up.

Extracted verbatim from
`py-modules/cli/macrostrat/cli/subsystems/storage.py` so that a decision about
the longer-term shape of S3 management has something concrete to look at. This
module is **not imported** and these commands are **not registered** on the
CLI. See README.md in this directory for why.
"""

from os import environ
from subprocess import run
from typing import List, Optional

from typer import Argument, Option

# NOTE: this module will not import as-is, deliberately. It references `app`,
# `log`, `get_secret` and `_s3_users` from the module it was extracted from —
# and `_s3_users` was never defined anywhere in the repository at all, which is
# why both commands raised NameError. Kept verbatim as a specimen for the
# decision described in README.md, not as a component to be re-imported.


@app.command(
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
    add_help_option=False,
    short_help="Run the Minio client in a Docker container",
    rich_help_panel="Tools",
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


@app.command(rich_help_panel="Tools")
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
