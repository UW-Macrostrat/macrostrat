from fastapi import APIRouter
from api.routes.dev_routes.convert import convert_router

dev_router = APIRouter(prefix="/dev", tags=["dev"])
dev_router.include_router(convert_router)