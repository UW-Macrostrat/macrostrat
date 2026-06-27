from fastapi import APIRouter
from .usage import router as usage_stats_router
from .requests import router as request_stats_router

stats_router = APIRouter()
stats_router.include_router(usage_stats_router, tags=["Web stats"], prefix="/web")
stats_router.include_router(
    request_stats_router, tags=["Tileserver stats"], prefix="/tileserver"
)
