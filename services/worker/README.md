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
- `REDIS_URL` — where management tasks stream their output and listen for a
  cancel; defaults to the broker.
- `S3_HOST` / `S3_ACCESS_KEY` / `S3_SECRET_KEY` / `S3_BUCKET` / `S3_SECURE` —
  optional MinIO/S3 staging store for the map tasks.

## Running

```bash
# Locally (from services/worker, with the `maps` extra installed):
uv run celery -A macrostrat.worker.app worker -Q maps --loglevel=info

# Enqueue by name from anywhere (no need to import this package):
celery_app.send_task("macrostrat.maps.delete", args=["some-slug"])
```

## Management tasks

`macrostrat.tasks.run <run_id>` (the `tasks` extra, `admin` queue) executes a
registered management task — `topology.update`, `maps.process-pipeline` — for the row of that id
in `tasks.run`, streaming its terminal output to Redis and ending it like
Ctrl-C when cancelled. See `py-modules/task-runner` for the framework and the
API's `/tasks` routes for how a run is started. The `admin` worker runs one task
at a time in a fresh process (`--concurrency=1 --max-tasks-per-child=1`) with a
terminal environment (`FORCE_COLOR`, `COLUMNS`, …) so Rich renders colour and
progress bars into the stream.
