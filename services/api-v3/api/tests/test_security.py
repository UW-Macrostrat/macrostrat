"""Session role handling in `api.routes.security`.

These run without a database: the user lookup is stubbed, and the routes under
test only read the stored user's role and re-mint the cookie. The RLS chain
that consumes the resulting `role` claim is covered by
`test_postgrest_caddy_rls.py` against a running stack.
"""

import os
from types import SimpleNamespace

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from jose import jwt

os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("JWT_ENCRYPTION_ALGORITHM", "HS256")
os.environ.setdefault("REDIRECT_URI", "http://localhost:8000/security/callback")

from api.database import get_database  # noqa: E402
from api.routes import security  # noqa: E402

SECRET = os.environ["SECRET_KEY"]
ALGORITHM = os.environ["JWT_ENCRYPTION_ALGORITHM"]


def fake_user(role: str = "admin", sub: str = "0000-0000-0000-0001"):
    """Enough of `schemas.User` for `role_claim` and `session_claims`."""
    postgres_role = {
        "admin": "web_admin",
        "authorized": "web_authorized",
        "user": "web_user",
    }[role]
    return SimpleNamespace(
        id=46,
        sub=sub,
        name="Test Person",
        display_name="Test",
        email="test@example.com",
        role=role,
        role_definition=SimpleNamespace(id=role, postgres_role=postgres_role),
        created_on="2026-01-01T00:00:00+00:00",
        updated_on="2026-01-01T00:00:00+00:00",
    )


# --------------------------------------------------------------------------- #
# Pure role logic
# --------------------------------------------------------------------------- #


def test_role_claim_falls_back_for_unknown_mapping():
    user = fake_user("admin")
    user.role_definition.postgres_role = "something_else"
    assert security.role_claim(user) == security.DEFAULT_POSTGREST_ROLE
    assert security.role_claim(None) == security.DEFAULT_POSTGREST_ROLE


def test_resolve_assumed_role_restores_and_degrades():
    assert security.resolve_assumed_role("web_admin", None) == "web_admin"
    assert security.resolve_assumed_role("web_admin", "web_admin") == "web_admin"
    assert security.resolve_assumed_role("web_admin", "web_user") == "web_user"
    assert (
        security.resolve_assumed_role("web_admin", "web_authorized") == "web_authorized"
    )
    assert security.resolve_assumed_role("web_authorized", "web_user") == "web_user"
    assert security.resolve_assumed_role("web_user", None) == "web_user"


@pytest.mark.parametrize(
    "actual,requested",
    [
        ("web_user", "web_admin"),
        ("web_user", "web_authorized"),
        ("web_authorized", "web_admin"),
    ],
)
def test_resolve_assumed_role_never_climbs(actual, requested):
    with pytest.raises(HTTPException) as info:
        security.resolve_assumed_role(actual, requested)
    assert info.value.status_code == 403


def test_audit_actor_matches_the_trigger_fallback():
    token = security.TokenData(sub="0000-0001-2345-6789", role="web_admin")
    assert security.audit_actor(token) == "orcid:0000-0001-2345-6789"


# --------------------------------------------------------------------------- #
# Cookie scoping, shared by every route that issues or clears a session
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "redirect_uri,domain,samesite,secure",
    [
        # Production: the API's own host, first-party.
        (
            "https://macrostrat.org/api/v3/security/callback",
            "macrostrat.org",
            "lax",
            True,
        ),
        # Local stack: scoped to the parent .local domain and sent cross-site
        # (from https://macrostrat.local or http://localhost:3000).
        (
            "https://api.macrostrat.local/security/callback",
            "macrostrat.local",
            "none",
            True,
        ),
        # The same over plain http: SameSite=None needs Secure, so Lax.
        (
            "http://api.macrostrat.local/security/callback",
            "macrostrat.local",
            "lax",
            False,
        ),
        # Bare localhost: a host-only cookie.
        ("http://localhost:8000/security/callback", None, "lax", False),
    ],
)
def test_auth_cookie_params(monkeypatch, redirect_uri, domain, samesite, secure):
    monkeypatch.setenv("REDIRECT_URI", redirect_uri)
    params = security.auth_cookie_params()
    assert params.domain == domain
    assert params.samesite == samesite
    assert params.secure is secure


def test_redirect_uri_falls_back_to_old_name(monkeypatch):
    monkeypatch.delenv("REDIRECT_URI", raising=False)
    monkeypatch.setenv("REDIRECT_URI_ENV", "https://old.example/security/callback")
    assert security.redirect_uri() == "https://old.example/security/callback"


def test_resolve_assumed_role_rejects_unknown_roles():
    with pytest.raises(HTTPException) as info:
        security.resolve_assumed_role("web_admin", "superuser")
    assert info.value.status_code == 422


def test_session_claims_mark_only_degraded_sessions():
    user = fake_user("admin")
    plain = security.session_claims(user)
    assert plain["role"] == "web_admin"
    assert "actual_role" not in plain

    degraded = security.session_claims(user, role="web_user")
    assert degraded["role"] == "web_user"
    assert degraded["actual_role"] == "web_admin"
    assert degraded["name"] == "Test"


def test_token_data_degraded_property():
    assert not security.TokenData(sub="x", role="web_admin").degraded
    assert security.TokenData(
        sub="x", role="web_user", actual_role="web_admin"
    ).degraded


# --------------------------------------------------------------------------- #
# The routes, with the user lookup stubbed
# --------------------------------------------------------------------------- #


@pytest.fixture
def client(monkeypatch):
    """A client for the security router alone, with a stubbed user store.

    `users` maps ORCID iD -> fake user; a test fills it in. The database
    dependency is a placeholder: the routes exercised here reach the database
    only through `get_user`, which is patched to read the dict instead.
    """
    users = {}

    async def get_user(sub, async_session):
        return users.get(sub)

    monkeypatch.setattr(security, "get_user", get_user)

    app = FastAPI()
    app.include_router(security.router)
    app.dependency_overrides[get_database] = lambda: SimpleNamespace(
        async_sessionmaker=None, async_engine=None
    )
    with TestClient(app) as c:
        c.users = users
        yield c


def cookie_for(claims: dict) -> dict:
    """Request headers carrying a session cookie minted from `claims`."""
    token = jwt.encode(claims, SECRET, algorithm=ALGORITHM)
    return {"Cookie": f"access_token=Bearer {token}"}


def issued_cookie(response) -> dict:
    """The access cookie a response set, as headers for the next request.

    Read off the response rather than through the client's jar, which would
    hold the seeded cookie and the issued one under different domains and
    refuse to pick between them. Starlette quotes a value containing a space;
    the browser (and the web server's cookie parser) strip the quotes again.
    """
    raw = response.cookies.get("access_token")
    assert raw is not None, "no access cookie issued"
    return {"Cookie": f"access_token={raw.strip(chr(34))}"}


def decode_cookie(headers: dict) -> dict:
    value = headers["Cookie"].split("=", 1)[1]
    assert value.startswith("Bearer ")
    return jwt.decode(value[len("Bearer ") :], SECRET, algorithms=[ALGORITHM])


def test_assume_role_requires_a_session(client):
    res = client.post("/security/role", json={"role": "web_user"})
    assert res.status_code == 401


def test_admin_can_degrade_and_restore(client):
    user = fake_user("admin")
    client.users[user.sub] = user
    cookies = cookie_for(security.session_claims(user))

    res = client.post("/security/role", json={"role": "web_user"}, headers=cookies)
    assert res.status_code == 200, res.text
    assert res.json() == {
        "role": "web_user",
        "actual_role": "web_admin",
        "degraded": True,
    }
    degraded = issued_cookie(res)
    claims = decode_cookie(degraded)
    assert claims["role"] == "web_user"
    assert claims["actual_role"] == "web_admin"

    # With the degraded cookie, /me reports the state, and the admin-only
    # routes refuse the session like any other user's.
    me = client.get("/security/me", headers=degraded)
    assert me.status_code == 200, me.text
    body = me.json()
    assert body["role"] == "web_user"
    assert body["actual_role"] == "web_admin"
    assert body["app_role"] == "admin"
    assert body["degraded"] is True

    # The route reads the user table, which is stubbed away; the point is that
    # it is refused before it gets there.
    assert client.get("/security/users", headers=degraded).status_code == 403

    # A degraded session can restore itself: entitlement is read from the
    # stored record, not from the cookie being replaced.
    res = client.post("/security/role", json={"role": None}, headers=degraded)
    assert res.status_code == 200, res.text
    assert res.json()["degraded"] is False
    claims = decode_cookie(issued_cookie(res))
    assert claims["role"] == "web_admin"
    assert "actual_role" not in claims


def test_role_switch_issues_cookie_with_login_scoping(client, monkeypatch):
    """The re-issued cookie must land where the login callback put the original,
    or the browser ends up holding two and sends whichever it likes."""
    monkeypatch.setenv("REDIRECT_URI", "https://api.macrostrat.local/security/callback")
    user = fake_user("admin")
    client.users[user.sub] = user
    cookies = cookie_for(security.session_claims(user))

    res = client.post("/security/role", json={"role": "web_user"}, headers=cookies)
    assert res.status_code == 200, res.text
    set_cookie = res.headers["set-cookie"].lower()
    assert "domain=macrostrat.local" in set_cookie
    assert "samesite=none" in set_cookie
    assert "secure" in set_cookie
    assert "httponly" in set_cookie


def test_authorized_user_can_degrade_to_user_but_not_climb(client):
    user = fake_user("authorized")
    client.users[user.sub] = user
    cookies = cookie_for(security.session_claims(user))

    res = client.post("/security/role", json={"role": "web_user"}, headers=cookies)
    assert res.status_code == 200, res.text
    assert res.json() == {
        "role": "web_user",
        "actual_role": "web_authorized",
        "degraded": True,
    }

    res = client.post("/security/role", json={"role": "web_admin"}, headers=cookies)
    assert res.status_code == 403


def test_user_cannot_claim_admin(client):
    user = fake_user("user")
    client.users[user.sub] = user
    cookies = cookie_for(security.session_claims(user))

    res = client.post("/security/role", json={"role": "web_admin"}, headers=cookies)
    assert res.status_code == 403
    # Nothing was issued: the session stays as it was.
    assert res.cookies.get("access_token") is None


def test_me_on_a_plain_session(client):
    user = fake_user("user")
    client.users[user.sub] = user
    cookies = cookie_for(security.session_claims(user))

    body = client.get("/security/me", headers=cookies).json()
    assert body["sub"] == user.sub
    assert body["email"] == "test@example.com"
    assert body["role"] == "web_user"
    assert body["actual_role"] == "web_user"
    assert body["app_role"] == "user"
    assert body["degraded"] is False


def test_me_without_a_session(client):
    assert client.get("/security/me").status_code == 401
