import hashlib
import os
import re
import urllib.parse
from datetime import datetime, timedelta, timezone
from typing import Annotated, Optional

import aiohttp
import dotenv
from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
    OAuth2AuthorizationCodeBearer,
)
from fastapi.security.utils import get_authorization_scheme_param
from jose import JWTError, jwt
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from starlette.status import HTTP_401_UNAUTHORIZED

from macrostrat.utils import get_logger

dotenv.load_dotenv()

import api.database as db
import api.schemas as schemas
from api.database import DatabaseDep

ACCESS_TOKEN_EXPIRE_MINUTES = 1440  # can change to 1m for manual testing
DELEGATED_TOKEN_TYPE = "delegated"
SCOPE_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*:[a-z0-9]+(?:-[a-z0-9]+)*$")
SCOPE_EXAMPLE = "rasters:emit-minerals"
# Postgres roles PostgREST may be asked to assume. The mapping from an
# application role to one of these lives in `macrostrat_auth.role.postgres_role`;
# this set is the guard against a bad mapping turning into an unusable — or
# over-privileged — `role` claim.
DEFAULT_POSTGREST_ROLE = "web_user"
AUTHORIZED_POSTGREST_ROLE = "web_authorized"
ADMIN_POSTGREST_ROLE = "web_admin"
# The tiers nest (each inherits the one below it in Postgres), so a session may
# be *degraded* to any lower rank but never raised above the stored one.
POSTGREST_ROLE_RANK = {
    DEFAULT_POSTGREST_ROLE: 1,
    AUTHORIZED_POSTGREST_ROLE: 2,
    ADMIN_POSTGREST_ROLE: 3,
}
POSTGREST_ROLES = frozenset(POSTGREST_ROLE_RANK)

# Application roles (`macrostrat_auth.role.id`). `role` has no database default,
# so a new user is created in DEFAULT_ROLE explicitly. Anyone with an ORCID iD
# can sign in and become a `user`, so that tier confers nothing substantial;
# `authorized` users are designated by an admin and may view anything; only
# `admin` makes real edits.
DEFAULT_ROLE = "user"
AUTHORIZED_ROLE = "authorized"
ADMIN_ROLE = "admin"

REFRESH_TOKEN_EXPIRE_DAYS = 7
refresh_token_key = "refresh_token"

# TODO: Log to the proper channel
log = get_logger("uvicorn")


class TokenData(BaseModel):
    """The claims this service reads back out of an access JWT.

    `actual_role` is present only on a *degraded* session: an admin who asked
    (via `POST /security/role`) to browse with a lesser Postgres role. `role`
    is then what PostgREST and `has_access` see; `actual_role` is what the
    stored user record would grant, so the UI can offer to restore it.
    """

    sub: str
    role: str | None = None
    actual_role: str | None = None

    @property
    def degraded(self) -> bool:
        return self.actual_role is not None and self.actual_role != self.role


class AssumeRoleRequest(BaseModel):
    """Body of `POST /security/role`. A null `role` restores the stored one."""

    role: str | None = None


class SessionRole(BaseModel):
    """The role claims of the caller's (re-minted) session."""

    role: str
    actual_role: str
    degraded: bool


class UserInfo(BaseModel):
    """A user record, as the dashboard and the admin user table see it.

    `role` is the application role (`user`, `admin`); `postgres_role` the role a
    fresh session in it assumes. Never carries anything a user did not supply
    themselves plus the role, so it is safe to show an admin.
    """

    id: int
    sub: str
    name: str | None = None
    display_name: str | None = None
    email: str | None = None
    role: str
    postgres_role: str
    created_on: datetime
    updated_on: datetime

    @classmethod
    def from_user(cls, user: schemas.User) -> "UserInfo":
        return cls(
            id=user.id,
            sub=user.sub,
            name=user.name,
            display_name=user.display_name,
            email=user.email,
            role=user.role,
            postgres_role=role_claim(user),
            created_on=user.created_on,
            updated_on=user.updated_on,
        )


class CurrentUser(BaseModel):
    """`GET /security/me`: the stored record plus the session's role claims.

    `role` means the same thing here as the JWT claim the web app already
    reads — the Postgres role the *current cookie* carries, what PostgREST
    assumes and the web guards compare against — so a client can treat the
    server-rendered claims and this record interchangeably. `actual_role` is
    the Postgres role the stored record grants; the two differ only on a
    degraded session. `app_role` is the application role (`user`, `admin`).
    """

    id: int
    sub: str
    name: str | None = None
    display_name: str | None = None
    email: str | None = None
    role: str
    actual_role: str
    app_role: str
    degraded: bool
    created_on: datetime
    updated_on: datetime

    @classmethod
    def from_user(cls, user: schemas.User, session_role: str | None) -> "CurrentUser":
        actual = role_claim(user)
        role = session_role or actual
        return cls(
            id=user.id,
            sub=user.sub,
            name=user.name,
            display_name=user.display_name,
            email=user.email,
            role=role,
            actual_role=actual,
            app_role=user.role,
            degraded=role != actual,
            created_on=user.created_on,
            updated_on=user.updated_on,
        )


class SetUserRoleRequest(BaseModel):
    role: str


class AuthChange(BaseModel):
    """One row of the change-tracking trail for the account tables."""

    id: int
    changed_at: datetime
    actor_id: str | None = None
    table_name: str
    action: str
    record_pk: dict | None = None
    changed: dict | None = None


class RoleInfo(BaseModel):
    id: str
    postgres_role: str
    description: str | None = None


class DelegateTokenRequest(BaseModel):
    """Mint request for a delegated API token.

    `expiration` is a Unix timestamp. Supply `user_id` to delegate a Macrostrat
    user's authority, or `label` to issue to a third party with no account —
    at least one of the two is required (`token_has_subject` in the schema).
    """

    expiration: int
    label: str | None = None
    user_id: int | None = None
    scopes: list[str] | None = None


class DelegateToken(BaseModel):
    """A freshly minted token.

    `token` is the only time the raw value exists outside the caller's hands —
    the database stores only its sha256 digest, so a lost token is reissued,
    never recovered.
    """

    id: int
    token: str
    expires_on: datetime
    label: str | None = None
    user_id: int | None = None
    scopes: list[str] | None = None


class DelegateTokenInfo(BaseModel):
    """An issued token, as seen when administering it.

    Deliberately has no `token` field. The stored value is a digest and is not
    needed to administer a token, so it is never returned — a response that
    carries it invites pasting it somewhere it can leak.
    """

    id: int
    label: str | None = None
    token_type: str
    scopes: list[str] | None = None
    user_id: int | None = None
    # The delegated user's ORCID iD, so a listing can name who a token stands
    # for without a second lookup.
    user_sub: str | None = None
    created_by: int | None = None
    created_on: datetime
    expires_on: datetime
    used_on: datetime | None = None
    active: bool

    @classmethod
    def from_token(cls, token: schemas.Token, *, now: datetime) -> "DelegateTokenInfo":
        user = token.user
        return cls(
            id=token.id,
            label=token.label,
            token_type=token.token_type,
            scopes=token.scopes,
            user_id=token.user_id,
            user_sub=user.sub if user is not None else None,
            created_by=token.created_by,
            created_on=token.created_on,
            expires_on=token.expires_on,
            used_on=token.used_on,
            active=token.expires_on > now,
        )


access_token_key = "access_token"


class OAuth2AuthorizationCodeBearerWithCookie(OAuth2AuthorizationCodeBearer):
    """Tweak FastAPI's OAuth2AuthorizationCodeBearer to use a cookie instead of a header"""

    async def __call__(self, request: Request) -> Optional[str]:
        authorization = request.cookies.get(access_token_key)
        if authorization is None:
            # Use the header if the cookie isn't set
            authorization = request.headers.get(access_token_key)

        scheme, param = get_authorization_scheme_param(authorization)
        if not authorization or scheme.lower() != "bearer":
            if self.auto_error:
                raise HTTPException(
                    status_code=HTTP_401_UNAUTHORIZED,
                    detail="Not authenticated",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            else:
                return None  # pragma: nocover
        return param


oauth2_scheme = OAuth2AuthorizationCodeBearerWithCookie(
    authorizationUrl="/security/login", tokenUrl="/security/callback", auto_error=False
)

http_bearer = HTTPBearer(auto_error=False)

router = APIRouter(
    prefix="/security",
    tags=["security"],
    responses={404: {"description": "Not found"}},
)


def hash_token(raw_token: str) -> str:
    """Digest an API token for storage and lookup.

    Plain sha256, deliberately. It is unkeyed (uses no salt), so a service holding only a database connection
    (the tile server) can verify a token without SECRET_KEY.
    """
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def sign_delegated_token(label: str | None, expires_on: datetime) -> str:
    """A delegated token: a JWT signed with SECRET_KEY.

    Signed rather than random so a token is self-describing and provably ours —
    decode one and read what it is for and when it lapses, with no database
    access. The signature proves origin, not authority: it is still the stored
    row that grants scopes, and revocation acts on that row rather than on the
    signature (a signature cannot be un-signed).

    This is deliberately the same signer the login flow uses, so there is one
    place where SECRET_KEY is applied. Note the tile server does **not** verify
    the signature — it hashes the token and looks the row up, which it must do
    for revocation anyway. Keeping SECRET_KEY out of the tile server matters:
    the same key signs login JWTs, so a tile server compromise would otherwise
    let an attacker forge `role: web_admin` sessions.

    The payload is `{label, exp}` and nothing else, so the token is a pure
    function of those two values and the key. Labels are unique by convention,
    which is what keeps the stored digest (UNIQUE) from colliding: minting the
    same label twice in the same second with the same expiry produces the same
    token and so fails on that constraint.
    """
    return create_access_token(
        data={"label": label},
        expires_delta=expires_on - datetime.now(timezone.utc),
    )


def role_claim(user: schemas.User) -> str:
    """The `role` claim for a user's JWT — always a role PostgREST can assume.

    The application role (`admin`) is *not* the claim; the Postgres role it maps
    to (`web_admin`) is, because PostgREST `SET ROLE`s to whatever the claim says
    and the RLS policies are written against those names.
    """
    definition = user.role_definition if user is not None else None
    name = definition.postgres_role if definition is not None else None
    if name in POSTGREST_ROLES:
        return name
    return DEFAULT_POSTGREST_ROLE


def resolve_assumed_role(actual_role: str, requested: str | None) -> str:
    """The Postgres role a session may carry, given what its user is entitled to.

    `None` means "the stored role" — the way back from a degraded session. A
    role may be assumed only downward: an admin may browse as `web_authorized`
    or `web_user` (to see the site as they do), but nobody can claim more than
    their record grants, and nothing outside the roles PostgREST knows is a
    session at all.
    """
    if requested is None or requested == actual_role:
        return actual_role
    if requested not in POSTGREST_ROLES:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown role {requested!r}; expected one of "
            + ", ".join(sorted(POSTGREST_ROLES)),
        )
    if POSTGREST_ROLE_RANK[requested] < POSTGREST_ROLE_RANK.get(actual_role, 0):
        return requested
    raise HTTPException(
        status_code=403,
        detail=f"Your account cannot assume the {requested} role",
    )


def audit_actor(token: TokenData) -> str:
    """How the change-tracking trail names this session's user.

    Same spelling as the audit trigger's own fallback for PostgREST writes
    (`'orcid:' || sub`), so a change made through api-v3 and one made through
    PostgREST read as the same person.
    """
    return f"orcid:{token.sub}"


def session_claims(user: schemas.User, role: str | None = None) -> dict:
    """The claims of an access JWT for `user`, optionally in an assumed role.

    One place builds the login claims, so the callback, the refresh, and the
    role switch cannot drift apart. `actual_role` rides along only when the
    session is degraded, so an ordinary token is exactly what it always was.
    """
    actual = role_claim(user)
    effective = role or actual
    claims = {"sub": user.sub, "role": effective, "name": user.display_name}
    if effective != actual:
        claims["actual_role"] = actual
    return claims


def redirect_uri() -> str:
    """The OAuth callback URL. `REDIRECT_URI_ENV` is its old name."""
    return os.environ.get("REDIRECT_URI") or os.environ["REDIRECT_URI_ENV"]


def parse_redirect_uri():
    """Parse the redirect URI once and reuse consistently."""
    uri = redirect_uri()
    parsed = urllib.parse.urlparse(uri)
    hostname = parsed.hostname or ""
    scheme = parsed.scheme or "http"
    secure = scheme == "https"
    cookie_domain = None if hostname in ("localhost", "127.0.0.1") else hostname
    return parsed, hostname, cookie_domain, secure


class CookieParams(BaseModel):
    """The attributes every auth cookie is issued with.

    One derivation, used by the login callback, the refresh, the role switch and
    the logout alike: a cookie set under one domain and re-issued under another
    leaves the browser holding two, and whichever it sends first wins.
    """

    domain: str | None
    samesite: str | None
    secure: bool


def auth_cookie_params() -> CookieParams:
    """Where and how the session cookies are scoped.

    Production: the API's own host, `SameSite=Lax`, `Secure` under https.

    Local development reaches the API at a `.local` subdomain (e.g.
    `api.macrostrat.local`) from a site served elsewhere (`https://macrostrat.local`
    or `http://localhost:3000`), so the cookie is scoped to the parent domain and
    sent cross-site: `SameSite=None`, which must be the string "none" rather than
    Python None (that drops the attribute and defaults to Lax) and requires
    `Secure`, so it falls back to Lax over plain http.
    """
    parsed, hostname, cookie_domain, secure = parse_redirect_uri()
    samesite: str | None = "lax"
    if (
        cookie_domain
        and cookie_domain.endswith(".local")
        and cookie_domain.count(".") > 1
    ):
        cookie_domain = ".".join(cookie_domain.split(".")[-2:])
        samesite = "none" if secure else "lax"
    return CookieParams(domain=cookie_domain, samesite=samesite, secure=secure)


def set_access_cookie(response: Response, access_token: str):
    """Issue (or re-issue) the access cookie.

    Its lifetime tracks the token's `exp`, so a browser stops auto-sending it
    the moment it expires. Caddy then adds no Authorization header and
    PostgREST falls back to web_anon instead of 401ing on a stale token.
    """
    params = auth_cookie_params()
    response.set_cookie(
        access_token_key,
        f"Bearer {access_token}",
        domain=params.domain,
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        httponly=True,
        samesite=params.samesite,
        secure=params.secure,
    )


def set_refresh_cookie(response: Response, refresh_jwt: str):
    """Issue the refresh cookie. It outlives the access cookie (7d vs 24h); once
    it too expires the browser drops it and the user is fully anonymous."""
    params = auth_cookie_params()
    response.set_cookie(
        refresh_token_key,
        refresh_jwt,
        domain=params.domain,
        max_age=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        httponly=True,
        samesite=params.samesite,
        secure=params.secure,
    )


def clear_auth_cookies(response: Response):
    """Delete the session cookies under every domain they may have been set for:
    the one issued now, the API's own host, and the host-only forms."""
    _, hostname, cookie_domain, _ = parse_redirect_uri()
    issued = auth_cookie_params().domain
    for dom in {None, issued, cookie_domain, "localhost", "127.0.0.1", hostname}:
        response.delete_cookie(key=access_token_key, domain=dom)
        response.delete_cookie(key=refresh_token_key, domain=dom)


async def get_token_from_header(
    database: DatabaseDep,
    header_token: Annotated[HTTPAuthorizationCredentials, Depends(http_bearer)],
) -> schemas.Token | None:
    """Resolve a bearer token in the Authorization header to its stored row."""

    if header_token is None:
        return None

    return await db.get_token_by_hash(
        async_session=database.async_sessionmaker,
        token_hash=hash_token(header_token.credentials),
    )


async def get_user(
    sub: str, async_session: async_sessionmaker[AsyncSession]
) -> schemas.User | None:
    """Get an existing user"""

    async with async_session() as session:
        stmt = select(schemas.User).where(schemas.User.sub == sub)
        user = await session.scalar(stmt)

    return user


def get_display_name(name: str) -> str:
    """Parses first name in the name string coming from orcid"""
    return name.split(" ")[0] if name else ""


async def create_user(
    sub: str, name: str, email: str, async_session: async_sessionmaker[AsyncSession]
) -> schemas.User:
    """Create a new user, in the default role.

    `role` is NOT NULL with no database default, so it has to be set here or the
    insert fails. It is the role's own name, so there is no id to look up — the
    insert fails loudly on the foreign key if the role table was never seeded.
    """

    user = schemas.User(
        sub=sub,
        name=name,
        display_name=get_display_name(name),
        email=email,
        role=DEFAULT_ROLE,
    )

    async with async_session() as session:
        session.add(user)
        await session.commit()

    return await get_user(sub, async_session)


async def get_user_token_from_cookie(
    token: Annotated[str | None, Depends(oauth2_scheme)],
):
    """Get the current user from the JWT token in the cookies"""

    # If there wasn't a token include in the request
    if token is None:
        return None

    try:
        payload = jwt.decode(
            token,
            os.environ["SECRET_KEY"],
            algorithms=[os.environ["JWT_ENCRYPTION_ALGORITHM"]],
        )
        sub: str = payload.get("sub")
        role: str | None = payload.get("role")
        actual_role: str | None = payload.get("actual_role")
        token_data = TokenData(sub=sub, role=role, actual_role=actual_role)
    except JWTError as e:
        return None

    return token_data


async def has_access(
    user_token_data: TokenData | None = Depends(get_user_token_from_cookie),
    header_token: schemas.Token | None = Depends(get_token_from_header),
) -> bool:
    """Admin access, via the JWT role or an API token delegating an admin.

    A token issued to a third party carries no `user_id`, so it can never grant
    admin here — it grants only what is listed in its `scopes`. This replaces
    the old "token belongs to group 1" check, which conflated an API key with
    membership in an authorization group.
    """
    # The JWT carries the *Postgres* role (what PostgREST assumes), the user row
    # the application role — hence the two different names for the same check.
    if user_token_data is not None and user_token_data.role == ADMIN_POSTGREST_ROLE:
        return True

    if header_token is None or header_token.user is None:
        return False

    return header_token.user.role == ADMIN_ROLE


def create_access_token(data: dict, expires_delta: timedelta | None = None):
    """Create a JWT token"""

    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(
        to_encode,
        os.environ["SECRET_KEY"],
        algorithm=os.environ["JWT_ENCRYPTION_ALGORITHM"],
    )


@router.get("/login")
async def redirect_authorization(return_url: str = None):
    """Redirect to the authorization URL with the appropriate parameters"""

    params = {
        "scope": "openid profile email",
        "client_id": os.environ["OAUTH_CLIENT_ID"],
        "response_type": "code",
        "redirect_uri": redirect_uri(),
    }

    if return_url is not None:
        params["state"] = return_url

    return RedirectResponse(
        os.environ["OAUTH_AUTHORIZATION_URL"] + "?" + urllib.parse.urlencode(params)
    )


@router.get("/callback")
async def redirect_callback(
    code: str, database: DatabaseDep, state: Optional[str] = None
):
    """Exchange the code for a token and redirect to the state URL"""

    uri = redirect_uri()
    data = {
        "grant_type": "authorization_code",
        "client_id": os.environ["OAUTH_CLIENT_ID"],
        "client_secret": os.environ["OAUTH_CLIENT_SECRET"],
        "code": code,
        "redirect_uri": uri,
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(
            os.environ["OAUTH_TOKEN_URL"], data=data
        ) as token_response:
            if token_response.status != 200:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid code: {await token_response.text()} ",
                )

            response_data = await token_response.json()

        log.info("Obtained token response: %s", response_data)

        async with session.post(
            os.environ["OAUTH_USERINFO_URL"], data=response_data
        ) as user_response:
            log.info("Obtained user response: %s", await user_response.text())

            if user_response.status != 200:
                raise HTTPException(
                    status_code=400,
                    detail=f"Couldn't get user information: {await user_response.text()} ",
                )

            user_data = await user_response.json()
            # look up the user by their OIDC subject to compute their role
            user = await get_user(user_data["sub"], database.async_sessionmaker)

            if user is None:
                given_name = (
                    user_data.get("given_name") if user_data.get("given_name") else ""
                )
                family_name = (
                    user_data.get("family_name") if user_data.get("family_name") else ""
                )

                user = await create_user(
                    user_data["sub"],
                    f"{given_name} {family_name}".strip(),
                    user_data.get("email", ""),
                    database.async_sessionmaker,
                )

            # The `role` claim is for PostgREST; inspect a session at /dashboard
            access_token = create_access_token(data=session_claims(user))

            log.info("Created access token: %s", access_token)

            response = RedirectResponse(state if state else "/")
            set_access_cookie(response, access_token)

            # TODO remove the token type
            refresh_jwt = jwt.encode(
                {
                    "sub": user.sub,
                    "type": "refresh",
                    "name": user.display_name,
                    "exp": datetime.utcnow()
                    + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
                },
                os.environ["SECRET_KEY"],
                algorithm=os.environ["JWT_ENCRYPTION_ALGORITHM"],
            )
            set_refresh_cookie(response, refresh_jwt)

            return response


@router.post("/refresh")
async def refresh_token(
    request: Request,
    response: Response,
    database: DatabaseDep,
    refresh_token: str | None = Cookie(default=None, alias=refresh_token_key),
):
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    # verify the jwt is valid/not expired and signature
    try:
        payload = jwt.decode(
            refresh_token,
            os.environ["SECRET_KEY"],
            algorithms=[os.environ["JWT_ENCRYPTION_ALGORITHM"]],
        )
    except JWTError:
        clear_auth_cookies(response)
        raise HTTPException(status_code=401, detail="Refresh token invalid")

    if payload.get("type") != "refresh":
        clear_auth_cookies(response)
        raise HTTPException(status_code=401, detail="Refresh token invalid")

    sub = payload.get("sub")
    if not sub:
        clear_auth_cookies(response)
        raise HTTPException(status_code=401, detail="Refresh token invalid")

    # verifying the user via the subject claim
    user = await get_user(sub, database.async_sessionmaker)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    # A refresh always restores the stored role: a degraded admin session that
    # lapses comes back as a full one, the same as logging in again would.
    set_access_cookie(response, create_access_token(data=session_claims(user)))

    return {"status": "refreshed"}


@router.post("/role", response_model=SessionRole)
async def assume_role(
    body: AssumeRoleRequest,
    response: Response,
    database: DatabaseDep,
    user_token: TokenData | None = Depends(get_user_token_from_cookie),
):
    """Re-mint the session cookie in a lesser Postgres role, or restore it.

    This is a tool for admins to see the site as a user does: with
    `{"role": "web_user"}` the new cookie carries `role: web_user` — so
    PostgREST, `has_access` and the web guards all treat the session as an
    ordinary user — and `actual_role: web_admin`, so the UI can show the
    degraded state and offer the way back. `{"role": null}` (or logging out
    and in, or a token refresh) restores the stored role.

    Entitlement comes from the stored user record, never from the cookie being
    replaced: a degraded session can restore itself, and no session can climb.
    """
    if user_token is None:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user = await get_user(user_token.sub, database.async_sessionmaker)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    actual = role_claim(user)
    effective = resolve_assumed_role(actual, body.role)

    set_access_cookie(
        response, create_access_token(data=session_claims(user, role=effective))
    )
    return SessionRole(role=effective, actual_role=actual, degraded=effective != actual)


async def require_admin(
    user_token: TokenData = Depends(get_user_token_from_cookie),
    user_has_access: bool = Depends(has_access),
) -> TokenData:
    """Require a web_admin session, and hand back who it is.

    Token and user administration are the same operations as
    `macrostrat auth …` in the CLI. The CLI's authorization is possession of
    database credentials; here it is the `web_admin` role on the caller's JWT.
    A degraded admin session (see `assume_role`) carries `web_user` and is
    refused here like any other user — that is what degrading is for.
    """
    if user_token is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    if not user_has_access:
        raise HTTPException(status_code=403, detail="Only admins can do this")
    return user_token


@router.post("/tokens", response_model=DelegateToken)
async def create_delegate_token(
    token_request: DelegateTokenRequest,
    database: DatabaseDep,
    user_token: TokenData = Depends(require_admin),
):
    """Mint a delegated API token. Admin only.

    Issuing a credential that outlives a session is an admin action, so this is
    gated on the caller's role rather than on their own authority — the old
    group-scoped version let any user mint a token for a group they belonged to.

    The raw token is returned here and nowhere else; only its digest is stored.
    """

    if token_request.user_id is None and token_request.label is None:
        raise HTTPException(
            status_code=422,
            detail="A token needs a user_id or a label identifying who it is for",
        )

    expires_on = datetime.fromtimestamp(token_request.expiration, tz=timezone.utc)
    if expires_on <= datetime.now(timezone.utc):
        raise HTTPException(status_code=422, detail="Expiration is in the past")

    # Scopes are compared as exact strings by the guarded service, so a
    # malformed one would mint a token that authenticates and then grants
    # nothing. Reject it here instead.
    malformed = [s for s in (token_request.scopes or []) if not SCOPE_PATTERN.match(s)]
    if malformed:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Malformed scope: {', '.join(malformed)}. "
                f"Scopes are `<namespace>:<resource>`, e.g. {SCOPE_EXAMPLE}"
            ),
        )

    issuer = await get_user(user_token.sub, database.async_sessionmaker)

    token = create_access_token(
        data={"label": token_request.label, "user_id": token_request.user_id},
        expires_delta=expires_on - datetime.now(timezone.utc),
    )
    token_id = await db.insert_token(
        engine=database.async_engine,
        token_hash=hash_token(token),
        expires_on=expires_on,
        token_type=DELEGATED_TOKEN_TYPE,
        user_id=token_request.user_id,
        created_by=issuer.id if issuer is not None else None,
        label=token_request.label,
        scopes=token_request.scopes,
        actor=audit_actor(user_token),
    )

    return DelegateToken(
        id=token_id,
        token=token,
        expires_on=expires_on,
        label=token_request.label,
        user_id=token_request.user_id,
        scopes=token_request.scopes,
    )


@router.get("/tokens", response_model=list[DelegateTokenInfo])
async def list_delegate_tokens(
    database: DatabaseDep,
    token_type: str | None = None,
    _admin: TokenData = Depends(require_admin),
):
    """List issued API tokens, newest first. Admin only.

    Never returns the tokens themselves — the stored value is a digest, and it
    is not needed to administer a token. Pass `token_type` to narrow to one
    kind (e.g. `delegated`).
    """

    tokens = await db.list_tokens(database.async_sessionmaker, token_type=token_type)
    now = datetime.now(timezone.utc)
    return [DelegateTokenInfo.from_token(token, now=now) for token in tokens]


@router.post("/tokens/{token_id}/revoke")
async def revoke_delegate_token(
    token_id: int,
    database: DatabaseDep,
    admin: TokenData = Depends(require_admin),
):
    """Revoke a token by expiring it now. Admin only.

    The row is kept, so the record of who was issued what survives. Consumers
    of guarded endpoints cache token lookups briefly, so a revocation can take
    up to a minute to take effect.
    """

    outcome = await db.revoke_token(
        database.async_engine, token_id, actor=audit_actor(admin)
    )

    if outcome == "not_found":
        raise HTTPException(status_code=404, detail=f"No token with id {token_id}")

    return {"id": token_id, "status": outcome}


@router.post("/logout")
async def logout(response: Response):
    clear_auth_cookies(response)
    return {"status": "success"}


@router.get("/me", response_model=CurrentUser)
async def read_users_me(
    database: DatabaseDep,
    user_token_data: TokenData = Depends(get_user_token_from_cookie),
):
    """The caller's stored user record, with the role their session carries.

    `role` comes from the cookie and `actual_role` from the record; they
    differ only on a degraded session (`degraded` says so directly).
    """

    if user_token_data is None:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user = await get_user(user_token_data.sub, database.async_sessionmaker)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    return CurrentUser.from_user(user, user_token_data.role)


@router.get("/roles", response_model=list[RoleInfo])
async def list_roles(
    database: DatabaseDep,
    _admin: TokenData = Depends(require_admin),
):
    """The application roles a user can be moved between. Admin only."""
    roles = await db.list_roles(database.async_sessionmaker)
    return [
        RoleInfo(id=r.id, postgres_role=r.postgres_role, description=r.description)
        for r in roles
    ]


@router.get("/users", response_model=list[UserInfo])
async def list_users(
    database: DatabaseDep,
    q: str | None = None,
    limit: int = 500,
    _admin: TokenData = Depends(require_admin),
):
    """Users, newest first. Admin only.

    `q` narrows by name, display name, email or ORCID iD (case-insensitive
    substring). The listing is bounded (`limit`, at most 2000) because it is
    for a table, not an export.
    """
    users = await db.list_users(
        database.async_sessionmaker, query=q, limit=max(1, min(limit, 2000))
    )
    return [UserInfo.from_user(u) for u in users]


@router.get("/history", response_model=list[AuthChange])
async def list_auth_history(
    database: DatabaseDep,
    limit: int = 100,
    _admin: TokenData = Depends(require_admin),
):
    """Recent changes to users and tokens, newest first. Admin only.

    Read from the change-tracking trail (`audit.changes`), which records who
    moved whom to which role and who minted or revoked which token. Empty when
    the audit subsystem is not installed in this database.
    """
    rows = await db.list_auth_history(
        database.async_engine, limit=max(1, min(limit, 1000))
    )
    return [AuthChange(**row) for row in rows]


@router.patch("/users/{user_id}", response_model=UserInfo)
async def set_user_role(
    user_id: int,
    body: SetUserRoleRequest,
    database: DatabaseDep,
    admin: TokenData = Depends(require_admin),
):
    """Move a user to another application role. Admin only.

    An admin cannot change their own role: demoting yourself would leave the
    instance with one admin fewer and nobody at the keyboard to undo it. Have
    another admin do it, or use the database directly.
    """
    roles = {r.id for r in await db.list_roles(database.async_sessionmaker)}
    if body.role not in roles:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown role {body.role!r}; expected one of "
            + ", ".join(sorted(roles)),
        )

    user = await db.get_user_by_id(database.async_sessionmaker, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail=f"No user with id {user_id}")
    if user.sub == admin.sub:
        raise HTTPException(status_code=403, detail="You cannot change your own role")

    await db.set_user_role(
        database.async_engine, user_id, body.role, actor=audit_actor(admin)
    )
    user = await db.get_user_by_id(database.async_sessionmaker, user_id)
    return UserInfo.from_user(user)
