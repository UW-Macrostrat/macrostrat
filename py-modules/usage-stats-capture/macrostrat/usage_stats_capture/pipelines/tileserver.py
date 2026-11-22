"""Tileserver request pipeline.

Aggregates tile requests out of the access logs into three long-term indexes:
`tileserver_day_index` (per layer/day/referrer/cache-status),
`tileserver_location_index` (z<=8 spatial cells, for the request-density
heatmap) and `tileserver_source_index` (per map and day: the maps a tile drew,
read from the tileserver's `X-Macrostrat-Sources` response header). Raw
per-request rows are never stored — at tile volume they are enormous and the
indexes are the durable artifact.
"""

import re
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from ipaddress import ip_address, ip_network
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
# `map/carto` is the compilation-system carto (`/map/carto/{z}/{x}/{y}`), which
# the legacy routes redirect to once an environment switches over; `dev/carto`
# its deprecated alias.
KEEP_LAYERS = {"carto", "carto-slim", "map/carto", "dev/carto"}

# The tileserver names the maps a tile draws, as comma-separated source ids, in
# `X-Macrostrat-Sources`. Traefik keeps it in the access log under the
# `downstream_` prefix it gives every response header.
SOURCES_FIELD = "downstream_X-Macrostrat-Sources"

# The tile cache's render limit: `deny` (answered 429) or `would-deny` (report mode).
THROTTLE_FIELD = "downstream_X-Throttle"

# Native apps send no Referer, so they name themselves in the User-Agent:
# `Rockd/4.2.3` (the app) and `RockdMapCache/4.2.3 (iOS)` (offline downloads).
USER_AGENT_FIELD = "request_User-Agent"
APP_TOKENS = {"Rockd": "rockd", "RockdMapCache": "rockd-map-cache"}
APP_TOKEN_RE = re.compile(r"(?<![\w/])(RockdMapCache|Rockd)(?:/([\w.\-]+))?(?!\w)")

# Known automated clients (cache-warmers, prefetchers, scrapers) by source IP.
# Their requests are still aggregated, but tagged `is_bot` so organic traffic
# can be separated from machine traffic. See the 2026-06-28 spike investigation:
# 96.19.11.45 emits a fixed ~19.7k-tile carto.png set repeatedly and has driven
# 50–80% of all logged requests since the May outage.
KNOWN_BOTS = {
    "96.19.11.45",
}

# Clients are also tagged by volume, since sweepers rotate addresses. Measured
# 2026-11-12: a sweeper sent ~600k tiles/hour; the busiest other client sent 6.6k.
HEAVY_CLIENT_TILES_PER_HOUR = 20_000
# Short log objects are judged as if this long, so a brief burst is not a rate.
MIN_RATE_SPAN = timedelta(minutes=15)


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


def app_identity(rec: dict) -> tuple[str, str]:
    """(app, app_version) from a known product token in the User-Agent, else
    ('none', 'none'), the convention for requests that name no app."""
    m = APP_TOKEN_RE.search(rec.get(USER_AGENT_FIELD) or "")
    if m is None:
        return "none", "none"
    return APP_TOKENS[m.group(1)], (m.group(2) or "none")[:64]


def parse_sources(value: str | None) -> list[int]:
    """The source ids named by an `X-Macrostrat-Sources` header value.

    Empty when the header is absent -- the legacy build and responses from
    before the header existed -- so those requests credit no map. A token that
    is not an integer is skipped rather than failing the record.
    """
    if not value:
        return []
    ids = []
    for token in value.split(","):
        token = token.strip()
        if token.isdigit():
            ids.append(int(token))
    return ids


def is_relevant_request(host: str | None, layer: str) -> bool:
    """Whether a tile request counts toward the stats: production host + a
    canonical layer. Tweak KEEP_HOSTS / KEEP_LAYERS to widen coverage."""
    return host in KEEP_HOSTS and layer in KEEP_LAYERS


def is_known_bot(client: str | None) -> bool:
    """Whether a request's client is a known automated agent."""
    return client in KNOWN_BOTS


def served(rows: list[dict]) -> list[dict]:
    """Requests that delivered a tile; the render limit's 429s did not."""
    return [r for r in rows if r.get("status") != 429]


def aggregate_throttled(rows: list[dict]) -> list[dict]:
    """Per-client, per-day counts of requests the render limit refused or marked."""
    groups: dict[tuple, list] = {}
    for r in rows:
        t = r["time"]
        if not r.get("throttle") or t is None or r.get("client") is None:
            continue
        key = (datetime(t.year, t.month, t.day), r["client"], r["throttle"])
        group = groups.setdefault(key, [0, t, t])
        group[0] += 1
        group[1] = min(group[1], t)
        group[2] = max(group[2], t)
    return [
        {
            "date": date,
            "client": client,
            "action": action,
            "num_requests": n,
            "first_seen": first.replace(tzinfo=timezone.utc),
            "last_seen": last.replace(tzinfo=timezone.utc),
        }
        for (date, client, action), (n, first, last) in groups.items()
    ]


def client_network(client: str | None) -> str | None:
    """The unit a client is counted as: its /64 for IPv6, else its address.

    An IPv6 host picks new addresses within its /64 at will.
    """
    if not client:
        return None
    try:
        address = ip_address(client)
    except ValueError:
        return client
    if address.version == 6:
        return str(ip_network(f"{address}/64", strict=False))
    return client


def tag_heavy_clients(rows: list[dict]) -> list[dict]:
    """Mark `is_bot` on every request from a client whose rate over the batch
    exceeds HEAVY_CLIENT_TILES_PER_HOUR. A batch is one log object."""
    times = [r["time"] for r in rows if r["time"] is not None]
    if not times:
        return rows
    span = max(max(times) - min(times), MIN_RATE_SPAN)
    limit = HEAVY_CLIENT_TILES_PER_HOUR * span / timedelta(hours=1)
    counts = Counter(r["client"] for r in rows if r.get("client") is not None)
    heavy = {client for client, n in counts.items() if n > limit}
    for r in rows:
        if r.get("client") in heavy:
            r["is_bot"] = True
    return rows


# Upserts accumulate counts (new_system rows; legacy rows carry new_system=false
# and never collide). Aggregation dedupes keys, so no in-batch conflicts. Passed
# a list of param dicts, db.run_query runs them as an executemany.
#
# app / app_version once came from legacy `?referrer=`/`?version=` query params;
# they now come from the User-Agent (see app_identity).
DAY_UPSERT = """
    INSERT INTO usage_stats.tileserver_day_index
        (layer, ext, referrer, app, app_version, date, num_requests, new_system, is_bot, x_cache, x_tile_cache)
    VALUES (:layer, :ext, :referrer, :app, :app_version, :date, :num_requests, true, :is_bot, :x_cache, :x_tile_cache)
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


# One row per map per day: how many kept requests drew it. A request naming
# several maps credits each of them in full, so sums across maps exceed the
# request count by design.
SOURCE_UPSERT = """
    INSERT INTO usage_stats.tileserver_source_index
        (source_id, layer, ext, date, num_requests, is_bot)
    VALUES (:source_id, :layer, :ext, :date, :num_requests, :is_bot)
    ON CONFLICT (source_id, layer, ext, date, is_bot)
    DO UPDATE SET num_requests =
        usage_stats.tileserver_source_index.num_requests + EXCLUDED.num_requests
"""


THROTTLED_UPSERT = """
    INSERT INTO usage_stats.tileserver_throttled_clients
        (date, client, action, num_requests, first_seen, last_seen)
    VALUES (:date, :client, :action, :num_requests, :first_seen, :last_seen)
    ON CONFLICT (date, client, action)
    DO UPDATE SET
        num_requests = usage_stats.tileserver_throttled_clients.num_requests
            + EXCLUDED.num_requests,
        first_seen = least(
            usage_stats.tileserver_throttled_clients.first_seen, EXCLUDED.first_seen
        ),
        last_seen = greatest(
            usage_stats.tileserver_throttled_clients.last_seen, EXCLUDED.last_seen
        )
"""

DAILY_SERIES = """
    SELECT date, new_system, sum(num_requests)::bigint AS count
    FROM usage_stats.tileserver_day_index
    WHERE (NOT :skip_bots OR NOT is_bot)
    GROUP BY date, new_system
    ORDER BY date
"""


class TileserverPipeline:
    name = "tileserver"

    plot_label = "Tile requests per day"
    plot_options = frozenset({"skip_bots"})
    # The 2021+ systematic scrapes and the 2026 cache-warmer produce order-of-
    # magnitude spikes that swamp the real signal, so cutting them is the right
    # default here.
    plot_omit_spikes = True

    def parse(self, rec: dict) -> dict | None:
        if rec.get("RequestMethod") != "GET":
            return None
        tile = parse_tile_path(rec.get("RequestPath"))
        if tile is None:
            return None
        if not is_relevant_request(rec.get("RequestHost"), tile["layer"]):
            return None
        app, app_version = app_identity(rec)
        return {
            "layer": tile["layer"],
            "ext": (tile["ext"] or "").lower(),
            "x": tile["x"],
            "y": tile["y"],
            "z": tile["z"],
            "time": parse_timestamp(rec),
            "is_bot": is_known_bot(rec.get("ClientHost")),
            "client": client_network(rec.get("ClientHost")),
            "referrer": referrer_host(rec),
            "app": app,
            "app_version": app_version,
            # Client-facing cache status ('' when the header is absent, e.g.
            # pre-config-change logs). downstream_* is what the client got.
            "x_cache": (rec.get("downstream_X-Cache") or "").lower(),
            "x_tile_cache": (rec.get("downstream_X-Tile-Cache") or "").lower(),
            "status": rec.get("DownstreamStatus"),
            "throttle": (rec.get(THROTTLE_FIELD) or "").lower(),
            "sources": parse_sources(rec.get(SOURCES_FIELD)),
        }

    def write(self, db, rows: list[dict]) -> None:
        rows = tag_heavy_clients(rows)
        throttled_rows = aggregate_throttled(rows)
        if throttled_rows:
            db.run_query(THROTTLED_UPSERT, throttled_rows)
        day_rows, loc_rows, source_rows = aggregate(served(rows))
        if day_rows:
            db.run_query(DAY_UPSERT, day_rows)
        if loc_rows:
            db.run_query(LOCATION_UPSERT, loc_rows)
        if source_rows:
            db.run_query(SOURCE_UPSERT, source_rows)

    def daily_series(self, db, *, skip_bots: bool = False, **_) -> list[dict]:
        """Daily tile-request totals, split by pipeline lineage.

        skip_bots excludes known automated clients so the series reflects
        organic traffic only.
        """
        result = db.run_query(DAILY_SERIES, {"skip_bots": skip_bots})
        return [dict(r._mapping) for r in result]

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
        # Entirely from the log dumps: no legacy lineage to keep.
        n_src = db.run_query("DELETE FROM usage_stats.tileserver_source_index").rowcount
        n_thr = db.run_query(
            "DELETE FROM usage_stats.tileserver_throttled_clients"
        ).rowcount
        return (
            f"{n_day} day rows, {n_loc} location rows, {n_src} source rows,"
            f" {n_thr} throttled-client rows"
            " (legacy lineage kept)"
        )


def aggregate(rows: list[dict]) -> tuple[list[dict], list[dict], list[dict]]:
    """Roll parsed requests up into day_index, location_index and source_index
    upsert rows. Location cells are downsampled to z<=8 (the index's heatmap
    resolution), keeping the original zoom as orig_z."""
    day: dict[tuple, int] = defaultdict(int)
    loc: dict[tuple, int] = defaultdict(int)
    src: dict[tuple, int] = defaultdict(int)
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
            for source_id in r.get("sources", ()):
                src[(source_id, r["layer"], r["ext"], date, bot)] += 1
            # Referrer and cache status are day_index-only dimensions (kept off
            # location_index to avoid multiplying its cardinality).
            day[
                (
                    r["layer"],
                    r["ext"],
                    r["referrer"],
                    r["app"],
                    r["app_version"],
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
            "app": k[3],
            "app_version": k[4],
            "date": k[5],
            "is_bot": k[6],
            "x_cache": k[7],
            "x_tile_cache": k[8],
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
    source_rows = [
        {
            "source_id": k[0],
            "layer": k[1],
            "ext": k[2],
            "date": k[3],
            "is_bot": k[4],
            "num_requests": n,
        }
        for k, n in src.items()
    ]
    return day_rows, loc_rows, source_rows
