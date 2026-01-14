import base64
import hashlib
import hmac
import os
import secrets
import string
import urllib.parse
from datetime import datetime, timedelta, timezone
from typing import Annotated, Optional

import aiohttp
import bcrypt
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
from macrostrat.utils import get_logger
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from starlette.status import HTTP_401_UNAUTHORIZED

dotenv.load_dotenv()

import api.database as db
import api.schemas as schemas

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1440  # 24 hours
GROUP_TOKEN_LENGTH = 32
GROUP_TOKEN_SALT = (
    b"$2b$12$yQrslvQGWDFjwmDBMURAUe"  # Hardcode salt so hashes are consistent
)

REFRESH_TOKEN_EXPIRE_DAYS = 7
refresh_token_key = "refresh_token"

# TODO: Log to the proper channel
log = get_logger("uvicorn")


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    sub: str
    groups: list[int] = []


class User(BaseModel):
    username: str
    email: str | None = None
    full_name: str | None = None
    disabled: bool | None = None


class AccessToken(BaseModel):
    group: int
    token: str


class GroupTokenRequest(BaseModel):
    expiration: int
    group_id: int


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


def hash_refresh_token(raw_token: str) -> str:
    # Deterministic hash so you can LOOKUP in DB by value.
    key = os.environ["SECRET_KEY"].encode("utf-8")
    digest = hmac.new(key, raw_token.encode("utf-8"), hashlib.sha256).digest()
    return base64.urlsafe_b64encode(digest).decode("utf-8")


async def get_user_by_id(user_id: int) -> schemas.User | None:
    engine = db.get_engine()
    async_session = db.get_async_session(engine)

    async with async_session() as session:
        stmt = (
            select(schemas.User)
            .options(selectinload(schemas.User.groups))
            .where(schemas.User.id == user_id)
        )
        return await session.scalar(stmt)


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


async def get_groups_from_header_token(
    header_token: Annotated[HTTPAuthorizationCredentials, Depends(http_bearer)]
) -> int | None:
    """Get the groups from the bearer token in the header"""

    if header_token is None:
        return None

    token_hash = bcrypt.hashpw(header_token.credentials.encode(), GROUP_TOKEN_SALT)
    token_hash_string = token_hash.decode("utf-8")

    engine = db.get_engine()
    async_session = db.get_async_session(engine)

    token = await db.get_access_token(
        async_session=async_session, token=token_hash_string
    )

    if token is None:
        return None

    return token.group


async def get_user(sub: str) -> schemas.User | None:
    """Get an existing user"""

    engine = db.get_engine()
    async_session = db.get_async_session(engine)

    async with async_session() as session:
        stmt = (
            select(schemas.User)
            .options(selectinload(schemas.User.groups))
            .where(schemas.User.sub == sub)
        )
        user = await session.scalar(stmt)

    return user


async def create_user(sub: str, name: str, email: str) -> schemas.User:
    """Create a new user"""

    engine = db.get_engine()
    async_session = db.get_async_session(engine)

    user = schemas.User(sub=sub, name=name, email=email)

    async with async_session() as session:
        session.add(user)
        await session.commit()

    return await get_user(sub)


async def get_user_token_from_cookie(
    token: Annotated[str | None, Depends(oauth2_scheme)]
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
        groups = payload.get("groups", [])
        token_data = TokenData(sub=sub, groups=groups)
    except JWTError as e:
        return None

    return token_data


async def get_groups(
    user_token_data: TokenData | None = Depends(get_user_token_from_cookie),
    header_token: int | None = Depends(get_groups_from_header_token),
) -> list[int]:
    """Get the groups from both the cookies and header"""

    groups = []
    if user_token_data is not None:
        groups = user_token_data.groups

    if header_token is not None:
        groups.append(header_token)

    return groups


async def has_access(groups: list[int] = Depends(get_groups)) -> bool:
    """Check if the user has access to the group"""
    return 1 in groups


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
async def redirect_callback(code: str, state: Optional[str] = None):
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
            # need to look up the user_id and return it in the jwt
            user = await get_user(user_data["sub"])

            if user is None:

                given_name = (
                    user_data.get("given_name") if user_data.get("given_name") else ""
                )
                family_name = (
                    user_data.get("family_name") if user_data.get("family_name") else ""
                )

                user = await create_user(
                    user_data["sub"],
                    f"{given_name} {family_name}",
                    user_data.get("email", ""),
                )

            # Check if the user is in the admin group to set the appropriate database role
            names = {g.name for g in user.groups}
            ids = {g.id for g in user.groups}
            role = (
                "web_admin"
                if ("web_admin" in names or "admin" in names or 1 in ids)
                else "web_user"
            )

            # validate jwt https://dev.macrostrat.org/dev/me
            access_token = create_access_token(
                data={
                    "sub": user.sub,
                    "role": role,  # For PostgREST
                    # ensure user_id is correctly being returned
                    "user_id": user.id,
                    "groups": list(ids),
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
                httponly=True,
                samesite=samesite,
                secure=secure,
            )

            refresh_jwt = jwt.encode(
                {
                    "user_id": user.id,
                    "sub": user.sub,
                    "type": "refresh",
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
                httponly=True,
                samesite=samesite,
                secure=secure,
            )

            return response


@router.post("/refresh")
async def refresh_token(
    request: Request,
    response: Response,
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

    user_id = payload.get("user_id")
    if not user_id:
        clear_auth_cookies(response)
        raise HTTPException(status_code=401, detail="Refresh token invalid")

    # verifying the user_id and group_id
    user = await get_user_by_id(int(user_id))
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    names = {g.name for g in user.groups}
    ids = {g.id for g in user.groups}
    role = (
        "web_admin"
        if ("web_admin" in names or "admin" in names or 1 in ids)
        else "web_user"
    )
    # setting new access cookie
    access_token = create_access_token(
        data={"sub": user.sub, "role": role, "user_id": user.id, "groups": list(ids)}
    )

    parsed_url, hostname, cookie_domain, secure = parse_redirect_uri()

    response.set_cookie(
        access_token_key,
        f"Bearer {access_token}",
        domain=cookie_domain,
        httponly=True,
        samesite="lax",
        secure=(parsed_url.scheme == "https"),
    )

    return {"status": "refreshed"}


@router.post("/token", response_model=AccessToken)
async def create_group_token(
    group_token_request: GroupTokenRequest,
    user_token: TokenData = Depends(get_user_token_from_cookie),
):
    """Get an access token for the current user"""

    if group_token_request.group_id not in user_token.groups:
        raise HTTPException(
            status_code=401,
            detail=f"User cannot create tokens for group {group_token_request.group_id}",
        )

    engine = db.get_engine()

    token = "".join(
        secrets.choice(string.ascii_letters + string.digits)
        for i in range(GROUP_TOKEN_LENGTH)
    )
    token_hash_string = bcrypt.hashpw(token.encode("utf-8"), bcrypt.gensalt()).decode(
        "utf-8"
    )

    await db.insert_group_api_token(
        engine=db.get_engine(),
        token_hash_string=token_hash_string,
        group_id=group_token_request.group_id,
        expiration_dt=datetime.fromtimestamp(
            group_token_request.expiration, tz=timezone.utc
        ),
    )

    return AccessToken(group=group_token_request.group_id, token=token)


@router.post("/logout")
async def logout(response: Response):
    clear_auth_cookies(response)
    return {"status": "success"}


@router.get("/groups")
async def get_security_groups(groups: list[int] = Depends(get_groups)):
    """Get the groups for the current user"""

    return groups


@router.get("/me")
async def read_users_me(
    user_token_data: TokenData = Depends(get_user_token_from_cookie),
):
    """Return JWT content"""

    if user_token_data is None:
        raise HTTPException(status_code=401, detail="User not found")

    engine = db.get_engine()
    async_session = db.get_async_session(engine)

    async with async_session() as session:
        user_stmt = (
            select(schemas.User)
            .options(selectinload(schemas.User.groups))
            .filter(schemas.User.sub == user_token_data.sub)
        )
        user = await session.scalar(user_stmt)

        if user is None:
            raise HTTPException(status_code=404, detail="User not found")
        return {
            "sub": user.sub,
            "email": user.email,
            "id": user.id,
            "name": user.name,
            "created_on": user.created_on,
            "updated_on": user.updated_on,
            "groups": [{"name": g.name, "id": g.id} for g in user.groups],
        }
