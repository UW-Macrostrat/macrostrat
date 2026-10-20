"""Execute one run: what the worker task calls."""

import os
import traceback
from contextlib import redirect_stderr, redirect_stdout
from urllib.parse import urlencode, urlsplit, urlunsplit

from redis import Redis

from macrostrat.database import Database

from . import ledger
from .cancel import CancelWatcher, TaskCancelled, cancel_backends, interruptible
from .context import RunContext
from .output import OutputStream, expire, read_all
from .spec import TaskSpec, load_registry

# Rich reads these when it creates a console, so they must be set before the
# task imports anything that does. The worker's service sets them too.
TERMINAL_ENV = {
    "FORCE_COLOR": "1",
    "COLORTERM": "truecolor",
    "TERM": "xterm-256color",
    "COLUMNS": "120",
    "LINES": "40",
}


def execute_run(
    *,
    run_id: str,
    db_url: str,
    redis_url: str,
    registry: dict[str, TaskSpec] | None = None,
) -> dict:
    """Run the ledger row `run_id` to completion and record how it ended.

    Must run in a main thread (see `interruptible`). Output goes to the run's
    Redis stream for the duration; the ledger gets the archived copy.
    """
    for key, value in TERMINAL_ENV.items():
        os.environ.setdefault(key, value)

    redis = Redis.from_url(redis_url)
    ledger_db = Database(db_url)
    run = ledger.get_run(ledger_db, run_id)
    if run is None:
        raise ValueError(f"No run {run_id}")
    spec = (registry or load_registry())[run.task]
    params = spec.parse(run.params or {})

    application_name = f"task-run:{run_id}"
    task_db = Database(_with_application_name(db_url, application_name))
    output = OutputStream(redis, run_id)
    ctx = RunContext(run_id=run_id, output=output)
    watcher = CancelWatcher(
        redis, run_id, on_cancel=lambda: cancel_backends(db_url, application_name)
    )

    ledger.start_run(ledger_db, run_id)
    state, result, error = "succeeded", None, None
    watcher.start()
    try:
        with redirect_stdout(output), redirect_stderr(output), interruptible():
            result = spec.resolve()(task_db, params, ctx)
    except TaskCancelled:
        state = "cancelled"
        output.write("\n^C  cancelled\n")
    except BaseException as err:
        state = "failed"
        error = f"{type(err).__name__}: {err}"
        output.write("\n" + traceback.format_exc())
    finally:
        watcher.stop()
        output.flush()
        task_db.session.rollback()
        task_db.engine.dispose()

    log = read_all(redis, run_id)
    ledger.finish_run(
        ledger_db, run_id, state=state, result=result, error=error, log=log
    )
    expire(redis, run_id)
    ledger_db.engine.dispose()
    return {"run_id": run_id, "state": state}


def _with_application_name(db_url: str, name: str) -> str:
    """The URL with `application_name` set, so the run's sessions can be found."""
    parts = urlsplit(db_url)
    query = (
        parts.query
        + ("&" if parts.query else "")
        + urlencode({"application_name": name})
    )
    return urlunsplit(parts._replace(query=query))
