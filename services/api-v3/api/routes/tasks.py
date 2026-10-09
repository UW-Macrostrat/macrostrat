"""Management tasks: start, watch, cancel and kill runs of registered tasks.

Admin only. A task is a `TaskSpec` registered through the `macrostrat.tasks`
entry points; this service validates parameters against its model, records the
run in `tasks.run`, and enqueues `macrostrat.tasks.run` for the admin worker,
which executes it and streams its terminal output to Redis.
`GET /runs/{id}/output` serves that stream as Server-Sent Events — replaying
from the start or from `Last-Event-ID`, then following until the run ends —
and the archived copy once the stream has expired. Never a shell: only a
listed task, with parameters its model accepts, can be started.
"""

import json
import os
from datetime import datetime
from functools import lru_cache
from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, ValidationError
from redis import Redis
from redis.asyncio import Redis as AsyncRedis
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from api.celery_app import celery_app
from api.database import DatabaseDep
from api.routes.security import TokenData, require_admin
from macrostrat.task_runner import ledger, load_registry
from macrostrat.task_runner.output import control_channel, output_key, read_all
from macrostrat.task_runner.tail import tail_output

router = APIRouter(prefix="/tasks", tags=["Tasks"])

RUN_TASK = "macrostrat.tasks.run"


def redis_url() -> str:
    """Where runs stream their output; the broker unless told otherwise."""
    return os.environ.get(
        "REDIS_URL", os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/0")
    )


@lru_cache
def registry():
    return load_registry()


class TaskInfo(BaseModel):
    name: str
    title: str
    description: str
    params_schema: dict


class RunRequest(BaseModel):
    task: str
    params: dict[str, Any] = {}


class Run(BaseModel):
    """A ledger row, without its archived log."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    task: str
    params: dict
    requested_by: Optional[int]
    requested_by_name: Optional[str]
    celery_task_id: Optional[str]
    state: str
    created_on: datetime
    started_on: Optional[datetime]
    finished_on: Optional[datetime]
    result: Any
    error: Optional[str]


@router.get("", response_model=list[TaskInfo])
def list_tasks(_admin: TokenData = Depends(require_admin)) -> list[TaskInfo]:
    """The catalog: every registered task with its parameter schema."""
    return [
        TaskInfo(
            name=spec.name,
            title=spec.title,
            description=spec.description,
            params_schema=spec.schema(),
        )
        for spec in registry().values()
    ]


@router.get("/runs", response_model=list[Run])
def list_runs(
    database: DatabaseDep, limit: int = 50, _admin: TokenData = Depends(require_admin)
) -> list[Run]:
    rows = ledger.list_runs(database.sync, limit=min(max(limit, 1), 500))
    return [Run.model_validate(row) for row in rows]


@router.post("/runs", response_model=Run, status_code=202)
def start_run(
    body: RunRequest, database: DatabaseDep, admin: TokenData = Depends(require_admin)
) -> Run:
    """Record a run and hand it to the admin worker.

    One live run per task: a second is refused with 409 naming the first, and
    the ledger's partial unique index holds that under a race.
    """
    spec = registry().get(body.task)
    if spec is None:
        raise HTTPException(status_code=404, detail=f"No task named {body.task!r}")
    try:
        params = spec.parse(body.params)
    except ValidationError as err:
        raise HTTPException(status_code=422, detail=json.loads(err.json()))

    db = database.sync
    live = ledger.live_run(db, spec.name)
    if live is not None:
        raise HTTPException(
            status_code=409,
            detail=f"{spec.name} is already {live.state} (run {live.id})",
        )
    requested_by = db.run_query(
        'SELECT id FROM macrostrat_auth."user" WHERE sub = :sub', dict(sub=admin.sub)
    ).scalar()
    try:
        run_id = ledger.create_run(
            db,
            task=spec.name,
            params=params.model_dump(mode="json"),
            requested_by=requested_by,
        )
    except IntegrityError:
        db.session.rollback()
        raise HTTPException(status_code=409, detail=f"{spec.name} is already running")

    try:
        task = celery_app.send_task(RUN_TASK, args=[run_id])
    except Exception as err:
        ledger.finish_run(db, run_id, state="failed", error=f"Could not enqueue: {err}")
        raise HTTPException(status_code=503, detail=f"Could not enqueue the run: {err}")
    ledger.set_celery_task(db, run_id, task.id)
    return Run.model_validate(ledger.get_run(db, run_id))


@router.get("/runs/{run_id}", response_model=Run)
def get_run(
    run_id: str, database: DatabaseDep, _admin: TokenData = Depends(require_admin)
) -> Run:
    return Run.model_validate(_require_run(database, run_id))


@router.post("/runs/{run_id}/cancel", response_model=Run)
def cancel_run(
    run_id: str, database: DatabaseDep, admin: TokenData = Depends(require_admin)
) -> Run:
    """End a run the way Ctrl-C would.

    A running task gets `cancel` on its control channel: the worker interrupts
    it and cancels its statements, and records the outcome itself. One still
    queued is revoked and recorded here, since no worker has it.
    """
    db = database.sync
    run = _require_run(database, run_id)
    if run.state == "queued":
        if run.celery_task_id:
            celery_app.control.revoke(run.celery_task_id)
        ledger.finish_run(
            db,
            run_id,
            state="cancelled",
            error=f"Cancelled before it started by {admin.sub}",
        )
    elif run.state == "running":
        Redis.from_url(redis_url()).publish(control_channel(run_id), "cancel")
    else:
        raise HTTPException(status_code=409, detail=f"Run is already {run.state}")
    return Run.model_validate(ledger.get_run(db, run_id))


@router.post("/runs/{run_id}/kill", response_model=Run)
def kill_run(
    run_id: str, database: DatabaseDep, admin: TokenData = Depends(require_admin)
) -> Run:
    """Kill the worker process of a run that will not stop.

    The process is gone before it can record anything, so the row and the
    archived output are written here. The last resort after `cancel`.
    """
    db = database.sync
    run = _require_run(database, run_id)
    if run.state not in ledger.LIVE_STATES:
        raise HTTPException(status_code=409, detail=f"Run is already {run.state}")
    if run.celery_task_id:
        celery_app.control.revoke(run.celery_task_id, terminate=True, signal="SIGKILL")
    redis = Redis.from_url(redis_url())
    ledger.finish_run(
        db,
        run_id,
        state="killed",
        error=f"Killed by {admin.sub}",
        log=read_all(redis, run_id) or None,
    )
    return Run.model_validate(ledger.get_run(db, run_id))


@router.get("/runs/{run_id}/output")
async def run_output(
    run_id: str,
    request: Request,
    database: DatabaseDep,
    since: Optional[str] = None,
    _admin: TokenData = Depends(require_admin),
):
    """The run's terminal output as Server-Sent Events.

    Each `data` is `{"d": chunk}` — JSON, because a raw carriage return would
    end an SSE line — with the Redis stream entry as its `id`, so a reconnecting
    `EventSource` resumes where it left off. A comment keeps the connection
    alive through quiet stretches; `event: end` carries the final state.
    """
    _uuid(run_id)
    start = request.headers.get("last-event-id") or since or "0-0"

    async def state() -> Optional[str]:
        async with database.async_connection() as conn:
            row = await conn.execute(text(ledger.RUN_STATE_SQL), {"id": run_id})
            return row.scalar()

    current = await state()
    if current is None:
        raise HTTPException(status_code=404, detail="No such run")

    async def events():
        redis = AsyncRedis.from_url(redis_url())
        try:
            if current in ledger.FINAL_STATES and not await redis.exists(
                output_key(run_id)
            ):
                async with database.async_connection() as conn:
                    row = await conn.execute(text(ledger.RUN_LOG_SQL), {"id": run_id})
                    log = row.scalar()
                if log:
                    yield _event("0-0", log)
                yield _end(current)
                return

            async def finished() -> bool:
                return (await state()) in ledger.FINAL_STATES

            async for item in tail_output(
                redis, run_id, since=start, finished=finished
            ):
                if await request.is_disconnected():
                    return
                if item is None:
                    yield ": ping\n\n"
                    continue
                yield _event(*item)
            yield _end(await state())
        finally:
            close = getattr(redis, "aclose", redis.close)
            await close()

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


def _event(entry_id: str, chunk: str) -> str:
    return f"id: {entry_id}\ndata: {json.dumps({'d': chunk})}\n\n"


def _end(state: Optional[str]) -> str:
    return f"event: end\ndata: {json.dumps({'state': state})}\n\n"


def _uuid(run_id: str) -> None:
    try:
        UUID(run_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="No such run")


def _require_run(database, run_id: str):
    _uuid(run_id)
    run = ledger.get_run(database.sync, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="No such run")
    return run
