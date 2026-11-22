from fastapi import APIRouter

from .rockd import router as rockd_stats_router
from .tiles import router as request_stats_router
from .usage import router as usage_stats_router

stats_router = APIRouter()
stats_router.include_router(usage_stats_router, tags=["Web stats"], prefix="/web")
stats_router.include_router(
    request_stats_router, tags=["Tileserver stats"], prefix="/tileserver"
)
stats_router.include_router(rockd_stats_router, tags=["Rockd stats"], prefix="/rockd")
