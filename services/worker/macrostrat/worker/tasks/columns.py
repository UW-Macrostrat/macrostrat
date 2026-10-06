"""
Column-ingestion Celery task.

Takes the spreadsheet from the task message (dry runs) or from object storage
(real ingests), then calls the existing `macrostrat.column_ingestion` ingest
logic. `dry_run` is forwarded to that function, which rolls its transaction back
instead of committing.

Requires the `columns` worker extra (`macrostrat.column-ingestion`).
"""

import base64
import os
import tempfile
from pathlib import Path

from minio import Minio

from macrostrat.database import Database
from macrostrat.worker.app import app

# Object-storage bucket the column-ingest files are pulled from. Hardcoded to
# match the API upload location (api/routes/columns.py) so both agree.
BUCKET = "temp-storage"


def _database() -> Database:
    url = os.environ.get("DB_URL")
    if not url:
        raise RuntimeError("DB_URL environment variable is not set")
    return Database(url)


def _storage() -> Minio:
    return Minio(
        os.environ["S3_HOST"],
        access_key=os.environ["S3_ACCESS_KEY"],
        secret_key=os.environ["S3_SECRET_KEY"],
        secure=True,
    )


@app.task(name="macrostrat.columns.ingest")
def ingest_columns_task(ref: dict) -> dict:
    """Ingest a column spreadsheet previously uploaded to object storage.

    ``ref`` = ``{filename, dry_run}`` plus either ``content`` (the file, base64 —
    sent for dry runs) or ``{bucket, key}`` (an object in storage). Writes the file
    to a temp file and runs the ingest; on ``dry_run`` the ingest rolls back
    instead of committing (enforced inside ``ingest_columns_from_file``).
    """
    from macrostrat.column_ingestion.ingest import ingest_columns_from_file

    dry_run = ref.get("dry_run", True)
    db = _database()

    suffix = Path(ref["filename"]).suffix or ".xlsx"
    with tempfile.NamedTemporaryFile(suffix=suffix) as tmp:
        if "content" in ref:
            tmp.write(base64.b64decode(ref["content"]))
            tmp.flush()
        else:
            _storage().fget_object(BUCKET, ref["key"], tmp.name)
        result = ingest_columns_from_file(db, tmp.name, dry_run=dry_run)

    return {
        "key": ref.get("key"),
        "filename": ref["filename"],
        "dry_run": dry_run,
        "result": result,
    }
