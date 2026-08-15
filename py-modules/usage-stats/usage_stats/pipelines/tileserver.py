"""Tileserver request pipeline.

Aggregates tile requests out of the access logs into two long-term indexes:
`tileserver_day_index` (per layer/day/referrer/cache-status) and
`tileserver_location_index` (z<=8 spatial cells, for the request-density
heatmap). Raw per-request rows are never stored — at tile volume they are
enormous and the indexes are the durable artifact.
"""

import re
from collections import defaultdict
from datetime import datetime
from urllib.parse import urlsplit

# A tile request path is `/<layer>/<z>/<x>/<y>[.ext]`, where <layer> may span
# multiple segments (e.g. `dev/topology/faces/<map_layer>`). The trailing three
# numeric segments are z/x/y; everything before them is the layer.
TILE_PATH_RE = re.compile(
    r"^/(?P<layer>.+?)/(?P<z>\d+)/(?P<x>\d+)/(?P<y>\d+)(?:\.(?P<ext>[A-Za-z0-9]+))?/?$"
)

# We only care about tile requests served from the production tile host for a
# small set of canonical map layers. Everything else in the access logs — other
# hosts, garbled layer names (`carto/lite`, `carto|PNG`, `tiles/carto`, …),
# subsidiary/dev layers, and scraper noise — is dropped before aggregation.
KEEP_HOSTS = {"tiles.macrostrat.org"}
KEEP_LAYERS = {"carto", "carto-slim"}

# Known automated clients (cache-warmers, prefetchers, scrapers) by source IP.
# Their requests are still aggregated, but tagged `is_bot` so organic traffic
# can be separated from machine traffic. See the 2026-06-28 spike investigation:
# 96.19.11.45 emits a fixed ~19.7k-tile carto.png set repeatedly and has driven
# 50–80% of all logged requests since the May outage.
KNOWN_BOTS = {
    "96.19.11.45",
}


def parse_tile_path(path: str | None) -> dict | None:
    """Parse a request path into (layer, z, x, y, ext), or None if not a tile."""
    if not path:
        return None
    path = path.split("?", 1)[0]  # drop any query string
    m = TILE_PATH_RE.match(path)
    if m is None:
        return None
    return {
        "layer": m.group("layer"),
        "z": int(m.group("z")),
        "x": int(m.group("x")),
        "y": int(m.group("y")),
        "ext": m.group("ext"),
    }


def parse_timestamp(rec: dict) -> datetime | None:
    """Parse a Traefik log timestamp. Prefers ns-precision StartUTC; tolerates
    the trailing 'Z' and truncates sub-microsecond digits for fromisoformat."""
    raw = rec.get("StartUTC") or rec.get("time") or rec.get("StartLocal")
    if not raw:
        return None
    s = raw.rstrip("Z")
    if "." in s:
        head, frac = s.split(".", 1)
        s = f"{head}.{frac[:6]}"
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        return None


def referrer_host(rec: dict) -> str:
    """The host of the request's Referer header, or '' when absent.

    Normalized to the bare host — scheme, `www.`, port, path and query all
    dropped, lowercased. `referrer` is part of the day_index unique key, so
    cardinality matters: hosts number in the dozens, whereas full URLs grow
    without bound and answer a question we aren't asking.
    """
    raw = rec.get("request_Referer") or ""
    if not raw:
        return ""
    host = urlsplit(raw).hostname or ""
    if host.startswith("www."):
        host = host[4:]
    return host.lower()


def is_relevant_request(host: str | None, layer: str) -> bool:
    """Whether a tile request counts toward the stats: production host + a
    canonical layer. Tweak KEEP_HOSTS / KEEP_LAYERS to widen coverage."""
    return host in KEEP_HOSTS and layer in KEEP_LAYERS


def is_known_bot(client: str | None) -> bool:
    """Whether a request's client is a known automated agent."""
    return client in KNOWN_BOTS


# Upserts accumulate counts (new_system rows; legacy rows carry new_system=false
# and never collide). Aggregation dedupes keys, so no in-batch conflicts. Passed
# a list of param dicts, db.run_query runs them as an executemany.
#
# app / app_version came from the legacy `?referrer=`/`?version=` query params,
# which current clients no longer send (357 of 20,315 sampled tile requests
# carried any query string at all). They stay 'none' rather than being invented;
# the referrer host is the dimension that carries the signal now.
DAY_UPSERT = """
    INSERT INTO usage_stats.tileserver_day_index
        (layer, ext, referrer, app, app_version, date, num_requests, new_system, is_bot, x_cache, x_tile_cache)
    VALUES (:layer, :ext, :referrer, 'none', 'none', :date, :num_requests, true, :is_bot, :x_cache, :x_tile_cache)
    ON CONFLICT (layer, ext, referrer, app, app_version, date, new_system, is_bot, x_cache, x_tile_cache)
    DO UPDATE SET num_requests =
        usage_stats.tileserver_day_index.num_requests + EXCLUDED.num_requests
"""

LOCATION_UPSERT = """
    INSERT INTO usage_stats.tileserver_location_index
        (layer, ext, x, y, z, orig_z, num_requests, new_system, is_bot)
    VALUES (:layer, :ext, :x, :y, :z, :orig_z, :num_requests, true, :is_bot)
    ON CONFLICT (layer, ext, x, y, z, orig_z, new_system, is_bot)
    DO UPDATE SET num_requests =
        usage_stats.tileserver_location_index.num_requests + EXCLUDED.num_requests
"""


class TileserverPipeline:
    name = "tileserver"

    def parse(self, rec: dict) -> dict | None:
        if rec.get("RequestMethod") != "GET":
            return None
        tile = parse_tile_path(rec.get("RequestPath"))
        if tile is None:
            return None
        if not is_relevant_request(rec.get("RequestHost"), tile["layer"]):
            return None
        return {
            "layer": tile["layer"],
            "ext": (tile["ext"] or "").lower(),
            "x": tile["x"],
            "y": tile["y"],
            "z": tile["z"],
            "time": parse_timestamp(rec),
            "is_bot": is_known_bot(rec.get("ClientHost")),
            "referrer": referrer_host(rec),
            # Client-facing cache status ('' when the header is absent, e.g.
            # pre-config-change logs). downstream_* is what the client got.
            "x_cache": (rec.get("downstream_X-Cache") or "").lower(),
            "x_tile_cache": (rec.get("downstream_X-Tile-Cache") or "").lower(),
        }

    def write(self, db, rows: list[dict]) -> None:
        day_rows, loc_rows = aggregate(rows)
        if day_rows:
            db.run_query(DAY_UPSERT, day_rows)
        if loc_rows:
            db.run_query(LOCATION_UPSERT, loc_rows)

    def reset(self, db) -> str:
        # Only the log-dump lineage. The legacy rows (new_system = false, back
        # to 2018) predate the dumps, have no surviving source, and must never
        # be cleared by a rebuild.
        n_day = db.run_query(
            "DELETE FROM usage_stats.tileserver_day_index WHERE new_system"
        ).rowcount
        n_loc = db.run_query(
            "DELETE FROM usage_stats.tileserver_location_index WHERE new_system"
        ).rowcount
        return f"{n_day} day rows, {n_loc} location rows (legacy lineage kept)"


def aggregate(rows: list[dict]) -> tuple[list[dict], list[dict]]:
    """Roll parsed requests up into day_index and location_index upsert rows.
    Location cells are downsampled to z<=8 (the index's heatmap resolution),
    keeping the original zoom as orig_z."""
    day: dict[tuple, int] = defaultdict(int)
    loc: dict[tuple, int] = defaultdict(int)
    for r in rows:
        bot = r["is_bot"]
        z, x, y = r["z"], r["x"], r["y"]
        if z > 8:
            lx, ly, lz = x >> (z - 8), y >> (z - 8), 8
        else:
            lx, ly, lz = x, y, z
        loc[(r["layer"], r["ext"], lx, ly, lz, z, bot)] += 1
        t = r["time"]
        if t is not None:
            date = datetime(t.year, t.month, t.day)
            # Referrer and cache status are day_index-only dimensions (kept off
            # location_index to avoid multiplying its cardinality).
            day[
                (
                    r["layer"],
                    r["ext"],
                    r["referrer"],
                    date,
                    bot,
                    r["x_cache"],
                    r["x_tile_cache"],
                )
            ] += 1

    day_rows = [
        {
            "layer": k[0],
            "ext": k[1],
            "referrer": k[2],
            "date": k[3],
            "is_bot": k[4],
            "x_cache": k[5],
            "x_tile_cache": k[6],
            "num_requests": n,
        }
        for k, n in day.items()
    ]
    loc_rows = [
        {
            "layer": k[0],
            "ext": k[1],
            "x": k[2],
            "y": k[3],
            "z": k[4],
            "orig_z": k[5],
            "is_bot": k[6],
            "num_requests": n,
        }
        for k, n in loc.items()
    ]
    return day_rows, loc_rows
