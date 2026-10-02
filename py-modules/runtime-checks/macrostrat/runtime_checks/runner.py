"""Run catalog checks over HTTP, concurrently."""

import asyncio
import ssl
import time
from typing import Iterable, Mapping, Optional

import httpx

from .model import TIERS, Check, Result

#: Which configured host each service is reached through.
SERVICE_HOSTS = {
    "web": "base_url",
    "api-v2": "base_url",
    "api-v3": "base_url",
    "postgrest": "base_url",
    "tiles": "tiles_url",
    "local": None,
}


def ssl_context() -> ssl.SSLContext:
    import truststore

    return truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)


def run_checks(
    checks: Iterable[Check],
    hosts: Mapping[str, Optional[str]],
    *,
    timeout: float = 10,
    concurrency: int = 8,
    transport: Optional[httpx.AsyncBaseTransport] = None,
) -> list[Result]:
    """Run each check against the host its service maps to, in catalog order.

    A service whose host is unset yields one warning instead of its checks.
    """
    runnable, results = [], []
    unreachable: dict[str, int] = {}
    for check in checks:
        if check.tier not in TIERS:
            continue
        key = SERVICE_HOSTS.get(check.service)
        host = hosts.get(key) if key else ""
        if host is None:
            unreachable[check.service] = unreachable.get(check.service, 0) + 1
            continue
        runnable.append((check, _join(host, check.path)))

    for service, count in unreachable.items():
        key = SERVICE_HOSTS[service]
        results.append(
            Result(
                service,
                "warn",
                f"no {key} configured; {count} checks skipped",
                service=service,
            )
        )

    results[:0] = asyncio.run(_run_all(runnable, timeout, concurrency, transport))
    return results


async def _run_all(runnable, timeout, concurrency, transport):
    limit = asyncio.Semaphore(concurrency)
    kwargs = {"transport": transport} if transport else {"verify": ssl_context()}
    async with httpx.AsyncClient(timeout=timeout, **kwargs) as client:

        async def run(check, url):
            async with limit:
                return await run_check(client, check, url)

        return await asyncio.gather(*(run(c, u) for c, u in runnable))


async def run_check(client: httpx.AsyncClient, check: Check, url: str) -> Result:
    start = time.monotonic()
    try:
        response = await client.get(url, follow_redirects=check.follow_redirects)
    except httpx.HTTPError as err:
        detail = f"{type(err).__name__}: {err}" if str(err) else type(err).__name__
        return _result(check, url, "fail", detail, start)
    problems = [p for p in (e(response) for e in check.expect) if p]
    if problems:
        return _result(check, url, check.severity, "; ".join(problems), start)
    return _result(check, url, "ok", str(response.status_code), start)


def _result(check, url, status, detail, start):
    elapsed = round(time.monotonic() - start, 3)
    return Result(check.name, status, detail, check.service, url, elapsed)


def _join(host: str, path: str) -> str:
    if path.startswith(("http://", "https://")) or not host:
        return path
    return host.rstrip("/") + "/" + path.lstrip("/")
