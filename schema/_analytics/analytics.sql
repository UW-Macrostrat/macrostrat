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
