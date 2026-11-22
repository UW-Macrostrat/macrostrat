"""Two-tier CORS: credentialed for listed origins, anonymous for every other."""

from starlette.datastructures import Headers
from starlette.middleware.cors import CORSMiddleware
from starlette.types import ASGIApp, Receive, Scope, Send

# Origins allowed to send cookies; the website itself is same-origin.
CREDENTIALED_ORIGINS = [
    "http://localhost:8000",
    "http://localhost:3000",
    "http://localhost:6006",
    "https://dev.rockd.org",
    "https://staging.rockd.org",
]

# Readable from a page: which maps a tile draws, and whether the database cache
# answered.
EXPOSE_HEADERS = ["X-Macrostrat-Sources", "X-Tile-Cache"]


class TwoTierCORSMiddleware:
    """Any origin may read what an anonymous request returns.

    Without `Access-Control-Allow-Credentials`, browsers send no cookies on a
    cross-origin request and refuse to expose a credentialed response, so the
    open tier reveals nothing a signed-out visitor couldn't see.
    """

    def __init__(self, app: ASGIApp, credentialed_origins: list[str]):
        self.origins = set(credentialed_origins)
        self.credentialed = CORSMiddleware(
            app,
            allow_origins=credentialed_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
            expose_headers=EXPOSE_HEADERS,
        )
        self.anonymous = CORSMiddleware(
            app,
            allow_origins=["*"],
            allow_methods=["*"],
            allow_headers=["*"],
            expose_headers=EXPOSE_HEADERS,
        )

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        tier = self.anonymous
        if scope["type"] == "http":
            if Headers(scope=scope).get("origin") in self.origins:
                tier = self.credentialed
        await tier(scope, receive, send)
