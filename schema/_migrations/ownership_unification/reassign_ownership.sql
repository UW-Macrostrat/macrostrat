-- Re-own every application-schema object held by a legacy role
-- (macrostrat_admin / xdd_writer) to macrostrat. Scoped to application schemas: the
-- foundational public/topology schemas, extensions, and external data (sources/tiger)
-- are left as-is. See ownership_unification/__init__.py for the full rationale.
--
-- Deliberately free of `%` and `::`: the query layer routes any statement containing
-- `%s` through raw psycopg (which then mis-parses the other `%`), and the SQLAlchemy
-- text() path mis-reads `::cast` as a bind — so this uses `||` + quote_ident() and
-- cast(... AS ...) instead of format()/`::`.

DO $$
DECLARE
  r record;
  excluded text[] := ARRAY['pg_catalog','information_schema','public','topology','sources','tiger','tiger_data'];
  legacy   text[] := ARRAY['macrostrat_admin','xdd_writer'];
BEGIN
  -- Relations: the command keyword depends on relkind (foreign tables and matviews
  -- need their own ALTER form; ALTER TABLE covers tables, views, and sequences).
  FOR r IN
    SELECT n.nspname AS s, c.relname AS o, c.relkind AS k
    FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE c.relkind IN ('r','p','v','m','S','f')
      AND n.nspname <> ALL(excluded) AND left(n.nspname, 3) <> 'pg_'
      AND pg_get_userbyid(c.relowner) = ANY(legacy)
      -- Skip sequences owned by a table column (serial/identity): their owner is
      -- tied to the table and follows it automatically when the table is reassigned.
      AND NOT (c.relkind = 'S' AND EXISTS (
        SELECT 1 FROM pg_depend d
        WHERE d.objid = c.oid AND d.deptype IN ('a','i') AND d.refobjsubid <> 0))
  LOOP
    EXECUTE 'ALTER '
      || (CASE r.k WHEN 'f' THEN 'FOREIGN TABLE'
                   WHEN 'm' THEN 'MATERIALIZED VIEW'
                   ELSE 'TABLE' END)
      || ' ' || quote_ident(r.s) || '.' || quote_ident(r.o)
      || ' OWNER TO macrostrat';
  END LOOP;

  -- Routines (functions + procedures) and aggregates, addressed by regprocedure.
  FOR r IN
    SELECT p.oid AS oid, (p.prokind = 'a') AS is_agg
    FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname <> ALL(excluded) AND left(n.nspname, 3) <> 'pg_'
      AND pg_get_userbyid(p.proowner) = ANY(legacy)
  LOOP
    EXECUTE 'ALTER ' || (CASE WHEN r.is_agg THEN 'AGGREGATE' ELSE 'ROUTINE' END)
      || ' ' || cast(r.oid AS regprocedure) || ' OWNER TO macrostrat';
  END LOOP;

  -- Standalone types: enums, domains, and non-table composite types.
  FOR r IN
    SELECT n.nspname AS s, t.typname AS o
    FROM pg_type t JOIN pg_namespace n ON n.oid = t.typnamespace
    WHERE n.nspname <> ALL(excluded) AND left(n.nspname, 3) <> 'pg_'
      AND pg_get_userbyid(t.typowner) = ANY(legacy)
      AND (t.typtype IN ('e','d')
           OR (t.typtype = 'c'
               AND EXISTS (SELECT 1 FROM pg_class rc WHERE rc.oid = t.typrelid AND rc.relkind = 'c')))
  LOOP
    EXECUTE 'ALTER TYPE ' || quote_ident(r.s) || '.' || quote_ident(r.o)
      || ' OWNER TO macrostrat';
  END LOOP;

  -- The schemas themselves.
  FOR r IN
    SELECT n.nspname AS s FROM pg_namespace n
    WHERE n.nspname <> ALL(excluded) AND left(n.nspname, 3) <> 'pg_'
      AND pg_get_userbyid(n.nspowner) = ANY(legacy)
  LOOP
    EXECUTE 'ALTER SCHEMA ' || quote_ident(r.s) || ' OWNER TO macrostrat';
  END LOOP;
END $$;
