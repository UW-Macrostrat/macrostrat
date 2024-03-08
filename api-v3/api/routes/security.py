import os
import secrets
import string
import urllib.parse
from datetime import datetime, timedelta
from typing import Annotated, Optional

import aiohttp
import bcrypt
import dotenv
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
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
from starlette.status import HTTP_401_UNAUTHORIZED

dotenv.load_dotenv()

import api.database as db
import api.schemas as schemas

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1440  # 24 hours
GROUP_TOKEN_LENGTH = 32
GROUP_TOKEN_SALT = b'$2b$12$yQrslvQGWDFjwmDBMURAUe'  # Hardcode salt so hashes are consistent


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


class OAuth2AuthorizationCodeBearerWithCookie(OAuth2AuthorizationCodeBearer):
    """Tweak FastAPI's OAuth2AuthorizationCodeBearer to use a cookie instead of a header"""

    async def __call__(self, request: Request) -> Optional[str]:
        authorization = request.cookies.get("Authorization")  # authorization = request.headers.get("Authorization")
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
    authorizationUrl='/security/login',
    tokenUrl="/security/callback",
    auto_error=False
)

http_bearer = HTTPBearer(auto_error=False)

router = APIRouter(
    prefix="/security",
    tags=["security"],
    responses={404: {"description": "Not found"}},
)


async def get_groups_from_header_token(header_token: Annotated[HTTPAuthorizationCredentials, Depends(http_bearer)]) -> int | None:
    """Get the groups from the bearer token in the header"""

    if header_token is None:
        return None

    token_hash = bcrypt.hashpw(header_token.credentials.encode(), GROUP_TOKEN_SALT)
    token_hash_string = token_hash.decode('utf-8')

    engine = db.get_engine()
    async_session = db.get_async_session(engine)

    token = await db.get_access_token(async_session=async_session, token=token_hash_string)

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


async def get_user_token_from_cookie(token: Annotated[str | None, Depends(oauth2_scheme)]):
    """Get the current user from the JWT token in the cookies"""

    # If there wasn't a token include in the request
    if token is None:
        return None

    try:
        payload = jwt.decode(token, os.environ['SECRET_KEY'], algorithms=[os.environ['JWT_ENCRYPTION_ALGORITHM']])
        sub: str = payload.get("sub")
        groups = payload.get("groups", [])
        token_data = TokenData(sub=sub, groups=groups)
    except JWTError as e:
        return None

    return token_data


async def get_groups(
    user_token_data: TokenData | None = Depends(get_user_token_from_cookie),
    header_token: int | None = Depends(get_groups_from_header_token)
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

    if os.environ['ENVIRONMENT'] == 'development':
        return True

    return 1 in groups


def create_access_token(data: dict, expires_delta: timedelta | None = None):
    """Create a JWT token"""

    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, os.environ['SECRET_KEY'], algorithm=os.environ['JWT_ENCRYPTION_ALGORITHM'])
    return encoded_jwt


@router.get("/login")
async def redirect_authorization(return_url: str = None):
    """Redirect to the authorization URL with the appropriate parameters"""

    params = {
        'scope': "openid profile email org.cilogon.userinfo",
        'client_id': os.environ['OAUTH_CLIENT_ID'],
        'response_type': "code",
        'redirect_uri': os.environ['REDIRECT_URI']
    }

    if return_url is not None:
        params['state'] = return_url

    return RedirectResponse(os.environ['OAUTH_AUTHORIZATION_URL'] + "?" + urllib.parse.urlencode(params))


@router.get("/callback")
async def redirect_callback(code: str, state: Optional[str] = None):
    """Exchange the code for a token and redirect to the state URL"""

    data = {
        'grant_type': 'authorization_code',
        'client_id': os.environ['OAUTH_CLIENT_ID'],
        'client_secret': os.environ['OAUTH_CLIENT_SECRET'],
        'code': code,
        'redirect_uri': os.environ['REDIRECT_URI']
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(os.environ['OAUTH_TOKEN_URL'], data=data) as token_response:

            if token_response.status != 200:
                raise HTTPException(status_code=400, detail=f"Invalid code: {await token_response.text()} ")

            response_data = await token_response.json()

        async with session.post(os.environ['OAUTH_USERINFO_URL'], data=response_data) as user_response:

            if user_response.status != 200:
                raise HTTPException(status_code=400, detail=f"Couldn't get user information: {await user_response.text()} ")

            user_data = await user_response.json()

            user = await get_user(user_data['sub'])

            if user is None:
                user = await create_user(user_data['sub'], user_data.get('name', ''), user_data.get('email', ''))

            access_token = create_access_token(
                data={
                    "sub": user.sub,
                    "role": "web_user", # For PostgREST
                    "groups": [group.id for group in user.groups],

                }
            )

            response = RedirectResponse(state if state else "/")
            response.set_cookie(key="Authorization", value=f"Bearer {access_token}", httponly=True, samesite="lax")

            return response


@router.post("/token", response_model=AccessToken)
async def create_group_token(group_token_request: GroupTokenRequest, user_token: TokenData = Depends(get_user_token_from_cookie)):
    """Get an access token for the current user"""

    if group_token_request.group_id not in user_token.groups:
        raise HTTPException(status_code=401, detail=f"User cannot create tokens for group {group_token_request.group_id}")

    engine = db.get_engine()

    token = ''.join(secrets.choice(string.ascii_letters + string.digits) for i in range(GROUP_TOKEN_LENGTH))
    token_hash = bcrypt.hashpw(token.encode("utf-8"), GROUP_TOKEN_SALT)
    token_hash_string = token_hash.decode('utf-8')

    await db.insert_access_token(
        engine=engine,
        token=token_hash_string,
        group_id=group_token_request.group_id,
        expiration=datetime.fromtimestamp(group_token_request.expiration)
    )

    return AccessToken(group=group_token_request.group_id, token=token)


@router.get("/logout")
async def logout(response: Response):
    """Logout the active user"""

    response.delete_cookie(key="Authorization")
    return response


@router.get("/groups")
async def get_security_groups(groups: list[int] = Depends(get_groups)):
    """Get the groups for the current user"""

    return groups

@router.get("/me")
async def read_users_me(user_token_data: TokenData = Depends(get_user_token_from_cookie)):
    """Return JWT content"""

    return user_token_data
