"""
Storage system management
"""

import subprocess
from functools import wraps
from os import environ, path
from textwrap import dedent

from rich import print
from typer import Option, Typer

from macrostrat.core import app as app_
from macrostrat.utils import get_logger

from ...core.exc import MacrostratError
from ...core.storage import ADMIN_ENDPOINT, credential_file
from ..kubernetes import _kubectl
from .rebuild import short_help

settings = app_.settings

log = get_logger(__name__)

# The default app if we don't have a storage setup defined
admonitions = "[bold red](none defined for the current environment)[/]"
app = Typer(no_args_is_help=True, help="Storage system management\n" + admonitions)


def _export_radosgw_credentials():
    """Put the Ceph cluster-admin credential in the environment, per invocation.

    `radosgw_admin` reads `RADOSGW_*` inside `get_connection()`, at command-run
    time, so this only has to have happened before a storage command's body
    runs — not at import.

    That distinction is the whole point. This used to run in the module body, so
    importing the storage subsystem — which the CLI does while building its
    command tree for *any* invocation, `macrostrat --help` included — put a
    credential that can create and delete users and buckets cluster-wide into
    the environment of every subprocess of every command.

    Residual exposure, worth being clear about: for the storage admin commands
    themselves the credential still passes through `os.environ` and is
    inherited by anything they spawn. Closing that needs `radosgw_admin` to
    accept credentials directly (`get_connection` already takes them as
    arguments) rather than reading the environment, which is a change in the
    storage-admin submodule.
    """
    endpoint = settings.storage_endpoint(ADMIN_ENDPOINT)
    if endpoint is None:
        raise MacrostratError(
            "No Ceph object-storage admin endpoint is configured",
            details="Expected a [<env>.storage.admin] table for this environment.",
        )
    access_key, secret_key = endpoint.credentials()
    environ["RADOSGW_ACCESS_KEY"] = access_key
    environ["RADOSGW_SECRET_KEY"] = secret_key
    environ["RADOSGW_HOST"] = endpoint.host


def _wrap_callback(typer_app, hook):
    """Run *hook* before *typer_app*'s existing group callback.

    Typer allows one callback per app and `radosgw_admin` already registers one
    (`--output`, `--json/--human`, `--verbose`), so the existing function is
    wrapped rather than replaced. `functools.wraps` copies `__wrapped__`, which
    is what keeps `inspect.signature` — and so Typer's option generation —
    seeing the original signature.
    """
    info = getattr(typer_app, "registered_callback", None)
    original = getattr(info, "callback", None) if info is not None else None

    if original is None:
        typer_app.callback()(hook)
        return

    @wraps(original)
    def wrapped(*args, **kwargs):
        hook()
        return original(*args, **kwargs)

    info.callback = wrapped


if admin := settings.get("storage.admin", None):
    if str(getattr(admin, "type", "")) == "ceph-object-storage":
        from macrostrat.radosgw_admin.cli import app as storage_app

        # Imported at module scope so `--help` still lists the commands; the
        # credential itself is resolved and exported only once one of them runs.
        _wrap_callback(storage_app, _export_radosgw_credentials)
        app = storage_app


def _bucket_credentials(endpoint_name: str, legacy_prefix: str):
    """An access/secret pair, preferring a named storage endpoint.

    Falls back to the flat `storage.<prefix>_access` / `_secret` keys this
    command has always read, so existing configs keep working while new ones
    can name the credential in a secret manager under
    `[<env>.storage.endpoints.<name>]`.
    """
    endpoint = settings.storage_endpoint(endpoint_name)
    if endpoint is not None:
        return endpoint.credentials()

    access = settings.get(f"storage.{legacy_prefix}_access")
    secret = settings.get(f"storage.{legacy_prefix}_secret")
    if access is None or secret is None:
        raise MacrostratError(
            f"No credentials for {endpoint_name}",
            details=(
                f"Expected [<env>.storage.endpoints.{endpoint_name}], or the "
                f"legacy storage.{legacy_prefix}_access / _secret keys."
            ),
        )
    return access, secret


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
    b_access, b_secret = _bucket_credentials("rockd-backup", "rockd_backup")
    p_access, p_secret = _bucket_credentials("rockd-prod", "rockd_prod")

    cfg = dedent(f"""
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
    """)

    # rclone has no way to take credentials on stdin, so they have to reach it
    # as a file. Two things follow: the file is created private and truncated on
    # the way out (`_credential_file` below), and it is *deleted* — this used to
    # be a NamedTemporaryFile(delete=False) with no unlink anywhere, so every
    # run left four Ceph access/secret pairs in the temp directory permanently.
    with credential_file(cfg, prefix="macrostrat-rclone-", suffix=".conf") as tf_name:
        # local rclone cmd
        cmd = [
            "rclone",
            "copy",
            f"rockd-backup:{src}",
            f"rockd-prod:{dst}",
            "--config",
            tf_name,
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
            conf_dir, conf_name = path.dirname(tf_name), path.basename(tf_name)
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
