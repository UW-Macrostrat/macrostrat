"""The runner against real Redis and Postgres: output, ledger, and a cancel that
lands mid-statement.

Needs a database holding the `tasks` chunk and an admin user, plus Redis:

    TASK_RUNNER_E2E_DB_URL=postgresql://… TASK_RUNNER_E2E_REDIS_URL=redis://… pytest

Skipped otherwise. The run executes in a subprocess, as it does under the
worker: `execute_run` installs a signal handler, so it needs a main thread.
"""

import json
import os
import subprocess
import sys
import threading
import time

import pytest

DB_URL = os.environ.get("TASK_RUNNER_E2E_DB_URL")
REDIS_URL = os.environ.get("TASK_RUNNER_E2E_REDIS_URL")

pytestmark = pytest.mark.skipif(
    not (DB_URL and REDIS_URL), reason="TASK_RUNNER_E2E_* not set"
)

# A task that sleeps in Postgres in steps, swallowing errors per step the way
# a library would, so only a BaseException can end it early.
TASK_SOURCE = """
from pydantic import BaseModel, Field
from macrostrat.task_runner import TaskSpec

class Params(BaseModel):
    steps: int = 3
    seconds: float = 1.0

def run(db, params, ctx):
    from rich import print
    from rich.progress import Progress
    print("[bold green]e2e[/] start")
    with Progress() as progress:
        task = progress.add_task("Sleeping", total=params.steps)
        for i in range(params.steps):
            try:
                db.run_query("SELECT pg_sleep(:s)", dict(s=params.seconds))
            except Exception as err:
                print(f"  [red]caught[/] {type(err).__name__}")
                db.session.rollback()
            progress.update(task, advance=1)
            print(f"  step {i} done")
    return {"steps": params.steps}

TASKS = [TaskSpec(name="e2e.sleep", title="Sleep", description="", params=Params, run="e2e_task:run")]
"""

RUNNER = """
import sys
from macrostrat.task_runner.run import execute_run
import e2e_task
registry = {s.name: s for s in e2e_task.TASKS}
print(execute_run(run_id=sys.argv[1], db_url=sys.argv[2], redis_url=sys.argv[3], registry=registry))
"""


@pytest.fixture(scope="module")
def task_module(tmp_path_factory):
    path = tmp_path_factory.mktemp("e2e")
    (path / "e2e_task.py").write_text(TASK_SOURCE)
    return path


@pytest.fixture
def db():
    from macrostrat.database import Database

    database = Database(DB_URL)
    yield database
    database.engine.dispose()


@pytest.fixture
def redis():
    from redis import Redis

    return Redis.from_url(REDIS_URL)


def _start(db, task_module, run_id):
    env = {**os.environ, "PYTHONPATH": str(task_module)}
    return subprocess.Popen(
        [sys.executable, "-c", RUNNER, run_id, DB_URL, REDIS_URL],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )


def _wait_state(db, run_id, states, timeout=30):
    from macrostrat.task_runner import ledger

    deadline = time.time() + timeout
    while time.time() < deadline:
        run = ledger.get_run(db, run_id)
        if run.state in states:
            return run
        time.sleep(0.2)
    raise AssertionError(f"run never reached {states}; last: {run.state}")


def test_run_succeeds_and_archives_its_output(db, redis, task_module):
    from macrostrat.task_runner import ledger
    from macrostrat.task_runner.output import read_all

    run_id = ledger.create_run(
        db, task="e2e.sleep", params={"steps": 2, "seconds": 0.2}, requested_by=None
    )
    proc = _start(db, task_module, run_id)
    assert proc.wait(timeout=60) == 0, proc.stdout.read()
    run = ledger.get_run(db, run_id)
    assert run.state == "succeeded"
    assert run.result == {"steps": 2}
    log = ledger.get_log(db, run_id)
    assert "e2e" in log and "step 1 done" in log and "\x1b[" in log
    assert read_all(redis, run_id) == log


def test_cancel_interrupts_a_running_statement(db, redis, task_module):
    from macrostrat.task_runner import ledger
    from macrostrat.task_runner.output import control_channel

    run_id = ledger.create_run(
        db, task="e2e.sleep", params={"steps": 5, "seconds": 20}, requested_by=None
    )
    proc = _start(db, task_module, run_id)
    _wait_state(db, run_id, ("running",))
    # Let it get into the first pg_sleep, then cancel.
    time.sleep(2)
    t0 = time.time()
    redis.publish(control_channel(run_id), "cancel")
    assert proc.wait(timeout=30) == 0, proc.stdout.read()
    took = time.time() - t0
    run = ledger.get_run(db, run_id)
    assert run.state == "cancelled"
    # Immediate: not the 20 s the statement would have taken, nor a later step.
    assert took < 10, took
    log = ledger.get_log(db, run_id)
    assert "cancelled" in log and "step 0 done" not in log
