--shows all the permissions of a given user and table
SELECT
  has_table_privilege('macrostrat', 'tile_cache.tile', 'SELECT')   AS can_select,
  has_table_privilege('macrostrat', 'tile_cache.tile', 'INSERT')   AS can_insert,
  has_table_privilege('macrostrat', 'tile_cache.tile', 'UPDATE')   AS can_update,
  has_table_privilege('macrostrat', 'tile_cache.tile', 'DELETE')   AS can_delete,
  has_table_privilege('macrostrat', 'tile_cache.tile', 'TRUNCATE') AS can_truncate,
  has_table_privilege('macrostrat', 'tile_cache.tile', 'REFERENCES') AS can_references,
  has_table_privilege('macrostrat', 'tile_cache.tile', 'TRIGGER')  AS can_trigger,
  has_schema_privilege('macrostrat', 'tile_cache', 'USAGE') AS can_use_schema,
  has_table_privilege('macrostrat', 'tile_cache.tile', 'SELECT') AS macrostrat_can_select;

--shows the rows counts for every table in every schema of a given database:
--run ANALYZE on all db's before running the query
--update the environment for whatever env you're running the query in
SELECT
    'development' as environment,
    schemaname,
    relname AS table_name,
    n_live_tup AS estimated_rows
FROM pg_stat_user_tables
ORDER BY schemaname, relname;

--returns schema, view name, and sql definition for all views dependent on a specified table

SELECT DISTINCT
    n.nspname AS view_schema,
    c.relname AS view_name,
    pg_get_viewdef(c.oid, true) AS view_definition
FROM pg_depend d
JOIN pg_rewrite r
    ON d.objid = r.oid
JOIN pg_class c
    ON r.ev_class = c.oid
JOIN pg_namespace n
    ON c.relnamespace = n.oid
WHERE d.refobjid = 'maps_metadata.ingest_process'::regclass
  AND c.relkind = 'v'
ORDER BY n.nspname, c.relname;


