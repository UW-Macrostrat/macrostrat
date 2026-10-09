"""
Tile cache management CLI
"""

from typing import Optional

from typer import Argument, Exit, Option, Typer, confirm

from macrostrat.core.database import get_database

cli = Typer(name="cache", help="Tile cache management")

#: How long the admin token the CLI signs for the flush is good for.
_FLUSH_TOKEN_TTL_SECONDS = 300

#: Profiles holding carto tiles, as in the tileserver's `/cache/refresh/carto`.
_CARTO_PROFILES = ["carto", "carto-slim", "carto-image", "map-carto", "map-carto-full"]

#: Half the width of the Web Mercator square, in metres.
_MERCATOR_HALF = 20037508.342789244

# Each map's Web Mercator extent, over the zooms of its own scale band.
_MAP_EXTENTS_SQL = """
WITH band AS (
  SELECT
    scale::text AS scale,
    min_zoom,
    coalesce(lead(min_zoom) OVER (ORDER BY min_zoom) - 1, 14) AS max_zoom
  FROM map_bounds.scale_band
)
SELECT
  s.slug,
  ST_XMin(f.ext) AS minx,
  ST_YMin(f.ext) AS miny,
  ST_XMax(f.ext) AS maxx,
  ST_YMax(f.ext) AS maxy,
  coalesce(b.min_zoom, 0) AS min_zoom,
  coalesce(b.max_zoom, 14) AS max_zoom
FROM maps.sources s
LEFT JOIN band b ON b.scale = s.scale
CROSS JOIN LATERAL (
  SELECT ST_Transform(
    -- Web Mercator ends at about 85.0511 degrees.
    ST_ClipByBox2D(
      ST_SetSRID(ST_Extent(geometry)::geometry, 4326),
      ST_MakeEnvelope(-180, -85.0511, 180, 85.0511)::box2d
    ),
    3857
  ) AS ext
  FROM map_bounds_topology.map_face
  WHERE map_id = s.source_id
) f
WHERE s.source_id = ANY(:source_ids)
  AND NOT coalesce(ST_IsEmpty(f.ext), true)
ORDER BY s.source_id
"""

# Constant bounds per zoom, so the planner can range-scan `tile_pkey` on x.
_DELETE_TILE_RANGE_SQL = """
WITH deleted AS (
  DELETE FROM tile_cache.tile
  WHERE z = :z
    AND x BETWEEN :x0 AND :x1
    AND y BETWEEN :y0 AND :y1
    AND profile = ANY(:profiles)
  RETURNING 1
)
SELECT count(*) FROM deleted
"""


@cli.command(name="clear")
def clear_cache(
    maps: Optional[list[str]] = Argument(
        None,
        help="Only expire tiles covering these maps: slugs, source ids, or slug"
        " globs (e.g. 'ngs-*')",
    ),
    exclude: Optional[list[str]] = Option(
        None,
        "--exclude",
        help="Slug globs to leave out of the selection (e.g. 'arizona-adgm-*')",
    ),
    yes: bool = Option(False, "--yes", "-y", help="Skip the confirmation prompt"),
    varnish: bool = Option(
        True,
        "--varnish/--no-varnish",
        help="Also flush Varnish, the cache in front of the tileserver",
    ),
):
    """Clear the tile cache: the database's, then Varnish's.

    The database cache (`tile_cache.tile`) is truncated rather than deleted from.
    DELETE leaves the space allocated to the relation for autovacuum to reclaim
    later and writes WAL in proportion to the rows removed -- on a volume that is
    already full it frees nothing while making the immediate problem worse, which
    is how the September 2026 outage deepened. TRUNCATE returns the space
    immediately and writes almost no WAL. The cost is a brief ACCESS EXCLUSIVE
    lock: in-flight tile requests block until it completes.

    Varnish is flushed second, so it cannot refill from the rows just removed.
    It goes through api-v3's admin-only `/cache/flush`, the route the website's
    cache page uses, so the same command works on every environment: the API
    knows where its Varnish is, and the CLI proves admin by signing a short-lived
    token with the environment's `token_signing_key`.

    Given maps, only the carto tiles covering each one's extent, across its own
    scale band, are deleted, and Varnish is flushed wholesale.
    """
    from macrostrat.core.config import settings

    db = get_database()

    also = ""
    if varnish:
        also = f", then flush Varnish at {settings.base_url}"

    if maps:
        _clear_maps(db, settings, maps, exclude, yes, varnish, also)
        return

    tiles, size = db.run_query(
        """SELECT
            greatest(
                (SELECT reltuples FROM pg_class
                 WHERE oid = 'tile_cache.tile'::regclass),
                0
            )::bigint AS tiles,
            pg_size_pretty(pg_total_relation_size('tile_cache.tile')) AS size"""
    ).one()

    if not yes:
        confirm(
            f"Truncate tile_cache.tile (about {tiles:,} tiles, {size}){also}? "
            "Tile requests will block briefly and the cache will be cold.",
            abort=True,
        )

    db.run_query("TRUNCATE tile_cache.tile")
    db.session.commit()

    print(f"Truncated tile_cache.tile — reclaimed {size} (about {tiles:,} tiles)")

    if not varnish:
        return
    try:
        banned = flush_varnish(settings)
    except FlushError as err:
        print(f"Varnish was not flushed: {err}")
        raise Exit(1)
    print(f"Flushed Varnish ({banned})")


def _clear_maps(db, settings, selectors, exclude, yes, varnish, also):
    from macrostrat.map_integration.utils.map_info import resolve_maps

    selected = resolve_maps(db, selectors, exclude=exclude)
    if not yes:
        names = ", ".join(m.slug for m in selected[:5])
        if len(selected) > 5:
            names += f", and {len(selected) - 5} more"
        confirm(
            f"Expire cached carto tiles covering {len(selected)} map(s)"
            f" ({names}){also}?",
            abort=True,
        )

    deleted = expire_map_tiles(db, [m.id for m in selected])
    print(f"Deleted {deleted:,} tiles from tile_cache.tile")

    if not varnish:
        return
    try:
        banned = flush_varnish(settings)
    except FlushError as err:
        print(f"Varnish was not flushed: {err}")
        raise Exit(1)
    print(f"Flushed Varnish ({banned})")


def expire_map_tiles(db, source_ids: list[int]) -> int:
    """Delete cached carto tiles covering each map's extent across its scale band."""
    profiles = (
        db.run_query(
            "SELECT id FROM tile_cache.profile WHERE name = ANY(:names)",
            dict(names=_CARTO_PROFILES),
        )
        .scalars()
        .all()
    )
    extents = db.run_query(_MAP_EXTENTS_SQL, dict(source_ids=source_ids)).all()

    total = 0
    for e in extents:
        for z in range(e.min_zoom, e.max_zoom + 1):
            x0, y0 = tile_index(e.minx, e.maxy, z)
            x1, y1 = tile_index(e.maxx, e.miny, z)
            params = dict(z=z, x0=x0, x1=x1, y0=y0, y1=y1, profiles=profiles)
            total += db.run_query(_DELETE_TILE_RANGE_SQL, params).scalar()
        # One transaction per map keeps each WAL burst bounded.
        db.session.commit()
    return total


def tile_index(x: float, y: float, z: int) -> tuple[int, int]:
    """Column and row of the zoom-`z` tile holding a Web Mercator point."""
    n = 2**z
    size = 2 * _MERCATOR_HALF / n
    col = int((x + _MERCATOR_HALF) // size)
    row = int((_MERCATOR_HALF - y) // size)
    return min(max(col, 0), n - 1), min(max(row, 0), n - 1)


class FlushError(Exception):
    pass


def flush_varnish(settings) -> str:
    """Ban everything in the environment's Varnish, through api-v3.

    Returns the ban expression the API applied.
    """
    from datetime import datetime, timedelta, timezone

    import requests
    from jose import jwt

    # The local stack's certificate is signed by a local authority that only the
    # system trust store knows.
    try:
        import truststore

        truststore.inject_into_ssl()
    except ImportError:
        pass

    key = settings.resolve_token_signing_key()
    if not key:
        raise FlushError("this environment has no token_signing_key to sign with")

    # What api-v3's `require_admin` accepts: a session JWT with PostgREST's admin
    # role, sent in the `access_token` header as the website's cookie would be.
    expires = datetime.now(timezone.utc) + timedelta(seconds=_FLUSH_TOKEN_TTL_SECONDS)
    token = jwt.encode(
        {"sub": "macrostrat-cli", "role": "web_admin", "exp": expires},
        key,
        algorithm="HS256",
    )

    url = settings.base_url.rstrip("/") + "/api/v3/cache/flush"
    try:
        resp = requests.post(
            url, headers={"access_token": f"Bearer {token}"}, json={}, timeout=30
        )
    except requests.RequestException as err:
        raise FlushError(f"could not reach {url}: {err}")
    if resp.status_code >= 400:
        raise FlushError(f"{url} answered {resp.status_code}: {resp.text[:200]}")
    return resp.json().get("banned", "all objects")
