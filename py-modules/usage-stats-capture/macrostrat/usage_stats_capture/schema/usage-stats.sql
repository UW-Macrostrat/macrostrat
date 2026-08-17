CREATE SCHEMA IF NOT EXISTS usage_stats;

-- Central ingestion ledger, shared by every pipeline.
--
-- Keyed by (object_name, pipeline) rather than carrying a boolean flag per
-- pipeline: per-pipeline record counts stay meaningful, a new pipeline can
-- backfill over retained history with no schema change, and a pipeline that
-- fails on an object doesn't falsely mark the others as done.
--
-- The row is written LAST within an object's transaction, so an interrupted
-- run leaves the object unrecorded and safely re-processes it.
CREATE TABLE IF NOT EXISTS usage_stats.processed_logs (
  object_name text NOT NULL,
  pipeline text NOT NULL,
  etag text,
  size bigint,
  last_modified timestamptz,
  num_records integer,   -- total log lines read from the object
  num_matched integer,   -- records this pipeline kept
  processed_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (object_name, pipeline)
);

CREATE INDEX IF NOT EXISTS processed_logs_pipeline
  ON usage_stats.processed_logs (pipeline);

--------------------------------------------------------------------------------
-- Tileserver pipeline
--------------------------------------------------------------------------------
-- new_system distinguishes rows aggregated by the log-dump pipeline (true) from
-- legacy rows migrated from the old direct-push era (false). is_bot separates
-- known automated clients (cache-warmers/scrapers) from organic traffic.
-- x_cache / x_tile_cache record the client-facing cache status (downstream
-- X-Cache ~ L1/Varnish, X-Tile-Cache ~ L2/tileserver): hit/miss/bypass, or ''
-- when the header is absent. All are part of the unique key so the classes
-- accumulate separately and never merge.
--
-- referrer holds the *host* of the Referer header (scheme, `www.`, path and
-- query stripped; '' when absent) — bounded cardinality, unlike full URLs.
-- app / app_version came from the legacy `?referrer=`/`?version=` query params,
-- which current clients no longer send; they are retained for the legacy
-- lineage and written as 'none' by the current pipeline.
CREATE TABLE IF NOT EXISTS usage_stats.tileserver_day_index (
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
  CONSTRAINT tileserver_day_index_unique
    UNIQUE (layer, ext, referrer, app, app_version, date, new_system, is_bot, x_cache, x_tile_cache)
);

CREATE TABLE IF NOT EXISTS usage_stats.tileserver_location_index (
  layer text NOT NULL,
  ext text NOT NULL,
  x integer NOT NULL,
  y integer NOT NULL,
  z integer NOT NULL,
  orig_z integer NOT NULL,
  num_requests integer NOT NULL,
  new_system boolean NOT NULL DEFAULT false,
  is_bot boolean NOT NULL DEFAULT false,
  CONSTRAINT tileserver_location_index_unique
    UNIQUE (layer, ext, x, y, z, orig_z, new_system, is_bot)
);

-- Supports the spatial-heatmap tile route, which filters by z + x/y ranges
-- (the unique constraint above leads with layer/ext, so it can't serve this).
CREATE INDEX IF NOT EXISTS tileserver_location_index_zxy
  ON usage_stats.tileserver_location_index (z, x, y);

--------------------------------------------------------------------------------
-- Rockd dashboard pipeline
--------------------------------------------------------------------------------
-- One row per dashboard load: GET /api/v2/mobile/dashboard on macrostrat.org.
-- The route is only called when a user opens the Rockd app's dashboard, and the
-- coordinates come from the device GPS — so each row is a real user at a real
-- place and time.
--
-- Stored raw (no ingest-time deduplication): consecutive requests from a
-- stationary device sit ~110 m apart from GPS jitter alone, so any dedup
-- threshold is a judgement call and belongs in a view that can be revised
-- without re-pulling the logs. See the dashboard_loads_deduplicated views.
--
-- client_id is a keyed BLAKE2b digest of the client address, never the address
-- itself; the key is a secret resolved from configuration at ingest. It is
-- stable across runs (dedup must work across log-object boundaries) which makes
-- it a long-lived pseudonym — rotating the key trades longitudinal reach for
-- unlinkability and is a configuration change, not a schema one.
CREATE TABLE IF NOT EXISTS usage_stats.rockd_dashboard_loads (
  id bigserial PRIMARY KEY,
  time timestamptz NOT NULL,
  lat double precision NOT NULL,
  lng double precision NOT NULL,
  app text NOT NULL DEFAULT '',
  app_version text NOT NULL DEFAULT '',
  client_id text NOT NULL,
  status smallint,
  -- Makes re-ingestion idempotent, so --reprocess and interrupted backfills
  -- can't duplicate rows. Timestamps carry sub-second precision, so a genuine
  -- collision needs one client hitting the route twice in the same microsecond.
  CONSTRAINT rockd_dashboard_loads_unique UNIQUE (time, client_id)
);

CREATE INDEX IF NOT EXISTS rockd_dashboard_loads_time
  ON usage_stats.rockd_dashboard_loads (time);

-- Serves the dedup window functions (partition by client, order by time).
CREATE INDEX IF NOT EXISTS rockd_dashboard_loads_client_time
  ON usage_stats.rockd_dashboard_loads (client_id, time);

-- Spatial index for the map route.
CREATE INDEX IF NOT EXISTS rockd_dashboard_loads_geom
  ON usage_stats.rockd_dashboard_loads
  USING gist (ST_SetSRID(ST_MakePoint(lng, lat), 4326));

--------------------------------------------------------------------------------
-- Deduplicated views
--------------------------------------------------------------------------------
-- A load is a *repeat* of its predecessor when the same client reports from
-- within both a distance and a time threshold. Thresholds are deliberately
-- above the ~110 m median GPS jitter between consecutive same-client requests;
-- below that, dedup removes almost nothing (100 m / 15 min retains 4 in 5).
--
--   distinct view: 250 m / 15 min  -> ~25 in 100 retained over the full corpus
--   session view:  500 m / 1 h     -> ~20 in 100 retained
--
-- (Percent signs are spelled out throughout this file: it is executed through
-- SQLAlchemy, whose driver reads a bare percent sign -- even inside a comment --
-- as a bind parameter and fails with "incomplete placeholder".)
--
-- IMPORTANT -- which request a row is compared against. These views compare each
-- request to the *immediately preceding* one from the same client, because that
-- is what a window function can express. The alternative is to compare against
-- the last *kept* request, which retains noticeably more (on 2026-08-14: 30.6
-- in 100 here, versus 47.7 in 100 for last-kept) and arguably describes usage
-- better: a user walking a traverse in sub-threshold steps collapses to a single
-- point under these views, but would yield a point every 250 m under last-kept.
-- Last-kept needs an iterative/recursive evaluation, so it is not implemented;
-- treat these counts as a conservative lower bound on distinct views.
CREATE OR REPLACE VIEW usage_stats.rockd_dashboard_views AS
WITH stepped AS (
  SELECT
    *,
    lag(time) OVER w AS prev_time,
    lag(lat) OVER w AS prev_lat,
    lag(lng) OVER w AS prev_lng
  FROM usage_stats.rockd_dashboard_loads
  WINDOW w AS (PARTITION BY client_id ORDER BY time)
)
SELECT id, time, lat, lng, app, app_version, client_id, status
FROM stepped
WHERE prev_time IS NULL
   OR time - prev_time > INTERVAL '15 minutes'
   OR ST_DistanceSphere(
        ST_SetSRID(ST_MakePoint(lng, lat), 4326),
        ST_SetSRID(ST_MakePoint(prev_lng, prev_lat), 4326)
      ) > 250;

CREATE OR REPLACE VIEW usage_stats.rockd_dashboard_sessions AS
WITH stepped AS (
  SELECT
    *,
    lag(time) OVER w AS prev_time,
    lag(lat) OVER w AS prev_lat,
    lag(lng) OVER w AS prev_lng
  FROM usage_stats.rockd_dashboard_loads
  WINDOW w AS (PARTITION BY client_id ORDER BY time)
)
SELECT id, time, lat, lng, app, app_version, client_id, status
FROM stepped
WHERE prev_time IS NULL
   OR time - prev_time > INTERVAL '1 hour'
   OR ST_DistanceSphere(
        ST_SetSRID(ST_MakePoint(lng, lat), 4326),
        ST_SetSRID(ST_MakePoint(prev_lng, prev_lat), 4326)
      ) > 500;

--------------------------------------------------------------------------------
-- Back-compatibility
--------------------------------------------------------------------------------
-- The tileserver heatmap route, the `plot` command and any ad-hoc queries still
-- reference tileserver_stats.{day,location}_index. Keep those names resolving
-- to the renamed tables while consumers migrate. The legacy
-- tileserver_stats.requests / processing_status tables are untouched (see
-- tileserver-stats.legacy.sql).
CREATE SCHEMA IF NOT EXISTS tileserver_stats;

CREATE OR REPLACE VIEW tileserver_stats.day_index AS
  SELECT * FROM usage_stats.tileserver_day_index;

CREATE OR REPLACE VIEW tileserver_stats.location_index AS
  SELECT * FROM usage_stats.tileserver_location_index;

/** PRIVILEGES */

-- Least-privilege access for the log harvester. Only grants on this schema's own
-- objects live here: the `logs_writer` role itself, and its membership for the
-- operator-created "logs-writer" login, are in schema/core/0000-roles.sql. That
-- chunk runs as the connector (superuser); this one runs as `macrostrat`, which
-- can neither CREATE ROLE nor grant membership in a role it has no admin option
-- on. Attempting either here aborts this file, and the harvester then reports
-- the confusing "permission denied for schema usage_stats".
--
-- No DELETE or TRUNCATE anywhere: `usage-stats reset` is an administrative act,
-- not something the scheduled job should be able to do to months of history. No
-- CREATE on the schema, and nothing on the deduplication views.
GRANT USAGE ON SCHEMA usage_stats TO logs_writer;

-- Read to find out which objects are already done, write to record new ones.
GRANT SELECT, INSERT, UPDATE ON usage_stats.processed_logs TO logs_writer;

-- Aggregates are upserted with ON CONFLICT ... DO UPDATE, which needs UPDATE
-- and also SELECT: the SET expression reads the existing row's count.
GRANT SELECT, INSERT, UPDATE ON usage_stats.tileserver_day_index TO logs_writer;
GRANT SELECT, INSERT, UPDATE
  ON usage_stats.tileserver_location_index TO logs_writer;

-- Dashboard loads are append-only, so no UPDATE. SELECT is required despite
-- that: the insert's ON CONFLICT (time, client_id) names those columns, and
-- referencing them needs read privilege even with DO NOTHING. Verified by
-- test -- INSERT alone is denied.
GRANT SELECT, INSERT ON usage_stats.rockd_dashboard_loads TO logs_writer;

-- Covers rockd_dashboard_loads' bigserial id, and anything added later.
GRANT USAGE ON ALL SEQUENCES IN SCHEMA usage_stats TO logs_writer;
