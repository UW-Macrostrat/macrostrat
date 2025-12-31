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
-- Name: storage; Type: SCHEMA; Schema: -; Owner: macrostrat
--

CREATE SCHEMA storage;


ALTER SCHEMA storage OWNER TO macrostrat;

--
-- Name: scheme; Type: TYPE; Schema: storage; Owner: macrostrat
--

CREATE TYPE storage.scheme AS ENUM (
    's3',
    'https',
    'http'
);


ALTER TYPE storage.scheme OWNER TO macrostrat;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: object; Type: TABLE; Schema: storage; Owner: macrostrat
--

CREATE TABLE storage.object (
    id integer NOT NULL,
    scheme storage.scheme NOT NULL,
    host character varying(255) NOT NULL,
    bucket character varying(255) NOT NULL,
    key character varying(255) NOT NULL,
    source jsonb,
    mime_type character varying(255),
    sha256_hash character varying(255),
    created_on timestamp with time zone DEFAULT now() NOT NULL,
    updated_on timestamp with time zone DEFAULT now() NOT NULL,
    deleted_on timestamp with time zone
);


ALTER TABLE storage.object OWNER TO macrostrat;

--
-- Name: object_id_seq; Type: SEQUENCE; Schema: storage; Owner: macrostrat
--

CREATE SEQUENCE storage.object_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE storage.object_id_seq OWNER TO macrostrat;

--
-- Name: object_id_seq; Type: SEQUENCE OWNED BY; Schema: storage; Owner: macrostrat
--

ALTER SEQUENCE storage.object_id_seq OWNED BY storage.object.id;


--
-- Name: object id; Type: DEFAULT; Schema: storage; Owner: macrostrat
--

ALTER TABLE ONLY storage.object ALTER COLUMN id SET DEFAULT nextval('storage.object_id_seq'::regclass);


--
-- Name: object object_pkey; Type: CONSTRAINT; Schema: storage; Owner: macrostrat
--

ALTER TABLE ONLY storage.object
    ADD CONSTRAINT object_pkey PRIMARY KEY (id);


--
-- Name: object unique_file; Type: CONSTRAINT; Schema: storage; Owner: macrostrat
--

ALTER TABLE ONLY storage.object
    ADD CONSTRAINT unique_file UNIQUE (scheme, host, bucket, key);


--
-- PostgreSQL database dump complete
--

