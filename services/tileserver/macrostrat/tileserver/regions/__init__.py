"""Regions: named areas such as physiographic provinces, basins and ice limits.

Stored as `geologic_boundaries.boundaries` until the tables are renamed; the
routes and tile properties already use the "region" vocabulary.
"""

from pathlib import Path
from typing import Annotated, Optional

from buildpg import render
from fastapi import APIRouter, Query, Request, Response

from macrostrat.tileserver_utils import MimeTypes

router = APIRouter()

LAYER_NAME = "regions"

_query = (Path(__file__).parent / "queries" / "regions.sql").read_text().strip()


def regions_sql(*, by_source: bool) -> str:
    where = "true"
    if by_source:
        where = "b.source_id = :source_id"
    q = _query.replace(":where", where)
    return (
        f"WITH feature_query AS ({q})"
        " SELECT ST_AsMVT(feature_query, :layer_name) FROM feature_query"
        " WHERE geom IS NOT NULL"
    )


# Under `/tiles`: a bare `/regions/{z}/{x}/{y}` is taken by the layer catalog.
@router.get("/tiles/{z}/{x}/{y}")
async def regions_tile(
    request: Request,
    z: int,
    x: int,
    y: int,
    source_id: Annotated[
        Optional[int], Query(description="Only regions from this source")
    ] = None,
):
    """Regions as vector tiles, in a `regions` layer."""
    params = dict(z=z, x=x, y=y, layer_name=LAYER_NAME)
    if source_id is not None:
        params["source_id"] = source_id
    q, p = render(regions_sql(by_source=source_id is not None), **params)
    async with request.app.state.pool.acquire() as con:
        data = await con.fetchval(q, *p)
    return Response(data, media_type=MimeTypes.pbf.value)
