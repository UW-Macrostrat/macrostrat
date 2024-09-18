from typing import List
from pathlib import Path

from buildpg import V, render, Empty, funcs, SqlBlock
from fastapi import APIRouter, Request, Response, Query
from timvt.resources.enums import MimeTypes

from ..utils import scales_for_zoom, get_layer_sql, join_layers


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

    data = join_layers([units_, lines_])
    kwargs = {}
    kwargs.setdefault("media_type", MimeTypes.pbf.value)
    return Response(data, **kwargs)


def get_lithology_clause(lithologies: List[str]):

    LITHOLOGY_COLUMNS = [
        "liths.lith_group",
        "liths.lith_class",
        "liths.lith_type",
        "liths.lith",
    ]

    if lithologies is None or len(lithologies) == 0:
        return Empty()

    return Empty() & funcs.OR(*map(lambda l: V(l) == funcs.any(funcs.cast(lithologies, "textarray")), LITHOLOGY_COLUMNS))


async def run_layer_query(con, layer_name, **params):
    query = get_layer_sql(layer_name)
    q, p = render(query, layer_name=layer_name, **params)

    # Overcomes a shortcoming in buildpg that deems casting to an array as unsafe
    # https://github.com/samuelcolvin/buildpg/blob/e2a16abea5c7607b53c501dbae74a5765ba66e15/buildpg/components.py#L21
    q = q.replace("textarray", "text[]")

    return await con.fetchval(q, *p)


