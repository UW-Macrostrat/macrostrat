from fastapi import APIRouter
from api.routes.dev_routes.interchange_data import interchange_router

dev_router = APIRouter(prefix="/dev", tags=["dev"])
dev_router.include_router(interchange_router)