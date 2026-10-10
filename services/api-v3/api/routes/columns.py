"""
Column-ingestion API routes.

`POST /columns/ingest` accepts an uploaded column spreadsheet and enqueues the
`macrostrat.columns.ingest` Celery task. A dry run carries the file inline in the
task message; a real ingest stashes it in object storage, where it is kept. `GET /columns/ingest/{task_id}` reports the task's status/result.

The API only *forwards* the `dry_run` flag; the worker (and the ingest function it
calls) enforce it. See the "Column ingestion task" feature-area note.
"""

import base64
import os
import re
from uuid import uuid4

import minio
from celery.result import AsyncResult
from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from minio.error import S3Error
from pydantic import BaseModel, Field
from sqlalchemy import text

from api.celery_app import celery_app
from api.database import DatabaseDep
from api.routes.security import TokenData, get_user_token_from_cookie, has_access


def _placement(
    project_id: int | None, col_group_id: int | None, col_group: str | None
) -> dict | None:
    """Where the columns should go, when the caller says; else the file decides.

    The pipeline's `Placement`: a project, and a group by id or by name. With a
    project and no group, the file's own project becomes the group's name.
    """
    if project_id is None and col_group_id is None and not col_group:
        return None
    return {
        "project_id": project_id,
        "col_group_id": col_group_id,
        "col_group": col_group or None,
    }


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

# Prefixes under `temp-storage` holding the downloadable example spreadsheet(s)
# the /columns/ingestion page offers. Each upload lands under its own
# `column-ingest/<uuid>/` folder, so a prefix here pins one curated upload as an
# example. Listing and downloads are restricted to these prefixes, so the
# endpoint can never serve another user's in-flight upload elsewhere in the bucket.
EXAMPLE_PREFIXES = (
    "column-ingest/ff5d060b-36f4-4bf7-888b-e2c075822d9d/",
    # Cordie et al. 2019 (Poleta Fm.) — curated example.
    "column-ingest/3cd66291-e261-446f-88b5-bf4f27c1a017/",
)

# Cap on a dry-run upload carried inline in the task message.
MAX_INLINE_BYTES = 10 * 1024 * 1024


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
    project_id: int | None = Form(None),
    col_group_id: int | None = Form(None),
    col_group: str | None = Form(None),
    user_token: TokenData | None = Depends(get_user_token_from_cookie),
    user_has_access: bool = Depends(has_access),
):
    """Upload a column spreadsheet and enqueue its ingestion.

    Any signed-in user may submit, but only admins may persist. For a non-admin
    (web_user) ``dry_run`` is forced on regardless of the submitted value, so a
    web_user can only ever validate — never write. This server-side enforcement
    is the real boundary; the web checkbox is only a convenience mirror of it.

    ``project_id``, ``col_group_id`` and ``col_group`` place the columns instead
    of the file's metadata: a project, and a group by id or by a name that is
    created if new. A project without a group demotes the file's project to the
    group, which is how files from many sources nest under one project.

    A dry run sends the file to the worker inline; a real ingest stores it in
    object storage and hands the worker a reference. Returns the Celery task id
    to poll via ``GET /columns/ingest/{task_id}``.
    ``dry_run`` is forwarded to the worker, which validates the file without
    persisting.
    """
    if user_token is None:
        raise HTTPException(status_code=401, detail="Not authenticated")

    # Non-admins are confined to dry runs — ignore whatever the form submitted.
    if not user_has_access:
        dry_run = True

    ref = {"filename": file.filename, "dry_run": dry_run}
    placement = _placement(project_id, col_group_id, col_group)
    if placement is not None:
        ref["placement"] = placement
    if dry_run:
        # A dry run's file is never kept, so it travels in the task message
        # rather than through object storage.
        content = await file.read()
        if len(content) > MAX_INLINE_BYTES:
            raise HTTPException(status_code=413, detail="File too large")
        ref["content"] = base64.b64encode(content).decode("ascii")
    else:
        ref["bucket"] = BUCKET
        ref["key"] = f"column-ingest/{uuid4()}/{file.filename}"
        _storage_client().put_object(
            bucket_name=BUCKET,
            object_name=ref["key"],
            data=file.file,
            length=file.size,
            content_type=file.content_type,
        )

    task = celery_app.send_task("macrostrat.columns.ingest", args=[ref])
    return {"task_id": task.id, "key": ref.get("key"), "dry_run": dry_run}


class ColumnSubmission(BaseModel):
    """A column dataset as the column-ingestion format's tables, in JSON.

    ``data`` holds the sheets by name — ``metadata`` as key/value pairs, the others
    as lists of row objects — exactly as a workbook would. The editor builds this
    from its units sheet, so a column edited in the browser and one uploaded as a
    spreadsheet are checked and written by the same code.
    """

    data: dict = Field(..., description="Sheets by name: metadata, columns, units, …")
    dry_run: bool = True
    # Placement, as for an upload: these override the metadata's project.
    project_id: int | None = None
    col_group_id: int | None = None
    col_group: str | None = None


@router.post("/submit")
async def submit_columns(
    submission: ColumnSubmission,
    user_token: TokenData | None = Depends(get_user_token_from_cookie),
    user_has_access: bool = Depends(has_access),
):
    """Check — or, for an admin, write — a column dataset given as JSON.

    Enqueues ``macrostrat.columns.ingest-data``; poll ``GET /columns/ingest/{task_id}``
    for the result, which carries graded notices and the ingested data as the API
    would serve it. Non-admins are confined to dry runs, as for uploads.
    """
    if user_token is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    dry_run = submission.dry_run
    if not user_has_access:
        dry_run = True
    if "units" not in submission.data:
        raise HTTPException(status_code=422, detail="`data.units` is required")

    payload = {"data": submission.data, "dry_run": dry_run}
    placement = _placement(
        submission.project_id, submission.col_group_id, submission.col_group
    )
    if placement is not None:
        payload["placement"] = placement
    task = celery_app.send_task("macrostrat.columns.ingest-data", args=[payload])
    return {"task_id": task.id, "dry_run": dry_run}


class ColumnPlacement(BaseModel):
    """Where an existing column belongs: a project and a group in it."""

    project_id: int | None = None
    col_group_id: int | None = None
    #: A group name: an existing group of the project, or one to create.
    col_group: str | None = None


@router.patch("/{col_id}/placement")
async def update_column_placement(
    col_id: int,
    placement: ColumnPlacement,
    database: DatabaseDep,
    user_token: TokenData | None = Depends(get_user_token_from_cookie),
    user_has_access: bool = Depends(has_access),
):
    """Move a column to a project and group (administrators only).

    A group given by id must belong to the project; one given by name is got or
    created in it. Moving to another project needs a group named for that
    project, since a group belongs to one project. Direct, not through the
    ingestion task: nothing is re-read or rewritten but the two columns of
    ``macrostrat.cols``.
    """
    if user_token is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    if not user_has_access:
        raise HTTPException(
            status_code=403, detail="Only administrators can move columns"
        )

    async with database.async_connection() as conn:
        row = (
            (
                await conn.execute(
                    text(
                        "SELECT id, project_id, col_group_id FROM macrostrat.cols WHERE id = :id"
                    ),
                    {"id": col_id},
                )
            )
            .mappings()
            .first()
        )
        if row is None:
            raise HTTPException(status_code=404, detail=f"Column {col_id} not found")

        project_id = placement.project_id or row["project_id"]
        project_changed = project_id != row["project_id"]

        if placement.col_group_id is not None:
            group = (
                (
                    await conn.execute(
                        text(
                            "SELECT id, col_group FROM macrostrat.col_groups"
                            " WHERE id = :id AND project_id = :project_id"
                        ),
                        {"id": placement.col_group_id, "project_id": project_id},
                    )
                )
                .mappings()
                .first()
            )
            if group is None:
                raise HTTPException(
                    status_code=422,
                    detail=f"Group {placement.col_group_id} is not in project {project_id}",
                )
        elif placement.col_group:
            name = placement.col_group.strip()
            group = (
                (
                    await conn.execute(
                        text(
                            "SELECT id, col_group FROM macrostrat.col_groups"
                            " WHERE project_id = :project_id AND col_group = :name"
                        ),
                        {"project_id": project_id, "name": name},
                    )
                )
                .mappings()
                .first()
            )
            if group is None:
                await _set_audit_context(conn, user_token, col_id)
                group = (
                    (
                        await conn.execute(
                            text(
                                "INSERT INTO macrostrat.col_groups (project_id, col_group, col_group_long)"
                                " VALUES (:project_id, :name, :long) RETURNING id, col_group"
                            ),
                            {
                                "project_id": project_id,
                                "name": name,
                                "long": f"{name} column group",
                            },
                        )
                    )
                    .mappings()
                    .first()
                )
        elif project_changed:
            raise HTTPException(
                status_code=422,
                detail="Moving a column to another project needs a group in that project",
            )
        else:
            group = {"id": row["col_group_id"], "col_group": None}

        if project_changed or group["id"] != row["col_group_id"]:
            await _set_audit_context(conn, user_token, col_id)
            await conn.execute(
                text(
                    "UPDATE macrostrat.cols SET project_id = :project_id,"
                    " col_group_id = :col_group_id WHERE id = :id"
                ),
                {"project_id": project_id, "col_group_id": group["id"], "id": col_id},
            )

        names = (
            (
                await conn.execute(
                    text(
                        "SELECT p.project, g.col_group FROM macrostrat.projects p"
                        " LEFT JOIN macrostrat.col_groups g ON g.id = :group_id"
                        " WHERE p.id = :project_id"
                    ),
                    {"group_id": group["id"], "project_id": project_id},
                )
            )
            .mappings()
            .first()
        )

    return {
        "col_id": col_id,
        "project_id": project_id,
        "project": names["project"] if names else None,
        "col_group_id": group["id"],
        "col_group": names["col_group"] if names else None,
    }


async def _set_audit_context(conn, user_token: TokenData, col_id: int) -> None:
    """Attribute the writes in the change-tracking trail, when it is installed
    (see `macrostrat.core.database.set_audit_context`). Transaction-local, which
    is where these statements run."""
    installed = (
        await conn.execute(
            text(
                "SELECT to_regprocedure('audit.set_context(text,text,boolean)') IS NOT NULL"
            )
        )
    ).scalar()
    if not installed:
        return
    await conn.execute(
        text("SELECT audit.set_context(:actor, :batch, true)"),
        {"actor": f"user:{user_token.sub}", "batch": f"column-placement:{col_id}"},
    )


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
    for prefix in EXAMPLE_PREFIXES:
        for obj in client.list_objects(BUCKET, prefix=prefix, recursive=True):
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
    if not key.startswith(EXAMPLE_PREFIXES):
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
