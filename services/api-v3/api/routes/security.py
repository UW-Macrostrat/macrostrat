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
POSTGREST_ROLES = frozenset({"web_admin", "web_user"})
DEFAULT_ROLE = "web_user"

REFRESH_TOKEN_EXPIRE_DAYS = 7
refresh_token_key = "refresh_token"

# TODO: Log to the proper channel
log = get_logger("uvicorn")


class TokenData(BaseModel):
    """The claims this service reads back out of an access JWT."""

    sub: str
    role: str | None = None


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
    created_by: int | None = None
    created_on: datetime
    expires_on: datetime
    used_on: datetime | None = None
    active: bool

    @classmethod
    def from_token(cls, token: schemas.Token, *, now: datetime) -> "DelegateTokenInfo":
        return cls(
            id=token.id,
            label=token.label,
            token_type=token.token_type,
            scopes=token.scopes,
            user_id=token.user_id,
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
    """The `role` claim for a user's JWT — always a role PostgREST can assume."""
    name = user.role.name if user.role is not None else None
    if name in POSTGREST_ROLES:
        return name
    return DEFAULT_ROLE


def parse_redirect_uri():
    """Parse REDIRECT_URI_ENV once and reuse consistently."""
    uri = os.environ["REDIRECT_URI_ENV"]
    parsed = urllib.parse.urlparse(uri)
    hostname = parsed.hostname or ""
    scheme = parsed.scheme or "http"
    secure = scheme == "https"
    cookie_domain = None if hostname in ("localhost", "127.0.0.1") else hostname
    return parsed, hostname, cookie_domain, secure


def clear_auth_cookies(response: Response):
    """
    Attempt to delete cookies for both host-only and domain cookies"""
    _, hostname, cookie_domain, _ = parse_redirect_uri()
    for dom in {None, cookie_domain, "localhost", "127.0.0.1", hostname}:
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

    `role_id` is NOT NULL with no database default, so it has to be set here or
    the insert fails. Resolved by name rather than by the seeded id so a
    rebuilt database with different ids still works.
    """

    role_id = await db.get_role_id(async_session, DEFAULT_ROLE)
    if role_id is None:
        raise HTTPException(
            status_code=500,
            detail=f"Role {DEFAULT_ROLE} is missing from macrostrat_auth.role",
        )

    user = schemas.User(
        sub=sub,
        name=name,
        display_name=get_display_name(name),
        email=email,
        role_id=role_id,
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
        token_data = TokenData(sub=sub, role=role)
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
    if user_token_data is not None and user_token_data.role == "web_admin":
        return True

    if header_token is None or header_token.user is None:
        return False

    return header_token.user.role.name == "web_admin"


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
        "redirect_uri": os.environ["REDIRECT_URI_ENV"],
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

    uri = os.environ["REDIRECT_URI_ENV"]
    data = {
        "grant_type": "authorization_code",
        "client_id": os.environ["OAUTH_CLIENT_ID"],
        "client_secret": os.environ["OAUTH_CLIENT_SECRET"],
        "code": code,
        "redirect_uri": uri,
    }

    parsed_url, hostname, cookie_domain, secure = parse_redirect_uri()

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

            # validate jwt https://dev.macrostrat.org/dev/me
            access_token = create_access_token(
                data={
                    "sub": user.sub,
                    "role": role_claim(user),  # For PostgREST
                    "name": user.display_name,
                }
            )

            log.info("Created access token: %s", access_token)

            response = RedirectResponse(state if state else "/")

            samesite = "lax"

            # Overrides for local development
            # Remove subdomins for .local domains (for local development)
            if cookie_domain.endswith(".local") and cookie_domain.count(".") > 1:
                parts = cookie_domain.split(".")
                # Remove the subdomain
                cookie_domain = ".".join(parts[-2:])
                # Must be the string "none" (not Python None, which drops the attribute and defaults to Lax). lets the
                # cookie allow cross-site fetches from http://localhost:3000 to https://macrostrat.local.
                samesite = None

            log.info("Redirecting to %s", cookie_domain)

            secure = parsed_url.scheme == "https"
            if not secure:
                # Samesite none requires secure cookies
                samesite = "lax"

            response.set_cookie(
                access_token_key,
                f"Bearer {access_token}",
                domain=cookie_domain,
                # Cookie lifetime tracks the access-token `exp`, so a
                # browser stops auto-sending it the moment it expires. Caddy then
                # adds no Authorization header and PostgREST falls back to
                # web_anon instead of 401ing on a stale token.
                max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
                httponly=True,
                samesite=samesite,
                secure=secure,
            )
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

            response.set_cookie(
                refresh_token_key,
                refresh_jwt,
                domain=cookie_domain,
                # Refresh cookie outlives the access cookie (7d vs 24h); once it
                # too expires the browser drops it and the user is fully anon.
                max_age=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
                httponly=True,
                samesite=samesite,
                secure=secure,
            )

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

    # setting new access cookie
    access_token = create_access_token(
        data={"sub": user.sub, "role": role_claim(user), "name": user.display_name}
    )

    parsed_url, hostname, cookie_domain, secure = parse_redirect_uri()

    response.set_cookie(
        access_token_key,
        f"Bearer {access_token}",
        domain=cookie_domain,
        # Same as the callback: cookie lifetime tracks the fresh access-token exp.
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        httponly=True,
        samesite="lax",
        secure=(parsed_url.scheme == "https"),
    )

    return {"status": "refreshed"}


async def require_admin(
    user_token: TokenData = Depends(get_user_token_from_cookie),
    user_has_access: bool = Depends(has_access),
) -> TokenData:
    """Require a web_admin session, and hand back who it is.

    Token administration is the same three operations as
    `macrostrat auth …` in the CLI. The CLI's authorization is possession of
    database credentials; here it is the `web_admin` role on the caller's JWT.
    """
    if user_token is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    if not user_has_access:
        raise HTTPException(
            status_code=403, detail="Only admins can administer API tokens"
        )
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
    _admin: TokenData = Depends(require_admin),
):
    """Revoke a token by expiring it now. Admin only.

    The row is kept, so the record of who was issued what survives. Consumers
    of guarded endpoints cache token lookups briefly, so a revocation can take
    up to a minute to take effect.
    """

    outcome = await db.revoke_token(database.async_engine, token_id)

    if outcome == "not_found":
        raise HTTPException(status_code=404, detail=f"No token with id {token_id}")

    return {"id": token_id, "status": outcome}


@router.post("/logout")
async def logout(response: Response):
    clear_auth_cookies(response)
    return {"status": "success"}


@router.get("/me")
async def read_users_me(
    database: DatabaseDep,
    user_token_data: TokenData = Depends(get_user_token_from_cookie),
):
    """Return the caller's stored user record"""

    if user_token_data is None:
        raise HTTPException(status_code=401, detail="User not found")

    async with database.async_session() as session:
        user_stmt = select(schemas.User).filter(schemas.User.sub == user_token_data.sub)
        user = await session.scalar(user_stmt)

        if user is None:
            raise HTTPException(status_code=404, detail="User not found")
        return {
            "sub": user.sub,
            "email": user.email,
            "id": user.id,
            "display_name": user.display_name,
            "created_on": user.created_on,
            "updated_on": user.updated_on,
        }
