"""Shared log-harvesting machinery: object storage access, record streaming,
and the single-pass capture loop that drives every pipeline.

Log objects are zstd-compressed JSONL — one Traefik access-log record per line —
date-partitioned under `<prefix>/YYYY/MM/DD/HHMM_HASH_access.log.zst`, so object
keys sort chronologically.
"""

import io
import json
from typing import Iterable, Iterator, Optional

import zstandard as zstd

from .pipelines import Pipeline
from .storage import S3Params


def iter_log_records(s3, bucket: str, object_name: str) -> Iterator[dict]:
    """Stream-decompress a zstd JSONL log object, yielding each parsed record.
    Blank and malformed lines are skipped."""
    response = s3.get_object(bucket, object_name)
    try:
        dctx = zstd.ZstdDecompressor()
        with dctx.stream_reader(response) as reader:
            stream = io.TextIOWrapper(reader, encoding="utf-8", errors="replace")
            for line in stream:
                line = line.strip()
                if not line:
                    continue
                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    continue
    finally:
        response.close()
        response.release_conn()


def latest_log_object(s3, bucket: str, prefix: str) -> str | None:
    """The most recently uploaded `.zst` object under `prefix`. Log keys are
    date-partitioned, so they sort chronologically."""
    latest = None
    for obj in s3.list_objects(bucket, prefix=prefix, recursive=True):
        name = obj.object_name
        if name.endswith(".zst") and (latest is None or name > latest):
            latest = name
    return latest


RECORD_LOG = """
    INSERT INTO usage_stats.processed_logs
        (object_name, pipeline, etag, size, last_modified, num_records, num_matched)
    VALUES (:object_name, :pipeline, :etag, :size, :last_modified, :num_records, :num_matched)
    ON CONFLICT (object_name, pipeline) DO UPDATE SET
        etag = EXCLUDED.etag,
        size = EXCLUDED.size,
        last_modified = EXCLUDED.last_modified,
        num_records = EXCLUDED.num_records,
        num_matched = EXCLUDED.num_matched,
        processed_at = now()
"""


def _processed_by_pipeline(db) -> dict[str, set[str]]:
    """Which objects each pipeline has already ingested."""
    processed: dict[str, set[str]] = {}
    for pipeline, object_name in db.run_query(
        "SELECT pipeline, object_name FROM usage_stats.processed_logs"
    ):
        processed.setdefault(pipeline, set()).add(object_name)
    return processed


def capture(
    db,
    config: S3Params,
    pipelines: Iterable[Pipeline],
    *,
    prefix: str = "prod",
    limit: Optional[int] = None,
    reprocess: bool = False,
) -> dict[str, int]:
    """Stream log objects from object storage and feed each one to every
    pipeline that has not yet processed it.

    Each object is read **once** and dispatched to all due pipelines. A full
    backfill moves 15–20 GB of compressed logs, so re-reading the objects per
    pipeline is not affordable — this is the reason the pipeline interface is
    record-at-a-time rather than each pipeline owning its own scan.

    Per object, all due pipelines are written in a single transaction, with
    their `processed_logs` rows written **last** — an interrupted run leaves
    the object unrecorded and re-processes it cleanly next time.

    `db` is a macrostrat.database Database; the caller constructs it, so this
    library holds no configuration of its own.

    Returns the number of matched records per pipeline.
    """
    s3 = config.get_client()

    pipelines = list(pipelines)  # iterated once per object
    processed = {} if reprocess else _processed_by_pipeline(db)
    totals = {p.name: 0 for p in pipelines}

    n_objects = 0
    for obj in s3.list_objects(config.bucket, prefix=prefix, recursive=True):
        if not obj.object_name.endswith(".zst"):
            continue

        due = [p for p in pipelines if obj.object_name not in processed.get(p.name, ())]
        if not due:
            continue
        if limit is not None and n_objects >= limit:
            break
        n_objects += 1

        matched, n_records = _process_object(s3, config.bucket, obj.object_name, due)

        with db.transaction():
            for pipeline in due:
                pipeline.write(db, matched[pipeline.name])
            for pipeline in due:
                db.run_query(
                    RECORD_LOG,
                    {
                        "object_name": obj.object_name,
                        "pipeline": pipeline.name,
                        "etag": getattr(obj, "etag", None),
                        "size": obj.size,
                        "last_modified": getattr(obj, "last_modified", None),
                        "num_records": n_records,
                        "num_matched": len(matched[pipeline.name]),
                    },
                )

        print(f"{obj.object_name}  ({n_records} records)")
        for pipeline in due:
            n = len(matched[pipeline.name])
            totals[pipeline.name] += n
            print(f"  {pipeline.name}: kept {n}")

    summary = ", ".join(f"{name} {n}" for name, n in totals.items())
    print(f"\nProcessed {n_objects} object(s) — {summary}")
    return totals


def _process_object(
    s3, bucket: str, object_name: str, pipelines: list[Pipeline]
) -> tuple[dict[str, list[dict]], int]:
    """Read one log object and fan each record out to every given pipeline."""
    matched: dict[str, list[dict]] = {p.name: [] for p in pipelines}
    n_records = 0
    for rec in iter_log_records(s3, bucket, object_name):
        n_records += 1
        for pipeline in pipelines:
            row = pipeline.parse(rec)
            if row is not None:
                matched[pipeline.name].append(row)
    return matched, n_records
