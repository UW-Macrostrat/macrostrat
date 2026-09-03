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

/* High-churn cache table: evictions are DELETEs, so autovacuum has to keep pace or
   the relation bloats without bound. The tile payload lives in TOAST, so the TOAST
   table needs the same treatment as the heap. */
ALTER TABLE tile_cache.tile SET (
  autovacuum_vacuum_scale_factor = 0.02,
  autovacuum_vacuum_threshold = 50000,
  autovacuum_vacuum_cost_limit = 2000,
  autovacuum_analyze_scale_factor = 0.05,
  toast.autovacuum_vacuum_scale_factor = 0.02,
  toast.autovacuum_vacuum_threshold = 50000,
  toast.autovacuum_vacuum_cost_limit = 2000
);

/* Superseded by the byte-budgeted signature below. Dropped explicitly because
   CREATE OR REPLACE would leave the old single-argument form in place as an
   overload, making a one-argument call ambiguous. */
DROP FUNCTION IF EXISTS tile_cache.remove_excess_tiles(bigint);

CREATE OR REPLACE FUNCTION tile_cache.remove_excess_tiles(
  max_bytes bigint DEFAULT 20000000000,
  max_tiles bigint DEFAULT 2000000,
  batch_size integer DEFAULT 50000
) RETURNS bigint AS $$
DECLARE
  _n_tiles bigint;
  _avg_tile_bytes numeric;
  _target_tiles bigint;
  _deleted bigint := 0;
  _batch bigint;
BEGIN
  /** Evict least-recently-used tiles until the cache fits within max_bytes.

    The budget is on *logical* payload bytes -- mean tile length times row count --
    and deliberately not on pg_total_relation_size. Eviction is a DELETE, which
    does not return space to the filesystem, so budgeting against physical size
    would chase bloat: the function would delete live tiles trying to reach a
    target that deleting cannot move. Physical size is held down by the autovacuum
    storage parameters set on the table above.

    max_tiles is a secondary ceiling, retaining the old row-count behaviour as a
    guard against pathologically small tiles.
  */

  SELECT reltuples::bigint FROM pg_class
  WHERE oid = 'tile_cache.tile'::regclass
  INTO _n_tiles;

  IF _n_tiles IS NULL OR _n_tiles <= 0 THEN
    RETURN 0;
  END IF;

  /* Sampled rather than aggregated: length(tile) over the whole table would
     detoast every row on every pass. */
  SELECT avg(length(tile)) FROM tile_cache.tile TABLESAMPLE SYSTEM (1)
  INTO _avg_tile_bytes;

  IF _avg_tile_bytes IS NULL OR _avg_tile_bytes <= 0 THEN
    -- Sample came back empty (small or sparsely-packed table); fall back to a head read.
    SELECT avg(length(tile)) FROM (SELECT tile FROM tile_cache.tile LIMIT 1000) s
    INTO _avg_tile_bytes;
  END IF;

  IF _avg_tile_bytes IS NULL OR _avg_tile_bytes <= 0 THEN
    RETURN 0;
  END IF;

  _target_tiles := least(max_tiles, (max_bytes / _avg_tile_bytes)::bigint);

  /* Batched so a large trim never lands as one oversized WAL burst. */
  WHILE _n_tiles - _deleted > _target_tiles LOOP
    _batch := least(batch_size::bigint, _n_tiles - _deleted - _target_tiles);

    DELETE FROM tile_cache.tile
    WHERE ctid IN (
      SELECT ctid FROM tile_cache.tile
      ORDER BY last_used ASC
      LIMIT _batch
    );

    GET DIAGNOSTICS _batch = ROW_COUNT;
    EXIT WHEN _batch = 0;
    _deleted := _deleted + _batch;
  END LOOP;

  IF _deleted > 0 THEN
    RAISE NOTICE USING MESSAGE =
      'Evicted ' || _deleted || ' tiles from tile_cache.tile (target ' || _target_tiles || ')';
  END IF;

  RETURN _deleted;
END;
$$ LANGUAGE plpgsql VOLATILE;


INSERT INTO tile_cache.profile (name, format, content_type, minzoom, maxzoom)
VALUES
  ('carto', 'pbf', 'application/x-protobuf', 0, 14),
  ('carto-slim', 'pbf', 'application/x-protobuf', 0, 14),
  ('carto-image', 'png', 'image/png', 0, 14),
  ('carto-slim-rotated', 'pbf', 'application/x-protobuf', 0, 14)
ON CONFLICT (name) DO NOTHING;
