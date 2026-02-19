

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

CREATE SCHEMA usage_stats;
ALTER SCHEMA usage_stats OWNER TO macrostrat_admin;
SET default_tablespace = '';
SET default_table_access_method = heap;

CREATE TABLE usage_stats.macrostrat_stats (
    id integer NOT NULL,
    date timestamp with time zone DEFAULT now() NOT NULL,
    ip text NOT NULL,
    lat double precision NOT NULL,
    lng double precision NOT NULL,
    matomo_id integer NOT NULL
);
ALTER TABLE usage_stats.macrostrat_stats OWNER TO macrostrat_admin;

CREATE TABLE usage_stats.rockd_stats (
    id integer NOT NULL,
    date timestamp with time zone DEFAULT now() NOT NULL,
    ip text NOT NULL,
    lat double precision NOT NULL,
    lng double precision NOT NULL,
    matomo_id integer NOT NULL
);
ALTER TABLE usage_stats.rockd_stats OWNER TO macrostrat_admin;

CREATE SEQUENCE usage_stats.macrostrat_stats_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
ALTER TABLE usage_stats.macrostrat_stats_id_seq OWNER TO macrostrat_admin;

ALTER SEQUENCE usage_stats.macrostrat_stats_id_seq OWNED BY usage_stats.macrostrat_stats.id;

CREATE SEQUENCE usage_stats.rockd_stats_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
ALTER TABLE usage_stats.rockd_stats_id_seq OWNER TO macrostrat_admin;

ALTER SEQUENCE usage_stats.rockd_stats_id_seq OWNED BY usage_stats.rockd_stats.id;

ALTER TABLE ONLY usage_stats.macrostrat_stats ALTER COLUMN id SET DEFAULT nextval('usage_stats.macrostrat_stats_id_seq'::regclass);

ALTER TABLE ONLY usage_stats.rockd_stats ALTER COLUMN id SET DEFAULT nextval('usage_stats.rockd_stats_id_seq'::regclass);

ALTER TABLE ONLY usage_stats.macrostrat_stats
    ADD CONSTRAINT macrostrat_stats_pkey PRIMARY KEY (id);

ALTER TABLE ONLY usage_stats.rockd_stats
    ADD CONSTRAINT rockd_stats_pkey PRIMARY KEY (id);

