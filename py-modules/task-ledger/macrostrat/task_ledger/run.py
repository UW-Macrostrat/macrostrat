"""Execute one run: what the worker task calls."""

import os

from macrostrat.database import Database
from macrostrat.task_runner import TaskSpec, execute, load_registry
from macrostrat.task_runner.execute import TERMINAL_ENV

from . import ledger


def execute_run(
    *,
    run_id: str,
    db_url: str,
    redis_url: str,
    registry: dict[str, TaskSpec] | None = None,
) -> dict:
    """Run the ledger row `run_id` to completion and record how it ended.

    Must run in a main thread. Output goes to the run's Redis stream for the
    duration; the ledger gets the archived copy.
    """
    # Before the registry imports task modules that may create a Rich console.
    for key, value in TERMINAL_ENV.items():
        os.environ.setdefault(key, value)

    ledger_db = Database(db_url)
    run = ledger.get_run(ledger_db, run_id)
    if run is None:
        raise ValueError(f"No run {run_id}")
    spec = (registry or load_registry())[run.task]
    params = spec.parse(run.params or {})

    ledger.start_run(ledger_db, run_id)
    outcome = execute(
        run_id,
        lambda db, ctx: spec.resolve()(db, params, ctx),
        db_url=db_url,
        redis_url=redis_url,
    )
    ledger.finish_run(
        ledger_db,
        run_id,
        state=outcome.state,
        result=outcome.result,
        error=outcome.error,
        log=outcome.log,
    )
    ledger_db.engine.dispose()
    return {"run_id": run_id, "state": outcome.state}
