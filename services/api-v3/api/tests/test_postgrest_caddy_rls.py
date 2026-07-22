"""
This suite only runs locally for now
Run
---
    uv run pytest -q --confcutdir=api/tests api/tests/test_postgrest_caddy_rls.py
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
import pytest
from dotenv import load_dotenv
from jose import jwt
from sqlalchemy import create_engine, text


_REPO_ROOT = Path(__file__).resolve().parents[4]

load_dotenv(_REPO_ROOT / "services" / "api-v3" / ".env", override=False)
load_dotenv(_REPO_ROOT / "local-root" / ".env", override=False)

SECRET_KEY = os.environ.get("SECRET_KEY")
ALGORITHM = os.environ.get("JWT_ENCRYPTION_ALGORITHM", "HS256")
GATEWAY_URL = os.environ.get("MACROSTRAT_GATEWAY_URL", "https://macrostrat.local").rstrip(
    "/"
)
PG_BASE = f"{GATEWAY_URL}/api/pg"

# fake orcid sub for tests
TEST_SUB = "0000-0000-0000-0001"

# Skip the whole module unless we can actually reach the gateway *and* we have a
# secret to sign tokens with
pytestmark = pytest.mark.skipif(
    not SECRET_KEY,
    reason="SECRET_KEY not set (needed to mint JWTs matching PostgREST's PGRST_JWT_SECRET)",
)


def _mint(
    *,
    role: str | None = None,
    user_id: int | None = None,
    sub: str = TEST_SUB,
    name: str = "Test",
    expires_delta: timedelta = timedelta(minutes=5),
    secret: str | None = None,
) -> str:
    """Mint a JWT the same way api-v3 does (``create_access_token``).

    ``role``/``user_id`` are included only when provided so we can test the
    presence/absence of individual claims. ``secret`` defaults to the shared
    ``SECRET_KEY``; pass a different value to forge an invalid-signature token.
    """
    claims: dict = {"sub": sub, "name": name}
    if role is not None:
        claims["role"] = role
    if user_id is not None:
        # current_app_user_id() reads this claim as text then casts to int.
        claims["user_id"] = user_id
    claims["exp"] = datetime.now(timezone.utc) + expires_delta
    return jwt.encode(claims, secret or SECRET_KEY, algorithm=ALGORITHM)


def _cookie_header(token: str) -> dict:
    """Build the raw ``Cookie`` header exactly as the browser sends it.

    The app stores the cookie value as ``"Bearer <jwt>"`` and Caddy copies that
    value verbatim into the ``Authorization`` header. We set the header by hand
    (rather than via the client cookie jar) so the ``Bearer `` prefix and space
    are passed through unquoted, matching Caddy's ``@auth_cookie`` matcher and
    ``{http.request.cookie.access_token}`` placeholder.
    """
    return {"Cookie": f"access_token=Bearer {token}"}


@pytest.fixture(scope="module")
def client():
    # Caddy serves local hosts with an internal (self-signed) CA, so TLS
    # verification is disabled for these local-dev integration tests.
    with httpx.Client(base_url=PG_BASE, verify=False, timeout=10.0) as c:
        # Reachability probe — skip the whole module if the stack isn't up.
        try:
            c.get("/rpc/auth_status")
        except httpx.HTTPError as exc:
            pytest.skip(f"Gateway not reachable at {PG_BASE}: {exc}")
        yield c


def _auth_status(client, token: str | None):
    headers = _cookie_header(token) if token is not None else {}
    return client.get("/rpc/auth_status", headers=headers)


# --------------------------------------------------------------------------- #
# The cookie → header → SET ROLE chain (via macrostrat_api.auth_status)
# --------------------------------------------------------------------------- #

def test_no_cookie_falls_back_to_web_anon(client):
    """No cookie ⇒ Caddy injects no Authorization ⇒ PostgREST uses web_anon."""
    resp = _auth_status(client, None)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["role"] == "web_anon"
    # No JWT ⇒ no authenticated subject. PostgREST may report the anon claims as
    # null / absent / ``{"role": "web_anon"}`` depending on version, so assert
    # the security-relevant invariant: there is no user identity (no ``sub``).
    token = body.get("token") or {}
    assert "sub" not in token


def test_valid_web_user_cookie_sets_role(client):
    """A valid web_user JWT cookie flows through Caddy and PostgREST SET ROLEs."""
    token = _mint(role="web_user")
    resp = _auth_status(client, token)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["role"] == "web_user"
    # The claims PostgREST decoded from the cookie-derived Authorization header.
    assert body["token"] is not None
    assert body["token"]["role"] == "web_user"
    assert body["token"]["sub"] == TEST_SUB


def test_valid_web_admin_cookie_sets_role(client):
    """A valid web_admin JWT cookie SET ROLEs to web_admin."""
    token = _mint(role="web_admin")
    resp = _auth_status(client, token)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["role"] == "web_admin"
    assert body["token"]["role"] == "web_admin"


def test_invalid_signature_cookie_is_rejected(client):
    """A JWT signed with the wrong secret must be rejected by PostgREST (401)."""
    token = _mint(role="web_admin", secret=(SECRET_KEY or "") + "-tampered")
    resp = _auth_status(client, token)
    assert resp.status_code == 401, resp.text
    # PostgREST reports a JWSError for a bad signature; assert leniently.
    assert "jw" in resp.text.lower()


def test_expired_cookie_is_rejected(client):
    """An expired JWT must be rejected by PostgREST (401), not honored."""
    token = _mint(role="web_admin", expires_delta=timedelta(hours=-1))
    resp = _auth_status(client, token)
    assert resp.status_code == 401, resp.text
    assert "expired" in resp.text.lower()


# --------------------------------------------------------------------------- #
# Row-Level Security on user_features.user_locations (read-only)
# --------------------------------------------------------------------------- #

def _get_locations(client, token: str):
    return client.get("/user_locations_view", headers=_cookie_header(token))


def _db_url() -> str | None:
    """Mirror api.database.get_db_url() without importing the app package."""
    for key in ("MACROSTRAT_DATABASE_URL", "uri", "DB_URL"):
        value = os.environ.get(key)
        if value:
            return value
    return None


@pytest.fixture(scope="module")
def db_engine():
    """Read-only SQLAlchemy engine used *only* to discover a real sub→id owner.

    Connects with the URL's (privileged) role, which bypasses RLS — that's fine,
    we only read. Skips if there's no URL or the DB isn't reachable.
    """
    url = _db_url()
    if not url:
        pytest.skip("No database URL (MACROSTRAT_DATABASE_URL) for RLS discovery")
    engine = create_engine(url)
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001 - any connect failure ⇒ skip
        engine.dispose()
        pytest.skip(f"Database not reachable for RLS discovery: {exc}")
    yield engine
    engine.dispose()


@pytest.fixture(scope="module")
def owner_with_locations(db_engine):
    """A real ``(sub, user_id, n)`` triple: the user who owns the most rows.

    This is the sub→id mapping the RLS scoping now depends on but which PostgREST
    does not expose, hence the direct read.
    """
    sql = text(
        """
        SELECT u.sub AS sub, ul.user_id AS user_id, count(*) AS n
        FROM user_features.user_locations ul
        JOIN macrostrat_auth."user" u ON u.id = ul.user_id
        GROUP BY u.sub, ul.user_id
        ORDER BY n DESC
        LIMIT 1
        """
    )
    with db_engine.connect() as conn:
        row = conn.execute(sql).mappings().first()
    if row is None:
        pytest.skip("No user_locations rows joined to a user to exercise RLS")
    return {"sub": row["sub"], "user_id": row["user_id"], "n": row["n"]}


def test_admin_sees_all_user_locations(client):
    """web_admin RLS branch: sees every row (or an empty table)."""
    resp = _get_locations(client, _mint(role="web_admin"))
    assert resp.status_code == 200, resp.text
    assert isinstance(resp.json(), list)


def test_web_user_rls_scopes_rows_to_owner_by_sub(client, owner_with_locations):
    """web_user RLS branch: only the rows owned by the JWT ``sub``'s user.

    ``current_app_user_id()`` resolves ``sub`` → integer id, and the
    ``pl_ul_select`` policy returns exactly that user's rows.
    """
    token = _mint(role="web_user", sub=owner_with_locations["sub"])
    resp = _get_locations(client, token)
    assert resp.status_code == 200, resp.text
    rows = resp.json()
    # Exactly this user's rows — no more, no fewer.
    assert rows, "web_user should see its own rows"
    assert all(r["user_id"] == owner_with_locations["user_id"] for r in rows)
    assert len(rows) == owner_with_locations["n"]


def test_web_user_scoping_ignores_user_id_claim(client, owner_with_locations):
    """Scoping is by ``sub`` — a stale/forged ``user_id`` claim must not matter.

    Locks in the new contract: even with a bogus ``user_id`` claim, the rows
    returned are still those of the ``sub``'s user, never the forged id's.
    """
    token = _mint(
        role="web_user", sub=owner_with_locations["sub"], user_id=999_999_999
    )
    resp = _get_locations(client, token)
    assert resp.status_code == 200, resp.text
    rows = resp.json()
    assert all(r["user_id"] == owner_with_locations["user_id"] for r in rows)
    assert len(rows) == owner_with_locations["n"]


def test_web_user_unknown_sub_sees_nothing(client):
    """Fail-safe: a ``sub`` that maps to no user resolves to NULL ⇒ no rows.

    This is the flipped former regression guard: pre-fix a plain ``web_user`` saw
    nothing because ``current_app_user_id()`` read a missing ``user_id`` claim;
    post-fix it sees nothing only when the ``sub`` genuinely matches no user.
    See ``ReadMe/jwt-auth-postgrest.md``.
    """
    token = _mint(role="web_user", sub="0000-0000-0000-0000")
    resp = _get_locations(client, token)
    assert resp.status_code == 200, resp.text
    assert resp.json() == []
