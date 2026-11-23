"""Admin-only reads of the `usage_stats` schema, for the website's usage page.

Request counts reveal who embeds our tiles and which maps they view, so every
route here is gated on `require_admin`. Tile routes sit under `/tiles` rather
than `/tileserver`: the services are merging into one API.

`bots` chooses between organic traffic (`exclude`, the default), everything,
or only the known automated clients the harvester tags `is_bot`.
"""

from datetime import date, datetime, timedelta
from typing import Annotated, Literal, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import text

from api.database import DatabaseDep
from api.presumed_bots import long_term_trend, presumed_bots
from api.routes.security import require_admin

router = APIRouter(
    prefix="/usage-stats",
    tags=["Usage stats"],
    dependencies=[Depends(require_admin)],
)

Bots = Literal["exclude", "include", "only"]
Bin = Literal["day", "week", "month"]

StartQuery = Annotated[Optional[date], Query(description="First day, inclusive")]
EndQuery = Annotated[Optional[date], Query(description="Last day, inclusive")]
BotsQuery = Annotated[Bots, Query(description="Known automated clients")]
BinQuery = Annotated[Bin, Query(description="Width of each point in the series")]

_IN_RANGE = """
  (CAST(:start AS date) IS NULL OR date >= CAST(:start AS date))
  AND (CAST(:end AS date) IS NULL OR date < CAST(:end AS date) + 1)
"""

_BOTS = """
  (CAST(:bots AS text) = 'include' OR is_bot = (CAST(:bots AS text) = 'only'))
"""

# Empty bins come back as rows of nulls, so a chart draws outages as gaps.
_FILL_BINS = """
bins AS (
  SELECT generate_series(
    min(bin), max(bin), CAST('1 ' || CAST(:bin AS text) AS interval)
  ) AS bin
  FROM counts
)
"""


def _params(start, end, bots="include", **extra) -> dict:
    return {"start": start, "end": end, "bots": bots, **extra}


class PipelineStatus(BaseModel):
    pipeline: str
    n_objects: int
    n_matched: Optional[int] = None
    last_run: Optional[datetime] = None
    #: Modification time of the newest log object captured.
    newest_log: Optional[datetime] = None


STATUS = text("""
SELECT pipeline,
       count(*) AS n_objects,
       sum(num_matched)::bigint AS n_matched,
       max(processed_at) AS last_run,
       max(last_modified) AS newest_log
FROM usage_stats.processed_logs
GROUP BY pipeline
ORDER BY pipeline
""")


@router.get("/status")
async def get_status(database: DatabaseDep) -> list[PipelineStatus]:
    """Capture freshness per pipeline, as `macrostrat usage-stats status` shows it."""
    async with database.async_connection() as conn:
        rows = (await conn.execute(STATUS)).mappings().all()
    return [PipelineStatus(**row) for row in rows]


class RequestsBin(BaseModel):
    date: date
    #: Requests from clients not tagged as bots, presumed bots included.
    organic: Optional[int] = None
    bot: Optional[int] = None
    #: The part of `organic` presumed automated (see `api.presumed_bots`).
    presumed_bot: Optional[int] = None
    #: Organic requests expected from the long-term trend, bot phases aside.
    trend: Optional[int] = None
    #: False for rows migrated from the pre-2026 direct-push logger.
    new_system: Optional[bool] = None


# Every day, whatever the range: a day's baseline depends on its neighbours.
DAILY_REQUESTS = text("""
SELECT date::date AS date,
       sum(num_requests) FILTER (WHERE NOT is_bot)::bigint AS organic,
       sum(num_requests) FILTER (WHERE is_bot)::bigint AS bot,
       bool_or(new_system) AS new_system
FROM usage_stats.tileserver_day_index
GROUP BY 1
ORDER BY 1
""")


@router.get("/tiles/requests")
async def get_tile_requests(
    database: DatabaseDep,
    start: StartQuery = None,
    end: EndQuery = None,
    bin: BinQuery = "day",
) -> list[RequestsBin]:
    """Tile requests over time: organic, known bots, and presumed bots."""
    async with database.async_connection() as conn:
        rows = (await conn.execute(DAILY_REQUESTS)).mappings().all()
    dates = [r["date"] for r in rows]
    counts = [r["organic"] or 0 for r in rows]
    trend = long_term_trend(dates, counts)
    presumed = presumed_bots(dates, counts, trend)
    days = [
        {**row, "presumed_bot": p, "trend": round(t)}
        for row, p, t in zip(rows, presumed, trend)
        if (start is None or row["date"] >= start)
        and (end is None or row["date"] <= end)
    ]
    return [RequestsBin(**row) for row in _bin_days(days, bin)]


def _bin_start(day: date, bin: Bin) -> date:
    if bin == "week":
        return day - timedelta(days=day.weekday())
    if bin == "month":
        return day.replace(day=1)
    return day


def _next_bin(start: date, bin: Bin) -> date:
    if bin == "week":
        return start + timedelta(days=7)
    if bin == "month":
        return (start + timedelta(days=31)).replace(day=1)
    return start + timedelta(days=1)


def _bin_days(days: list[dict], bin: Bin) -> list[dict]:
    """Sums days into bins as `date_trunc` does; empty bins are rows of nulls."""
    bins: dict[date, dict] = {}
    for day in days:
        key = _bin_start(day["date"], bin)
        total = bins.setdefault(key, {"date": key})
        for field in ("organic", "bot", "presumed_bot", "trend"):
            if day[field] is not None:
                total[field] = total.get(field, 0) + day[field]
        total["new_system"] = total.get("new_system", False) or day["new_system"]
    if not bins:
        return []
    filled = []
    current, last = min(bins), max(bins)
    while current <= last:
        filled.append(bins.get(current, {"date": current}))
        current = _next_bin(current, bin)
    return filled


class Referrer(BaseModel):
    #: Host of the Referer header; empty when the request carried none.
    referrer: str
    requests: int
    days: int
    first_seen: date
    last_seen: date


class Referrers(BaseModel):
    total_requests: int
    n_referrers: int
    referrers: list[Referrer]


# Only log-dump rows hold a normalized host in `referrer`.
REFERRERS = text(f"""
SELECT referrer,
       sum(num_requests)::bigint AS requests,
       count(DISTINCT date) AS days,
       min(date)::date AS first_seen,
       max(date)::date AS last_seen,
       count(*) OVER () AS n_referrers,
       sum(sum(num_requests)) OVER ()::bigint AS total_requests
FROM usage_stats.tileserver_day_index
WHERE new_system AND {_IN_RANGE} AND {_BOTS}
GROUP BY referrer
ORDER BY requests DESC
LIMIT :limit
""")


@router.get("/tiles/referrers")
async def get_tile_referrers(
    database: DatabaseDep,
    start: StartQuery = None,
    end: EndQuery = None,
    bots: BotsQuery = "exclude",
    limit: Annotated[int, Query(ge=1, le=1000)] = 20,
) -> Referrers:
    """The sites whose pages request our tiles, busiest first."""
    async with database.async_connection() as conn:
        res = await conn.execute(REFERRERS, _params(start, end, bots, limit=limit))
        rows = res.mappings().all()
    if not rows:
        return Referrers(total_requests=0, n_referrers=0, referrers=[])
    return Referrers(
        total_requests=rows[0]["total_requests"],
        n_referrers=rows[0]["n_referrers"],
        referrers=[Referrer(**row) for row in rows],
    )


class CacheBin(BaseModel):
    date: date
    requests: Optional[int] = None
    l1_hits: Optional[int] = None
    l1_misses: Optional[int] = None
    #: Tile-cache status among L1 misses, the only requests that reach it.
    l2_hits: Optional[int] = None
    l2_misses: Optional[int] = None


# An L1 hit replays the L2 header stored with the object, so L2 counts only misses.
CACHE = text(f"""
WITH counts AS (
  SELECT date_trunc(CAST(:bin AS text), date) AS bin,
         sum(num_requests)::bigint AS requests,
         sum(num_requests) FILTER (WHERE x_cache = 'hit')::bigint AS l1_hits,
         sum(num_requests) FILTER (WHERE x_cache = 'miss')::bigint AS l1_misses,
         sum(num_requests) FILTER (
           WHERE x_cache = 'miss' AND x_tile_cache = 'hit'
         )::bigint AS l2_hits,
         sum(num_requests) FILTER (
           WHERE x_cache = 'miss' AND x_tile_cache = 'miss'
         )::bigint AS l2_misses
  FROM usage_stats.tileserver_day_index
  WHERE new_system AND {_IN_RANGE} AND {_BOTS}
  GROUP BY 1
),
{_FILL_BINS}
SELECT b.bin::date AS date, c.requests, c.l1_hits, c.l1_misses, c.l2_hits, c.l2_misses
FROM bins b
LEFT JOIN counts c USING (bin)
ORDER BY 1
""")


@router.get("/tiles/cache")
async def get_tile_cache(
    database: DatabaseDep,
    start: StartQuery = None,
    end: EndQuery = None,
    bots: BotsQuery = "exclude",
    bin: BinQuery = "day",
) -> list[CacheBin]:
    """Varnish (L1) and tile-cache (L2) outcomes over time."""
    async with database.async_connection() as conn:
        res = await conn.execute(CACHE, _params(start, end, bots, bin=bin))
        rows = res.mappings().all()
    return [CacheBin(**row) for row in rows]


class LayerCount(BaseModel):
    layer: str
    ext: str
    requests: int


LAYERS = text(f"""
SELECT layer, ext, sum(num_requests)::bigint AS requests
FROM usage_stats.tileserver_day_index
WHERE {_IN_RANGE} AND {_BOTS}
GROUP BY layer, ext
ORDER BY requests DESC
""")


@router.get("/tiles/layers")
async def get_tile_layers(
    database: DatabaseDep,
    start: StartQuery = None,
    end: EndQuery = None,
    bots: BotsQuery = "exclude",
) -> list[LayerCount]:
    """Requests per tile layer and file extension."""
    async with database.async_connection() as conn:
        rows = (await conn.execute(LAYERS, _params(start, end, bots))).mappings().all()
    return [LayerCount(**row) for row in rows]


class MapViews(BaseModel):
    #: A production source id, whichever database this API reads.
    source_id: int
    requests: int
    days: int


class MapViewsList(BaseModel):
    n_maps: int
    #: Earliest and latest days with any map attribution in the range.
    first_date: Optional[date] = None
    last_date: Optional[date] = None
    maps: list[MapViews]


# The harvester reads production logs in every environment, so no local
# `maps.sources` join: its ids would name other maps outside production.
MAPS = text(f"""
SELECT source_id,
       sum(num_requests)::bigint AS requests,
       count(DISTINCT date) AS days,
       count(*) OVER () AS n_maps,
       min(min(date)) OVER ()::date AS first_date,
       max(max(date)) OVER ()::date AS last_date
FROM usage_stats.tileserver_source_index
WHERE {_IN_RANGE} AND {_BOTS}
GROUP BY source_id
ORDER BY requests DESC
LIMIT :limit
""")


@router.get("/tiles/maps")
async def get_map_views(
    database: DatabaseDep,
    start: StartQuery = None,
    end: EndQuery = None,
    bots: BotsQuery = "exclude",
    limit: Annotated[int, Query(ge=1, le=5000)] = 100,
) -> MapViewsList:
    """Requests whose tiles drew each map, busiest first.

    A tile names every map it draws, so a request credits each in full and the
    counts sum to more than the requests.
    """
    async with database.async_connection() as conn:
        res = await conn.execute(MAPS, _params(start, end, bots, limit=limit))
        rows = res.mappings().all()
    if not rows:
        return MapViewsList(n_maps=0, maps=[])
    first = rows[0]
    return MapViewsList(
        n_maps=first["n_maps"],
        first_date=first["first_date"],
        last_date=first["last_date"],
        maps=[MapViews(**row) for row in rows],
    )


class MapViewsBin(BaseModel):
    date: date
    requests: Optional[int] = None


MAP_SERIES = text(f"""
WITH counts AS (
  SELECT date_trunc(CAST(:bin AS text), date) AS bin,
         sum(num_requests)::bigint AS requests
  FROM usage_stats.tileserver_source_index
  WHERE source_id = :source_id AND {_IN_RANGE} AND {_BOTS}
  GROUP BY 1
),
{_FILL_BINS}
SELECT b.bin::date AS date, c.requests
FROM bins b
LEFT JOIN counts c USING (bin)
ORDER BY 1
""")


@router.get("/tiles/maps/{source_id}")
async def get_map_view_series(
    source_id: int,
    database: DatabaseDep,
    start: StartQuery = None,
    end: EndQuery = None,
    bots: BotsQuery = "exclude",
    bin: BinQuery = "day",
) -> list[MapViewsBin]:
    """One map's requests over time."""
    params = _params(start, end, bots, bin=bin, source_id=source_id)
    async with database.async_connection() as conn:
        rows = (await conn.execute(MAP_SERIES, params)).mappings().all()
    return [MapViewsBin(**row) for row in rows]


class ThrottledClient(BaseModel):
    #: An IPv4 address or an IPv6 /64, as the tile cache keys it.
    client: str
    #: `deny`, or `would-deny` while the cache only reports.
    action: str
    requests: int
    days: int
    first_seen: datetime
    last_seen: datetime


THROTTLED = text(f"""
SELECT client, action,
       sum(num_requests)::bigint AS requests,
       count(DISTINCT date) AS days,
       min(first_seen) AS first_seen,
       max(last_seen) AS last_seen
FROM usage_stats.tileserver_throttled_clients
WHERE {_IN_RANGE}
GROUP BY client, action
ORDER BY last_seen DESC
LIMIT :limit
""")


@router.get("/tiles/throttled")
async def get_throttled_clients(
    database: DatabaseDep,
    start: StartQuery = None,
    end: EndQuery = None,
    limit: Annotated[int, Query(ge=1, le=1000)] = 50,
) -> list[ThrottledClient]:
    """Clients the tile cache refused, or would have, most recent first."""
    async with database.async_connection() as conn:
        res = await conn.execute(THROTTLED, _params(start, end, limit=limit))
        rows = res.mappings().all()
    return [ThrottledClient(**row) for row in rows]
