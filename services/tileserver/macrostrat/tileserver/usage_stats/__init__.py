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

    if slug != "macrostrat" and slug != "rockd":
        raise ValueError(
            "Invalid slug provided. Only 'macrostrat' and 'rockd' are supported."
        )

    where = (
        "AND date >= (NOW() - INTERVAL '24 hours')"
        if "today" in request.query_params
        else ""
    )

    query = f"""
        WITH
            tile AS (
            SELECT ST_TileEnvelope({z}, {x}, {y}) AS envelope,
                    tile_layers.geographic_envelope({x}, {y}, {z}, 0.01) AS envelope_4326
            ),
            points AS (
            SELECT
                id,
                tile_layers.tile_geom(
                ST_Intersection(
                    ST_SetSRID(ST_MakePoint(lng, lat), 4326),
                    envelope_4326
                ),
                envelope
                ) AS geom
            FROM usage_stats.{slug}_stats, tile
            WHERE
                lat IS NOT NULL AND lng IS NOT NULL
                AND ST_Intersects(
                ST_SetSRID(ST_MakePoint(lng, lat), 4326),
                envelope_4326
                )
                {where}
            )

            SELECT ST_AsMVT(
            points.*,
            'default',
            4096,
            'geom'
            ) AS mvt
        FROM points
    """

    q, p = render(query, **{})
    q = q.replace("textarray", "text[]")

    async with pool.acquire() as con:
        data = await con.fetchval(q, *p)

    return Response(data, media_type=MimeTypes.pbf.value)
