CREATE SCHEMA IF NOT EXISTS stats;

CREATE TABLE IF NOT EXISTS stats.processing_status (
  last_row_id integer NOT NULL,
  last_row_time timestamp without time zone DEFAULT now()
);

CREATE TABLE IF NOT EXISTS stats.day_index (
  layer text NOT NULL,
  ext text NOT NULL,
  referrer text NOT NULL,
  app text NOT NULL,
  app_version text NOT NULL,
  date timestamp without time zone NOT NULL,
  num_requests integer NOT NULL,
  UNIQUE (layer, ext, referrer, app, app_version, date)
);

CREATE TABLE IF NOT EXISTS stats.location_index (
  layer text NOT NULL,
  ext text NOT NULL,
  x integer NOT NULL,
  y integer NOT NULL,
  z integer NOT NULL,
  orig_z integer NOT NULL,
  num_requests integer NOT NULL,
  UNIQUE (layer, ext, x, y, z, orig_z)
);

INSERT INTO stats.processing_status (last_row_id) VALUES (0);