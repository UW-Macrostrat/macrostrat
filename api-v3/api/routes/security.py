from datetime import datetime, timedelta
from typing import Annotated
import os
import urllib.parse

import aiohttp
from fastapi import HTTPException, APIRouter, Depends, status
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2AuthorizationCodeBearer
from jose import JWTError, jwt
from pydantic import BaseModel
from sqlalchemy import select

import api.schemas as schemas
import api.database as db

# to get a string like this run:
# openssl rand -hex 32
SECRET_KEY = "11937be5daeb452985fc2d4f8ab09841d2fa45f48d72960b470d52fd84f4088e"
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


oauth2_scheme = OAuth2AuthorizationCodeBearer(
    authorizationUrl='/security/authorize/redirect',
    tokenUrl=os.environ['OAUTH_TOKEN_URL'],
)

router = APIRouter(
    prefix="/security",
    tags=["security"],
    responses={404: {"description": "Not found"}},
)


async def get_user(sub: str) -> schemas.User | None:
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
    engine = db.get_engine()
    async_session = db.get_async_session(engine)

    user = schemas.User(sub=sub, name=name, email=email)

    async with async_session() as session:
        session.add(user)
        await session.commit()

    return await get_user(sub)


async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception
    user = get_user(sub=token_data.sub)
    if user is None:
        raise credentials_exception
    return user


def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


@router.get("/authorize/redirect")
async def redirect_authorization():
    params = {
        'scope': "openid profile email org.cilogon.userinfo",
        'client_id': os.environ['OAUTH_CLIENT_ID'],
        'response_type': "code",
        'redirect_uri': 'http://localhost:8000/security/callback',
    }

    return RedirectResponse(os.environ['OAUTH_AUTHORIZATION_URL'] + "?" + urllib.parse.urlencode(params))


@router.get("/callback")
async def redirect_callback(code: str):

    data = {
        'grant_type': 'authorization_code',
        'client_id': os.environ['OAUTH_CLIENT_ID'],
        'client_secret': os.environ['OAUTH_CLIENT_SECRET'],
        'code': code,
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(os.environ['OAUTH_TOKEN_URL'], data=data) as response:

            if response.status != 200:
                raise HTTPException(status_code=400, detail=f"Invalid code: {await response.text()} ")

            response_data = await response.json()

        async with session.post(os.environ['OAUTH_USERINFO_URL'], data=response_data) as response:

            if response.status != 200:
                raise HTTPException(status_code=400, detail=f"Couldn't get user information: {await response.text()} ")

            user_data = await response.json()

            user = await get_user(user_data['sub'])

            if user is None:
                user = await create_user(user_data['sub'], user_data.get('name', ''), user_data.get('email', ''))

            print(user)

@router.get("/me")
async def read_users_me(token: str = Depends(oauth2_scheme)):
    return {"token": token}