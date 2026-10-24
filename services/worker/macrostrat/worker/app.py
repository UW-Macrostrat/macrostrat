"""
The shared Celery application for Macrostrat background workers.
Broker + result backend are read from the environment so the same app runs
locally, in docker-compose, and in Kubernetes. Task modules are registered via
``include`` and routed to per-domain queues, so a worker can subscribe to just
the queues it should handle
"""

import os

from celery import Celery
from celery.worker.control import inspect_command

BROKER_URL = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/0")
RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND", BROKER_URL)

app = Celery(
    "macrostrat",
    broker=BROKER_URL,
    backend=RESULT_BACKEND,
    # Register task modules here. Each requires the matching worker extra to be installed
    include=[
        "macrostrat.worker.tasks.maps",
        "macrostrat.worker.tasks.columns",
        "macrostrat.worker.tasks.management",
    ],
)

# Route each domain's tasks to its own queue so workers can be scoped with `-Q`.
app.conf.task_routes = {
    "macrostrat.maps.*": {"queue": "maps"},
    "macrostrat.columns.*": {"queue": "columns"},
    # Management tasks run one at a time, on a worker of their own.
    "macrostrat.tasks.*": {"queue": "admin"},
}


@inspect_command()
def build(state):
    """The build this worker runs, for api-v3's `/workers/version`."""
    queues = []
    if state.consumer.task_consumer:
        queues = sorted(q.name for q in state.consumer.task_consumer.queues)
    return {
        "service": "worker",
        "version": os.environ.get("MACROSTRAT_VERSION") or None,
        "release": os.environ.get("MACROSTRAT_RELEASE") == "true",
        "commit": os.environ.get("MACROSTRAT_COMMIT") or None,
        "build_date": os.environ.get("MACROSTRAT_BUILD_DATE") or None,
        "repository": os.environ.get("MACROSTRAT_REPOSITORY") or None,
        "queues": queues,
    }
