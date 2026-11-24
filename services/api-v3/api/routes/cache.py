"""Admin-only tile-cache management.

Macrostrat's tiles are cached in two layers: L1 is Varnish, sitting in front of
the tileserver, and L2 is the ``tile_cache.tile`` table the tileserver renders
into. Expiring either one is a destructive, cheap-to-request operation, which
makes it a denial-of-service vector if left open — so every route here is gated
on ``require_admin``.

The web app is served from the same origin as ``/api/v3``, so its auth cookie
travels with the request. The tile host serves only ``/cache/footprints`` of
these (the gateway's ``tiles.caddy``).
"""

from os import environ
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from api.routes.security import TokenData, require_admin
from api.tiles.cache_management import (
    TILE_URL_PREFIX,
    InvalidationRequest,
    invalidate_carto,
)
from api.tiles.cache_management import router as footprints_router

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

# Every tile, and no API response, in the gateway's combined cache. The separate
# tile cache sets no profile, so there it matches everything, as before.
_MATCH_TILES = "obj.http.X-Cache-Profile != api"


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
    """Drop every tile from the Varnish cache. Admin only.

    This does not touch L2, so tiles come back without being re-rendered from
    the database — it is the cheap "the cache is serving something stale" fix,
    not a rebuild. Expiring L2 as well is what ``/cache/refresh/carto`` does.
    """
    expression = _MATCH_TILES
    if body is not None and body.prefix:
        # A prefix is a path segment, not a regex — anchor it so `carto` cannot
        # match `/dev/carto/…` and so a stray `.` can't widen the ban.
        pattern = TILE_URL_PREFIX + _escape(body.prefix) + "/"
        expression = f"{_BAN_FIELD} ~ {pattern}"

    await _ban(expression)
    return FlushResult(banned=expression, flushed=True)


@router.post("/refresh/carto")
async def refresh_carto_cache(
    body: InvalidationRequest,
    request: Request,
    user_token: TokenData = Depends(require_admin),
) -> dict:
    """Expire a region or a set of source maps from both cache layers. Admin only."""
    return await invalidate_carto(request.app.state.pool, body)


# The footprints tile layer the cache page draws; open, like other tiles.
router.include_router(footprints_router)


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
