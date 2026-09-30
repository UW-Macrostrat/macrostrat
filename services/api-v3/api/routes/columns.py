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
import re
from uuid import uuid4

import minio
from celery.result import AsyncResult
from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from minio.error import S3Error

from api.celery_app import celery_app
from api.routes.security import TokenData, get_user_token_from_cookie, has_access


def _format_task_error(error) -> str:
    """Return a user-readable message from a Celery/SQLAlchemy/Postgres error."""
    raw = str(error)

    # Some Celery serializers preserve escaped newlines in the exception repr.
    text = raw.replace("\\n", "\n")

    # Only clean up database errors. Leave normal validation errors untouched.
    if "psycopg.errors." not in text:
        return raw

    # Drop everything before the actual psycopg exception.
    match = re.search(
        r"(?:psycopg\.errors\.[A-Za-z0-9_]+[:)]\s*)(.*)",
        text,
        flags=re.DOTALL,
    )
    if match:
        text = match.group(1)

    # SQLAlchemy appends SQL, parameters, and documentation links.
    for marker in (
        "\n[SQL:",
        "\n[parameters:",
        "\n[Parameters:",
        "\n(Background on this error",
    ):
        text = text.split(marker, 1)[0]

    return text.strip()


# Object-storage bucket that column-ingest uploads are written to (and the worker
# pulls from). Hardcoded — not read from S3_BUCKET — so the API and worker always
# agree on one location. Every storage call in this module is pinned to this
# bucket; nothing here touches any other bucket.
BUCKET = "temp-storage"

# Prefix under `temp-storage` holding the downloadable example spreadsheet(s) the
# /columns/ingestion page offers. Downloads are restricted to this prefix so the
# endpoint can never serve another user's in-flight upload elsewhere in the bucket.
EXAMPLE_PREFIX = "column-ingest/ff5d060b-36f4-4bf7-888b-e2c075822d9d/"


def _storage_client() -> minio.Minio:
    """MinIO client for the temp-storage bucket (api-v3's S3 credentials)."""
    return minio.Minio(
        endpoint=os.environ["S3_HOST"],
        access_key=os.environ["S3_ACCESS_KEY"],
        secret_key=os.environ["S3_SECRET_KEY"],
        secure=True,
    )


router = APIRouter(
    prefix="/columns",
    tags=["columns"],
    responses={404: {"description": "Not found"}},
)


@router.post("/ingest")
async def ingest_columns(
    file: UploadFile,
    dry_run: bool = Form(True),
    user_token: TokenData | None = Depends(get_user_token_from_cookie),
    user_has_access: bool = Depends(has_access),
):
    """Upload a column spreadsheet and enqueue its ingestion.

    Any signed-in user may submit, but only admins may persist. For a non-admin
    (web_user) ``dry_run`` is forced on regardless of the submitted value, so a
    web_user can only ever validate — never write. This server-side enforcement
    is the real boundary; the web checkbox is only a convenience mirror of it.

    Stores the file in object storage and hands the worker a reference, then
    returns the Celery task id to poll via ``GET /columns/ingest/{task_id}``.
    ``dry_run`` is forwarded to the worker, which validates the file without
    persisting.
    """
    if user_token is None:
        raise HTTPException(status_code=401, detail="Not authenticated")

    # Non-admins are confined to dry runs — ignore whatever the form submitted.
    if not user_has_access:
        dry_run = True

    client = _storage_client()
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
async def ingest_status(
    task_id: str,
    user_token: TokenData | None = Depends(get_user_token_from_cookie),
):
    """Report the status/result of a column-ingestion task for the web poller.

    Requires a signed-in user (web_user or web_admin) so a submitter can poll
    their own task; anonymous callers are rejected. Matches ``POST /ingest``,
    which any signed-in user may call.
    """
    if user_token is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    result = AsyncResult(task_id, app=celery_app)
    body: dict = {"task_id": task_id, "state": result.state}
    if result.failed():
        body["error"] = _format_task_error(result.result)
        body["traceback"] = result.traceback
    elif result.successful():
        body["result"] = result.result
    return body


@router.get("/examples")
async def list_examples(
    user_token: TokenData | None = Depends(get_user_token_from_cookie),
):
    """List the example spreadsheets offered on the ingestion page.

    Signed-in users only. Reads only the fixed example prefix within
    ``temp-storage``; it never lists any other bucket or prefix.
    """
    if user_token is None:
        raise HTTPException(status_code=401, detail="Not authenticated")

    client = _storage_client()
    examples = []
    for obj in client.list_objects(BUCKET, prefix=EXAMPLE_PREFIX, recursive=True):
        filename = obj.object_name.rsplit("/", 1)[-1]
        if not filename:
            continue
        examples.append(
            {"key": obj.object_name, "filename": filename, "size": obj.size}
        )
    return {"examples": examples}


@router.get("/examples/download")
async def download_example(
    key: str,
    user_token: TokenData | None = Depends(get_user_token_from_cookie),
):
    """Stream one example spreadsheet from ``temp-storage``.

    Signed-in users only, and confined to the example prefix — an arbitrary key
    (e.g. another user's upload elsewhere in the bucket) is refused. Streams
    through the API so the browser never needs credentials for object storage.
    """
    if user_token is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    if not key.startswith(EXAMPLE_PREFIX):
        raise HTTPException(
            status_code=400, detail="Only example files may be downloaded"
        )

    client = _storage_client()
    try:
        response = client.get_object(BUCKET, key)
    except S3Error:
        raise HTTPException(status_code=404, detail="Example not found")

    def stream():
        try:
            yield from response.stream(32 * 1024)
        finally:
            response.close()
            response.release_conn()

    filename = key.rsplit("/", 1)[-1] or "example.xlsx"
    return StreamingResponse(
        stream(),
        media_type=(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ),
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
