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
-- SCOPE: the hand-curated column tree plus the unit tables. What is deliberately
-- left out:
--
--   * lookup_* / autocomplete / stats and other derived tables. The provenance
--     that matters is their inputs', they have no primary key to key history on,
--     and the rebuild drops and recreates them -- which would silently strip any
--     trigger attached here.
--   * macrostrat_backup, macrostratbak2, macrostrat_api -- legacy copies.

select audit.enable('macrostrat.cols');
select audit.enable('macrostrat.col_groups');
select audit.enable('macrostrat.col_areas');
select audit.enable('macrostrat.col_notes');
select audit.enable('macrostrat.col_refs');
select audit.enable('macrostrat.sections');

-- The unit tables. These hold user- and model-initialized rows side by side, so
-- they have to be tracked rather than excluded -- an age model boundary that a
-- curator later corrects is exactly the history worth having.
--
-- Auditing them is only affordable because they carry
-- suppress_redundant_updates_trigger (schema/core/0002-macrostrat/05-triggers.sql):
-- the rebuild scripts recompute derived values across whole tables, and without
-- suppression one `unit-boundaries.sql` run wrote 144,959 history rows to record
-- 29 real changes. With it, that run writes 29. If those triggers are ever
-- removed, remove these three lines with them.
--
-- Machine writes are tagged (`system:rebuild` / `system:column-ingest`) via
-- macrostrat.core.database.set_audit_context, so recomputation stays
-- distinguishable from curation -- and prunable by batch_id if it ever needs to be.
select audit.enable('macrostrat.units');
select audit.enable('macrostrat.unit_liths');
select audit.enable('macrostrat.unit_boundaries');
