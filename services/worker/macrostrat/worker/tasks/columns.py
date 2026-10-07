"""
Column-ingestion Celery tasks.

`macrostrat.columns.ingest` takes a spreadsheet from the task message (dry runs)
or from object storage (real ingests) and runs `macrostrat.column_ingestion` over
it; `macrostrat.columns.ingest-data` runs the same logic over the format's tables
given as JSON, which is how an editor submits a column. Both forward `dry_run`,
which the ingest function enforces by rolling its transaction back, and both
return the ingest's result: a summary, graded notices, and the ingested data as
the web API would serve it.

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
        result = _run(ingest_columns_from_file, db, tmp.name, dry_run=dry_run)

    return {
        "key": ref.get("key"),
        "filename": ref["filename"],
        "dry_run": dry_run,
        "result": result,
    }


@app.task(name="macrostrat.columns.ingest-data")
def ingest_column_data_task(payload: dict) -> dict:
    """Ingest a column dataset given as the format's tables in JSON.

    ``payload`` = ``{data: {metadata, columns, units, refs?, facies?}, dry_run}``.
    """
    from macrostrat.column_ingestion.ingest import ingest_column_data

    dry_run = payload.get("dry_run", True)
    db = _database()
    result = _run(ingest_column_data, db, payload["data"], dry_run=dry_run)
    return {"dry_run": dry_run, "result": result}


def _run(fn, db, source, *, dry_run: bool) -> dict:
    """Run an ingest, turning a validation refusal into a result rather than a failure.

    A dataset with error-level notices is refused on a real write. That is an
    outcome to report — the notices are the point — not a task failure, so it comes
    back as the same result shape with ``ok: false`` and no summary.
    """
    from macrostrat.column_ingestion.notices import IngestValidationError

    try:
        return fn(db, source, dry_run=dry_run)
    except IngestValidationError as err:
        return {
            "dry_run": dry_run,
            "ok": False,
            "summary": None,
            "notices": err.notices.to_list(),
            "notice_counts": err.notices.summary(),
            "data": None,
        }
