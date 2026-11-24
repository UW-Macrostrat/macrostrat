CREATE SCHEMA IF NOT EXISTS tileserver_stats;

/** Keep legacy tileserver_stats.requests and tileserver_stats.processing_status tables
  for now, so the old direct-push pipeline can still write to them. */
-- auto-generated definition
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
  time timestamp DEFAULT NOW()
);

CREATE TABLE tileserver_stats.processing_status (
  last_row_id integer NOT NULL,
  last_row_time timestamp DEFAULT NOW()
);

-- Readable by the `db copy` source login, as the rest of this schema is.
GRANT SELECT ON tileserver_stats.requests, tileserver_stats.processing_status
  TO macrostrat_reader;
GRANT SELECT ON SEQUENCE tileserver_stats.requests_req_id_seq TO macrostrat_reader;
