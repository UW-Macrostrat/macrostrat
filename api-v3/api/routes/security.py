from datetime import datetime, timedelta
from typing import Annotated, Optional
import os
import urllib.parse

import aiohttp
from fastapi import HTTPException, APIRouter, Depends, status, Response, Request
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2AuthorizationCodeBearer
from fastapi.security.utils import get_authorization_scheme_param
from starlette.status import HTTP_401_UNAUTHORIZED
from jose import JWTError, jwt
from pydantic import BaseModel
from sqlalchemy import select

import dotenv
dotenv.load_dotenv()

import api.schemas as schemas
import api.database as db


ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    sub: str
    groups: list[str] = []


class User(BaseModel):
    username: str
    email: str | None = None
    full_name: str | None = None
    disabled: bool | None = None


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
    tokenUrl="/security/callback"
)

router = APIRouter(
    prefix="/security",
    tags=["security"],
    responses={404: {"description": "Not found"}},
)


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


async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]):
    """Get the current user from the JWT token"""

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, os.environ['SECRET_KEY'], algorithms=[os.environ['JWT_ENCRYPTION_ALGORITHM']])
        sub: str = payload.get("sub")
        if sub is None:
            raise credentials_exception
        token_data = TokenData(sub=sub, groups=payload.get("groups", []))
    except JWTError:
        raise credentials_exception

    return token_data


def create_access_token(data: dict, expires_delta: timedelta | None = None):
    """Create a JWT token"""

    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
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
                    "groups": [group.name for group in user.groups]
                }
            )

            response = RedirectResponse(state if state else "/")
            response.set_cookie(key="Authorization", value=f"Bearer {access_token}", httponly=True, samesite="strict")

            return response


@router.get("/logout")
async def logout(response: Response):
    """Logout the active user"""

    response.delete_cookie(key="Authorization")
    return response


@router.get("/refresh")
async def refresh(response: Response, user_token_data: Annotated[TokenData, Depends(get_current_user)]):
    """Update groups and provide a new token"""

    user = await get_user(user_token_data.sub)
    access_token = create_access_token(
        data={
            "sub": user.sub,
            "groups": [group.name for group in user.groups]
        }
    )
    response.set_cookie(key="Authorization", value=f"Bearer {access_token}", httponly=True, samesite="strict")
    return response


@router.get("/me")
async def read_users_me(user_token_data: TokenData = Depends(get_current_user)):
    """Return JWT content"""

    return user_token_data

