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

