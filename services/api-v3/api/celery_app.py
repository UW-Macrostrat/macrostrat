"""
Celery client for the API service.

The role of the API enqueues named tasks onto the shared broker. The worker that executes
the tasks lives in `macrostrat.cli.worker`.
"""

import os
from celery import Celery

BROKER_URL = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/0")
RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND", BROKER_URL)

celery_app = Celery("macrostrat_api", broker=BROKER_URL, backend=RESULT_BACKEND)
