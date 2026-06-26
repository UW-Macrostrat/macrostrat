CREATE SCHEMA IF NOT EXISTS tileserver_stats;

CREATE TABLE tileserver_stats.requests (
  req_id serial
    PRIMARY KEY,
  uri text,
  layer text,
  ext text,
  x integer,
  y integer,
  z integer,
  referrer text,
  app text,
  app_version text,
  cache_hit boolean DEFAULT FALSE,
  redis_hit boolean DEFAULT FALSE,
  time timestamp DEFAULT now()
);

CREATE TABLE IF NOT EXISTS tileserver_stats.processing_status (
  last_row_id integer NOT NULL,
  last_row_time timestamp without time zone DEFAULT now()
);

-- Tracks which log-dump objects have been ingested, so reruns never
-- reprocess (or require deleting) a log file. Keyed by object name; etag/size
-- are retained so a re-uploaded object can be detected and re-ingested later.
CREATE TABLE IF NOT EXISTS tileserver_stats.processed_logs (
  object_name text PRIMARY KEY,
  etag text,
  size bigint,
  last_modified timestamptz,
  num_records integer,        -- total log lines parsed from the object
  num_tile_requests integer,  -- tile rows inserted into requests
  processed_at timestamptz NOT NULL DEFAULT now()
);

-- new_system distinguishes rows aggregated by the new log-dump pipeline
-- (true) from legacy rows migrated from the old direct-push era (false). It is
-- part of the unique key so the two lineages accumulate separately and never
-- merge.
CREATE TABLE IF NOT EXISTS tileserver_stats.day_index (
  layer text NOT NULL,
  ext text NOT NULL,
  referrer text NOT NULL,
  app text NOT NULL,
  app_version text NOT NULL,
  date timestamp without time zone NOT NULL,
  num_requests integer NOT NULL,
  new_system boolean NOT NULL DEFAULT false,
  CONSTRAINT day_index_unique UNIQUE (layer, ext, referrer, app, app_version, date, new_system)
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
  CONSTRAINT location_index_unique UNIQUE (layer, ext, x, y, z, orig_z, new_system)
);

--INSERT INTO tileserver_stats.processing_status (last_row_id) VALUES (0);
