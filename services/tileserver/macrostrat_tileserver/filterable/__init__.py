from pathlib import Path
from typing import List

from buildpg import V, render
from fastapi import APIRouter, Request, Query
from macrostrat.utils import get_logger

from ..utils import scales_for_zoom, MapCompilation, get_layer_sql, VectorTileResponse

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
            lithology=lithology,
            **params
        )
        lines_ = await run_layer_query(
            con,
            "lines",
            compilation=V(compilation_name + ".lines"),
            **params
        )
    return VectorTileResponse(units_, lines_)

def build_lithology_clause(lithology: List[str]):
    """Build a WHERE clause to filter by lithology."""
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
    if ":where_lithology" in query:
        lith_clause = build_lithology_clause(params.get("lithology"))
        query = query.replace(":where_lithology", lith_clause)
    q, p = render(query, layer_name=layer_name, **params)
    return await con.fetchval(q, *p)
