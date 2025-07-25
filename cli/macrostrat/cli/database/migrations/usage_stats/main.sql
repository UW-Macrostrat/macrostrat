CREATE SCHEMA usage_stats;

CREATE TABLE IF NOT EXISTS usage_stats.rockd_stats (
    id serial PRIMARY KEY,
    date timestamp with time zone NOT NULL DEFAULT now(),
    ip text NOT NULL,
    lat float NOT NULL,
    lng float NOT NULL,
    matomo_id integer NOT NULL
);

CREATE TABLE IF NOT EXISTS usage_stats.macrostrat_stats (
    id serial PRIMARY KEY,
    date timestamp with time zone NOT NULL DEFAULT now(),
    ip text NOT NULL,
    lat float NOT NULL,
    lng float NOT NULL,
    matomo_id integer NOT NULL
);

CREATE TABLE IF NOT EXISTS usage_stats.tileserver_stats (
    req_id serial PRIMARY KEY,
    uri text NOT NULL,
    layer text NOT NULL,
    ext text NOT NULL,
    x integer NOT NULL,
    y integer NOT NULL,
    z integer NOT NULL,
    referrer text NOT NULL,
    app text,
    app_version text,
    cache_hit boolean NOT NULL,
    redis_hit boolean NOT NULL,
    time timestamp without time zone NOT NULL
);

