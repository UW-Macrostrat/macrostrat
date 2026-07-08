# macrostrat.worker

The Celery task-queue **application** and workers for Macrostrat background jobs.

This module owns the *task framework* — the shared Celery app, its broker/result
configuration, and thin task wrappers. It deliberately keeps its base dependency
footprint tiny (just `celery[redis]`); the actual domain logic lives in
light, GIS-free modules like [`macrostrat.map_utils`](../../py-modules/map-utils) and is pulled
in through **extras** so each worker image installs only what its tasks need.

## Layout

- `macrostrat/worker/app.py` — the Celery app (broker/backend from env vars,
  queue routing, task discovery).
- `macrostrat/worker/tasks/` — thin Celery task wrappers, grouped by domain.
  Each wrapper calls into a domain module (e.g. `map_utils.delete_map`).

## Configuration (environment variables)

- `CELERY_BROKER_URL` / `CELERY_RESULT_BACKEND` — Redis (default
  `redis://localhost:6379/0`).
- `DB_URL` — Postgres connection string (used by the map tasks).
- `S3_ENDPOINT` / `S3_ACCESS_KEY` / `S3_SECRET_KEY` / `S3_BUCKET` / `S3_SECURE` —
  optional MinIO/S3 staging store for the map tasks.

## Running

```bash
# Locally (from services/worker, with the `maps` extra installed):
uv run celery -A macrostrat.worker.app worker -Q maps --loglevel=info

# Enqueue by name from anywhere (no need to import this package):
celery_app.send_task("macrostrat.maps.delete", args=["some-slug"])
```
