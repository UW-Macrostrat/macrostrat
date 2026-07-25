-- =============================================================================
-- Generic JSONB change-tracking for Macrostrat
-- =============================================================================
-- Design goals (from our discussion):
--   * One mechanism for both tiers: "who touched this" everywhere,
--     "what changed" for free on the columns-path + link tables.
--   * Full-row snapshots (write-seldom, no revert -> we don't need
--     re-insertable fidelity, so we ignore that whole class of concerns).
--   * Resilient to schema evolution: to_jsonb(NEW) picks up new columns
--     automatically, so adding a column never touches the audit machinery.
--   * Append-only, tamper-evident against the application role.
--
-- THINGS YOU MUST ADAPT (marked "ADAPT" below):
--   1. Role names (app role vs. the owner that runs migrations).
--   2. The columns-path pk/FK convention: this file assumes macrostrat.cols
--      has pk `id` and child/link tables reference it as `col_id`. Change the
--      key names in audit.column_history() if your convention differs.
--   3. Your app MUST propagate the human actor into each transaction
--      (see audit.set_context). Without it you only ever capture "the app".
-- =============================================================================

create schema if not exists audit;

-- -----------------------------------------------------------------------------
-- 1. History table  (the single sink for everything)
-- -----------------------------------------------------------------------------
-- We store schema/table as TEXT (not oid) so the log stays readable across
-- renames/drops and reflects the name as it was at write time.
-- `changed_at` uses now() = transaction start, so all rows in one txn share it;
-- the identity `id` gives deterministic intra-transaction ordering.
create table if not exists audit.record_history (
  id           bigint generated always as identity primary key,
  txid         bigint      not null default txid_current(),
  changed_at   timestamptz not null default now(),
  action       text        not null,              -- INSERT|UPDATE|DELETE|TRUNCATE
  schema_name  text        not null,
  table_name   text        not null,
  actor_id     text,                              -- from app.actor_id GUC
  batch_id     text,                              -- from app.batch_id GUC
  old_record   jsonb,                             -- null on INSERT/TRUNCATE
  new_record   jsonb                              -- null on DELETE/TRUNCATE
);

-- Coarse provenance lookups
create index if not exists record_history_table_time_idx
  on audit.record_history (schema_name, table_name, changed_at);
create index if not exists record_history_actor_idx
  on audit.record_history (actor_id) where actor_id is not null;
create index if not exists record_history_batch_idx
  on audit.record_history (batch_id) where batch_id is not null;
create index if not exists record_history_txid_idx
  on audit.record_history (txid);

-- Hot-path JSONB lookups for the columns tree. Expression indexes are far
-- more effective here than a blanket GIN, because our queries are equality on
-- a specific key (->>'col_id' = ...), not containment.
create index if not exists record_history_new_colid_idx
  on audit.record_history ((new_record->>'col_id'));
create index if not exists record_history_old_colid_idx
  on audit.record_history ((old_record->>'col_id'));
create index if not exists record_history_new_col_pk_idx
  on audit.record_history ((new_record->>'id')) where table_name = 'cols';
-- Add a GIN index only if you also want ad-hoc containment queries:
--   create index on audit.record_history using gin (new_record jsonb_path_ops);

-- Future scaling note: this table only grows and is append-only, which makes
-- it a clean candidate for RANGE partitioning on changed_at if it ever gets
-- large. Not needed for a write-seldom workload, but the shape is ready.

-- -----------------------------------------------------------------------------
-- 2. Append-only / tamper-evidence
-- -----------------------------------------------------------------------------
-- The capture function below is SECURITY DEFINER and owned by the migration
-- owner, so it can INSERT even though the app role cannot. The app role gets
-- SELECT only -> it can read history but never rewrite it.
-- (True tamper-proofing against a superuser/owner isn't a DB-level guarantee;
--  the realistic goal is that the *application* can't alter the trail.)
revoke all on audit.record_history from public;
-- ADAPT role names:
-- grant usage  on schema audit          to macrostrat_app;
-- grant select on audit.record_history  to macrostrat_app;
--   (deliberately NO insert/update/delete to the app role)

-- -----------------------------------------------------------------------------
-- 3. Actor / batch propagation
-- -----------------------------------------------------------------------------
-- The app calls this ONCE at the start of each writing transaction:
--     select audit.set_context('contributor:4417', 'ingest:2025-07-batch-12');
-- is_local = true  -> the setting is scoped to the current transaction and is
-- cleared on commit/rollback, so it is safe under connection pooling (never
-- leaks into the next session that checks out the connection).
create or replace function audit.set_context(p_actor text, p_batch text default null)
  returns void
  language plpgsql
as $$
begin
  perform set_config('app.actor_id', coalesce(p_actor, ''), true);
  perform set_config('app.batch_id', coalesce(p_batch, ''), true);
end;
$$;

-- -----------------------------------------------------------------------------
-- 4. The capture trigger function
-- -----------------------------------------------------------------------------
-- SECURITY DEFINER so it can write to a table the app role can't.
-- Explicit search_path closes the classic definer-function hijack vector.
create or replace function audit.capture()
  returns trigger
  language plpgsql
  security definer
  set search_path = pg_catalog, public
as $$
declare
  v_old jsonb;
  v_new jsonb;
begin
  if tg_op = 'UPDATE' then
    v_old := to_jsonb(old);
    v_new := to_jsonb(new);
  elsif tg_op = 'DELETE' then
    v_old := to_jsonb(old);       -- captures the row as it was un-linked/removed
  elsif tg_op = 'INSERT' then
    v_new := to_jsonb(new);
  end if;
  -- TRUNCATE: statement-level, no OLD/NEW; we still record that it happened.

  insert into audit.record_history (
    action, schema_name, table_name,
    actor_id, batch_id, old_record, new_record
  )
  values (
    tg_op,
    tg_table_schema,
    tg_table_name,
    nullif(current_setting('app.actor_id', true), ''),  -- '' / unset -> null
    nullif(current_setting('app.batch_id', true), ''),
    v_old,
    v_new
  );

  return null;   -- AFTER trigger: return value is ignored
end;
$$;

-- -----------------------------------------------------------------------------
-- 5. Attach / detach helpers
-- -----------------------------------------------------------------------------
-- AFTER triggers so we capture the final row (post any BEFORE-trigger mutation).
-- The zzz_ name prefix makes these fire last among AFTER triggers.
-- %s on a regclass expands to the schema-qualified, properly-quoted name.
create or replace function audit.enable(target_table regclass)
  returns void
  language plpgsql
as $outer$
begin
  execute format('drop trigger if exists zzz_audit_row on %s', target_table);
  execute format(
    'create trigger zzz_audit_row after insert or update or delete on %s '
      'for each row execute function audit.capture()', target_table);

  execute format('drop trigger if exists zzz_audit_truncate on %s', target_table);
  execute format(
    'create trigger zzz_audit_truncate after truncate on %s '
      'for each statement execute function audit.capture()', target_table);
end;
$outer$;

create or replace function audit.disable(target_table regclass)
  returns void
  language plpgsql
as $outer$
begin
  execute format('drop trigger if exists zzz_audit_row on %s', target_table);
  execute format('drop trigger if exists zzz_audit_truncate on %s', target_table);
end;
$outer$;

-- -----------------------------------------------------------------------------
-- 6. Diff helper + human-readable view
-- -----------------------------------------------------------------------------
-- For UPDATEs, returns only the changed keys as {key: {old, new}}.
-- For INSERT/DELETE returns the whole new/old row (everything is "changed").
create or replace function audit.diff(p_old jsonb, p_new jsonb)
  returns jsonb
  language sql
  immutable
as $$
select case
         when p_old is null then p_new       -- INSERT
         when p_new is null then p_old        -- DELETE
         else (
           select jsonb_object_agg(
             key,
             jsonb_build_object('old', p_old -> key, 'new', p_new -> key))
           from (
             select jsonb_object_keys(p_old) as key
             union
             select jsonb_object_keys(p_new) as key
           ) k
           where (p_old -> key) is distinct from (p_new -> key)
         )
  end;
$$;

create or replace view audit.changes as
select
  h.id, h.changed_at, h.txid, h.actor_id, h.batch_id,
  h.schema_name, h.table_name, h.action,
  audit.diff(h.old_record, h.new_record) as changed,
  h.old_record, h.new_record
from audit.record_history h;

-- -----------------------------------------------------------------------------
-- 7. "History of one column, including its link tables"
-- -----------------------------------------------------------------------------
-- This is the payoff of full-row JSONB snapshots: ANY table that carries a
-- col_id is swept in automatically -- no per-table union to maintain, and new
-- link tables are covered the moment you audit.enable() them.
--
-- ADAPT: assumes cols pk = 'id' and children reference it as 'col_id'.
-- The OR over both old_record and new_record catches re-links (a col_id that
-- changed in an UPDATE shows up under both its old and new parent).
create or replace function audit.column_history(p_col_id bigint)
  returns table (
    changed_at timestamptz,
    txid       bigint,
    actor_id   text,
    batch_id   text,
    action     text,
    table_name text,
    changed    jsonb
  )
  language sql
  stable
as $$
select
  h.changed_at, h.txid, h.actor_id, h.batch_id, h.action, h.table_name,
  audit.diff(h.old_record, h.new_record)
from audit.record_history h
where
   -- the cols row itself (pk = id)
  (h.table_name = 'cols'
    and (h.new_record->>'id' = p_col_id::text
      or h.old_record->>'id' = p_col_id::text))
   -- anything that references this column via col_id
   or h.new_record->>'col_id' = p_col_id::text
   or h.old_record->>'col_id' = p_col_id::text
order by h.changed_at, h.id;
$$;

-- =============================================================================
-- USAGE
-- =============================================================================
-- Turn on auditing per table:
--     select audit.enable('macrostrat.cols');
--     select audit.enable('macrostrat.units');
--     select audit.enable('macrostrat.unit_liths');   -- a link table
--
-- Bulk-enable a whole schema:
--     do $$
--     declare r record;
--     begin
--       for r in
--         select format('%I.%I', schemaname, tablename) as t
--         from pg_tables where schemaname = 'macrostrat'
--       loop
--         perform audit.enable(r.t::regclass);
--       end loop;
--     end $$;
--
-- App-side, once per writing transaction:
--     begin;
--       select audit.set_context('contributor:4417', 'ingest:2025-07-batch-12');
--       update macrostrat.cols set col_name = '...' where id = 991;
--     commit;
--
-- Query the full story of one column:
--     select * from audit.column_history(991);
--
-- Everything a contributor / batch touched:
--     select * from audit.changes where actor_id = 'contributor:4417';
--     select * from audit.changes where batch_id = 'ingest:2025-07-batch-12';
-- =============================================================================
