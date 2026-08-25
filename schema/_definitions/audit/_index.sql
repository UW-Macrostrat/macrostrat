-- @subsystem: audit
-- @depends-on: core
-- =============================================================================
-- Generic JSONB change-tracking for Macrostrat
-- =============================================================================
-- This lead file is the machinery (sink table, capture trigger, attach/detach
-- helpers, read API). The *roster* of audited tables is its own file --
-- 20-enable.sql -- applied after this one in filename order.
--
-- `@depends-on: core` rather than `macrostrat`: the curated tables audited today
-- all live in the `macrostrat` chunk, but nothing depends on audit, so ordering
-- it after the last application chunk costs nothing and leaves the roster free
-- to name tables from the `core` remainder later.
--
-- Unlike schema/development/, this subsystem is applied in EVERY environment --
-- provenance for curated data is a production concern, not a dev convenience.
-- Design goals (from our discussion):
--   * One mechanism for both tiers: "who touched this" everywhere,
--     "what changed" for free on the columns-path + link tables.
--   * Full-row snapshots (write-seldom, no revert -> we don't need
--     re-insertable fidelity, so we ignore that whole class of concerns).
--   * Resilient to schema evolution: to_jsonb(NEW) picks up new columns
--     automatically, so adding a column never touches the audit machinery.
--   * Append-only, tamper-evident against the application role.
--
-- Macrostrat specifics (resolved against schema/core/0000-roles.sql and the
-- live schema, 2026-08-25):
--   * Owner is `macrostrat` (this chunk is applied as that role). The API-facing
--     roles are `web_anon` / `web_user` / `web_admin`, reached through the
--     `postgrest` authenticator -- distinct from the owner, so the append-only
--     property below actually holds for every write that arrives via the API.
--   * The columns-path FK convention is `col_id`, confirmed on 15 tables in the
--     `macrostrat` schema (cols, sections, units, col_refs, col_notes, ...).
--     Primary keys are handled automatically -- only the FK sweep is convention-
--     bound.
--   * Actor propagation is belt-and-braces: audit.set_context() for batch/CLI
--     work, with an automatic fallback to the PostgREST JWT `sub` already in the
--     session, so API writes are attributed without the app doing anything.
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
  action       text        not null
                 check (action in ('INSERT','UPDATE','DELETE','TRUNCATE')),
  schema_name  text        not null,
  table_name   text        not null,
  actor_id     text,                              -- from app.actor_id GUC
  batch_id     text,                              -- from app.batch_id GUC
  record_pk    jsonb,                             -- normalized pk {col: val};
  --   null if table has no pk
  old_record   jsonb,                             -- null on INSERT/TRUNCATE
  new_record   jsonb                              -- null on DELETE/TRUNCATE
);
-- record_pk is derived ONCE at enable() time (pk columns introspected from the
-- catalog and baked into the trigger args), then written from whichever of
-- NEW/OLD is present. It's stored as jsonb so single and composite keys are
-- handled uniformly. This buys a single clean index + clean row-lifecycle
-- queries across every table, at the cost of a re-coupling to pk *definition*
-- changes (rare; re-run audit.enable() to refresh). Tables with no declared pk
-- get null and fall back to blob queries -- graceful, not a failure.
--   Lighter alternative: drop record_pk entirely and query the pk out of the
--   JSONB blobs (new_record->>'id' ...). Fewer moving parts, but every
--   row-lifecycle query needs the OLD-or-NEW dance and per-key expression
--   indexes. Preferred here only if most of your tables lack simple pks.

-- Coarse provenance lookups
create index if not exists record_history_table_time_idx
  on audit.record_history (schema_name, table_name, changed_at);
create index if not exists record_history_actor_idx
  on audit.record_history (actor_id) where actor_id is not null;
create index if not exists record_history_batch_idx
  on audit.record_history (batch_id) where batch_id is not null;
create index if not exists record_history_txid_idx
  on audit.record_history (txid);

-- Row-lifecycle lookups ("this row's whole story"): one btree covers every
-- table, because the pk is normalized into record_pk. jsonb has btree equality
-- ops, so `record_pk = jsonb_build_object('id', 991)` uses this directly.
-- schema_name leads table_name because table names are NOT unique across
-- schemas in this database -- `cols` alone exists in macrostrat, macrostrat_api,
-- macrostrat_backup and macrostratbak2. Any lookup keyed on table_name only
-- silently merges four different tables' histories.
create index if not exists record_history_pk_idx
  on audit.record_history (schema_name, table_name, record_pk);

-- FK-sweep lookups for the columns tree (find every link/child row pointing at
-- a column). record_pk does NOT help here -- it's a foreign-key traversal, not
-- a pk lookup -- so we keep targeted expression indexes on col_id. They beat a
-- blanket GIN because the query is key equality (->>'col_id' = ...), not
-- containment.
-- Partial: only a minority of audited tables carry col_id at all, and a plain
-- expression index would still hold an entry per row of the whole log. The
-- predicate matches what the sweep in audit.column_history() actually asks for.
create index if not exists record_history_new_colid_idx
  on audit.record_history ((new_record->>'col_id'))
  where new_record ? 'col_id';
create index if not exists record_history_old_colid_idx
  on audit.record_history ((old_record->>'col_id'))
  where old_record ? 'col_id';
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
grant usage on schema audit to web_anon, web_user, web_admin;
-- Read-only to the API roles: deliberately NO insert/update/delete, so the
-- trail can be surfaced in the UI but never rewritten through the API.
grant select on audit.record_history to web_anon, web_user, web_admin;
grant select on audit.record_history to rockd_reader;

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
-- TG_ARGV holds the pk column names, baked in by enable() at attach time.
create or replace function audit.capture()
  returns trigger
  language plpgsql
  security definer
  set search_path = pg_catalog   -- no `public`: that IS the definer hijack vector
as $$
declare
  v_old jsonb;
  v_new jsonb;
  v_row jsonb;
  v_pk  jsonb;
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

  -- Normalized pk from whichever image is present. Null pk args (table has no
  -- pk) or TRUNCATE (no row) -> v_pk stays null and we fall back to blobs.
  if tg_nargs > 0 then
    v_row := coalesce(v_new, v_old);
    if v_row is not null then
      select jsonb_object_agg(k, v_row -> k)
      into v_pk
      from unnest(tg_argv) as k;
    end if;
  end if;

  insert into audit.record_history (
    action, schema_name, table_name, record_pk,
    actor_id, batch_id, old_record, new_record
  )
  values (
    tg_op,
    tg_table_schema,
    tg_table_name,
    v_pk,
    -- Prefer an explicitly-set actor (CLI / ingest / anything that calls
    -- set_context), then fall back to the PostgREST JWT that is already in the
    -- session. The fallback is a GUC read and a json subscript -- no catalog or
    -- table lookup -- so it costs nothing per row. `'orcid:' || null` is null,
    -- so an absent claim still yields an unattributed row rather than 'orcid:'.
    coalesce(
      nullif(current_setting('app.actor_id', true), ''),
      'orcid:' || (nullif(current_setting('request.jwt.claims', true), '')::json
                     ->> 'sub')
    ),
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
--
-- The DDL is assembled by concatenation, and this file contains no percent signs
-- anywhere -- not in SQL, not in comments. These files are applied through
-- psycopg, which uses a percent-s pair as its OWN bind placeholder: a format()
-- template written that way is rewritten to `$4` before Postgres ever sees it,
-- and the trigger DDL fails at runtime. Casting a regclass to text is equivalent
-- to what the template did anyway -- it yields the properly-quoted name,
-- schema-qualified exactly when qualification is needed to resolve back to the
-- same relation.
--
-- We introspect the pk columns ONCE here and pass them as trigger arguments
-- (a comma-separated list of quoted literals). No pk -> no args -> capture()
-- records a null record_pk for that table. Re-run enable() after any change to
-- a table's pk definition to refresh the baked-in columns.
create or replace function audit.enable(target_table regclass)
  returns void
  language plpgsql
as $outer$
declare
  v_pk_args text;
  v_schema  text;
begin
  -- Auditing audit.record_history would make every captured row capture itself.
  -- Cheap to do by accident: the bulk-enable recipe at the bottom of this file
  -- is one `where schemaname = 'audit'` away from an infinite recursion.
  select n.nspname into v_schema
  from pg_class c join pg_namespace n on n.oid = c.relnamespace
  where c.oid = target_table;
  if v_schema = 'audit' then
    -- Message built by concatenation rather than plpgsql's RAISE substitution,
    -- for the no-percent-signs reason documented in section 5 below.
    raise exception using message =
      'refusing to audit ' || target_table::text ||
      ' -- tables in the audit schema would capture their own writes recursively';
  end if;

  select string_agg(quote_literal(a.attname), ', '
                    order by array_position(i.indkey::smallint[], a.attnum))
  into v_pk_args
  from pg_index i
  join pg_attribute a
  on a.attrelid = i.indrelid
    and a.attnum = any(i.indkey::smallint[])
  where i.indrelid = target_table
    and i.indisprimary;

  execute 'drop trigger if exists zzz_audit_row on ' || target_table::text;
  execute 'create trigger zzz_audit_row'
       || ' after insert or update or delete on ' || target_table::text
       || ' for each row execute function audit.capture('
       || coalesce(v_pk_args, '') || ')';

  execute 'drop trigger if exists zzz_audit_truncate on ' || target_table::text;
  execute 'create trigger zzz_audit_truncate'
       || ' after truncate on ' || target_table::text
       || ' for each statement execute function audit.capture('
       || coalesce(v_pk_args, '') || ')';
end;
$outer$;

create or replace function audit.disable(target_table regclass)
  returns void
  language plpgsql
as $outer$
begin
  execute 'drop trigger if exists zzz_audit_row on ' || target_table::text;
  execute 'drop trigger if exists zzz_audit_truncate on ' || target_table::text;
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
         -- coalesce so an UPDATE that changed nothing reads as {} ("we looked,
         -- nothing moved") rather than null ("not applicable"), which is what
         -- INSERT/DELETE-of-an-empty-row and TRUNCATE mean.
         else coalesce((
           select jsonb_object_agg(
             key,
             jsonb_build_object('old', p_old -> key, 'new', p_new -> key))
           from (
             select jsonb_object_keys(p_old) as key
             union
             select jsonb_object_keys(p_new) as key
           ) k
           where (p_old -> key) is distinct from (p_new -> key)
         ), '{}'::jsonb)
  end;
$$;

create or replace view audit.changes as
select
  h.id, h.changed_at, h.txid, h.actor_id, h.batch_id,
  h.schema_name, h.table_name, h.record_pk, h.action,
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
-- Assumes cols pk = 'id' and children reference it as 'col_id'.
-- The OR over both old_record and new_record catches re-links (a col_id that
-- changed in an UPDATE shows up under both its old and new parent).
--
-- p_schema is a real parameter, not decoration: `cols` exists in four schemas
-- here, and an unqualified table_name filter would blend their histories.
create or replace function audit.column_history(
    p_col_id bigint, p_schema text default 'macrostrat')
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
where h.schema_name = p_schema
  and (
     -- The cols row itself, matched through the normalized pk so this branch
     -- rides record_history_pk_idx. Matching on new_record->>'id' instead would
     -- have no index behind it and seq-scan the entire log on every call.
     (h.table_name = 'cols' and h.record_pk = jsonb_build_object('id', p_col_id))
     -- anything that references this column via col_id
     or h.new_record->>'col_id' = p_col_id::text
     or h.old_record->>'col_id' = p_col_id::text
  )
order by h.changed_at, h.id;
$$;

-- =============================================================================
-- USAGE
-- =============================================================================
-- Which tables are audited is declared in 20-enable.sql -- add a line there
-- rather than calling audit.enable() by hand. An out-of-band `enable()` does not
-- survive: the schema diff builds its ideal side by *executing* these files
-- (planning_database -> apply_schema_for_environment), so a trigger that is not
-- in the roster is absent from the ideal schema, and `macrostrat db apply` will
-- emit `drop trigger` for it -- classified safe by is_unsafe_statement, so it
-- detaches silently. The roster file is the only durable place to say this.
--
-- Deliberately no bulk "audit the whole schema" recipe here. It would sweep in
-- the legacy copies (macrostrat_backup / macrostratbak2 / macrostrat_api) and
-- the bulk-rewritten lookup tables, whose churn would swamp the log.
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
