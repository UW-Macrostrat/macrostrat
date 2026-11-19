"""Session role handling in `api.routes.security`.

These run without a database: the user lookup is stubbed, and the routes under
test only read the stored user's role and re-mint the cookie. The RLS chain
that consumes the resulting `role` claim is covered by
`test_postgrest_caddy_rls.py` against a running stack.
"""

import os
from types import SimpleNamespace
from urllib.parse import parse_qs, urlparse

import httpx2
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
        # Deployed: host-only, so production's session never reaches dev.
        (
            "https://macrostrat.org/api/v3/security/callback",
            None,
            "lax",
            True,
        ),
        (
            "https://dev.macrostrat.org/api/v3/security/callback",
            None,
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


def test_logout_clears_domain_cookies(monkeypatch):
    # Sessions issued before cookies went host-only carry Domain=macrostrat.org.
    from starlette.responses import Response

    monkeypatch.setenv(
        "REDIRECT_URI", "https://macrostrat.org/api/v3/security/callback"
    )
    response = Response()
    security.clear_auth_cookies(response)
    cleared = response.headers.getlist("set-cookie")
    for key in (security.access_token_key, security.refresh_token_key):
        assert any(
            c.startswith(f"{key}=") and "Domain=macrostrat.org" in c for c in cleared
        )
        assert any(c.startswith(f"{key}=") and "Domain=" not in c for c in cleared)


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


# --------------------------------------------------------------------------- #
# Sign-in, with ORCID stubbed
# --------------------------------------------------------------------------- #


def orcid(request: httpx2.Request) -> httpx2.Response:
    if request.url.path.endswith("/token"):
        return httpx2.Response(200, json={"access_token": "provider-token"})
    return httpx2.Response(
        200,
        json={
            "sub": "0000-0002-1825-0097",
            "given_name": "Josiah",
            "family_name": "Carberry",
        },
    )


@pytest.fixture
def sign_in_client(monkeypatch):
    users = {}

    async def get_user(sub, async_session):
        return users.get(sub)

    async def create_user(sub, name, email, async_session):
        users[sub] = fake_user("user", sub=sub)
        return users[sub]

    monkeypatch.setattr(security, "get_user", get_user)
    monkeypatch.setattr(security, "create_user", create_user)
    settings = security.auth_settings().model_copy(
        update={"allowed_return_origins": ["https://dev.macrostrat.local"]}
    )
    routes = security.session_router(
        settings, security.Accounts(), transport=httpx2.MockTransport(orcid)
    )
    app = FastAPI()
    app.include_router(routes, prefix="/security")
    app.include_router(security.router)
    app.dependency_overrides[get_database] = lambda: SimpleNamespace(
        async_sessionmaker=None, async_engine=None
    )
    with TestClient(app, follow_redirects=False) as c:
        c.users = users
        yield c


def sign_in(client, return_url):
    res = client.get("/security/login", params={"return_url": return_url})
    assert res.status_code == 307
    state = parse_qs(urlparse(res.headers["location"]).query)["state"][0]
    return client.get("/security/callback", params={"code": "x", "state": state})


def test_sign_in_creates_a_user_session(sign_in_client):
    res = sign_in(sign_in_client, "https://dev.macrostrat.local/maps")
    assert res.headers["location"] == "https://dev.macrostrat.local/maps"
    claims = decode_cookie(issued_cookie(res))
    assert claims["sub"] == "0000-0002-1825-0097"
    assert claims["role"] == "web_user"
    assert "0000-0002-1825-0097" in sign_in_client.users

    me = sign_in_client.get("/security/me", headers=issued_cookie(res))
    assert me.json()["app_role"] == "user"


def test_sign_in_discards_a_foreign_return_url(sign_in_client):
    res = sign_in(sign_in_client, "https://evil.example.com/")
    assert res.headers["location"] == "/"


def test_refresh_token_is_not_a_session(sign_in_client):
    res = sign_in(sign_in_client, "/")
    refresh = res.cookies.get("refresh_token")
    headers = {"Cookie": f"access_token=Bearer {refresh}"}
    assert sign_in_client.get("/security/me", headers=headers).status_code == 401


def test_only_sign_in_routes_come_from_the_library():
    paths = [r.path for r in security.router.routes]
    for path in ("/security/login", "/security/callback", "/security/refresh"):
        assert paths.count(path) == 1
    assert paths.count("/security/me") == 1
    assert paths.count("/security/logout") == 1


# --------------------------------------------------------------------------- #
# User and token administration (database calls stubbed)
# --------------------------------------------------------------------------- #


@pytest.fixture
def admin_client(client, monkeypatch):
    """`client` signed in as an admin, with the admin database calls recorded."""
    admin = fake_user("admin")
    other = fake_user("user", sub="0000-0000-0000-0002")
    other.id = 47
    client.users[admin.sub] = admin
    by_id = {46: admin, 47: other}
    calls = []

    async def get_user_by_id(async_session, user_id):
        return by_id.get(user_id)

    async def list_roles(async_session):
        return [SimpleNamespace(id=r) for r in ("admin", "user", "test")]

    async def update_user(engine, user_id, values, actor=None):
        calls.append(("update", user_id, values))
        return True

    async def delete_user(engine, user_id, actor=None):
        calls.append(("delete", user_id))
        return client.delete_outcome

    async def set_token_scopes(engine, token_id, scopes, actor=None):
        calls.append(("scopes", token_id, scopes))
        return True

    for name, fn in [
        ("get_user_by_id", get_user_by_id),
        ("list_roles", list_roles),
        ("update_user", update_user),
        ("delete_user", delete_user),
        ("set_token_scopes", set_token_scopes),
    ]:
        monkeypatch.setattr(security.db, name, fn)

    client.calls = calls
    client.delete_outcome = "deleted"
    client.admin_cookies = cookie_for(security.session_claims(admin))
    return client


def test_admin_edits_own_name_with_unchanged_role(admin_client):
    res = admin_client.patch(
        "/security/users/46",
        json={"role": "admin", "display_name": " New ", "email": ""},
        headers=admin_client.admin_cookies,
    )
    assert res.status_code == 200, res.text
    assert admin_client.calls == [
        ("update", 46, {"role": "admin", "display_name": "New", "email": None})
    ]


def test_admin_cannot_change_own_role(admin_client):
    res = admin_client.patch(
        "/security/users/46", json={"role": "user"}, headers=admin_client.admin_cookies
    )
    assert res.status_code == 403
    assert admin_client.calls == []


def test_unknown_role_is_refused(admin_client):
    res = admin_client.patch(
        "/security/users/47", json={"role": "owner"}, headers=admin_client.admin_cookies
    )
    assert res.status_code == 422


def test_admin_cannot_delete_self(admin_client):
    res = admin_client.delete("/security/users/46", headers=admin_client.admin_cookies)
    assert res.status_code == 403
    assert admin_client.calls == []


@pytest.mark.parametrize("outcome,status", [("deleted", 200), ("referenced", 409)])
def test_delete_user(admin_client, outcome, status):
    admin_client.delete_outcome = outcome
    res = admin_client.delete("/security/users/47", headers=admin_client.admin_cookies)
    assert res.status_code == status
    assert admin_client.calls == [("delete", 47)]


def test_token_scopes_are_validated(admin_client):
    res = admin_client.patch(
        "/security/tokens/3",
        json={"scopes": ["Not A Scope"]},
        headers=admin_client.admin_cookies,
    )
    assert res.status_code == 422
    res = admin_client.patch(
        "/security/tokens/3", json={"scopes": []}, headers=admin_client.admin_cookies
    )
    assert res.status_code == 200
    assert admin_client.calls == [("scopes", 3, None)]
