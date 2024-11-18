from pathlib import Path
from buildpg import render
from fastapi import APIRouter, Request, Response
from timvt.resources.enums import MimeTypes

router = APIRouter()

__here__ = Path(__file__).parent


@router.get("/checkins/{z}/{x}/{y}")
async def rgeom(
    request: Request,
    z: int,
    x: int,
    y: int,
):
    """Get a tile from the tileserver."""
    rockd_pool = request.app.state.rockd_pool
    async with rockd_pool.acquire() as con:
        data = await run_layer_query(
            con,
            "checkins",
            z=z,
            x=x,
            y=y,
        )
    kwargs = {}
    kwargs.setdefault("media_type", MimeTypes.pbf.value)
    return Response(data, **kwargs)


async def run_layer_query(con, layer_name, **params):
    query = get_layer_sql(layer_name)
    q, p = render(query, layer_name=layer_name, **params)
    try:
        return await con.fetchval(q, *p)
    except Exception as e:
        raise RuntimeError(f"Error executing layer query: {e}")


def get_layer_sql(layer: str):
    query = __here__ / "queries" / (layer + ".sql")

    q = query.read_text()
    q = q.strip()
    if q.endswith(";"):
        q = q[:-1]

    # Replace the envelope with the function call. Kind of awkward.
    q = q.replace(":envelope", "tile_utils.envelope(:x, :y, :z)")

    # Wrap with MVT creation
    return q
