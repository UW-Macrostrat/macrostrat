from pathlib import Path

from buildpg import render
from fastapi import APIRouter, Request, Response
from timvt.resources.enums import MimeTypes

router = APIRouter()

__here__ = Path(__file__).parent


@router.get("/bounds/{z}/{x}/{y}")
async def rgeom(
    request: Request,
    z: int,
    x: int,
    y: int,
):
    """Get a tile from the tileserver."""
    pool = request.app.state.pool

    async with pool.acquire() as con:
        data = await run_layer_query(
            con,
            "bounds",
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

    # Overcomes a shortcoming in buildpg that deems casting to an array as unsafe
    # https://github.com/samuelcolvin/buildpg/blob/e2a16abea5c7607b53c501dbae74a5765ba66e15/buildpg/components.py#L21
    q = q.replace("textarray", "text[]")

    return await con.fetchval(q, *p)


def get_layer_sql(layer: str):
    query = __here__ / "queries" / (layer + ".sql")
    q = query.read_text()
    q = q.strip()
    if q.endswith(";"):
        q = q[:-1]

    # Replace the envelope with the function call. Kind of awkward.
    q = q.replace(":envelope", "tile_utils.envelope(:x, :y, :z)")

    # Wrap with MVT creation
    return f"WITH feature_query AS ({q}) SELECT ST_AsMVT(feature_query, :layer_name) FROM feature_query"
