/* The tile-cache schema, copied from `schema/core/0029-tile_utils.setup.sql`
   and `schema/core/0032-tile_cache.sql`
   and `schema/core/0033-tile_cache.sources.sql`.

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

/* A generational cache. Tiles live in a ring of unlogged generations: new tiles go
   to the current one, and eviction truncates the oldest, which costs nothing per row
   and writes no WAL. A tile read from an older generation is copied forward, so
   tiles in use survive while unused ones expire with their generation. Expensive
   tiles go to generation 0, a logged partition that is never rotated, so they
   replicate and survive a crash or failover. */
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
  generation smallint NOT NULL,
  created timestamp without time zone NOT NULL DEFAULT now(),
  /* TODO: we could cache each layer separately and merge in the tile server */
  --layers text[] NOT NULL,
  tile bytea NOT NULL,
  -- A tile may sit in several generations until the older copies are truncated.
  PRIMARY KEY (x, y, z, profile, args_hash, generation),
  -- Make sure tile is within TMS bounds
  CHECK (x >= 0 AND y >= 0 AND z >= 0 AND x < 2^z AND y < 2^z)
) PARTITION BY LIST (generation);
/* We'll need to add a TMS column if we want to support non-mercator tiles */

-- Persistence is set per partition; a partitioned parent's own setting is not inherited.
CREATE TABLE IF NOT EXISTS tile_cache.tile_pinned
  PARTITION OF tile_cache.tile FOR VALUES IN (0);
CREATE UNLOGGED TABLE IF NOT EXISTS tile_cache.tile_g1
  PARTITION OF tile_cache.tile FOR VALUES IN (1);
CREATE UNLOGGED TABLE IF NOT EXISTS tile_cache.tile_g2
  PARTITION OF tile_cache.tile FOR VALUES IN (2);
CREATE UNLOGGED TABLE IF NOT EXISTS tile_cache.tile_g3
  PARTITION OF tile_cache.tile FOR VALUES IN (3);
CREATE UNLOGGED TABLE IF NOT EXISTS tile_cache.tile_g4
  PARTITION OF tile_cache.tile FOR VALUES IN (4);
CREATE UNLOGGED TABLE IF NOT EXISTS tile_cache.tile_g5
  PARTITION OF tile_cache.tile FOR VALUES IN (5);
CREATE UNLOGGED TABLE IF NOT EXISTS tile_cache.tile_g6
  PARTITION OF tile_cache.tile FOR VALUES IN (6);

/* The ring's position and the rules that place tiles in it. One row. */
CREATE TABLE IF NOT EXISTS tile_cache.state (
  id boolean PRIMARY KEY DEFAULT true CHECK (id),
  current_generation smallint NOT NULL DEFAULT 1,
  -- Must match the tile_g* partitions above.
  generations smallint NOT NULL DEFAULT 6,
  -- Copy a tile forward once it is this many generations behind the current one.
  promote_distance smallint NOT NULL DEFAULT 2,
  -- Tiles at or below this zoom, or slower than this to render, are pinned.
  pin_max_zoom smallint NOT NULL DEFAULT 6,
  pin_min_render_ms integer NOT NULL DEFAULT 2000,
  rotated_at timestamp with time zone,
  CHECK (current_generation BETWEEN 1 AND generations),
  CHECK (promote_distance BETWEEN 1 AND generations - 1)
);

INSERT INTO tile_cache.state DEFAULT VALUES ON CONFLICT DO NOTHING;

CREATE OR REPLACE VIEW tile_cache.tile_info AS
SELECT
  x,
  y,
  z,
  profile,
  args_hash,
  generation,
  length(tile) tile_size,
  created
FROM tile_cache.tile;

CREATE OR REPLACE VIEW tile_cache.partition_info AS
SELECT
  CASE
    WHEN c.relname = 'tile_pinned' THEN 0
    ELSE substring(c.relname FROM 'tile_g([0-9]+)')::smallint
  END AS generation,
  c.relname AS partition,
  c.relpersistence = 'u' AS unlogged,
  greatest(c.reltuples, 0)::bigint AS est_tiles,
  pg_total_relation_size(c.oid) AS bytes
FROM pg_inherits i
JOIN pg_class c ON c.oid = i.inhrelid
WHERE i.inhparent = 'tile_cache.tile'::regclass;

-- Replaced by tile_cache.rotate, which evicts by truncating a generation.
DROP FUNCTION IF EXISTS tile_cache.remove_excess_tiles(bigint);
DROP FUNCTION IF EXISTS tile_cache.remove_excess_tiles(bigint, bigint, integer);

CREATE OR REPLACE FUNCTION tile_cache.rotate(
  max_bytes bigint DEFAULT 20000000000,
  max_pinned_bytes bigint DEFAULT 2000000000,
  lock_timeout text DEFAULT '2s'
) RETURNS TABLE (rotated_to smallint, pinned_evicted bigint) AS $$
DECLARE
  _state tile_cache.state;
  _next smallint;
  _evicted bigint := 0;
BEGIN
  /** Advance the ring once the current generation holds its share of max_bytes, and
    trim the pinned partition to max_pinned_bytes. Safe to call often from many
    workers: only one call does anything at a time. */

  -- Every tileserver worker runs this on a timer.
  IF NOT pg_try_advisory_xact_lock(hashtext('tile_cache.rotate')) THEN
    RETURN;
  END IF;

  SELECT * INTO _state FROM tile_cache.state FOR UPDATE;

  IF pg_total_relation_size(('tile_cache.tile_g' || _state.current_generation)::regclass)
     >= max_bytes / _state.generations THEN
    _next := mod(_state.current_generation, _state.generations) + 1;
    /* TRUNCATE waits behind any query holding the partition, and every new lookup
       would queue behind it; give up quickly and retry on the next call. */
    PERFORM set_config('lock_timeout', lock_timeout, true);
    EXECUTE 'TRUNCATE tile_cache.' || quote_ident('tile_g' || _next);
    UPDATE tile_cache.state SET current_generation = _next, rotated_at = now();
    rotated_to := _next;
  END IF;

  -- Logical bytes: octet_length reads the stored size without detoasting.
  WITH ranked AS (
    SELECT ctid, sum(octet_length(tile)) OVER (ORDER BY created DESC, ctid) AS newer_bytes
    FROM tile_cache.tile_pinned
  )
  DELETE FROM tile_cache.tile_pinned p
  USING ranked r
  WHERE p.ctid = r.ctid AND r.newer_bytes > max_pinned_bytes;
  GET DIAGNOSTICS _evicted = ROW_COUNT;
  pinned_evicted := _evicted;

  RETURN NEXT;
END;
$$ LANGUAGE plpgsql VOLATILE;

ALTER TABLE tile_cache.tile ADD COLUMN IF NOT EXISTS sources integer[];

INSERT INTO tile_cache.profile (name, format, content_type, minzoom, maxzoom)
VALUES
  ('carto', 'pbf', 'application/x-protobuf', 0, 14),
  ('carto-slim', 'pbf', 'application/x-protobuf', 0, 14),
  ('carto-image', 'png', 'image/png', 0, 14),
  ('carto-slim-rotated', 'pbf', 'application/x-protobuf', 0, 14)
ON CONFLICT (name) DO NOTHING;
