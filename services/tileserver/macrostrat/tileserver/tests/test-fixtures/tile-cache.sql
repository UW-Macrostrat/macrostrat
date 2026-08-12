/* The tile-cache schema, copied from `schema/core/0029-tile_utils.setup.sql`
   and `schema/core/0032-tile_cache.sql`.

   The test dump predates database-side tile caching, so without this the
   cached layers (carto, carto-slim, carto-slim-rotated) fail on
   `tile_cache.profile`. Kept as a copy rather than a reference because the
   test fixtures have to stand alone from the schema build. */

/* Pre-create tile-related schemas and set their ownership to macrostrat user */
CREATE SCHEMA IF NOT EXISTS tile_layers;
CREATE SCHEMA IF NOT EXISTS tile_cache;
CREATE SCHEMA IF NOT EXISTS tile_utils;



CREATE TABLE IF NOT EXISTS tile_cache.profile (
  id serial PRIMARY KEY,
  name text NOT NULL UNIQUE,
  format text NOT NULL,
  content_type text NOT NULL,
  minzoom integer,
  maxzoom integer
);

CREATE TABLE IF NOT EXISTS tile_cache.tile (
  x integer NOT NULL,
  y integer NOT NULL,
  z integer NOT NULL,
  profile integer NOT NULL REFERENCES tile_cache.profile(id),
  -- For speed, we reduce the hash to an integer, increasing the likelihood of collisions
  -- but reducing the size of the index and efficiency of querying over it. This could be
  -- revisited if hash collisions become a problem, but they will only be important in edge
  -- cases where the same tile is requested with different parameters.
  -- We could also just index the parameters themselves (right now it's just t_step for paleogeography).
  args_hash integer NOT NULL,
  created timestamp without time zone NOT NULL DEFAULT now(),
  last_used timestamp without time zone NOT NULL DEFAULT now(),
  /* TODO: we could cache each layer separately and merge in the tile server */
  --layers text[] NOT NULL,
  tile bytea NOT NULL,
  PRIMARY KEY (x, y, z, profile, args_hash),
  -- Make sure tile is within TMS bounds
  CHECK (x >= 0 AND y >= 0 AND z >= 0 AND x < 2^z AND y < 2^z)
);
/* We'll need to add a TMS column if we want to support non-mercator tiles */


CREATE INDEX IF NOT EXISTS tile_cache_tile_last_used_idx ON tile_cache.tile (last_used);

CREATE OR REPLACE VIEW tile_cache.tile_info AS
SELECT 
  x,
  y,
  z,
  profile,
  args_hash,
  length(tile) tile_size,
  created,
  last_used
FROM tile_cache.tile;

CREATE OR REPLACE FUNCTION tile_cache.remove_excess_tiles(max_size bigint DEFAULT 100000) RETURNS void AS $$
DECLARE
  _current_size bigint;
  _num_deleted integer;
BEGIN
  /** Delete the most stale tiles until fewer than max_size tiles remain. */
  -- Get approximate size of cache
  SELECT pg_total_relation_size('tile_cache.tile') INTO _current_size;
  
  -- Get approximate number of tiles in cache table (without full table scan)
  SELECT reltuples::bigint AS estimate
  FROM pg_class
  WHERE oid = 'tile_cache.tile'::regclass
  INTO _current_size;

  -- Delete tiles until cache size is less than max_size
  _num_deleted := _current_size - max_size;

  IF _current_size > max_size THEN
    DELETE FROM tile_cache.tile
    WHERE last_used < (
      SELECT last_used FROM tile_cache.tile
      ORDER BY last_used ASC
      LIMIT 1
      OFFSET _num_deleted
    );

    RAISE NOTICE 'Deleted % tiles to reduce cache size', _num_deleted;
  END IF;
END;
$$ LANGUAGE plpgsql VOLATILE;


INSERT INTO tile_cache.profile (name, format, content_type, minzoom, maxzoom)
VALUES
  ('carto', 'pbf', 'application/x-protobuf', 0, 14),
  ('carto-slim', 'pbf', 'application/x-protobuf', 0, 14),
  ('carto-image', 'png', 'image/png', 0, 14),
  ('carto-slim-rotated', 'pbf', 'application/x-protobuf', 0, 14)
ON CONFLICT (name) DO NOTHING;
