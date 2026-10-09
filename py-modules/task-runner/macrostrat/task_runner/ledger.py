"""The `tasks.run` ledger: what the runner was asked to do, by whom, how it ended.

Sync helpers take a `macrostrat.database.Database`; the SQL constants serve the
API's async engine for the two reads a streaming route makes.
"""

import json
from datetime import datetime, timezone

from macrostrat.database import Database

LIVE_STATES = ("queued", "running")
FINAL_STATES = ("succeeded", "failed", "cancelled", "killed")

# Everything but the archived log, which only the output route serves.
RUN_COLUMNS = """
    r.id, r.task, r.params, r.requested_by, u.display_name AS requested_by_name,
    r.celery_task_id, r.state, r.created_on, r.started_on, r.finished_on,
    r.result, r.error
"""
RUN_FROM = (
    'FROM tasks.run r LEFT JOIN macrostrat_auth."user" u ON u.id = r.requested_by'
)

RUN_STATE_SQL = "SELECT state FROM tasks.run WHERE id = CAST(:id AS uuid)"
RUN_LOG_SQL = "SELECT log FROM tasks.run WHERE id = CAST(:id AS uuid)"


def create_run(
    db: Database, *, task: str, params: dict, requested_by: int | None
) -> str:
    run_id = db.run_query(
        """
        INSERT INTO tasks.run (task, params, requested_by)
        VALUES (:task, CAST(:params AS jsonb), :requested_by)
        RETURNING id
        """,
        dict(task=task, params=json.dumps(params), requested_by=requested_by),
    ).scalar()
    db.session.commit()
    return str(run_id)


def set_celery_task(db: Database, run_id: str, celery_task_id: str) -> None:
    db.run_query(
        "UPDATE tasks.run SET celery_task_id = :tid WHERE id = CAST(:id AS uuid)",
        dict(id=run_id, tid=celery_task_id),
    )
    db.session.commit()


def get_run(db: Database, run_id: str):
    return db.run_query(
        f"SELECT {RUN_COLUMNS} {RUN_FROM} WHERE r.id = CAST(:id AS uuid)",
        dict(id=run_id),
    ).first()


def list_runs(db: Database, *, limit: int = 50):
    return db.run_query(
        f"SELECT {RUN_COLUMNS} {RUN_FROM} ORDER BY r.created_on DESC LIMIT :limit",
        dict(limit=limit),
    ).all()


def live_run(db: Database, task: str):
    """The queued or running run of `task`, if there is one."""
    return db.run_query(
        f"SELECT {RUN_COLUMNS} {RUN_FROM}"
        " WHERE r.task = :task AND r.state IN ('queued', 'running')",
        dict(task=task),
    ).first()


def start_run(db: Database, run_id: str) -> None:
    db.run_query(
        "UPDATE tasks.run SET state = 'running', started_on = :now"
        " WHERE id = CAST(:id AS uuid)",
        dict(id=run_id, now=_now()),
    )
    db.session.commit()


def finish_run(
    db: Database,
    run_id: str,
    *,
    state: str,
    result=None,
    error: str | None = None,
    log: str | None = None,
) -> None:
    assert state in FINAL_STATES, state
    db.run_query(
        """
        UPDATE tasks.run
        SET state = :state, finished_on = :now, result = CAST(:result AS jsonb),
            error = :error, log = :log
        WHERE id = CAST(:id AS uuid)
        """,
        dict(
            id=run_id,
            state=state,
            now=_now(),
            result=json.dumps(result, default=str) if result is not None else None,
            error=error,
            log=log,
        ),
    )
    db.session.commit()


def get_log(db: Database, run_id: str) -> str | None:
    return db.run_query(RUN_LOG_SQL, dict(id=run_id)).scalar()


def _now() -> datetime:
    return datetime.now(timezone.utc)
