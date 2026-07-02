"""
Minimal Celery worker for the Macrostrat CLI. This runs inside the `macrostrat.cli`
environment. Celery tasks shell out to the real CLI, so the worker executes exactly
the same code as a human running the command by hand.

You can run it via ./py-modules/cli:
    `uv run celery -A macrostrat.cli.worker worker --loglevel=info`

The broker/result backend default to a local Redis and can be overridden with
the CELERY_BROKER_URL / CELERY_RESULT_BACKEND env var in /local-root/
"""

import os
import subprocess

from celery import Celery

BROKER_URL = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/0")
RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND", BROKER_URL)

app = Celery("macrostrat", broker=BROKER_URL, backend=RESULT_BACKEND)


@app.task(name="macrostrat.maps.delete")
def delete_map(slug: str) -> str:
    """Delete a staged map by slug via `macrostrat maps staging delete <slug>`."""
    result = subprocess.run(
        ["macrostrat", "maps", "staging", "delete", slug],
        capture_output=True,
        text=True,
    )
    output = (result.stdout or "") + (result.stderr or "")
    if result.returncode != 0:
        raise RuntimeError(f"Failed to delete map '{slug}':\n{output}")
    return output
