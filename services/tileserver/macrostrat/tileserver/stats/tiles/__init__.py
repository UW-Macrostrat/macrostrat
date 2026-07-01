from pathlib import Path

from buildpg import render
from fastapi import APIRouter, Request

from macrostrat.tileserver_utils import VectorTileResponse, get_sql

__here__ = Path(__file__).parent

router = APIRouter()


@router.get("/{z}/{x}/{y}")
async def get_tile(request: Request, z: int, x: int, y: int):
    """Tile-request density heatmap (source-layer `requests`) built from
    tileserver_stats.location_index — shows where tiles are requested most."""
    pool = request.app.state.pool

    sql = get_sql(__here__ / "heatmap.sql")
    query, params = render(sql, z=z, x=x, y=y)

    async with pool.acquire() as con:
        data = await con.fetchval(query, *params)
        return VectorTileResponse(data)
