from typing import List
from pathlib import Path

from buildpg import V, render, SqlBlock
from fastapi import APIRouter, Request, Response, Query
from timvt.resources.enums import MimeTypes
from ..utils import scales_for_zoom, MapCompilation, get_layer_sql, join_layers

from macrostrat.utils import get_logger

log = get_logger(__name__)

router = APIRouter()

__here__ = Path(__file__).parent


@router.get("/{compilation}/{z}/{x}/{y}")
async def get_tile(
        request: Request,
        compilation: MapCompilation,
        z: int,
        x: int,
        y: int,
        lithology: List[str] = Query(None)
):
    """Get a tile from the tileserver."""
    pool = request.app.state.pool

    mapsize, linesize = scales_for_zoom(z)

    compilation_name = compilation.value
    where_lithology = get_lithology_clause(lithology)

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
            compilation=V(compilation_name + ".polygons"),
            where_lithology=where_lithology,
            lithology=lithology,
            **params
        )
        lines_ = await run_layer_query(
            con,
            "lines",
            compilation=V(compilation_name + ".lines"),
            **params
        )
    data = join_layers([units_, lines_])
    kwargs = {}
    kwargs.setdefault("media_type", MimeTypes.pbf.value)
    return Response(data, **kwargs)


def get_lithology_clause(lithology: List[str]):
    if lithology is None or len(lithology) == 0:
        return "true"

    LITHOLOGY_COLUMNS = [
        "lith_group",
        "lith_class",
        "lith_type",
        "lith",
    ]

    cols = [f"liths.{col}::text = ANY(:lithology)" for col in LITHOLOGY_COLUMNS]
    q = " OR ".join(cols)
    return f"({q})"


async def run_layer_query(con, layer_name, **params):
    query = get_layer_sql( __here__ / "queries",  layer_name)
    lith_clause = get_lithology_clause(params.get("lithology"))
    query = query.replace(":where_lithology", lith_clause)

    q, p = render(query, layer_name=layer_name, **params)

    # Overcomes a shortcoming in buildpg that deems casting to an array as unsafe
    # https://github.com/samuelcolvin/buildpg/blob/e2a16abea5c7607b53c501dbae74a5765ba66e15/buildpg/components.py#L21
    log.info(q)

    return await con.fetchval(q, *p)
