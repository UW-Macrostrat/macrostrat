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

CREATE TABLE IF NOT EXISTS tileserver_stats.day_index (
  layer text NOT NULL,
  ext text NOT NULL,
  referrer text NOT NULL,
  app text NOT NULL,
  app_version text NOT NULL,
  date timestamp without time zone NOT NULL,
  num_requests integer NOT NULL,
  UNIQUE (layer, ext, referrer, app, app_version, date)
);

CREATE TABLE IF NOT EXISTS tileserver_stats.location_index (
  layer text NOT NULL,
  ext text NOT NULL,
  x integer NOT NULL,
  y integer NOT NULL,
  z integer NOT NULL,
  orig_z integer NOT NULL,
  num_requests integer NOT NULL,
  UNIQUE (layer, ext, x, y, z, orig_z)
);

--INSERT INTO tileserver_stats.processing_status (last_row_id) VALUES (0);
