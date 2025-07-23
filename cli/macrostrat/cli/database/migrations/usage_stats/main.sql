CREATE SCHEMA usage_stats;

CREATE TABLE IF NOT EXISTS usage_stats.rockd (
    id serial PRIMARY KEY,
    date timestamp with time zone NOT NULL DEFAULT now(),
    ip text NOT NULL,
    lat float NOT NULL,
    lng float NOT NULL,
    matomo_id integer NOT NULL
);

CREATE TABLE IF NOT EXISTS usage_stats.macrostrat (
    id serial PRIMARY KEY,
    date timestamp with time zone NOT NULL DEFAULT now(),
    ip text NOT NULL,
    lat float NOT NULL,
    lng float NOT NULL,
    matomo_id integer NOT NULL
);
