CREATE SCHEMA IF NOT EXISTS tileserver_stats;

-- The pipeline aggregates log-dump objects directly into the indexes below;
-- there is no raw `requests` staging table (and no processing_status watermark).
-- Per-object idempotency comes from processed_logs.
--
-- Tracks which log-dump objects have been ingested, so reruns never reprocess
-- (or require deleting) a log file. Keyed by object name; etag/size are retained
-- so a re-uploaded object can be detected and re-ingested later.
CREATE TABLE IF NOT EXISTS tileserver_stats.processed_logs (
  object_name text PRIMARY KEY,
  etag text,
  size bigint,
  last_modified timestamptz,
  num_records integer,        -- total log lines parsed from the object
  num_tile_requests integer,  -- relevant tile requests aggregated from the object
  processed_at timestamptz NOT NULL DEFAULT now()
);

-- new_system distinguishes rows aggregated by the new log-dump pipeline
-- (true) from legacy rows migrated from the old direct-push era (false).
-- is_bot separates known automated clients (cache-warmers/scrapers; see
-- KNOWN_BOTS) from organic traffic. x_cache / x_tile_cache record the
-- client-facing cache status (downstream X-Cache ≈ L1/Varnish, X-Tile-Cache ≈
-- L2/tileserver): hit/miss/bypass, or '' when the header is absent. All are part
-- of the unique key so the classes accumulate separately and never merge.
CREATE TABLE IF NOT EXISTS tileserver_stats.day_index (
  layer text NOT NULL,
  ext text NOT NULL,
  referrer text NOT NULL,
  app text NOT NULL,
  app_version text NOT NULL,
  date timestamp without time zone NOT NULL,
  num_requests integer NOT NULL,
  new_system boolean NOT NULL DEFAULT false,
  is_bot boolean NOT NULL DEFAULT false,
  x_cache text NOT NULL DEFAULT '',
  x_tile_cache text NOT NULL DEFAULT '',
  CONSTRAINT day_index_unique UNIQUE (layer, ext, referrer, app, app_version, date, new_system, is_bot, x_cache, x_tile_cache)
);

CREATE TABLE IF NOT EXISTS tileserver_stats.location_index (
  layer text NOT NULL,
  ext text NOT NULL,
  x integer NOT NULL,
  y integer NOT NULL,
  z integer NOT NULL,
  orig_z integer NOT NULL,
  num_requests integer NOT NULL,
  new_system boolean NOT NULL DEFAULT false,
  is_bot boolean NOT NULL DEFAULT false,
  CONSTRAINT location_index_unique UNIQUE (layer, ext, x, y, z, orig_z, new_system, is_bot)
);

-- Supports the spatial-heatmap tile route, which filters by z + x/y ranges
-- (the unique constraint above leads with layer/ext, so it can't serve this).
CREATE INDEX IF NOT EXISTS location_index_zxy
  ON tileserver_stats.location_index (z, x, y);
