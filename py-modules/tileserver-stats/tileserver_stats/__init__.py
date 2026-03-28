from datetime import datetime
from pathlib import Path
import asyncio
import json
import tempfile
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
    """Run the update procedure."""
    tileserver_db = settings.databases.get("tileserver_stats")
    db = Database(tileserver_db)

    # Run update
    fn = Path(relative_path(__file__, "procedures")) / "run-update.sql"
    sql = text(fn.read_text().replace(":", r"\:"))

    # check query timing
    conn = db.engine.connect()
    n_results = 10000
    start = datetime.now()
    step = start
    while n_results > 0:
        res = conn.execute(sql, execution_options=dict(no_parameters=True)).first()
        n_results = res.n_rows
        conn.execute(text("COMMIT"))
        next_step = datetime.now()
        dt = (next_step - step).total_seconds()
        print(f"{res.last_row_id} ({dt*1000:.0f} ms)")
        step = next_step

    if truncate and n_results == 0:
        conn.execute(text("TRUNCATE TABLE requests"))

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


@app.command(name="process")
def process_ingest_logs():
    """Ingest Traefik ingress logs from S3/MinIO."""
    storage_cfg = getattr(settings, "storage")
    res = get_config_attrs(getattr(storage_cfg, "access_logs"))

    ingest_traefik_logs_from_s3(res)


def ingest_traefik_logs_from_s3(
    config: S3Params,
    *,
    limit: int | None = 5000,
) -> int:
    """
    Download Traefik ingress logs from S3/MinIO, decompress Zstd JSON files,
    subset relevant records, and insert them into tileserver_stats.requests.

    Expected log format:
      - one JSON object per line, or a JSON array of objects
      - records should contain fields like:
          uri, method, status, time, referrer, app, app_version, cache_hit, redis_hit

    Args:
        bucket: S3 bucket name.
        prefix: Only process objects under this prefix.
        subset: Optional maximum number of log records to process per object.
        limit: Optional maximum number of objects to process.

    Returns:
        Number of inserted rows.
    """
    # MinIO client from settings
    s3 = config.get_client()
    bucket = config.bucket
    prefix = "prod"

    tileserver_db = settings.databases.get("tileserver_stats")
    db = Database(tileserver_db)

    insert_sql = text(
        """
        INSERT INTO tileserver_stats.requests (
            uri, layer, ext, x, y, z, referrer, app, app_version, cache_hit, redis_hit, time
        ) VALUES (
            :uri, :layer, :ext, :x, :y, :z, :referrer, :app, :app_version, :cache_hit, :redis_hit, :time
        )
        """
    )

    inserted = 0
    object_count = 0

    for obj in s3.list_objects(bucket, prefix=prefix, recursive=True):
        if limit is not None and object_count >= limit:
            break
        if not obj.object_name.endswith(".zst"):
            continue

        object_count += 1
        response = s3.get_object(bucket, obj.object_name)
        print(obj.object_name)
        try:
            dctx = zstd.ZstdDecompressor()
            with dctx.stream_reader(response) as reader:
                # Read decompressed bytes in chunks and parse lines
                with tempfile.SpooledTemporaryFile(
                    max_size=32 * 1024 * 1024, mode="w+b"
                ) as tmp:
                    while True:
                        chunk = reader.read(1024 * 1024)
                        if not chunk:
                            break
                        tmp.write(chunk)

                    tmp.seek(0)
                    raw_text = tmp.read().decode("utf-8", errors="replace")

            # Support either JSONL or a JSON array
            raw_text = raw_text.strip()
            if not raw_text:
                continue

            if raw_text.startswith("["):
                records = json.loads(raw_text)
            else:
                records = [
                    json.loads(line) for line in raw_text.splitlines() if line.strip()
                ]

            print(len(records))
            print(records[0])
            continue
            for record in records:
                # Filter to records that match tile queries
                path = record.get("RequestPath")
                is_tile = re.match(r"(\d+)/(\d+)/(\d+)", path)
                print(path)
                if is_tile:
                    print(path)

            continue

            # Subset to relevant log entries
            if subset is not None:
                records = records[:subset]

            rows = []
            for rec in records:
                uri = rec.get("uri") or rec.get("request_uri") or ""
                if not uri:
                    continue

                rows.append(
                    {
                        "uri": uri,
                        "layer": rec.get("layer"),
                        "ext": rec.get("ext"),
                        "x": rec.get("x"),
                        "y": rec.get("y"),
                        "z": rec.get("z"),
                        "referrer": rec.get("referrer"),
                        "app": rec.get("app"),
                        "app_version": rec.get("app_version"),
                        "cache_hit": bool(rec.get("cache_hit", False)),
                        "redis_hit": bool(rec.get("redis_hit", False)),
                        "time": rec.get("time") or datetime.utcnow(),
                    }
                )

            if rows:
                with db.engine.begin() as conn:
                    conn.execute(insert_sql, rows)
                inserted += len(rows)

        finally:
            response.close()
            response.release_conn()

    return inserted
