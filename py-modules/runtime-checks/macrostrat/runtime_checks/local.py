"""The compose-only `local` group: what no restart of the local stack repairs.

Whether each storage client holds credentials the store accepts, trusts its
certificate, and finds the buckets it writes to. Container state is left to
docker compose, which `macrostrat up` reconciles.
"""

import subprocess
from typing import Iterator

from .model import Check, Result, Status

#: The local object store's gateway routes, over both schemes its clients use.
STORAGE_ROUTES = [
    Check(
        f"storage-{scheme}",
        "local",
        f"{scheme}://storage.macrostrat.local/minio/health/live",
        [Status(200)],
    )
    for scheme in ("https", "http")
]

#: How each storage client in the stack reaches object storage, as its own
#: code does: (python command, host var, access var, secret var, secure var,
#: buckets it writes to).
CONTAINER_STORAGE = {
    # api/routes/columns.py: secure=True, and BUCKET for the column-ingest upload.
    "api_v3": (
        "uv run --no-sync python",
        "S3_HOST",
        "access_key",
        "secret_key",
        None,
        ("temp-storage",),
    ),
    "celery_worker": (
        "python",
        "S3_ENDPOINT",
        "S3_ACCESS_KEY",
        "S3_SECRET_KEY",
        "S3_SECURE",
        (),
    ),
}

_STORAGE_PROBE = """
import os, sys, minio
host, access, secret, secure_var = sys.argv[1:5]
buckets = sys.argv[5:]
secure = True
if secure_var != "-":
    secure = os.environ.get(secure_var) == "true"
try:
    client = minio.Minio(
        endpoint=os.environ[host],
        access_key=os.environ[access],
        secret_key=os.environ[secret],
        secure=secure,
    )
    names = {b.name for b in client.list_buckets()}
except Exception as err:
    print(type(err).__name__ + ": " + str(err).splitlines()[0][:200])
    sys.exit(1)
missing = [b for b in buckets if b not in names]
if missing:
    print("missing buckets: " + ", ".join(missing))
    sys.exit(2)
print("ok")
"""


def check_local_setup(settings) -> Iterator[Result]:
    yield from check_host_storage(settings)
    yield from check_container_storage()


def _run(*args: str, timeout: int = 30) -> subprocess.CompletedProcess:
    return subprocess.run(args, capture_output=True, text=True, timeout=timeout)


def _last_line(text: str) -> str:
    lines = text.strip().splitlines()
    if not lines:
        return ""
    return lines[-1]


def check_host_storage(settings) -> Iterator[Result]:
    name = "storage from host"
    endpoint = settings.storage_endpoint()
    if endpoint is None:
        yield Result(name, "warn", "no storage endpoint configured", "local")
        return
    try:
        from minio import Minio

        access, secret = endpoint.credentials()
        client = Minio(
            endpoint.host, access_key=access, secret_key=secret, secure=endpoint.secure
        )
        names = {b.name for b in client.list_buckets()}
    except Exception as err:
        detail = f"{endpoint.endpoint}: {type(err).__name__}"
        yield Result(name, "fail", detail, "local")
        return
    missing = [b for b in settings.buckets().values() if b not in names]
    if missing:
        yield Result(name, "fail", "missing buckets: " + ", ".join(missing), "local")
    else:
        yield Result(name, "ok", endpoint.endpoint, "local")


def check_container_storage() -> Iterator[Result]:
    for service, spec in CONTAINER_STORAGE.items():
        python, host, access, secret, secure, buckets = spec
        res = _run(
            "docker",
            "compose",
            "exec",
            "-T",
            service,
            *python.split(),
            "-c",
            _STORAGE_PROBE,
            *(host, access, secret, secure or "-"),
            *buckets,
        )
        status = {0: "ok", 2: "warn"}.get(res.returncode, "fail")
        detail = res.stdout.strip() or _last_line(res.stderr)
        yield Result(f"storage from {service}", status, detail, "local")
