"""Admin-only tile-cache management.

Macrostrat's tiles are cached in two layers: L1 is Varnish, sitting in front of
the tileserver, and L2 is the ``tile_cache.tile`` table the tileserver renders
into. Expiring either one is a destructive, cheap-to-request operation, which
makes it a denial-of-service vector if left open — so every route here is gated
on ``require_admin``.

These routes live in api_v3 rather than the tileserver because this is where the
session-based admin check already is. The web app is served from the same origin
as ``/api/v3``, so its auth cookie travels with the request; the tiles host
answers ``Access-Control-Allow-Origin: *``, which browsers refuse to combine
with credentials, so a button posting straight there could not be authenticated
at all. The tileserver's own ``/cache/*`` routes stay internal (see the ACL in
the Varnish VCL) and are reached through this proxy.
"""

from os import environ
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from api.routes.security import TokenData, require_admin

router = APIRouter(tags=["Cache"])

# Varnish evaluates a ban against every object older than it. A ban written over
# `obj.*` can be applied by the background "ban lurker", which then drops it from
# the list; one written over `req.*` cannot, so it is re-evaluated on every
# request forever. `X-Ban-Url` is set on stored objects for exactly this reason
# (see the VCL) — always ban over it rather than `req.url`.
_BAN_FIELD = "obj.http.X-Ban-Url"

# The regex in a ban expression is NOT quoted — the parser takes the rest of the
# expression as the pattern. Wrapping it in double quotes, as the tileserver's
# original invalidation did, makes them literal characters in the pattern, so the
# ban parses, registers, reports success and matches nothing.

# Matches every cached object.
_MATCH_ALL = "^/"


class FlushRequest(BaseModel):
    """A total flush, or one narrowed to a URL prefix such as ``carto``."""

    prefix: Optional[str] = None


class FlushResult(BaseModel):
    banned: str
    flushed: bool


@router.post("/flush", response_model=FlushResult)
async def flush_tile_cache(
    body: Optional[FlushRequest] = None,
    user_token: TokenData = Depends(require_admin),
) -> FlushResult:
    """Drop everything from the Varnish tile cache. Admin only.

    This does not touch L2, so tiles come back without being re-rendered from
    the database — it is the cheap "the cache is serving something stale" fix,
    not a rebuild. Expiring L2 as well is what ``/cache/refresh/carto`` does.
    """
    pattern = _MATCH_ALL
    if body is not None and body.prefix:
        # A prefix is a path segment, not a regex — anchor it so `carto` cannot
        # match `/dev/carto/…` and so a stray `.` can't widen the ban.
        pattern = "^/" + _escape(body.prefix) + "/"

    expression = f"{_BAN_FIELD} ~ {pattern}"
    await _ban(expression)
    return FlushResult(banned=expression, flushed=True)


@router.post("/refresh/carto")
async def refresh_carto_cache(
    body: dict,
    user_token: TokenData = Depends(require_admin),
) -> dict:
    """Expire a region or a set of source maps from both cache layers. Admin only.

    Forwarded verbatim to the tileserver, which owns the L2 expiry logic (it has
    the tile-geometry SQL and the connection pool for it). The body shape is the
    tileserver's ``InvalidationRequest``.
    """
    url = _require_setting(environ.get("TILESERVER_URL"), "TILESERVER_URL")
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                url.rstrip("/") + "/cache/refresh/carto", json=body, timeout=60.0
            )
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502, detail=f"Could not reach the tileserver: {exc}"
        )
    if resp.status_code >= 400:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    return resp.json()


async def _ban(expression: str) -> None:
    """Send a Varnish BAN, or raise the reason it couldn't be sent."""
    url = _require_setting(environ.get("VARNISH_URL"), "VARNISH_URL")
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.request(
                "BAN",
                url.rstrip("/") + "/",
                headers={"X-Ban-Expression": expression},
                timeout=10.0,
            )
            resp.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Varnish BAN failed: {exc}")


def _require_setting(value: Optional[str], name: str) -> str:
    """Fail loudly on an unconfigured upstream.

    The previous implementation of this (in the tileserver) logged a warning and
    returned success, so a flush that never happened looked like one that had.
    """
    if not value:
        raise HTTPException(
            status_code=503,
            detail=f"{name} is not configured, so the cache cannot be flushed",
        )
    return value


def _escape(segment: str) -> str:
    """Quote regex metacharacters in a caller-supplied path segment."""
    return "".join("\\" + c if c in ".^$*+?()[]{}|\\/" else c for c in segment)
