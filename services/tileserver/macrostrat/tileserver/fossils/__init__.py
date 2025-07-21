from pathlib import Path

from buildpg import render
from fastapi import APIRouter, Request, Response
from timvt.resources.enums import MimeTypes

router = APIRouter()

__here__ = Path(__file__).parent


@router.get("/fossils/{z}/{x}/{y}")
async def rgeom(
    request: Request,
    z: int,
    x: int,
    y: int,
):
    """Get a tile from the tileserver."""
    pool = request.app.state.pool
    query = __here__ / "queries" / "fossils.sql"

    query = query.read_text()
    query = query.strip()
    if query.endswith(";"):
        query = query[:-1]

    params = {
        "z": z,
        "x": x,
        "y": y,
    }

    q, p = render(query, **params)
    q = q.replace("textarray", "text[]")

    async with pool.acquire() as con:
        data = await con.fetchval(q, *p)

    return Response(data, media_type=MimeTypes.pbf.value)