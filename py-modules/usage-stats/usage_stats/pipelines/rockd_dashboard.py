"""Rockd dashboard-load pipeline.

`GET /api/v2/mobile/dashboard?lng=…&lat=…&app=rockd&version=…` is called only
when a user opens the Rockd app's dashboard, and the coordinates come from the
device GPS. Each record is therefore a real user, at a real place, at a known
time — the most direct measure of app usage we have.

Rows are stored raw. Consecutive requests from a stationary device sit ~110 m
apart on GPS jitter alone, so any deduplication threshold is a judgement call;
it lives in the `rockd_dashboard_views` / `rockd_dashboard_sessions` views,
where it can be revised without re-pulling five months of logs.
"""

from hashlib import blake2b
from urllib.parse import parse_qs, urlsplit

from macrostrat.core.config import settings

from .tileserver import parse_timestamp

# Observed hosts serving the dashboard route. As sampled (2026-08-14, 25,180
# requests) this is macrostrat.org for 100% of them — rockd.org serves the web
# app but not this API route.
KEEP_HOSTS = {"macrostrat.org"}

DASHBOARD_PATH = "/api/v2/mobile/dashboard"

# The route is also hit by CORS preflights, which carry the same query string
# but represent no user action — in the sampled day they were 12,888 of 25,180
# requests, so counting them would inflate usage by ~2x.
KEEP_METHOD = "GET"


def _client_salt() -> bytes:
    """The secret key used to pseudonymize client addresses.

    Must be secret: a bare digest of an IPv4 address is not a pseudonym at all,
    since the whole space inverts by brute force in seconds. Must also be
    stable across runs — deduplication compares consecutive requests from one
    client, and those routinely straddle log-object boundaries.

    Prefers an explicit `usage_stats_client_salt`; otherwise derives one from
    the application `secret_key`, domain-separated so the derived value can't
    be used to attack anything else keyed on it.
    """
    explicit = settings.get("usage_stats_client_salt", None)
    if explicit:
        return str(explicit).encode()

    secret = settings.get("secret_key", None)
    if not secret:
        raise RuntimeError(
            "Cannot pseudonymize client addresses: set `usage_stats_client_salt` "
            "(or `secret_key`) in the Macrostrat configuration. Note that "
            "changing this value forks client_id and breaks deduplication "
            "against already-ingested rows."
        )
    return blake2b(str(secret).encode(), person=b"usage-stats", digest_size=32).digest()


def client_id(address: str | None) -> str:
    """A stable pseudonym for a client address. The address itself is never
    stored — see the schema comment on rockd_dashboard_loads."""
    if not address:
        return ""
    return blake2b(address.encode(), key=_client_salt(), digest_size=16).hexdigest()


def _coord(value: str | None) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def valid_coordinates(lat: float | None, lng: float | None) -> bool:
    """Reject unusable positions. Null Island is excluded deliberately: it is
    the canonical signature of a device reporting a failed GPS fix as 0,0
    rather than a user in the Gulf of Guinea."""
    if lat is None or lng is None:
        return False
    if not (-90 <= lat <= 90) or not (-180 <= lng <= 180):
        return False
    if lat == 0 and lng == 0:
        return False
    return True


# (time, client_id) makes re-ingestion idempotent, so --reprocess and an
# interrupted backfill can't duplicate rows. Timestamps carry sub-second
# precision, so two genuinely distinct loads colliding on the key would require
# one client to hit the route twice within the same microsecond.
INSERT = """
    INSERT INTO usage_stats.rockd_dashboard_loads
        (time, lat, lng, app, app_version, client_id, status)
    VALUES (:time, :lat, :lng, :app, :app_version, :client_id, :status)
    ON CONFLICT (time, client_id) DO NOTHING
"""


# Which relation the daily series counts. `raw` is every logged dashboard load;
# the other two are the deduplication views, which collapse the GPS-jitter
# cloud a stationary device produces (see the schema comments for thresholds).
DEDUP_RELATIONS = {
    "raw": "usage_stats.rockd_dashboard_loads",
    "views": "usage_stats.rockd_dashboard_views",
    "sessions": "usage_stats.rockd_dashboard_sessions",
}

# Days are bucketed in UTC, matching the tileserver day_index (whose `date` is a
# naive UTC timestamp), so the two series are directly comparable.
DAILY_SERIES = """
    SELECT date_trunc('day', time AT TIME ZONE 'UTC') AS date,
           count(*)::bigint AS count
    FROM {relation}
    GROUP BY 1
    ORDER BY 1
"""


class RockdDashboardPipeline:
    name = "rockd-dashboard"

    plot_label = "Rockd dashboard loads per day"
    plot_options = frozenset({"dedup"})
    # Unlike the tileserver series, every spike here is real usage — there is no
    # scraper analogue. Cutting the top quantile would delete the busiest days
    # of genuine app traffic, so spike-omission defaults off.
    plot_omit_spikes = False

    def parse(self, rec: dict) -> dict | None:
        if rec.get("RequestMethod") != KEEP_METHOD:
            return None
        if rec.get("RequestHost") not in KEEP_HOSTS:
            return None

        path = rec.get("RequestPath") or ""
        route, _, query = path.partition("?")
        if route.rstrip("/") != DASHBOARD_PATH:
            return None

        # Keep successful and cached responses (a 304 still means the user
        # opened the dashboard); drop client aborts and server errors. The
        # status is stored so this can be narrowed later without a re-pull.
        status = rec.get("DownstreamStatus")
        if not isinstance(status, int) or status >= 400:
            return None

        params = parse_qs(query)
        lat = _coord(params.get("lat", [None])[0])
        lng = _coord(params.get("lng", [None])[0])
        if not valid_coordinates(lat, lng):
            return None

        time = parse_timestamp(rec)
        if time is None:
            return None

        return {
            "time": time,
            "lat": lat,
            "lng": lng,
            "app": (params.get("app", [""])[0] or "")[:64],
            "app_version": (params.get("version", [""])[0] or "")[:64],
            "client_id": client_id(rec.get("ClientHost")),
            "status": status,
        }

    def write(self, db, rows: list[dict]) -> None:
        if not rows:
            return
        # Within a single object a client can repeat a timestamp only by
        # colliding at microsecond resolution; dedupe here anyway so the
        # executemany can't trip over its own batch.
        seen = set()
        unique = []
        for row in rows:
            key = (row["time"], row["client_id"])
            if key in seen:
                continue
            seen.add(key)
            unique.append(row)
        db.run_query(INSERT, unique)

    def daily_series(self, db, *, dedup: str = "raw", **_) -> list[dict]:
        """Daily dashboard-load counts.

        dedup selects the relation: `raw` (every request), `views`
        (250 m / 15 min) or `sessions` (500 m / 1 h).
        """
        try:
            relation = DEDUP_RELATIONS[dedup]
        except KeyError:
            raise ValueError(
                f"Unknown dedup mode {dedup!r}. "
                f"Choose from: {', '.join(DEDUP_RELATIONS)}"
            )
        # `relation` is looked up from the table above, never interpolated from
        # user input.
        result = db.run_query(DAILY_SERIES.format(relation=relation))
        return [dict(r._mapping) for r in result]

    def reset(self, db) -> str:
        # Every row comes from the log dumps, so all of it is reproducible.
        n = db.run_query("DELETE FROM usage_stats.rockd_dashboard_loads").rowcount
        return f"{n} dashboard loads"
