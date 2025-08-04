from pathlib import Path
from typing import List

from buildpg import V, render
from fastapi import APIRouter, Request

from macrostrat.tileserver_utils import VectorTileResponse
from macrostrat.utils import get_logger

from ..utils import get_layer_sql

log = get_logger(__name__)

router = APIRouter()

__here__ = Path(__file__).parent


@router.get("/{slug}/{z}/{x}/{y}")
async def get_tile(
    request: Request,
    slug: str,
    z: int,
    x: int,
    y: int,
):
    """Get a tile from the tileserver."""
    pool = request.app.state.pool

    params = dict(
        z=z,
        x=x,
        y=y,
        slug=slug,
    )

    async with pool.acquire() as con:
        units_ = await run_layer_query(
            con,
            "units",
            compilation=V(compilation_name + ".polygons"),
            lithology=lithology,
            **params,
        )
        lines_ = await run_layer_query(
            con, "lines", compilation=V(compilation_name + ".lines"), **params
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
    query = get_layer_sql(__here__ / "queries", layer_name)
    if ":where_lithology" in query:
        lith_clause = build_lithology_clause(params.get("lithology"))
        query = query.replace(":where_lithology", lith_clause)
    q, p = render(query, layer_name=layer_name, **params)
    return await con.fetchval(q, *p)
