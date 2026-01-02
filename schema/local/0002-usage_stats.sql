--
-- PostgreSQL database dump
--

-- Dumped from database version 15.15 (Debian 15.15-1.pgdg12+1)
-- Dumped by pg_dump version 15.13 (Debian 15.13-1.pgdg120+1)

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

--
-- Name: usage_stats; Type: SCHEMA; Schema: -; Owner: macrostrat-admin
--

CREATE SCHEMA usage_stats;


ALTER SCHEMA usage_stats OWNER TO "macrostrat-admin";

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: macrostrat_stats; Type: TABLE; Schema: usage_stats; Owner: macrostrat-admin
--

CREATE TABLE usage_stats.macrostrat_stats (
    id integer NOT NULL,
    date timestamp with time zone DEFAULT now() NOT NULL,
    ip text NOT NULL,
    lat double precision NOT NULL,
    lng double precision NOT NULL,
    matomo_id integer NOT NULL
);


ALTER TABLE usage_stats.macrostrat_stats OWNER TO "macrostrat-admin";

--
-- Name: rockd_stats; Type: TABLE; Schema: usage_stats; Owner: macrostrat-admin
--

CREATE TABLE usage_stats.rockd_stats (
    id integer NOT NULL,
    date timestamp with time zone DEFAULT now() NOT NULL,
    ip text NOT NULL,
    lat double precision NOT NULL,
    lng double precision NOT NULL,
    matomo_id integer NOT NULL
);


ALTER TABLE usage_stats.rockd_stats OWNER TO "macrostrat-admin";

--
-- Name: macrostrat_stats_id_seq; Type: SEQUENCE; Schema: usage_stats; Owner: macrostrat-admin
--

CREATE SEQUENCE usage_stats.macrostrat_stats_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE usage_stats.macrostrat_stats_id_seq OWNER TO "macrostrat-admin";

--
-- Name: macrostrat_stats_id_seq; Type: SEQUENCE OWNED BY; Schema: usage_stats; Owner: macrostrat-admin
--

ALTER SEQUENCE usage_stats.macrostrat_stats_id_seq OWNED BY usage_stats.macrostrat_stats.id;


--
-- Name: rockd_stats_id_seq; Type: SEQUENCE; Schema: usage_stats; Owner: macrostrat-admin
--

CREATE SEQUENCE usage_stats.rockd_stats_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE usage_stats.rockd_stats_id_seq OWNER TO "macrostrat-admin";

--
-- Name: rockd_stats_id_seq; Type: SEQUENCE OWNED BY; Schema: usage_stats; Owner: macrostrat-admin
--

ALTER SEQUENCE usage_stats.rockd_stats_id_seq OWNED BY usage_stats.rockd_stats.id;


--
-- Name: macrostrat_stats id; Type: DEFAULT; Schema: usage_stats; Owner: macrostrat-admin
--

ALTER TABLE ONLY usage_stats.macrostrat_stats ALTER COLUMN id SET DEFAULT nextval('usage_stats.macrostrat_stats_id_seq'::regclass);


--
-- Name: rockd_stats id; Type: DEFAULT; Schema: usage_stats; Owner: macrostrat-admin
--

ALTER TABLE ONLY usage_stats.rockd_stats ALTER COLUMN id SET DEFAULT nextval('usage_stats.rockd_stats_id_seq'::regclass);


--
-- Name: macrostrat_stats macrostrat_stats_pkey; Type: CONSTRAINT; Schema: usage_stats; Owner: macrostrat-admin
--

ALTER TABLE ONLY usage_stats.macrostrat_stats
    ADD CONSTRAINT macrostrat_stats_pkey PRIMARY KEY (id);


--
-- Name: rockd_stats rockd_stats_pkey; Type: CONSTRAINT; Schema: usage_stats; Owner: macrostrat-admin
--

ALTER TABLE ONLY usage_stats.rockd_stats
    ADD CONSTRAINT rockd_stats_pkey PRIMARY KEY (id);


--
-- PostgreSQL database dump complete
--

