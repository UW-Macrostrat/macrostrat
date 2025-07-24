from api.database import get_async_session
from api.schemas import RockdUsageStats
from app.models import UsageStats as UsageStatsModel
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import insert
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


@router.post("/rockd-usage_stats", response_model=RockdUsageStats)
async def create_usage_stats(
    request: Request,
    session: AsyncSession = Depends(get_async_session),
):
    """Create a new usage stats record from request body"""
    try:
        data = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON in request body")

    try:
        # Validate input against Pydantic model
        usage_stat = RockdUsageStats(**data)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Validation error: {e}")

    stmt = (
        insert(UsageStatsModel)
        .values(**usage_stat.model_dump())  # For Pydantic v2
        .returning(UsageStatsModel)
    )

    result = await session.execute(stmt)
    await session.commit()

    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=500, detail="Failed to create usage stats")

    return RockdUsageStats(**row._mapping)
