"""
Celery client for the API service.

The API only *enqueues* named tasks onto the shared broker; it deliberately does
not import the worker's Celery app. The worker that executes them lives in
`macrostrat.worker` (task name `macrostrat.maps.delete`).

The task_routes below MUST match the worker's routing
(py-modules/worker/macrostrat/worker/app.py): the worker consumes only the
`maps` queue (`-Q maps`), so sends have to be routed there — otherwise
send_task() publishes to the default queue that the worker never listens on.
"""

import os

from celery import Celery

BROKER_URL = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/0")
RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND", BROKER_URL)

celery_app = Celery("macrostrat_api", broker=BROKER_URL, backend=RESULT_BACKEND)

# Producer-side routing — routing is applied by whoever sends the task, so this
# must mirror the worker's task_routes or map tasks land on the wrong queue.
celery_app.conf.task_routes = {
    "macrostrat.maps.*": {"queue": "maps"},
}
