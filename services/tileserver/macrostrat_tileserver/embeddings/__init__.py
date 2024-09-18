from typing import List
from pathlib import Path

from buildpg import V, render
from fastapi import APIRouter, Request, Query

from ..utils import scales_for_zoom, get_layer_sql, VectorTileResponse


router = APIRouter()

__here__ = Path(__file__).parent


@router.get("/{model}/{z}/{x}/{y}")
async def get_tile(
    request: Request,
    model: str,
    z: int,
    x: int,
    y: int,
    lithology: List[str] = Query(None)
):
    """Get a tile from the tileserver."""
    pool = request.app.state.pool

    mapsize, linesize = scales_for_zoom(z)

    params = dict(
        z=z,
        x=x,
        y=y,
        mapsize=mapsize,
        linesize=linesize,
    )

    async with pool.acquire() as con:
        units_ = await run_layer_query(
            con,
            "units",
            compilation=V("carto.polygons"),
            **params
        )
        lines_ = await run_layer_query(
            con,
            "lines",
            compilation=V("carto.lines"),
            **params
        )

    return VectorTileResponse(units_, lines_)


async def run_layer_query(con, layer_name, **params):
    query = get_layer_sql(layer_name)
    q, p = render(query, layer_name=layer_name, **params)
    return await con.fetchval(q, *p)


