"""Regions: named areas such as physiographic provinces, basins and ice limits.

Stored as `geologic_boundaries.boundaries` until the tables are renamed. These
routes describe regions; their shapes are drawn from the tileserver's
`/regions/tiles`, and API v2's `/boundaries` still returns one as GeoJSON.
"""

from pathlib import Path
from typing import Annotated, Optional

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import text

from api.database import DatabaseDep

from .models import Region, RegionDetail, RegionSource, RegionSourceSummary

router = APIRouter(prefix="/regions", tags=["regions"])

_queries = Path(__file__).parent / "queries"


def _query(name: str):
    return text((_queries / f"{name}.sql").read_text())


@router.get("", summary="List regions")
async def list_regions(
    database: DatabaseDep,
    source_id: Annotated[
        Optional[int], Query(description="Only regions from this source")
    ] = None,
) -> list[Region]:
    """Every region, without geometry or description."""
    async with database.async_connection() as conn:
        res = await conn.execute(_query("regions"), dict(source_id=source_id))
        return [Region(**row) for row in res.mappings()]


@router.get("/sources", summary="List the datasets regions come from")
async def list_sources(database: DatabaseDep) -> list[RegionSourceSummary]:
    """Declared before `/{region_id}` so `sources` is not read as an id."""
    async with database.async_connection() as conn:
        res = await conn.execute(_query("sources"))
        return [RegionSourceSummary(**row) for row in res.mappings()]


@router.get("/{region_id}", summary="Show a region")
async def get_region(region_id: int, database: DatabaseDep) -> RegionDetail:
    """One region with its description and the citation for its source."""
    async with database.async_connection() as conn:
        res = await conn.execute(_query("region"), dict(region_id=region_id))
        row = res.mappings().first()
    if row is None:
        raise HTTPException(404, f"No region with id {region_id}")
    source = None
    if row["source_name"] is not None:
        source = RegionSource(**{**row, "name": row["source_name"]})
    return RegionDetail(**row, source=source)
