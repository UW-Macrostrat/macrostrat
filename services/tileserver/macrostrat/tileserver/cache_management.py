"""Cache management routes — expire tiles from Varnish (L1) and the database (L2).

L2 (the ``tile_cache.tile`` table) is expired precisely by region: a bbox maps
to a tile set via ``tile_utils.containing_tiles`` and those rows are deleted,
forcing regeneration from the data store on next request.

L1 (Varnish) is only a thin memory cache in front of L2, so we don't bother
with precise regional bans — any invalidation simply flushes all carto tiles
with one ``req.url`` ban.  A cold L1 re-fetches from L2 cheaply, except in the
region we just expired from L2 (which is exactly what we want regenerated).
"""

from os import environ
from typing import Optional

import httpx
from buildpg import render
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from macrostrat.tileserver_utils import VectorTileResponse
from macrostrat.utils import get_logger

log = get_logger(__name__)

router = APIRouter()

# Profiles to expire on cache invalidation (rotated paleo layer excluded)
_CARTO_PROFILES = ["carto", "carto-slim", "carto-image"]

_VARNISH_URL = environ.get("VARNISH_URL", "http://tileserver_cache:8000")

# Carto scale band → [min_zoom, max_zoom], mirroring tile_layers.carto_slim.
# A source is expired only across its own scale band. Unknown scales fall back
# to the full zoom range.
_SCALE_BANDS = {
    "tiny": (0, 2),
    "small": (3, 5),
    "medium": (6, 8),
    "large": (9, 14),
}
_FULL_RANGE = (0, 14)


class InvalidationRequest(BaseModel):
    # Region mode: an explicit bbox or a layer slug, expired across [min,max] zoom.
    bbox: Optional[list[float]] = None  # [minx, miny, maxx, maxy] in WGS84
    layer_slug: Optional[str] = None
    min_zoom: int = 0
    max_zoom: int = 14
    # Map mode: one expiry per source, each across its own scale band.
    source_ids: Optional[list[int]] = None


# Bbox of a map_face set as a [minx, miny, maxx, maxy] float array, built from
# an ``ST_Extent(geometry) AS ext`` subquery.
_BBOX_ARRAY = (
    "ARRAY[ST_XMin(ext)::float, ST_YMin(ext)::float, "
    "ST_XMax(ext)::float, ST_YMax(ext)::float]"
)


@router.post("/invalidate")
async def invalidate_cache(body: InvalidationRequest, request: Request):
    """Expire tiles from L1 (Varnish) and L2 (database) caches.

    Map mode (``source_ids``): each source is expired across its own scale band.
    Region mode (``bbox`` or ``layer_slug``): expired across the given zoom range.
    L1 is flushed wholesale once at the end either way.
    """
    pool = request.app.state.pool

    if body.source_ids:
        deleted_l2 = await _delete_l2_for_sources(pool, body.source_ids)
    else:
        bbox = body.bbox
        if bbox is None and body.layer_slug is not None:
            bbox = await _bbox_for_layer(pool, body.layer_slug)
        if bbox is None:
            raise HTTPException(
                status_code=400,
                detail="Provide source_ids, bbox, or layer_slug",
            )
        async with pool.acquire() as conn:
            deleted_l2 = await _delete_l2_tiles(
                conn, bbox, body.min_zoom, body.max_zoom
            )

    flushed_l1 = await _flush_l1_carto()
    return {"deleted_l2": deleted_l2, "flushed_l1": flushed_l1}


# ─── Footprints tile layer (for the cache UI) ─────────────────────────────────
# Shows the maps composited into the carto layer at a given zoom, picking the
# scale band the same way tile_layers.carto_slim does. Two modes: "all" (full
# source footprints) and "active" (the realized topological faces actually
# rendered). `dz` shifts the band so footprints appear at a lower zoom than the
# maps themselves display, making them easier to click before they shrink away.


def _scale_band(z: int) -> str:
    if z < 3:
        return "tiny"
    if z < 6:
        return "small"
    if z < 9:
        return "medium"
    return "large"


_FOOTPRINTS_TILE = """
    WITH tile AS (
        SELECT
            ST_TileEnvelope(:z, :x, :y) AS mercator_bbox,
            tile_layers.geographic_envelope(:x, :y, :z, 0.01) AS projected_envelope
    ), feats AS (
        {source}
    )
    SELECT ST_AsMVT(feats, 'footprints', 4096, 'geom') FROM feats
"""

# Full source footprints for the band.
_FOOTPRINTS_ALL = """
    SELECT s.source_id, s.name, s.slug, s.scale,
           tile_layers.tile_geom(
               ST_Intersection(ma.geometry, tile.projected_envelope),
               tile.mercator_bbox
           ) AS geom
    FROM map_bounds.map_area ma
    JOIN tile ON ST_Intersects(ma.geometry, tile.projected_envelope)
    JOIN maps.sources s ON ma.id = s.source_id
    WHERE s.scale = :band AND s.status_code = 'active'
"""

# Realized topological faces actually rendered for the band's compilation.
_FOOTPRINTS_ACTIVE = """
    SELECT s.source_id, s.name, s.slug, s.scale,
           tile_layers.tile_geom(
               ST_Intersection(f.geometry, tile.projected_envelope),
               tile.mercator_bbox
           ) AS geom
    FROM map_bounds_topology.map_face f
    JOIN map_bounds.map_layer ml ON f.map_layer = ml.id
    JOIN tile ON ST_Intersects(f.geometry, tile.projected_envelope)
    JOIN maps.sources s ON f.map_id = s.source_id
    WHERE ml.slug = :band AND s.status_code = 'active'
"""


@router.get("/footprints/{z}/{x}/{y}")
async def footprints_tile(
    request: Request, z: int, x: int, y: int, mode: str = "all", dz: int = 0
):
    """Vector tile of carto map footprints for the band visible at zoom z+dz."""
    band = _scale_band(z + dz)
    source = _FOOTPRINTS_ACTIVE if mode == "active" else _FOOTPRINTS_ALL
    q, p = render(_FOOTPRINTS_TILE.format(source=source), z=z, x=x, y=y, band=band)
    async with request.app.state.pool.acquire() as conn:
        data = await conn.fetchval(q, *p)
    return VectorTileResponse(data or b"", headers={"cache-control": "no-cache"})


# Per-source scale + map_face bbox, for map-mode expiry.
_SOURCE_INFO_SQL = f"""
    SELECT s.scale, {_BBOX_ARRAY} AS bbox
    FROM maps.sources s
    LEFT JOIN LATERAL (
        SELECT ST_Extent(geometry) AS ext
        FROM map_bounds_topology.map_face
        WHERE map_id = s.source_id
    ) f ON true
    WHERE s.source_id = :source_id
"""


async def _delete_l2_for_sources(pool, source_ids: list[int]) -> int:
    """Expire each source across its own scale band; return total tiles deleted."""
    total = 0
    async with pool.acquire() as conn:
        for source_id in source_ids:
            q, p = render(_SOURCE_INFO_SQL, source_id=source_id)
            row = await conn.fetchrow(q, *p)
            # No faces compiled for this source → nothing cached to expire.
            if row is None or row["bbox"] is None:
                continue
            min_zoom, max_zoom = _SCALE_BANDS.get(row["scale"], _FULL_RANGE)
            total += await _delete_l2_tiles(conn, row["bbox"], min_zoom, max_zoom)
    return total


async def _bbox_for_layer(pool, layer_slug: str):
    q, p = render(
        f"""SELECT {_BBOX_ARRAY}
            FROM (
                SELECT ST_Extent(geometry) AS ext
                FROM map_bounds_topology.map_face
                WHERE map_layer = map_bounds.layer_id(:slug)
            ) t""",
        slug=layer_slug,
    )
    async with pool.acquire() as conn:
        return await conn.fetchval(q, *p)


async def _delete_l2_tiles(
    conn, bbox: list[float], min_zoom: int, max_zoom: int
) -> int:
    """Delete matching tiles from tile_cache.tile (on `conn`), return row count."""
    minx, miny, maxx, maxy = bbox
    q, p = render(
        """WITH tiles AS (
               SELECT x, y, z
               FROM tile_utils.containing_tiles(
                   ST_MakeEnvelope(:minx, :miny, :maxx, :maxy, 4326)
               )
               WHERE z BETWEEN :min_zoom AND :max_zoom
           )
           DELETE FROM tile_cache.tile tc
           USING tiles t, tile_cache.profile p
           WHERE tc.x = t.x
             AND tc.y = t.y
             AND tc.z = t.z
             AND tc.profile = p.id
             AND p.name = ANY(:profiles)""",
        minx=minx,
        miny=miny,
        maxx=maxx,
        maxy=maxy,
        min_zoom=min_zoom,
        max_zoom=max_zoom,
        profiles=_CARTO_PROFILES,
    )
    result = await conn.execute(q, *p)
    # asyncpg returns "DELETE N" as a status string
    return int(result.split()[-1]) if result else 0


async def _flush_l1_carto() -> bool:
    """Flush the entire carto L1 (Varnish) cache via a single URL ban.

    L1 is only a memory cache in front of L2; a cold L1 simply re-fetches from
    L2 (cheap, except in the region we just expired from L2).  So rather than
    computing a precise per-region ban, we drop all carto tiles wholesale —
    far simpler, and the cost is just a transient re-population from L2.
    """
    profile_alt = "|".join(_CARTO_PROFILES)
    ban_expr = f'req.url ~ "^/(?:{profile_alt})/"'

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.request(
                "BAN",
                _VARNISH_URL + "/",
                headers={"X-Ban-Expression": ban_expr},
                timeout=5.0,
            )
            resp.raise_for_status()
    except httpx.HTTPError as exc:
        log.warning("Varnish BAN failed (L2 deletion still applied): %s", exc)
        return False

    return True
