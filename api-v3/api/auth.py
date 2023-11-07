"""
Authentication based on username/password and JWTs stored in cookies.
"""

import os
import time
import warnings
from typing import Any, Optional, Tuple

import jwt
from fastapi import APIRouter, Request
from starlette.authentication import (
    AuthCredentials,
    AuthenticationBackend,
    AuthenticationError,
    BaseUser,
    SimpleUser,
    UnauthenticatedUser,
    requires,
)
from starlette.requests import HTTPConnection
from starlette.responses import JSONResponse, Response

from api.models import User

HOUR = 60 * 60
DAY = 24 * HOUR
MONTH = 30 * DAY

router = APIRouter(prefix="/auth", tags=["auth"])


class JWTAuthBackend(AuthenticationBackend):
    """
    JSON Web Token authenticator backend for Starlette's authentication system.

    Prior art: https://github.com/retnikt/star_jwt/blob/master/star_jwt/backend.py

    Creates two cookies: `access_token_cookie` and `refresh_token_cookie`. This
    structure is modeled on `flask_jwt_extended`. Each cookie should have a `type`
    and `identity` field.
    """

    def __init__(self, encode_key: str):
        self.encode_key = encode_key

    def _encode(self, payload):
        return jwt.encode(payload, self.encode_key, algorithm="HS256")

    def _decode(self, cookie):
        options = {"require": ["iat", "nbf", "exp"]}
        return jwt.decode(cookie, self.encode_key, algorithms=["HS256"], options=options)

    def set_cookie(self, response: Optional[Response], type: str, **data):
        """
        Set a basic cookie on the response.
        """
        now = time.time()
        max_age = data.pop("max_age", DAY)
        name = type + "_token_cookie"

        payload = {"iat": now, "nbf": now, "exp": now + max_age, "type": type}
        payload.update(data)

        token = self._encode(payload)

        if response is None:
            return token

        response.set_cookie(
            name,
            value=token,
            max_age=max_age,
            secure=True,
            httponly=True,
        )

    def get_identity(self, request: HTTPConnection, type: str = "access"):
        name = f"{type}_token_cookie"
        try:
            cookie = request.cookies.get(name)
            if cookie is None:
                if "Authorization" not in request.headers:
                    raise AuthenticationError(f"Could not find {name} on request")
                header = request.headers["Authorization"]
                if header.startswith("Bearer "):
                    header = header[7:]
                else:
                    warnings.warn(
                        "Authorization header did not start with 'Bearer '. This is invalid and deprecated."
                    )
                value = self._decode(header)
            else:
                value = self._decode(cookie)

            identity = value.get("identity")
            if identity is None:
                raise AuthenticationError(f"{name} has no key identity")
            if type != value.get("type"):
                raise AuthenticationError(f"{name} did not have a matching type")
            return identity
        except jwt.PyJWTError as e:
            raise AuthenticationError(*e.args) from None

    async def authenticate(self, conn: HTTPConnection) -> Tuple[AuthCredentials, BaseUser]:
        try:
            identity = self.get_identity(conn, type="access")
            user = SimpleUser(identity)
            return (AuthCredentials(("authenticated",)), user)
        except AuthenticationError:
            return (AuthCredentials(("public",)), UnauthenticatedUser())

    def set_login_cookies(self, response: Response, **data: Any) -> Response:
        self.set_access_cookie(response, **data)
        self.set_cookie(response, "refresh", max_age=MONTH, **data)
        return response

    def set_access_cookie(self, response: Response, **data: Any) -> Response:
        self.set_cookie(response, "access", max_age=DAY, **data)
        return response

    def logout(self, response: Response) -> Response:
        response.delete_cookie(key="access_token_cookie")
        response.delete_cookie(key="refresh_token_cookie")
        return response


def UnauthorizedResponse(**kwargs):
    return JSONResponse(
        {
            "login": False,
            "username": None,
            "message": "User is not authenticated",
            **kwargs,
        }
    )


def get_backend(request: Request) -> JWTAuthBackend:
    return request.app.state.auth_backend  # type: ignore [no-any-return]


@router.post("/login")
async def login(request: Request, username: str, password: str):
    backend = get_backend(request)
    db = get_database()
    current_user = db.session.query(User).get(username)

    if current_user is not None and current_user.is_correct_password(password):
        token = backend.set_cookie(None, "access", max_age=DAY, identity=username)
        resp = JSONResponse({"login": True, "username": username, "token": token})
        return backend.set_login_cookies(resp, identity=username)

    return backend.logout(UnauthorizedResponse(status_code=401))


@router.post("/logout")
def logout(request: Request):
    backend = get_backend(request)
    return backend.logout(UnauthorizedResponse(status_code=200))


@router.post("/refresh")
def refresh(request: Request):
    backend = get_backend(request)
    identity = backend.get_identity(request, type="refresh")
    response = JSONResponse({"login": True, "refresh": True, "username": identity})

    return backend.set_access_cookie(response, identity=identity)


@router.get("/status")
def status(request: Request):
    backend = get_backend(request)
    try:
        identity = backend.get_identity(request)
        return JSONResponse({"login": True, "username": identity})
    except AuthenticationError:
        return UnauthorizedResponse(status_code=200)


@router.get("/debug/login")
def debug_login(request: Request, username: str, password: str):
    backend = get_backend(request)

    if username == os.environ["DEBUG_USERNAME"] and password == os.environ["DEBUG_PASSWORD"]:
        token = backend.set_cookie(None, "access", max_age=DAY, identity=username)
        resp = JSONResponse({"login": True, "username": username, "token": token})
        return backend.set_login_cookies(resp, identity=username)

    return backend.logout(UnauthorizedResponse(status_code=401))


@router.get("/debug/check-auth")
@requires("authenticated")
def debug_check_auth(request: Request):
    return {"authenticated": True}
