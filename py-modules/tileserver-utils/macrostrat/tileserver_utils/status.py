from os import environ

from fastapi import APIRouter, Request
from starlette.responses import JSONResponse

from macrostrat.utils import get_logger

log = get_logger(__name__)

# Varnish must not cache what these report
NO_STORE = {"Cache-Control": "no-store"}


def build_info(service: str) -> dict:
    """The build this process runs, from the variables CI sets in the image."""
    return {
        "service": service,
        "version": environ.get("MACROSTRAT_VERSION") or None,
        "release": environ.get("MACROSTRAT_RELEASE") == "true",
        "commit": environ.get("MACROSTRAT_COMMIT") or None,
        "build_date": environ.get("MACROSTRAT_BUILD_DATE") or None,
        "repository": environ.get("MACROSTRAT_REPOSITORY") or None,
    }


def status_router(service: str) -> APIRouter:
    """`/version` and `/health` for an app holding an asyncpg pool on `app.state.pool`."""
    router = APIRouter(tags=["Status"])

    @router.get("/version")
    async def version():
        return JSONResponse(build_info(service), headers=NO_STORE)

    @router.get("/health")
    async def health(request: Request):
        try:
            async with request.app.state.pool.acquire(timeout=5) as conn:
                await conn.fetchval("SELECT 1", timeout=5)
        except Exception as err:
            log.warning("Health check failed: %s", err)
            return JSONResponse(
                {"status": "unavailable"}, status_code=503, headers=NO_STORE
            )
        return JSONResponse({"status": "ok"}, headers=NO_STORE)

    return router
