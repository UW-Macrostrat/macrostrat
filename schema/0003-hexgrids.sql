--
-- PostgreSQL database dump
--

-- Dumped from database version 15.8
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
-- Name: hexgrids; Type: SCHEMA; Schema: -; Owner: macrostrat
--

CREATE SCHEMA hexgrids;


ALTER SCHEMA hexgrids OWNER TO macrostrat;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: bedrock_index; Type: TABLE; Schema: hexgrids; Owner: macrostrat
--

CREATE TABLE hexgrids.bedrock_index (
    legend_id integer NOT NULL,
    hex_id integer NOT NULL,
    coverage numeric
);


ALTER TABLE hexgrids.bedrock_index OWNER TO macrostrat;

--
-- Name: hexgrids; Type: TABLE; Schema: hexgrids; Owner: macrostrat
--

CREATE TABLE hexgrids.hexgrids (
    hex_id integer NOT NULL,
    res integer,
    geom public.geometry
);


ALTER TABLE hexgrids.hexgrids OWNER TO macrostrat;

--
-- Name: pbdb_index; Type: TABLE; Schema: hexgrids; Owner: macrostrat
--

CREATE TABLE hexgrids.pbdb_index (
    collection_no integer NOT NULL,
    hex_id integer NOT NULL
);


ALTER TABLE hexgrids.pbdb_index OWNER TO macrostrat;

--
-- Name: r10; Type: TABLE; Schema: hexgrids; Owner: macrostrat
--

CREATE TABLE hexgrids.r10 (
    hex_id integer NOT NULL,
    geom public.geometry(MultiPolygon,4326),
    web_geom public.geometry
);


ALTER TABLE hexgrids.r10 OWNER TO macrostrat;

--
-- Name: r10_ogc_fid_seq; Type: SEQUENCE; Schema: hexgrids; Owner: macrostrat
--

CREATE SEQUENCE hexgrids.r10_ogc_fid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE hexgrids.r10_ogc_fid_seq OWNER TO macrostrat;

--
-- Name: r10_ogc_fid_seq; Type: SEQUENCE OWNED BY; Schema: hexgrids; Owner: macrostrat
--

ALTER SEQUENCE hexgrids.r10_ogc_fid_seq OWNED BY hexgrids.r10.hex_id;


--
-- Name: r11; Type: TABLE; Schema: hexgrids; Owner: macrostrat
--

CREATE TABLE hexgrids.r11 (
    hex_id integer NOT NULL,
    geom public.geometry(MultiPolygon,4326),
    web_geom public.geometry
);


ALTER TABLE hexgrids.r11 OWNER TO macrostrat;

--
-- Name: r11_ogc_fid_seq; Type: SEQUENCE; Schema: hexgrids; Owner: macrostrat
--

CREATE SEQUENCE hexgrids.r11_ogc_fid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE hexgrids.r11_ogc_fid_seq OWNER TO macrostrat;

--
-- Name: r11_ogc_fid_seq; Type: SEQUENCE OWNED BY; Schema: hexgrids; Owner: macrostrat
--

ALTER SEQUENCE hexgrids.r11_ogc_fid_seq OWNED BY hexgrids.r11.hex_id;


--
-- Name: r12; Type: TABLE; Schema: hexgrids; Owner: macrostrat
--

CREATE TABLE hexgrids.r12 (
    hex_id integer NOT NULL,
    geom public.geometry(MultiPolygon,4326),
    web_geom public.geometry
);


ALTER TABLE hexgrids.r12 OWNER TO macrostrat;

--
-- Name: r12_ogc_fid_seq; Type: SEQUENCE; Schema: hexgrids; Owner: macrostrat
--

CREATE SEQUENCE hexgrids.r12_ogc_fid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE hexgrids.r12_ogc_fid_seq OWNER TO macrostrat;

--
-- Name: r12_ogc_fid_seq; Type: SEQUENCE OWNED BY; Schema: hexgrids; Owner: macrostrat
--

ALTER SEQUENCE hexgrids.r12_ogc_fid_seq OWNED BY hexgrids.r12.hex_id;


--
-- Name: r5; Type: TABLE; Schema: hexgrids; Owner: macrostrat
--

CREATE TABLE hexgrids.r5 (
    hex_id integer NOT NULL,
    geom public.geometry(MultiPolygon,4326),
    web_geom public.geometry
);


ALTER TABLE hexgrids.r5 OWNER TO macrostrat;

--
-- Name: r5_ogc_fid_seq; Type: SEQUENCE; Schema: hexgrids; Owner: macrostrat
--

CREATE SEQUENCE hexgrids.r5_ogc_fid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE hexgrids.r5_ogc_fid_seq OWNER TO macrostrat;

--
-- Name: r5_ogc_fid_seq; Type: SEQUENCE OWNED BY; Schema: hexgrids; Owner: macrostrat
--

ALTER SEQUENCE hexgrids.r5_ogc_fid_seq OWNED BY hexgrids.r5.hex_id;


--
-- Name: r6; Type: TABLE; Schema: hexgrids; Owner: macrostrat
--

CREATE TABLE hexgrids.r6 (
    hex_id integer NOT NULL,
    geom public.geometry(MultiPolygon,4326),
    web_geom public.geometry
);


ALTER TABLE hexgrids.r6 OWNER TO macrostrat;

--
-- Name: r6_ogc_fid_seq; Type: SEQUENCE; Schema: hexgrids; Owner: macrostrat
--

CREATE SEQUENCE hexgrids.r6_ogc_fid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE hexgrids.r6_ogc_fid_seq OWNER TO macrostrat;

--
-- Name: r6_ogc_fid_seq; Type: SEQUENCE OWNED BY; Schema: hexgrids; Owner: macrostrat
--

ALTER SEQUENCE hexgrids.r6_ogc_fid_seq OWNED BY hexgrids.r6.hex_id;


--
-- Name: r7; Type: TABLE; Schema: hexgrids; Owner: macrostrat
--

CREATE TABLE hexgrids.r7 (
    hex_id integer NOT NULL,
    geom public.geometry(MultiPolygon,4326),
    web_geom public.geometry
);


ALTER TABLE hexgrids.r7 OWNER TO macrostrat;

--
-- Name: r7_ogc_fid_seq; Type: SEQUENCE; Schema: hexgrids; Owner: macrostrat
--

CREATE SEQUENCE hexgrids.r7_ogc_fid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE hexgrids.r7_ogc_fid_seq OWNER TO macrostrat;

--
-- Name: r7_ogc_fid_seq; Type: SEQUENCE OWNED BY; Schema: hexgrids; Owner: macrostrat
--

ALTER SEQUENCE hexgrids.r7_ogc_fid_seq OWNED BY hexgrids.r7.hex_id;


--
-- Name: r8; Type: TABLE; Schema: hexgrids; Owner: macrostrat
--

CREATE TABLE hexgrids.r8 (
    hex_id integer NOT NULL,
    geom public.geometry(MultiPolygon,4326),
    web_geom public.geometry
);


ALTER TABLE hexgrids.r8 OWNER TO macrostrat;

--
-- Name: r8_ogc_fid_seq; Type: SEQUENCE; Schema: hexgrids; Owner: macrostrat
--

CREATE SEQUENCE hexgrids.r8_ogc_fid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE hexgrids.r8_ogc_fid_seq OWNER TO macrostrat;

--
-- Name: r8_ogc_fid_seq; Type: SEQUENCE OWNED BY; Schema: hexgrids; Owner: macrostrat
--

ALTER SEQUENCE hexgrids.r8_ogc_fid_seq OWNED BY hexgrids.r8.hex_id;


--
-- Name: r9; Type: TABLE; Schema: hexgrids; Owner: macrostrat
--

CREATE TABLE hexgrids.r9 (
    hex_id integer NOT NULL,
    geom public.geometry(MultiPolygon,4326),
    web_geom public.geometry
);


ALTER TABLE hexgrids.r9 OWNER TO macrostrat;

--
-- Name: r9_ogc_fid_seq; Type: SEQUENCE; Schema: hexgrids; Owner: macrostrat
--

CREATE SEQUENCE hexgrids.r9_ogc_fid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE hexgrids.r9_ogc_fid_seq OWNER TO macrostrat;

--
-- Name: r9_ogc_fid_seq; Type: SEQUENCE OWNED BY; Schema: hexgrids; Owner: macrostrat
--

ALTER SEQUENCE hexgrids.r9_ogc_fid_seq OWNED BY hexgrids.r9.hex_id;


--
-- Name: r10 hex_id; Type: DEFAULT; Schema: hexgrids; Owner: macrostrat
--

ALTER TABLE ONLY hexgrids.r10 ALTER COLUMN hex_id SET DEFAULT nextval('hexgrids.r10_ogc_fid_seq'::regclass);


--
-- Name: r11 hex_id; Type: DEFAULT; Schema: hexgrids; Owner: macrostrat
--

ALTER TABLE ONLY hexgrids.r11 ALTER COLUMN hex_id SET DEFAULT nextval('hexgrids.r11_ogc_fid_seq'::regclass);


--
-- Name: r12 hex_id; Type: DEFAULT; Schema: hexgrids; Owner: macrostrat
--

ALTER TABLE ONLY hexgrids.r12 ALTER COLUMN hex_id SET DEFAULT nextval('hexgrids.r12_ogc_fid_seq'::regclass);


--
-- Name: r5 hex_id; Type: DEFAULT; Schema: hexgrids; Owner: macrostrat
--

ALTER TABLE ONLY hexgrids.r5 ALTER COLUMN hex_id SET DEFAULT nextval('hexgrids.r5_ogc_fid_seq'::regclass);


--
-- Name: r6 hex_id; Type: DEFAULT; Schema: hexgrids; Owner: macrostrat
--

ALTER TABLE ONLY hexgrids.r6 ALTER COLUMN hex_id SET DEFAULT nextval('hexgrids.r6_ogc_fid_seq'::regclass);


--
-- Name: r7 hex_id; Type: DEFAULT; Schema: hexgrids; Owner: macrostrat
--

ALTER TABLE ONLY hexgrids.r7 ALTER COLUMN hex_id SET DEFAULT nextval('hexgrids.r7_ogc_fid_seq'::regclass);


--
-- Name: r8 hex_id; Type: DEFAULT; Schema: hexgrids; Owner: macrostrat
--

ALTER TABLE ONLY hexgrids.r8 ALTER COLUMN hex_id SET DEFAULT nextval('hexgrids.r8_ogc_fid_seq'::regclass);


--
-- Name: r9 hex_id; Type: DEFAULT; Schema: hexgrids; Owner: macrostrat
--

ALTER TABLE ONLY hexgrids.r9 ALTER COLUMN hex_id SET DEFAULT nextval('hexgrids.r9_ogc_fid_seq'::regclass);


--
-- Name: hexgrids hexgrids_pkey; Type: CONSTRAINT; Schema: hexgrids; Owner: macrostrat
--

ALTER TABLE ONLY hexgrids.hexgrids
    ADD CONSTRAINT hexgrids_pkey PRIMARY KEY (hex_id);


--
-- Name: r10 r10_pkey; Type: CONSTRAINT; Schema: hexgrids; Owner: macrostrat
--

ALTER TABLE ONLY hexgrids.r10
    ADD CONSTRAINT r10_pkey PRIMARY KEY (hex_id);


--
-- Name: r11 r11_pkey; Type: CONSTRAINT; Schema: hexgrids; Owner: macrostrat
--

ALTER TABLE ONLY hexgrids.r11
    ADD CONSTRAINT r11_pkey PRIMARY KEY (hex_id);


--
-- Name: r12 r12_pkey; Type: CONSTRAINT; Schema: hexgrids; Owner: macrostrat
--

ALTER TABLE ONLY hexgrids.r12
    ADD CONSTRAINT r12_pkey PRIMARY KEY (hex_id);


--
-- Name: r5 r5_pkey; Type: CONSTRAINT; Schema: hexgrids; Owner: macrostrat
--

ALTER TABLE ONLY hexgrids.r5
    ADD CONSTRAINT r5_pkey PRIMARY KEY (hex_id);


--
-- Name: r6 r6_pkey; Type: CONSTRAINT; Schema: hexgrids; Owner: macrostrat
--

ALTER TABLE ONLY hexgrids.r6
    ADD CONSTRAINT r6_pkey PRIMARY KEY (hex_id);


--
-- Name: r7 r7_pkey; Type: CONSTRAINT; Schema: hexgrids; Owner: macrostrat
--

ALTER TABLE ONLY hexgrids.r7
    ADD CONSTRAINT r7_pkey PRIMARY KEY (hex_id);


--
-- Name: r8 r8_pkey; Type: CONSTRAINT; Schema: hexgrids; Owner: macrostrat
--

ALTER TABLE ONLY hexgrids.r8
    ADD CONSTRAINT r8_pkey PRIMARY KEY (hex_id);


--
-- Name: r9 r9_pkey; Type: CONSTRAINT; Schema: hexgrids; Owner: macrostrat
--

ALTER TABLE ONLY hexgrids.r9
    ADD CONSTRAINT r9_pkey PRIMARY KEY (hex_id);


--
-- Name: bedrock_index_hex_id_idx; Type: INDEX; Schema: hexgrids; Owner: macrostrat
--

CREATE INDEX bedrock_index_hex_id_idx ON hexgrids.bedrock_index USING btree (hex_id);


--
-- Name: bedrock_index_legend_id_hex_id_idx; Type: INDEX; Schema: hexgrids; Owner: macrostrat
--

CREATE UNIQUE INDEX bedrock_index_legend_id_hex_id_idx ON hexgrids.bedrock_index USING btree (legend_id, hex_id);


--
-- Name: bedrock_index_legend_id_idx; Type: INDEX; Schema: hexgrids; Owner: macrostrat
--

CREATE INDEX bedrock_index_legend_id_idx ON hexgrids.bedrock_index USING btree (legend_id);


--
-- Name: hexgrids_geom_idx; Type: INDEX; Schema: hexgrids; Owner: macrostrat
--

CREATE INDEX hexgrids_geom_idx ON hexgrids.hexgrids USING gist (geom);


--
-- Name: hexgrids_res_idx; Type: INDEX; Schema: hexgrids; Owner: macrostrat
--

CREATE INDEX hexgrids_res_idx ON hexgrids.hexgrids USING btree (res);


--
-- Name: pbdb_index_collection_no_hex_id_idx; Type: INDEX; Schema: hexgrids; Owner: macrostrat
--

CREATE UNIQUE INDEX pbdb_index_collection_no_hex_id_idx ON hexgrids.pbdb_index USING btree (collection_no, hex_id);


--
-- Name: pbdb_index_collection_no_idx; Type: INDEX; Schema: hexgrids; Owner: macrostrat
--

CREATE INDEX pbdb_index_collection_no_idx ON hexgrids.pbdb_index USING btree (collection_no);


--
-- Name: pbdb_index_hex_id_idx; Type: INDEX; Schema: hexgrids; Owner: macrostrat
--

CREATE INDEX pbdb_index_hex_id_idx ON hexgrids.pbdb_index USING btree (hex_id);


--
-- Name: r10_geom_geom_idx; Type: INDEX; Schema: hexgrids; Owner: macrostrat
--

CREATE INDEX r10_geom_geom_idx ON hexgrids.r10 USING gist (geom);


--
-- Name: r10_geom_idx; Type: INDEX; Schema: hexgrids; Owner: macrostrat
--

CREATE INDEX r10_geom_idx ON hexgrids.r10 USING gist (geom);


--
-- Name: r10_web_geom_idx; Type: INDEX; Schema: hexgrids; Owner: macrostrat
--

CREATE INDEX r10_web_geom_idx ON hexgrids.r10 USING gist (web_geom);


--
-- Name: r11_geom_geom_idx; Type: INDEX; Schema: hexgrids; Owner: macrostrat
--

CREATE INDEX r11_geom_geom_idx ON hexgrids.r11 USING gist (geom);


--
-- Name: r11_web_geom_idx; Type: INDEX; Schema: hexgrids; Owner: macrostrat
--

CREATE INDEX r11_web_geom_idx ON hexgrids.r11 USING gist (web_geom);


--
-- Name: r12_geom_geom_idx; Type: INDEX; Schema: hexgrids; Owner: macrostrat
--

CREATE INDEX r12_geom_geom_idx ON hexgrids.r12 USING gist (geom);


--
-- Name: r12_web_geom_idx; Type: INDEX; Schema: hexgrids; Owner: macrostrat
--

CREATE INDEX r12_web_geom_idx ON hexgrids.r12 USING gist (web_geom);


--
-- Name: r5_geom_idx; Type: INDEX; Schema: hexgrids; Owner: macrostrat
--

CREATE INDEX r5_geom_idx ON hexgrids.r5 USING gist (geom);


--
-- Name: r5_web_geom_idx; Type: INDEX; Schema: hexgrids; Owner: macrostrat
--

CREATE INDEX r5_web_geom_idx ON hexgrids.r5 USING gist (web_geom);


--
-- Name: r6_geom_idx; Type: INDEX; Schema: hexgrids; Owner: macrostrat
--

CREATE INDEX r6_geom_idx ON hexgrids.r6 USING gist (geom);


--
-- Name: r6_web_geom_idx; Type: INDEX; Schema: hexgrids; Owner: macrostrat
--

CREATE INDEX r6_web_geom_idx ON hexgrids.r6 USING gist (web_geom);


--
-- Name: r7_geom_idx; Type: INDEX; Schema: hexgrids; Owner: macrostrat
--

CREATE INDEX r7_geom_idx ON hexgrids.r7 USING gist (geom);


--
-- Name: r7_geom_idx1; Type: INDEX; Schema: hexgrids; Owner: macrostrat
--

CREATE INDEX r7_geom_idx1 ON hexgrids.r7 USING gist (geom);


--
-- Name: r7_geom_idx2; Type: INDEX; Schema: hexgrids; Owner: macrostrat
--

CREATE INDEX r7_geom_idx2 ON hexgrids.r7 USING gist (geom);


--
-- Name: r7_web_geom_idx; Type: INDEX; Schema: hexgrids; Owner: macrostrat
--

CREATE INDEX r7_web_geom_idx ON hexgrids.r7 USING gist (web_geom);


--
-- Name: r8_geom_idx; Type: INDEX; Schema: hexgrids; Owner: macrostrat
--

CREATE INDEX r8_geom_idx ON hexgrids.r8 USING gist (geom);


--
-- Name: r8_geom_idx1; Type: INDEX; Schema: hexgrids; Owner: macrostrat
--

CREATE INDEX r8_geom_idx1 ON hexgrids.r8 USING gist (geom);


--
-- Name: r8_geom_idx2; Type: INDEX; Schema: hexgrids; Owner: macrostrat
--

CREATE INDEX r8_geom_idx2 ON hexgrids.r8 USING gist (geom);


--
-- Name: r8_web_geom_idx; Type: INDEX; Schema: hexgrids; Owner: macrostrat
--

CREATE INDEX r8_web_geom_idx ON hexgrids.r8 USING gist (web_geom);


--
-- Name: r9_geom_idx; Type: INDEX; Schema: hexgrids; Owner: macrostrat
--

CREATE INDEX r9_geom_idx ON hexgrids.r9 USING gist (geom);


--
-- Name: r9_geom_idx1; Type: INDEX; Schema: hexgrids; Owner: macrostrat
--

CREATE INDEX r9_geom_idx1 ON hexgrids.r9 USING gist (geom);


--
-- Name: r9_web_geom_idx; Type: INDEX; Schema: hexgrids; Owner: macrostrat
--

CREATE INDEX r9_web_geom_idx ON hexgrids.r9 USING gist (web_geom);


--
-- Name: DEFAULT PRIVILEGES FOR SEQUENCES; Type: DEFAULT ACL; Schema: hexgrids; Owner: macrostrat-admin
--

ALTER DEFAULT PRIVILEGES FOR ROLE "macrostrat-admin" IN SCHEMA hexgrids GRANT SELECT,USAGE ON SEQUENCES  TO macrostrat;


--
-- Name: DEFAULT PRIVILEGES FOR TABLES; Type: DEFAULT ACL; Schema: hexgrids; Owner: macrostrat-admin
--

ALTER DEFAULT PRIVILEGES FOR ROLE "macrostrat-admin" IN SCHEMA hexgrids GRANT SELECT ON TABLES  TO macrostrat;


--
-- PostgreSQL database dump complete
--

