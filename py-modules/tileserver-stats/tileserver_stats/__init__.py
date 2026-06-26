from datetime import datetime
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
from typer import Typer
from pydantic import BaseModel

from macrostrat.database import Database
from macrostrat.utils import relative_path
from macrostrat.core.config import settings
from macrostrat.core import get_database

load_dotenv()

app = Typer(no_args_is_help=True, short_help="Compile tileserver statistics")


@app.command(name="compute")
def compute_stats(truncate: bool = False):
    """Aggregate tileserver_stats.requests into the day_index / location_index.

    Rolls forward from the processing_status watermark in 100k-row batches until
    the staging table is drained. With --truncate, clears requests once fully
    aggregated (the serial is preserved, so the watermark stays valid)."""
    db = get_database()

    fn = Path(relative_path(__file__, "procedures")) / "run-update.sql"
    # Escape ':' so SQLAlchemy's text() doesn't treat regex fragments like
    # ':www' (in `(?:www\.)`) as bind params; '\:' renders back to a literal ':'.
    sql = text(fn.read_text().replace(":", r"\:"))

    conn = db.engine.connect()
    n_results = 1
    start = datetime.now()
    step = start
    while n_results > 0:
        res = conn.execute(sql, execution_options=dict(no_parameters=True)).first()
        n_results = res.n_rows
        conn.execute(text("COMMIT"))
        next_step = datetime.now()
        dt = (next_step - step).total_seconds()
        print(f"last_row_id={res.last_row_id} rows={n_results} ({dt*1000:.0f} ms)")
        step = next_step

    if truncate:
        conn.execute(text("TRUNCATE TABLE tileserver_stats.requests"))
        conn.execute(text("COMMIT"))

    print(f"Total time: {datetime.now() - start}")


@app.command()
def integrate_schema(drop: bool = False):
    """Merge the tileserver_stats schema into the core Macrostrat database."""
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


@app.command()
def show_database():
    """Show the database connection string."""
    tileserver_db = settings.databases.get("tileserver_stats")
    print(tileserver_db)


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


@app.command(name="process")
def process_ingest_logs(
    prefix: str = "prod",
    limit: Optional[int] = None,
    reprocess: bool = False,
):
    """Ingest Traefik ingress logs from S3/MinIO into tileserver_stats.requests.

    Already-ingested objects are skipped (tracked in tileserver_stats.processed_logs);
    pass --reprocess to re-ingest them. --limit caps the number of new objects.
    """
    config = _resolve_access_logs_config()
    n = ingest_traefik_logs_from_s3(
        config, prefix=prefix, limit=limit, reprocess=reprocess
    )
    print(f"Inserted {n} tile requests")


def _parse_log_object(s3, bucket: str, object_name: str) -> tuple[list[dict], int]:
    """Stream-decompress one zstd JSONL log object and return (tile rows, total lines)."""
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
                rows.append(
                    {
                        "uri": rec.get("RequestPath"),
                        "layer": tile["layer"],
                        "ext": tile["ext"],
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


def ingest_traefik_logs_from_s3(
    config: S3Params,
    *,
    prefix: str = "prod",
    limit: int | None = None,
    reprocess: bool = False,
    insert_batch: int = 10000,
) -> int:
    """Download Traefik access-log dumps from S3/MinIO, parse tile requests, and
    load them into tileserver_stats.requests in the core Macrostrat database.

    Objects are JSONL (one Traefik access-log record per line), zstd-compressed,
    date-partitioned under `<prefix>/YYYY/MM/DD/...`. Each object is processed
    atomically and recorded in tileserver_stats.processed_logs so it is never
    reprocessed (and never needs deleting). NOTE: referrer/app/app_version and
    cache levels (L1/L2) are not present in default Traefik logs and are left
    null until the access-log config is extended — see the feature-area doc.

    Returns the number of tile-request rows inserted.
    """
    s3 = config.get_client()
    db = get_database()

    insert_sql = text(
        """
        INSERT INTO tileserver_stats.requests (uri, layer, ext, x, y, z, time)
        VALUES (:uri, :layer, :ext, :x, :y, :z, :time)
        """
    )
    record_sql = text(
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

    with db.engine.connect() as conn:
        already = {
            row[0]
            for row in conn.execute(
                text("SELECT object_name FROM tileserver_stats.processed_logs")
            )
        }

    inserted = 0
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

        with db.engine.begin() as conn:
            for start in range(0, len(rows), insert_batch):
                conn.execute(insert_sql, rows[start : start + insert_batch])
            conn.execute(
                record_sql,
                {
                    "object_name": obj.object_name,
                    "etag": getattr(obj, "etag", None),
                    "size": obj.size,
                    "last_modified": getattr(obj, "last_modified", None),
                    "num_records": n_records,
                    "num_tile_requests": len(rows),
                },
            )

        inserted += len(rows)
        print(f"{obj.object_name}: {len(rows)}/{n_records} tile requests")

    print(f"Processed {n_objects} new object(s), inserted {inserted} tile requests")
    return inserted
