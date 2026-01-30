--shows all the permissions of a given user and table
SELECT
  has_table_privilege('macrostrat', 'tile_cache.tile_info', 'SELECT')   AS can_select,
  has_table_privilege('macrostrat', 'tile_cache.tile_info', 'INSERT')   AS can_insert,
  has_table_privilege('macrostrat', 'tile_cache.tile_info', 'UPDATE')   AS can_update,
  has_table_privilege('macrostrat', 'tile_cache.tile_info', 'DELETE')   AS can_delete,
  has_table_privilege('macrostrat', 'tile_cache.tile_info', 'TRUNCATE') AS can_truncate,
  has_table_privilege('macrostrat', 'tile_cache.tile_info', 'REFERENCES') AS can_references,
  has_table_privilege('macrostrat', 'tile_cache.tile_info', 'TRIGGER')  AS can_trigger,
  has_schema_privilege('macrostrat', 'tile_cache', 'USAGE') AS can_use_schema,
  has_table_privilege('macrostrat', 'tile_cache.tile_info', 'SELECT') AS macrostrat_can_select;
