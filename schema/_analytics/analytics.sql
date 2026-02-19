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

