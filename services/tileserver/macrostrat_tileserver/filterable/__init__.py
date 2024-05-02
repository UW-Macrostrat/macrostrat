from buildpg import render
from fastapi import APIRouter, Request, Response
from timvt.resources.enums import MimeTypes

router = APIRouter()


@router.get("/carto/{z}/{x}/{y}")
async def get_tile(request: Request, z: int, x: int, y: int):
    """Get a tile from the tileserver."""
    pool = request.app.state.pool
    q, p = render(
        "SELECT tile_layers.carto_slim(:x::integer, :y::integer, :z::integer, '{}') AS data;",
        z=z,
        x=x,
        y=y,
    )
    async with pool.acquire() as con:
        data = await con.fetchval(q, *p)
    kwargs = {}
    kwargs.setdefault("media_type", MimeTypes.pbf.value)
    return Response(data, **kwargs)
