SELECT pg_catalog.set_config('search_path', 'public', false);

/* Pre-create tile-related schemas and set their ownership to macrostrat user */
CREATE SCHEMA IF NOT EXISTS tile_layers;
CREATE SCHEMA IF NOT EXISTS tile_cache;
CREATE SCHEMA IF NOT EXISTS tile_utils;

ALTER SCHEMA tile_layers OWNER TO macrostrat;
ALTER SCHEMA tile_cache OWNER TO macrostrat;
ALTER SCHEMA tile_utils OWNER TO macrostrat;
