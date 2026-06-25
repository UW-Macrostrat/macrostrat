from pathlib import Path

from buildpg import render
from fastapi import APIRouter, Request

from macrostrat.tileserver_utils import VectorTileResponse

from ..utils import get_sql

__here__ = Path(__file__).parent

router = APIRouter()


@router.get("/{z}/{x}/{y}")
async def get_tile(
    request: Request,
    z: int,
    x: int,
    y: int,
):
    """Get a tile from the tileserver."""
    pool = request.app.state.pool

    sql = get_sql(__here__ / "carto-dynamic.sql")
    query, params = render(sql, z=z, x=x, y=y)

    async with pool.acquire() as con:
        data = await con.fetchval(query, *params)
        return VectorTileResponse(data)
