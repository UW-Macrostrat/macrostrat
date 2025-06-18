from pathlib import Path

from buildpg import render
from fastapi import APIRouter, Request, Response

from macrostrat.tileserver_utils import MimeTypes
from macrostrat.utils import get_logger

router = APIRouter()

__here__ = Path(__file__).parent

log = get_logger(__name__)


@router.get("/{organization}/{type}/tiles/{z}/{x}/{y}")
async def integrations_tile(
    request: Request,
    organization: str,
    type: str,
    z: int,
    x: int,
    y: int,
):
    """Get a tile from the tileserver."""
    pool = request.app.state.pool
    async with pool.acquire() as con:
        data = await run_layer_query(
            con,
            "integrations",
            organization=organization,
            type=type,
            z=z,
            x=x,
            y=y,
        )
    kwargs = {}
    kwargs.setdefault("media_type", MimeTypes.pbf.value)
    return Response(data, **kwargs)


async def run_layer_query(con, layer_name, **params):
    query = get_layer_sql(layer_name)
    q, p = render(query, layer_name="default", **params)
    return await con.fetchval(q, *p)


def get_layer_sql(layer: str, layer_name="default"):
    query = __here__ / "queries" / (layer + ".sql")

    q = query.read_text()
    q = q.strip()
    if q.endswith(";"):
        q = q[:-1]

    # Replace the envelope with the function call. Kind of awkward.
    q = q.replace(":envelope", "tile_utils.envelope(:x, :y, :z)")

    # Wrap with MVT creation
    return f"WITH feature_query AS ({q}) SELECT ST_AsMVT(feature_query, :layer_name) FROM feature_query"
