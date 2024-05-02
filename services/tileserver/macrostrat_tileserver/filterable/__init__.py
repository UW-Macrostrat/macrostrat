from pathlib import Path

from buildpg import render
from fastapi import APIRouter, Request, Response
from timvt.resources.enums import MimeTypes

router = APIRouter()

__here__ = Path(__file__).parent


@router.get("/carto/{z}/{x}/{y}")
async def get_tile(request: Request, z: int, x: int, y: int):
    """Get a tile from the tileserver."""
    pool = request.app.state.pool

    units_query = __here__ / "queries" / "units.sql"

    q = units_query.read_text()
    q = q.strip()
    if q.endswith(";"):
        q = q[:-1]

    # Replace the envelope with the function call
    q = q.replace(":envelope", "tile_utils.envelope(:x, :y, :z)")

    # Wrap with MVT creation
    q1 = f"WITH feature_query AS ({q}) SELECT ST_AsMVT(feature_query, :layer_name) FROM feature_query"

    if z < 3:
        # Select from carto.tiny table
        mapsize = "tiny"
        linesize = ["tiny"]
    elif z < 6:
        mapsize = "small"
        linesize = ["tiny", "small"]
    elif z < 9:
        mapsize = "medium"
        linesize = ["small", "medium"]
    else:
        mapsize = "large"
        linesize = ["medium", "large"]

    q, p = render(q1, z=z, x=x, y=y, layer_name="units", mapsize=mapsize)
    async with pool.acquire() as con:
        data = await con.fetchval(q, *p)
    kwargs = {}
    kwargs.setdefault("media_type", MimeTypes.pbf.value)
    return Response(data, **kwargs)
