from asyncio import gather
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

    async with pool.acquire() as con:
        units_ = await run_layer_query(con, "units", z=z, x=x, y=y, mapsize=mapsize)
        lines_ = await run_layer_query(
            con, "lines", z=z, x=x, y=y, mapsize=mapsize, linesize=linesize
        )
    data = join_layers([units_, lines_])
    kwargs = {}
    kwargs.setdefault("media_type", MimeTypes.pbf.value)
    return Response(data, **kwargs)


def join_layers(layers):
    """Join tiles together."""
    return b"".join(layers)


async def run_layer_query(con, layer_name, **params):
    query = get_layer_sql(layer_name)
    q, p = render(query, layer_name=layer_name, **params)
    return await con.fetchval(q, *p)


def get_layer_sql(layer: str):
    units_query = __here__ / "queries" / "units.sql"

    q = units_query.read_text()
    q = q.strip()
    if q.endswith(";"):
        q = q[:-1]

    # Replace the envelope with the function call. Kind of awkward.
    q = q.replace(":envelope", "tile_utils.envelope(:x, :y, :z)")

    # Wrap with MVT creation
    return f"WITH feature_query AS ({q}) SELECT ST_AsMVT(feature_query, :layer_name) FROM feature_query"
