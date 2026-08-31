"""Delegated-token auth for guarded layers.

A delegated token is an opaque credential minted by `macrostrat auth
create-token` (or `POST /api/v3/security/tokens`) and handed to a third party.
Only its sha256 digest is stored, so this module digests whatever arrives and
looks that up.

Plain sha256, unkeyed, deliberately. The tile server holds a database
connection but no `SECRET_KEY`, and at ~190 bits of token entropy there is no
dictionary attack for a salt or pepper to defend against. The digest has to
match `hash_token` in `services/api-v3/api/routes/security.py` and
`py-modules/cli/macrostrat/cli/auth.py` — all three verify the same tokens.

Credentials are read from `Authorization: Bearer <token>` only, never a query
parameter: a tile URL ends up in access logs, browser history and `Referer`
headers, and a credential in any of those is a credential to rotate.
"""

import hashlib
from time import monotonic
from typing import Optional

from buildpg import render
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from macrostrat.utils import get_logger

log = get_logger(__name__)

__all__ = ["require_scope", "hash_token", "clear_token_cache"]

# Tile traffic would otherwise put a query on every single request. The cost of
# caching is revocation latency: a revoked token keeps working until its entry
# expires. Negative results are held only briefly — long enough to blunt a
# brute-force attempt, short enough that a freshly minted token isn't stranded
# by an earlier failed guess.
POSITIVE_TTL = 60
NEGATIVE_TTL = 5

# token digest -> (expiry on the monotonic clock, scopes or None if unknown)
_cache: dict[str, tuple[float, Optional[list[str]]]] = {}

_bearer = HTTPBearer(auto_error=False)

# ── Contract shared with the minting side ────────────────────────────────────
# Compared as an exact string against what `macrostrat/cli/auth.py` and
# `services/api-v3/api/routes/security.py` write. A mismatch raises nowhere —
# the token simply never matches, so it looks valid and grants nothing.
DELEGATED_TOKEN_TYPE = "delegated"

# Scopes are `<namespace>:<resource>`; `require_scope` is called with
# `f"rasters:{config.slug}"` and membership is an exact string match.
_LOOKUP = """
SELECT scopes
FROM macrostrat_auth.token
WHERE token = :token_hash
  AND token_type = :token_type
  AND expires_on > now()
"""


def hash_token(raw_token: str) -> str:
    """The digest stored in `macrostrat_auth.token.token`."""
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def clear_token_cache() -> None:
    """Drop every cached lookup. For tests, and for a manual revocation."""
    _cache.clear()


async def _scopes_for(pool, token_hash: str) -> Optional[list[str]]:
    """A live token's scopes, or None if it is unknown or expired.

    An empty list is meaningfully different from None: the token exists but
    grants nothing, which is a 403 rather than a 401.

    Expiry is evaluated by the database (`expires_on > now()`) so there is no
    clock skew between this process and the stored timestamp.
    """
    cached = _cache.get(token_hash)
    if cached is not None and cached[0] > monotonic():
        return cached[1]

    q, p = render(_LOOKUP, token_hash=token_hash, token_type=DELEGATED_TOKEN_TYPE)
    async with pool.acquire() as conn:
        row = await conn.fetchrow(q, *p)

    scopes = list(row["scopes"] or []) if row is not None else None
    ttl = NEGATIVE_TTL if scopes is None else POSITIVE_TTL
    _cache[token_hash] = (monotonic() + ttl, scopes)
    return scopes


def require_scope(scope: str):
    """Build a dependency requiring a delegated token that carries `scope`.

    Applied to a whole router rather than to individual routes, so every route
    a layer exposes is covered — the rendered tiles, but also `/point`, which
    returns the underlying values, and `/footprints`, which reveals where the
    datasets are. Gating only the tiles would protect the picture and not the
    data.
    """

    async def check(
        request: Request,
        credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    ) -> None:
        if credentials is None:
            raise HTTPException(
                status_code=401,
                detail=f"{scope} requires a delegated token",
                headers={"WWW-Authenticate": "Bearer"},
            )

        scopes = await _scopes_for(
            request.app.state.pool, hash_token(credentials.credentials)
        )

        if scopes is None:
            raise HTTPException(
                status_code=401,
                detail="Token is unknown or expired",
                headers={"WWW-Authenticate": 'Bearer error="invalid_token"'},
            )

        if scope not in scopes:
            raise HTTPException(
                status_code=403, detail=f"Token is not scoped for {scope}"
            )

    return check
