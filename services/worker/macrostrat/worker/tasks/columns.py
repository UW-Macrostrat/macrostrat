"""
Column-ingestion Celery task.

Downloads the uploaded spreadsheet from object storage, then calls the existing
`macrostrat.column_ingestion` ingest logic. `dry_run` is forwarded to that
function, which rolls its transaction back instead of committing.

Requires the `columns` worker extra (`macrostrat.column-ingestion`).

NB: `ingest_columns_from_file` gains its `dry_run` parameter (and a structured
return value) on the paired column-ingestion branch. Until that lands, this call
raises `TypeError` — which fails safe (nothing is ingested) rather than silently
committing.
"""

import os
import tempfile
from pathlib import Path

from minio import Minio

from macrostrat.database import Database
from macrostrat.worker.app import app


def _database() -> Database:
    url = os.environ.get("DB_URL")
    if not url:
        raise RuntimeError("DB_URL environment variable is not set")
    return Database(url)


def _storage() -> Minio:
    return Minio(
        os.environ["S3_ENDPOINT"],
        access_key=os.environ["S3_ACCESS_KEY"],
        secret_key=os.environ["S3_SECRET_KEY"],
        secure=os.environ.get("S3_SECURE", "false").lower() == "true",
    )


@app.task(name="macrostrat.columns.ingest")
def ingest_columns_task(ref: dict) -> dict:
    """Ingest a column spreadsheet previously uploaded to object storage.

    ``ref`` = ``{bucket, key, filename, dry_run}``. Downloads the object to a temp
    file and runs the ingest; on ``dry_run`` the ingest rolls back instead of
    committing (enforced inside ``ingest_columns_from_file``).
    """
    from macrostrat.column_ingestion.ingest import ingest_columns_from_file

    dry_run = ref.get("dry_run", True)
    db = _database()
    client = _storage()

    suffix = Path(ref["filename"]).suffix or ".xlsx"
    with tempfile.NamedTemporaryFile(suffix=suffix) as tmp:
        client.fget_object(ref["bucket"], ref["key"], tmp.name)
        result = ingest_columns_from_file(db, tmp.name, dry_run=dry_run)

    return {
        "key": ref["key"],
        "filename": ref["filename"],
        "dry_run": dry_run,
        "result": result,
    }
