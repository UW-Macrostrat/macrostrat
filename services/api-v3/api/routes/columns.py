"""
Column-ingestion API routes.

`POST /columns/ingest` accepts an uploaded column spreadsheet, stashes it in
object storage (so the separate worker container can read it — a Redis/JSON task
message can't carry the file itself), and enqueues the `macrostrat.columns.ingest`
Celery task. `GET /columns/ingest/{task_id}` reports the task's status/result.

The API only *forwards* the `dry_run` flag; the worker (and the ingest function it
calls) enforce it. See the "Column ingestion task" feature-area note.
"""

import os
from uuid import uuid4

import minio
from celery.result import AsyncResult
from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile

from api.celery_app import celery_app
from api.routes.security import has_access

# Object-storage bucket that column-ingest uploads are written to (and the worker
# pulls from). Hardcoded — not read from S3_BUCKET — so the API and worker always
# agree on one location.
BUCKET = "temp-storage"

router = APIRouter(
    prefix="/columns",
    tags=["columns"],
    responses={404: {"description": "Not found"}},
)


@router.post("/ingest")
async def ingest_columns(
    file: UploadFile,
    dry_run: bool = Form(True),
    user_has_access: bool = Depends(has_access),
):
    """Upload a column spreadsheet and enqueue its ingestion.

    Stores the file in object storage and hands the worker a reference, then
    returns the Celery task id to poll via ``GET /columns/ingest/{task_id}``.
    ``dry_run`` (default on) is forwarded to the worker, which validates the file
    without persisting.
    """
    if not user_has_access:
        raise HTTPException(
            status_code=403, detail="User does not have access to ingest columns"
        )

    # TODO this uses the api/routes/ingest.py::create_object credentials for maps. We need to update this
    # to where the columns are stored.
    # or should we store the file as a blob? i don't think this is possible since the worker is in a different container
    client = minio.Minio(
        endpoint=os.environ["S3_HOST"],
        access_key=os.environ["access_key"],
        secret_key=os.environ["secret_key"],
        secure=True,
    )
    bucket = BUCKET
    key = f"column-ingest/{uuid4()}/{file.filename}"
    client.put_object(
        bucket_name=bucket,
        object_name=key,
        data=file.file,
        length=file.size,
        content_type=file.content_type,
    )

    # The worker fetches `bucket`/`key` itself (using its own S3 endpoint/creds),
    # so the payload only carries the small reference, not the file.
    task = celery_app.send_task(
        "macrostrat.columns.ingest",
        args=[
            {
                "bucket": bucket,
                "key": key,
                "filename": file.filename,
                "dry_run": dry_run,
            }
        ],
    )
    return {"task_id": task.id, "key": key, "dry_run": dry_run}


@router.get("/ingest/{task_id}")
async def ingest_status(task_id: str):
    """Report the status/result of a column-ingestion task for the web poller."""
    result = AsyncResult(task_id, app=celery_app)
    body: dict = {"task_id": task_id, "state": result.state}
    if result.failed():
        # result.result is the worker-side exception; expose it (admin-only route).
        body["error"] = str(result.result)
        body["traceback"] = result.traceback
    elif result.successful():
        body["result"] = result.result
    return body
