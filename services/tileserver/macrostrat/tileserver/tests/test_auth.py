"""The delegated-token guard on guarded layers.

Deliberately database-free: a fake pool stands in for asyncpg so the decision
table (no header / unknown token / wrong scope / right scope) can be exercised
without a container. What needs a real database is the SQL itself, which is
covered by the route tests.
"""

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from macrostrat.tileserver.auth import (
    NEGATIVE_TTL,
    POSITIVE_TTL,
    clear_token_cache,
    hash_token,
    require_scope,
)

SCOPE = "rasters:emit-minerals"
TOKEN = "aVeryRealLookingDelegatedToken00"


class FakePool:
    """Minimal stand-in for the asyncpg pool.

    `rows` maps a token digest to the value of the `scopes` column. A digest
    that is absent behaves like a token that is unknown or expired, since the
    query filters on `expires_on > now()`.
    """

    def __init__(self, rows: dict):
        self.rows = rows
        self.queries = 0

    def acquire(self):
        return self

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def fetchrow(self, query, *params):
        self.queries += 1
        digest = params[0]
        if digest not in self.rows:
            return None
        return {"scopes": self.rows[digest]}


def build_app(pool) -> FastAPI:
    app = FastAPI()
    app.state.pool = pool

    @app.get("/guarded", dependencies=[Depends(require_scope(SCOPE))])
    def guarded():
        return {"ok": True}

    return app


@pytest.fixture(autouse=True)
def _fresh_cache():
    """The cache is module-level, so tests would otherwise leak into each other."""
    clear_token_cache()
    yield
    clear_token_cache()


def client_for(rows) -> tuple[TestClient, FakePool]:
    pool = FakePool(rows)
    return TestClient(build_app(pool)), pool


def get(client, token=None):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    return client.get("/guarded", headers=headers)


class TestDecisions:
    def test_no_header_is_401(self):
        client, pool = client_for({})
        response = get(client)
        assert response.status_code == 401
        assert SCOPE in response.json()["detail"]
        # Nothing to look up, so the database is never touched.
        assert pool.queries == 0

    def test_unknown_token_is_401(self):
        client, _ = client_for({})
        response = get(client, TOKEN)
        assert response.status_code == 401
        assert response.json()["detail"] == "Token is unknown or expired"

    def test_a_401_advertises_bearer(self):
        """So a client can tell auth apart from a generic failure."""
        client, _ = client_for({})
        assert "WWW-Authenticate" in get(client).headers
        assert "Bearer" in get(client, TOKEN).headers["WWW-Authenticate"]

    def test_wrong_scope_is_403(self):
        """The token is real, so this is authorization, not authentication."""
        client, _ = client_for({hash_token(TOKEN): ["rasters:something-else"]})
        response = get(client, TOKEN)
        assert response.status_code == 403
        assert SCOPE in response.json()["detail"]

    def test_no_scopes_is_403(self):
        """A token minted without --scope grants nothing, but it does exist."""
        client, _ = client_for({hash_token(TOKEN): None})
        assert get(client, TOKEN).status_code == 403

    def test_right_scope_passes(self):
        client, _ = client_for({hash_token(TOKEN): [SCOPE]})
        response = get(client, TOKEN)
        assert response.status_code == 200
        assert response.json() == {"ok": True}

    def test_extra_scopes_are_fine(self):
        client, _ = client_for({hash_token(TOKEN): ["rasters:other", SCOPE]})
        assert get(client, TOKEN).status_code == 200


class TestStorage:
    def test_only_the_digest_is_looked_up(self):
        """The raw token must never be what we compare against the database."""
        client, pool = client_for({hash_token(TOKEN): [SCOPE]})
        get(client, TOKEN)
        assert TOKEN not in pool.rows
        assert hash_token(TOKEN) in pool.rows

    def test_digest_is_sha256_hex(self):
        import hashlib

        assert hash_token(TOKEN) == hashlib.sha256(TOKEN.encode()).hexdigest()
        assert len(hash_token(TOKEN)) == 64


class TestCache:
    def test_repeated_requests_hit_the_database_once(self):
        """Otherwise every tile in a map view is a query."""
        client, pool = client_for({hash_token(TOKEN): [SCOPE]})
        for _ in range(5):
            assert get(client, TOKEN).status_code == 200
        assert pool.queries == 1

    def test_failures_are_cached_too(self):
        """A brute-force attempt shouldn't be free database load."""
        client, pool = client_for({})
        for _ in range(5):
            assert get(client, TOKEN).status_code == 401
        assert pool.queries == 1

    def test_failures_expire_sooner_than_successes(self):
        """So a token minted after a failed guess isn't stranded for a minute."""
        assert NEGATIVE_TTL < POSITIVE_TTL
