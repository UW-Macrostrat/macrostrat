CREATE TABLE IF NOT EXISTS processing_status (
  last_row_id integer NOT NULL,
  last_row_time timestamp without time zone DEFAULT now()
);

CREATE TABLE IF NOT EXISTS day_index (
  layer text NOT NULL,
  ext text NOT NULL,
  referrer text,
  app text,
  app_version text,
  date timestamp without time zone NOT NULL
);

CREATE TABLE IF NOT EXISTS location_index (
  layer text NOT NULL,
  ext text NOT NULL,
  x integer NOT NULL,
  y integer NOT NULL,
  z integer NOT NULL,
  orig_z integer
);

INSERT INTO processing_status (last_row_id) VALUES (0);