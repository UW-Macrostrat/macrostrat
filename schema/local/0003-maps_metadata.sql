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
-- Name: maps_metadata; Type: SCHEMA; Schema: -; Owner: macrostrat-admin
--

CREATE SCHEMA maps_metadata;


ALTER SCHEMA maps_metadata OWNER TO "macrostrat-admin";

--
-- Name: maps_metadata_update_trigger(); Type: FUNCTION; Schema: maps_metadata; Owner: macrostrat_admin
--

CREATE FUNCTION maps_metadata.maps_metadata_update_trigger() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
	UPDATE
		sources
	SET
		raster_source_url = NEW.raster_source_url,
		raster_bucket_url = NEW.raster_bucket_url,
		compiler_name = NEW.compiler_name,
		date_compiled = NEW.date_compiled
	WHERE source_id = NEW.source_id;
	RETURN NEW;
END;
$$;


ALTER FUNCTION maps_metadata.maps_metadata_update_trigger() OWNER TO macrostrat_admin;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: ingest_process; Type: TABLE; Schema: maps_metadata; Owner: macrostrat
--

CREATE TABLE maps_metadata.ingest_process (
    id integer NOT NULL,
    state maps.ingest_state,
    comments text,
    source_id integer,
    created_on timestamp with time zone DEFAULT now() NOT NULL,
    completed_on timestamp with time zone,
    map_id text,
    type maps.ingest_type,
    polygon_state jsonb,
    line_state jsonb,
    point_state jsonb,
    ingest_pipeline text,
    map_url text,
    ingested_by text,
    slug text
);


ALTER TABLE maps_metadata.ingest_process OWNER TO macrostrat;

--
-- Name: ingest_process_tag; Type: TABLE; Schema: maps_metadata; Owner: macrostrat
--

CREATE TABLE maps_metadata.ingest_process_tag (
    ingest_process_id integer NOT NULL,
    tag character varying(255) NOT NULL
);


ALTER TABLE maps_metadata.ingest_process_tag OWNER TO macrostrat;

--
-- Name: ingest_process_id_seq; Type: SEQUENCE; Schema: maps_metadata; Owner: macrostrat
--

CREATE SEQUENCE maps_metadata.ingest_process_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE maps_metadata.ingest_process_id_seq OWNER TO macrostrat;

--
-- Name: ingest_process_id_seq; Type: SEQUENCE OWNED BY; Schema: maps_metadata; Owner: macrostrat
--

ALTER SEQUENCE maps_metadata.ingest_process_id_seq OWNED BY maps_metadata.ingest_process.id;


--
-- Name: map_files; Type: TABLE; Schema: maps_metadata; Owner: macrostrat_admin
--

CREATE TABLE maps_metadata.map_files (
    id integer NOT NULL,
    ingest_process_id integer NOT NULL,
    object_id integer NOT NULL
);


ALTER TABLE maps_metadata.map_files OWNER TO macrostrat_admin;

--
-- Name: map_files_id_seq; Type: SEQUENCE; Schema: maps_metadata; Owner: macrostrat_admin
--

ALTER TABLE maps_metadata.map_files ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME maps_metadata.map_files_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: sources; Type: TABLE; Schema: maps_metadata; Owner: macrostrat_admin
--

CREATE TABLE maps_metadata.sources (
    source_id integer,
    raster_bucket_url text,
    date_compiled timestamp without time zone,
    compiler_name text,
    raster_source_url text
);


ALTER TABLE maps_metadata.sources OWNER TO macrostrat_admin;

--
-- Name: sources_meta; Type: VIEW; Schema: maps_metadata; Owner: macrostrat_admin
--

CREATE VIEW maps_metadata.sources_meta AS
 SELECT ms.source_id,
    ms.raster_bucket_url,
    ms.date_compiled,
    ms.compiler_name,
    ms.raster_source_url,
    s.name,
    s.url,
    s.ref_title,
    s.authors,
    s.ref_year,
    s.ref_source,
    s.isbn_doi,
    s.scale,
    s.license AS licence,
    s.features,
    s.area,
    s.priority,
    s.display_scales,
    s.status_code,
    s.slug
   FROM (maps.sources s
     LEFT JOIN maps_metadata.sources ms ON ((ms.source_id = s.source_id)));


ALTER TABLE maps_metadata.sources_meta OWNER TO macrostrat_admin;


--
-- Name: ingest_process id; Type: DEFAULT; Schema: maps_metadata; Owner: macrostrat
--

ALTER TABLE ONLY maps_metadata.ingest_process ALTER COLUMN id SET DEFAULT nextval('maps_metadata.ingest_process_id_seq'::regclass);


--
-- Name: ingest_process ingest_process_pkey; Type: CONSTRAINT; Schema: maps_metadata; Owner: macrostrat
--

ALTER TABLE ONLY maps_metadata.ingest_process
    ADD CONSTRAINT ingest_process_pkey PRIMARY KEY (id);


--
-- Name: map_files map_files_ingest_process_id_object_id_key; Type: CONSTRAINT; Schema: maps_metadata; Owner: macrostrat_admin
--

ALTER TABLE ONLY maps_metadata.map_files
    ADD CONSTRAINT map_files_ingest_process_id_object_id_key UNIQUE (ingest_process_id, object_id);


--
-- Name: map_files map_files_pkey; Type: CONSTRAINT; Schema: maps_metadata; Owner: macrostrat_admin
--

ALTER TABLE ONLY maps_metadata.map_files
    ADD CONSTRAINT map_files_pkey PRIMARY KEY (id);


--
-- Name: ingest_process_tag pk_tag; Type: CONSTRAINT; Schema: maps_metadata; Owner: macrostrat
--

ALTER TABLE ONLY maps_metadata.ingest_process_tag
    ADD CONSTRAINT pk_tag PRIMARY KEY (ingest_process_id, tag);


--
-- Name: sources_meta maps_metadata_update_trigger; Type: TRIGGER; Schema: maps_metadata; Owner: macrostrat_admin
--

CREATE TRIGGER maps_metadata_update_trigger INSTEAD OF UPDATE ON maps_metadata.sources_meta FOR EACH ROW EXECUTE FUNCTION maps_metadata.maps_metadata_update_trigger();


--
-- Name: ingest_process ingest_process_source_id_fkey; Type: FK CONSTRAINT; Schema: maps_metadata; Owner: macrostrat
--

ALTER TABLE ONLY maps_metadata.ingest_process
    ADD CONSTRAINT ingest_process_source_id_fkey FOREIGN KEY (source_id) REFERENCES maps.sources(source_id);


--
-- Name: ingest_process_tag ingest_process_tag_ingest_process_id_fkey; Type: FK CONSTRAINT; Schema: maps_metadata; Owner: macrostrat
--

ALTER TABLE ONLY maps_metadata.ingest_process_tag
    ADD CONSTRAINT ingest_process_tag_ingest_process_id_fkey FOREIGN KEY (ingest_process_id) REFERENCES maps_metadata.ingest_process(id);


--
-- Name: map_files map_files_ingest_process_id_fkey; Type: FK CONSTRAINT; Schema: maps_metadata; Owner: macrostrat_admin
--

ALTER TABLE ONLY maps_metadata.map_files
    ADD CONSTRAINT map_files_ingest_process_id_fkey FOREIGN KEY (ingest_process_id) REFERENCES maps_metadata.ingest_process(id) ON DELETE CASCADE;


--
-- Name: map_files map_files_object_id_fkey; Type: FK CONSTRAINT; Schema: maps_metadata; Owner: macrostrat_admin
--

ALTER TABLE ONLY maps_metadata.map_files
    ADD CONSTRAINT map_files_object_id_fkey FOREIGN KEY (object_id) REFERENCES storage.object(id);


--
-- Name: TABLE ingest_process; Type: ACL; Schema: maps_metadata; Owner: macrostrat
--

GRANT SELECT,UPDATE ON TABLE maps_metadata.ingest_process TO web_user;


--
-- PostgreSQL database dump complete
--

