"""`macrostrat check`: does the local stack answer the way its clients expect?

Two groups of read-only checks. **Routes** are plain HTTP requests from the
host, as a browser or API client makes them. **Local setup** covers what no
restart repairs: whether each storage client holds credentials the store
accepts, trusts its certificate, and finds the buckets it writes to. Container
state is left to docker compose, which `macrostrat up` reconciles.
"""

import subprocess
from dataclasses import dataclass
from sys import exit
from typing import Iterator

from rich.console import Console

#: Routes the gateway serves, fetched from the host. curl, not Python, so the
#: macOS keychain (where OrbStack's CA lives) decides trust, as in a browser.
ROUTES = (
    "https://macrostrat.local/api/v2/",
    "https://macrostrat.local/api/v3/openapi.json",
    "https://macrostrat.local/api/pg/",
    "https://tiles.macrostrat.local/openapi.json",
    "https://storage.macrostrat.local/minio/health/live",
    "http://storage.macrostrat.local/minio/health/live",
)

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


@dataclass
class Result:
    name: str
    status: str  # "ok", "warn" or "fail"
    detail: str = ""


def _run(*args: str, timeout: int = 30) -> subprocess.CompletedProcess:
    return subprocess.run(args, capture_output=True, text=True, timeout=timeout)


def _last_line(text: str) -> str:
    lines = text.strip().splitlines()
    if not lines:
        return ""
    return lines[-1]


def check_routes() -> Iterator[Result]:
    for url in ROUTES:
        res = _run(
            "curl", "-sS", "-o", "/dev/null", "-w", "%{http_code}", "-m", "10", url
        )
        code = res.stdout.strip()
        if res.returncode == 0 and code.startswith("2"):
            yield Result(url, "ok", code)
            continue
        yield Result(url, "fail", _last_line(res.stderr) or code)


def check_host_storage(settings) -> Iterator[Result]:
    name = "storage from host"
    endpoint = settings.storage_endpoint()
    if endpoint is None:
        yield Result(name, "warn", "no storage endpoint configured")
        return
    try:
        from minio import Minio

        access, secret = endpoint.credentials()
        client = Minio(
            endpoint.host, access_key=access, secret_key=secret, secure=endpoint.secure
        )
        names = {b.name for b in client.list_buckets()}
    except Exception as err:
        yield Result(name, "fail", f"{endpoint.endpoint}: {type(err).__name__}")
        return
    missing = [b for b in settings.buckets().values() if b not in names]
    if missing:
        yield Result(name, "fail", "missing buckets: " + ", ".join(missing))
    else:
        yield Result(name, "ok", endpoint.endpoint)


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
        yield Result(f"storage from {service}", status, detail)


_MARKS = {"ok": "[green]✓[/]", "warn": "[yellow]![/]", "fail": "[red]✗[/]"}


def print_section(console: Console, title: str, results: list):
    console.print(f"[bold]{title}[/]")
    for r in results:
        console.print(f"  {_MARKS[r.status]} {r.name} [dim]{r.detail}[/]")


def check():
    """Check that the local :app_name: stack answers as expected. Read-only."""
    from macrostrat.core import app

    routes = list(check_routes())
    setup = [*check_host_storage(app.settings), *check_container_storage()]
    print_section(app.console, "Routes", routes)
    print_section(app.console, "Local setup", setup)

    results = routes + setup
    failed = sum(r.status == "fail" for r in results)
    warned = sum(r.status == "warn" for r in results)
    app.console.print(f"\n{failed} failed, {warned} warnings, {len(results)} checks")
    if failed:
        exit(1)
