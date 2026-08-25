-- =============================================================================
-- Audit roster: which tables carry change-tracking triggers
-- =============================================================================
-- This file IS the declaration. It is applied after _index.sql (filename order)
-- on every build, which means the triggers it attaches also exist in the
-- planning database the schema diff builds its ideal side from -- so `db plan`
-- sees them on both sides and stays quiet. Conversely, a table dropped from this
-- list has its trigger removed by the next `db apply`, which is the intended way
-- to stop auditing something.
--
-- audit.enable() is idempotent (`drop trigger if exists` then `create`), so
-- re-running the whole file is free. Re-run it after any migration that recreates
-- an audited table, and after any change to a table's primary key -- the pk
-- columns are introspected once and baked into the trigger arguments.
--
-- SCOPE: the hand-curated column tree, where a human edit is the unit of change
-- and provenance is the point. Deliberately excluded for now:
--
--   * units, unit_liths, unit_boundaries -- correctness-wise these are the most
--     interesting targets, but they are rewritten in bulk by ingest and by the
--     lookup-table rebuilds. Every UPDATE writes a full-row JSONB snapshot, so
--     enabling them multiplies the write volume of those pipelines by a large and
--     currently unmeasured factor. Measure against production row counts, and
--     give the bulk writers an audit.set_context() batch_id, before adding them.
--   * lookup_* / carto / tile caches -- derived data. The provenance that matters
--     is that of their inputs, and they have no primary key to key history on.
--   * macrostrat_backup, macrostratbak2, macrostrat_api -- legacy copies.

select audit.enable('macrostrat.cols');
select audit.enable('macrostrat.col_groups');
select audit.enable('macrostrat.col_areas');
select audit.enable('macrostrat.col_notes');
select audit.enable('macrostrat.col_refs');
select audit.enable('macrostrat.sections');
