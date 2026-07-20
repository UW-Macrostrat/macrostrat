"""
The shared Celery application for Macrostrat background workers.
Broker + result backend are read from the environment so the same app runs
locally, in docker-compose, and in Kubernetes. Task modules are registered via
``include`` and routed to per-domain queues, so a worker can subscribe to just
the queues it should handle
"""

import os

from celery import Celery

BROKER_URL = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/0")
RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND", BROKER_URL)

app = Celery(
    "macrostrat",
    broker=BROKER_URL,
    backend=RESULT_BACKEND,
    # Register task modules here. Each requires the matching worker extra to be installed
    include=["macrostrat.worker.tasks.maps"],
)

# Route each domain's tasks to its own queue so workers can be scoped with `-Q`.
app.conf.task_routes = {
    "macrostrat.maps.*": {"queue": "maps"},
}
