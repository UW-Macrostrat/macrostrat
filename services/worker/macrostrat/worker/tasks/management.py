"""Management tasks: `macrostrat.tasks.run` executes one `tasks.run` ledger row.

The task is looked up by name in the registry (`macrostrat.tasks` entry
points) and run by `macrostrat.task_runner.execute_run`, which streams its
terminal output to Redis and honours a cancel like Ctrl-C. Runs are serial: the
`admin` queue's worker is a single prefork process, one task per child, so the
stdout redirection and SIGINT handler the runner installs are its own.

Requires the `tasks` worker extra.
"""

import os

from macrostrat.worker.app import BROKER_URL, app


@app.task(name="macrostrat.tasks.run")
def run_management_task(run_id: str) -> dict:
    from macrostrat.task_runner.run import execute_run

    db_url = os.environ.get("DB_URL")
    if not db_url:
        raise RuntimeError("DB_URL environment variable is not set")
    return execute_run(
        run_id=run_id,
        db_url=db_url,
        redis_url=os.environ.get("REDIS_URL", BROKER_URL),
    )
