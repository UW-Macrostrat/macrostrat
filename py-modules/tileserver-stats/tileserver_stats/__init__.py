from collections import defaultdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional
import asyncio
import io
import json
import re

import zstandard as zstd
from dotenv import load_dotenv
from macrostrat.database.transfer import move_tables
from minio import Minio
from rich import print
from sqlalchemy import text
from typer import Typer, Option, confirm
from pydantic import BaseModel

from macrostrat.database import Database
from macrostrat.core.config import settings
from macrostrat.core import get_database

load_dotenv()

app = Typer(no_args_is_help=True, short_help="Compile tileserver statistics")


@app.command()
def migrate_data(drop: bool = False):
    """Merge the tileserver_stats database into the core Macrostrat database."""
    tileserver_db = settings.databases.get("tileserver_stats")

    tdb = Database(tileserver_db)
    # Rename the schema stats to tileserver_stats
    tdb.run_sql("ALTER SCHEMA stats RENAME TO tileserver_stats")

    # Move the `requests` table into the `tileserver_stats` schema
    tdb.run_sql("ALTER TABLE requests SET SCHEMA tileserver_stats")

    # Switch to SQL in Macrostrat database
    db = get_database()
    # Merge the `tileserver_stats` schema into the core Macrostrat database

    task = move_tables(tdb.engine, db.engine, schemas=["tileserver_stats"])
    asyncio.run(task)


class SmoothOption(str, Enum):
    none = "none"  # raw daily
    weekly = "weekly"  # 7-day rolling mean
    monthly = "monthly"  # 30-day rolling mean


class RangeOption(str, Enum):
    last_month = "last-month"
    last_year = "last-year"
    last_5_years = "last-5-years"
    all = "all"


@app.command(name="plot")
def plot_command(
    out: Optional[Path] = Option(
        None,
        "--out",
        "-o",
        help="Output file (.pdf/.svg/.png). Omit to print inline (iTerm).",
    ),
    smooth: SmoothOption = Option(
        SmoothOption.weekly,
        "--smooth",
        help="Smoothing: none (raw daily), weekly (7-day mean), monthly (30-day mean).",
    ),
    range_: RangeOption = Option(
        RangeOption.all, "--range", help="Time window to plot."
    ),
    log: bool = Option(False, "--log/--linear", help="Logarithmic vs. linear y-axis."),
    omit_spikes: bool = Option(
        True,
        "--omit-spikes/--keep-spikes",
        help="Cut spike days before smoothing; drawn dashed.",
    ),
    spike_quantile: Optional[float] = Option(
        None,
        "--spike-quantile",
        help="Daily-count quantile above which days are treated as spikes "
        "(default: module SPIKE_QUANTILE).",
    ),
):
    """Plot tile requests per day for reports."""
    from .plot import SMOOTH_WINDOWS, SPIKE_QUANTILE, tileserver_stats_figure

    tileserver_stats_figure(
        out,
        log=log,
        omit_spikes=omit_spikes,
        spike_quantile=SPIKE_QUANTILE if spike_quantile is None else spike_quantile,
        smooth_window=SMOOTH_WINDOWS[smooth.value],
        range_opt=range_.value,
    )


@app.command()
def show_database():
    """Show the database connection string."""
    tileserver_db = settings.databases.get("tileserver_stats")
    print(tileserver_db)


@app.command(name="reset-new-system", rich_help_panel="Development")
def reset_new_system(
    yes: bool = Option(False, "--yes", "-y", help="Skip the confirmation prompt."),
):
    """Drop new-system aggregates and the processed-log records so the log dumps
    can be re-ingested from scratch.

    Deletes all `new_system = true` rows from day_index / location_index and
    empties processed_logs; legacy (`new_system = false`) data is left intact.
    For development/testing — handy when changing the ingestion or filter logic.
    """
    db = get_database()
    if not yes:
        confirm(
            "Delete all new-system rows from day_index/location_index and clear "
            "processed_logs?",
            abort=True,
        )
    with db.engine.begin() as conn:
        n_day = conn.execute(
            text("DELETE FROM tileserver_stats.day_index WHERE new_system")
        ).rowcount
        n_loc = conn.execute(
            text("DELETE FROM tileserver_stats.location_index WHERE new_system")
        ).rowcount
        n_log = conn.execute(
            text("DELETE FROM tileserver_stats.processed_logs")
        ).rowcount
    print(
        f"Cleared {n_day} day_index, {n_loc} location_index, "
        f"{n_log} processed_logs rows."
    )


class S3Params(BaseModel):
    bucket: str
    endpoint: str
    access_key: str
    secret_key: str

    def get_client(self):
        print(self.endpoint)
        secure = self.endpoint.startswith("https://")
        if "/" not in self.endpoint:
            secure = True
        # Remove trailing slash if present
        endpoint = self.endpoint.rstrip("/")
        for prefix in ["http://", "https://"]:
            endpoint = endpoint.replace(prefix, "")
        # Remove scheme if present
        return Minio(
            endpoint=endpoint,
            access_key=self.access_key,
            secret_key=self.secret_key,
            secure=secure,
        )


def get_config_attrs(config) -> S3Params:
    return S3Params(
        bucket=config.get("bucket"),
        endpoint=config.get("endpoint"),
        access_key=config.get("access_key"),
        secret_key=config.get("secret_key"),
    )


# A tile request path is `/<layer>/<z>/<x>/<y>[.ext]`, where <layer> may span
# multiple segments (e.g. `dev/topology/faces/<map_layer>`). The trailing three
# numeric segments are z/x/y; everything before them is the layer.
TILE_PATH_RE = re.compile(
    r"^/(?P<layer>.+?)/(?P<z>\d+)/(?P<x>\d+)/(?P<y>\d+)(?:\.(?P<ext>[A-Za-z0-9]+))?/?$"
)


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


def _parse_timestamp(rec: dict) -> datetime | None:
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


def _resolve_access_logs_config() -> S3Params:
    """Resolve the access-logs S3 config, tolerating either key spelling
    (`access-logs` in TOML vs. `access_logs`)."""
    storage_cfg = settings.storage
    for key in ("access-logs", "access_logs"):
        try:
            cfg = storage_cfg[key]
        except (KeyError, TypeError):
            cfg = None
        if cfg:
            return get_config_attrs(cfg)
    raise KeyError("storage.access-logs is not configured")


# --- Relevance filter -------------------------------------------------------
#
# We only care about tile requests served from the production tile host for a
# small set of canonical map layers. Everything else in the access logs — other
# hosts, garbled layer names (`carto/lite`, `carto|PNG`, `tiles/carto`, …),
# subsidiary/dev layers, and scraper noise — is dropped before aggregation.
KEEP_HOSTS = {"tiles.macrostrat.org"}
KEEP_LAYERS = {"carto", "carto-slim"}


def is_relevant_request(host: str | None, layer: str) -> bool:
    """Whether a tile request counts toward the stats: production host + a
    canonical layer. Tweak KEEP_HOSTS / KEEP_LAYERS to widen coverage."""
    return host in KEEP_HOSTS and layer in KEEP_LAYERS


@app.command(name="process")
def process_ingest_logs(
    prefix: str = "prod",
    limit: Optional[int] = None,
    reprocess: bool = False,
):
    """Ingest Traefik access-log dumps from S3/MinIO, aggregating relevant tile
    requests directly into tileserver_stats.day_index / location_index.

    Already-processed objects are skipped (tracked in tileserver_stats.processed_logs);
    --reprocess re-ingests them (note: this double-counts unless the indexes are
    cleared first). --limit caps the number of new objects.
    """
    config = _resolve_access_logs_config()
    n = ingest_traefik_logs_from_s3(
        config, prefix=prefix, limit=limit, reprocess=reprocess
    )
    print(f"Aggregated {n} relevant tile requests")


def _parse_log_object(s3, bucket: str, object_name: str) -> tuple[list[dict], int]:
    """Stream-decompress one zstd JSONL log object, returning (relevant tile
    rows, total log lines). Non-tile paths and irrelevant host/layer requests
    are filtered out; `ext` is normalized to lowercase ('' when absent)."""
    response = s3.get_object(bucket, object_name)
    rows: list[dict] = []
    n_records = 0
    try:
        dctx = zstd.ZstdDecompressor()
        with dctx.stream_reader(response) as reader:
            stream = io.TextIOWrapper(reader, encoding="utf-8", errors="replace")
            for line in stream:
                line = line.strip()
                if not line:
                    continue
                n_records += 1
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if rec.get("RequestMethod") != "GET":
                    continue
                tile = parse_tile_path(rec.get("RequestPath"))
                if tile is None:
                    continue
                if not is_relevant_request(rec.get("RequestHost"), tile["layer"]):
                    continue
                rows.append(
                    {
                        "layer": tile["layer"],
                        "ext": (tile["ext"] or "").lower(),
                        "x": tile["x"],
                        "y": tile["y"],
                        "z": tile["z"],
                        "time": _parse_timestamp(rec),
                    }
                )
    finally:
        response.close()
        response.release_conn()
    return rows, n_records


def _aggregate(rows: list[dict]) -> tuple[list[dict], list[dict]]:
    """Roll parsed requests up into day_index and location_index upsert rows.
    Location cells are downsampled to z<=8 (the index's heatmap resolution),
    keeping the original zoom as orig_z."""
    day: dict[tuple, int] = defaultdict(int)
    loc: dict[tuple, int] = defaultdict(int)
    for r in rows:
        z, x, y = r["z"], r["x"], r["y"]
        if z > 8:
            lx, ly, lz = x >> (z - 8), y >> (z - 8), 8
        else:
            lx, ly, lz = x, y, z
        loc[(r["layer"], r["ext"], lx, ly, lz, z)] += 1
        t = r["time"]
        if t is not None:
            date = datetime(t.year, t.month, t.day)
            day[(r["layer"], r["ext"], date)] += 1

    day_rows = [
        {"layer": k[0], "ext": k[1], "date": k[2], "num_requests": n}
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
            "num_requests": n,
        }
        for k, n in loc.items()
    ]
    return day_rows, loc_rows


# Upserts accumulate counts (new_system rows; legacy rows carry new_system=false
# and never collide). Aggregation dedupes keys, so no in-batch conflicts.
DAY_UPSERT = text(
    """
    INSERT INTO tileserver_stats.day_index
        (layer, ext, referrer, app, app_version, date, num_requests, new_system)
    VALUES (:layer, :ext, 'none', 'none', 'none', :date, :num_requests, true)
    ON CONFLICT (layer, ext, referrer, app, app_version, date, new_system)
    DO UPDATE SET num_requests =
        tileserver_stats.day_index.num_requests + EXCLUDED.num_requests
    """
)
LOCATION_UPSERT = text(
    """
    INSERT INTO tileserver_stats.location_index
        (layer, ext, x, y, z, orig_z, num_requests, new_system)
    VALUES (:layer, :ext, :x, :y, :z, :orig_z, :num_requests, true)
    ON CONFLICT (layer, ext, x, y, z, orig_z, new_system)
    DO UPDATE SET num_requests =
        tileserver_stats.location_index.num_requests + EXCLUDED.num_requests
    """
)
RECORD_LOG = text(
    """
    INSERT INTO tileserver_stats.processed_logs
        (object_name, etag, size, last_modified, num_records, num_tile_requests)
    VALUES (:object_name, :etag, :size, :last_modified, :num_records, :num_tile_requests)
    ON CONFLICT (object_name) DO UPDATE SET
        etag = EXCLUDED.etag,
        size = EXCLUDED.size,
        last_modified = EXCLUDED.last_modified,
        num_records = EXCLUDED.num_records,
        num_tile_requests = EXCLUDED.num_tile_requests,
        processed_at = now()
    """
)


def _executemany(conn, stmt, rows: list[dict], batch: int) -> None:
    for i in range(0, len(rows), batch):
        chunk = rows[i : i + batch]
        if chunk:
            conn.execute(stmt, chunk)


def ingest_traefik_logs_from_s3(
    config: S3Params,
    *,
    prefix: str = "prod",
    limit: int | None = None,
    reprocess: bool = False,
    batch: int = 5000,
) -> int:
    """Download Traefik access-log dumps from S3/MinIO and aggregate relevant
    tile requests directly into the core-DB day_index / location_index — no raw
    staging table.

    Objects are JSONL (one Traefik record per line), zstd-compressed,
    date-partitioned under `<prefix>/YYYY/MM/DD/...`. Each object is parsed,
    filtered (see is_relevant_request), aggregated, upserted, and recorded in
    tileserver_stats.processed_logs **atomically** (one transaction), so it's
    never reprocessed and never needs a staging table.

    NOTE: referrer/app/app_version and cache levels (L1/L2) aren't present in
    default Traefik logs, so day_index stores them as 'none' — see the
    feature-area doc.

    Returns the number of relevant tile requests aggregated.
    """
    s3 = config.get_client()
    db = get_database()

    with db.engine.connect() as conn:
        already = {
            row[0]
            for row in conn.execute(
                text("SELECT object_name FROM tileserver_stats.processed_logs")
            )
        }

    total_kept = 0
    n_objects = 0
    for obj in s3.list_objects(config.bucket, prefix=prefix, recursive=True):
        if not obj.object_name.endswith(".zst"):
            continue
        if not reprocess and obj.object_name in already:
            continue
        if limit is not None and n_objects >= limit:
            break
        n_objects += 1

        rows, n_records = _parse_log_object(s3, config.bucket, obj.object_name)
        day_rows, loc_rows = _aggregate(rows)

        with db.engine.begin() as conn:
            _executemany(conn, DAY_UPSERT, day_rows, batch)
            _executemany(conn, LOCATION_UPSERT, loc_rows, batch)
            conn.execute(
                RECORD_LOG,
                {
                    "object_name": obj.object_name,
                    "etag": getattr(obj, "etag", None),
                    "size": obj.size,
                    "last_modified": getattr(obj, "last_modified", None),
                    "num_records": n_records,
                    "num_tile_requests": len(rows),
                },
            )

        total_kept += len(rows)
        print(
            f"{obj.object_name}: kept {len(rows)}/{n_records} "
            f"→ {len(day_rows)} day-cells, {len(loc_rows)} location-cells"
        )

    print(
        f"Processed {n_objects} new object(s); "
        f"aggregated {total_kept} relevant tile requests"
    )
    return total_kept
