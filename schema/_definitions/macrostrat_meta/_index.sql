-- @subsystem: macrostrat_meta
-- @depends-on: core
/**
 * Operational records about the system itself, as opposed to the data it
 * holds: today the management task ledger, later comments, opinions and the
 * like. Read and written by api-v3 and the admin worker, never through PostgREST.
 */

CREATE SCHEMA macrostrat_meta;

/* What the task runner was asked to do, by whom, and how it ended. A run's
 * output streams through Redis while it runs and is archived on its row when
 * it ends, so history outlives the stream. */
CREATE TABLE macrostrat_meta.task_run (
    id              uuid primary key default gen_random_uuid(),
    task            text not null,
    params          jsonb not null default '{}'::jsonb,
    requested_by    integer references macrostrat_auth."user"(id),
    celery_task_id  text,
    state           text not null default 'queued'
                    check (state in ('queued', 'running', 'succeeded', 'failed', 'cancelled', 'killed')),
    created_on      timestamptz not null default now(),
    started_on      timestamptz,
    finished_on     timestamptz,
    result          jsonb,
    error           text,
    log             text
);

CREATE INDEX task_run_created_on_idx ON macrostrat_meta.task_run (created_on DESC);

-- One live run per task: the API refuses a duplicate, and this holds it to that.
CREATE UNIQUE INDEX task_run_live_idx ON macrostrat_meta.task_run (task)
    WHERE state IN ('queued', 'running');
