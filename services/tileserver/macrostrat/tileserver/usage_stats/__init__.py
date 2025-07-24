from pathlib import Path
from typing import List

from buildpg import V, render
from fastapi import APIRouter, Request, Response
from timvt.resources.enums import MimeTypes

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
    )

    """Get a tile from the tileserver."""
    pool = request.app.state.pool

    if slug == "macrostrat":
        if "today" in request.query_params:
            query = __here__ / "queries" / "macrostrat_today.sql"
        else:
            query = __here__ / "queries" / "macrostrat.sql"
    else:
        if "today" in request.query_params:
            query = __here__ / "queries" / "rockd_today.sql"
        else:
            query = __here__ / "queries" / "rockd.sql"

    query = query.read_text()
    query = query.strip()
    if query.endswith(";"):
        query = query[:-1]

    q, p = render(query, **params)
    q = q.replace("textarray", "text[]")

    async with pool.acquire() as con:
        data = await con.fetchval(q, *p)

    return Response(data, media_type=MimeTypes.pbf.value)