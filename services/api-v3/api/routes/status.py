import asyncio
from os import environ

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

from api.database import DatabaseDep
from macrostrat.utils import get_logger

log = get_logger(__name__)

router = APIRouter(tags=["Status"])

NO_STORE = {"Cache-Control": "no-store"}


@router.get("/version")
async def version():
    """The build this process runs, from the variables CI sets in the image."""
    info = {
        "service": "api-v3",
        "version": environ.get("MACROSTRAT_VERSION") or None,
        "release": environ.get("MACROSTRAT_RELEASE") == "true",
        "commit": environ.get("MACROSTRAT_COMMIT") or None,
        "build_date": environ.get("MACROSTRAT_BUILD_DATE") or None,
        "repository": environ.get("MACROSTRAT_REPOSITORY") or None,
    }
    return JSONResponse(info, headers=NO_STORE)


@router.get("/health")
async def health(database: DatabaseDep):
    async def ping():
        async with database.async_connection() as conn:
            await conn.execute(text("SELECT 1"))

    try:
        await asyncio.wait_for(ping(), timeout=5)
    except Exception as err:
        log.warning("Health check failed: %s", err)
        return JSONResponse(
            {"status": "unavailable"}, status_code=503, headers=NO_STORE
        )
    return JSONResponse({"status": "ok"}, headers=NO_STORE)
