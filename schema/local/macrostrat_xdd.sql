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
-- Name: macrostrat_xdd; Type: SCHEMA; Schema: -; Owner: macrostrat-admin
--

CREATE SCHEMA macrostrat_xdd;


ALTER SCHEMA macrostrat_xdd OWNER TO "macrostrat-admin";

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: extraction_feedback; Type: TABLE; Schema: macrostrat_xdd; Owner: macrostrat-admin
--

CREATE TABLE macrostrat_xdd.extraction_feedback (
    note_id integer NOT NULL,
    feedback_id integer,
    date timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    custom_note text
);


ALTER TABLE macrostrat_xdd.extraction_feedback OWNER TO "macrostrat-admin";

--
-- Name: extraction_feedback_type; Type: TABLE; Schema: macrostrat_xdd; Owner: macrostrat-admin
--

CREATE TABLE macrostrat_xdd.extraction_feedback_type (
    type_id integer NOT NULL,
    type text NOT NULL
);


ALTER TABLE macrostrat_xdd.extraction_feedback_type OWNER TO "macrostrat-admin";

--
-- Name: lookup_extraction_type; Type: TABLE; Schema: macrostrat_xdd; Owner: macrostrat-admin
--

CREATE TABLE macrostrat_xdd.lookup_extraction_type (
    note_id integer NOT NULL,
    type_id integer NOT NULL
);


ALTER TABLE macrostrat_xdd.lookup_extraction_type OWNER TO "macrostrat-admin";

--
-- Name: all_runs; Type: TABLE; Schema: macrostrat_xdd; Owner: xdd-writer
--

CREATE TABLE macrostrat_xdd.all_runs (
    user_id uuid,
    "timestamp" timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    model_id integer,
    version_id integer,
    id integer NOT NULL,
    model_job_id text,
    extraction_pipeline_id text,
    source_text_id integer NOT NULL,
    supersedes integer
);


ALTER TABLE macrostrat_xdd.all_runs OWNER TO "xdd-writer";

--
-- Name: entity; Type: TABLE; Schema: macrostrat_xdd; Owner: xdd-writer
--

CREATE TABLE macrostrat_xdd.entity (
    name text NOT NULL,
    corrected_name text,
    strat_name_id integer,
    lith_id integer,
    lith_att_id integer,
    start_index integer NOT NULL,
    end_index integer NOT NULL,
    run_id integer NOT NULL,
    id integer NOT NULL,
    entity_type_id integer NOT NULL,
    str_match_type text NOT NULL
);


ALTER TABLE macrostrat_xdd.entity OWNER TO "xdd-writer";

--
-- Name: entity_type; Type: TABLE; Schema: macrostrat_xdd; Owner: xdd-writer
--

CREATE TABLE macrostrat_xdd.entity_type (
    name text NOT NULL,
    description text,
    id integer NOT NULL,
    color text
);


ALTER TABLE macrostrat_xdd.entity_type OWNER TO "xdd-writer";

--
-- Name: model_run; Type: VIEW; Schema: macrostrat_xdd; Owner: xdd-writer
--

CREATE VIEW macrostrat_xdd.model_run AS
 SELECT all_runs.user_id,
    all_runs."timestamp",
    all_runs.model_id,
    all_runs.version_id,
    all_runs.id,
    all_runs.model_job_id,
    all_runs.extraction_pipeline_id,
    all_runs.source_text_id,
    all_runs.supersedes
   FROM macrostrat_xdd.all_runs;


ALTER TABLE macrostrat_xdd.model_run OWNER TO "xdd-writer";

--
-- Name: relationship; Type: TABLE; Schema: macrostrat_xdd; Owner: xdd-writer
--

CREATE TABLE macrostrat_xdd.relationship (
    id integer NOT NULL,
    run_id integer NOT NULL,
    src_entity_id integer NOT NULL,
    dst_entity_id integer NOT NULL,
    relationship_type_id integer NOT NULL,
    reasoning text
);


ALTER TABLE macrostrat_xdd.relationship OWNER TO "xdd-writer";

--
-- Name: source_text; Type: TABLE; Schema: macrostrat_xdd; Owner: xdd-writer
--

CREATE TABLE macrostrat_xdd.source_text (
    preprocessor_id text,
    paper_id text,
    hashed_text text NOT NULL,
    weaviate_id text,
    paragraph_text text NOT NULL,
    id integer NOT NULL,
    map_legend_id integer,
    source_text_type text NOT NULL,
    xdd_tags text
);


ALTER TABLE macrostrat_xdd.source_text OWNER TO "xdd-writer";

--
-- Name: model; Type: TABLE; Schema: macrostrat_xdd; Owner: xdd-writer
--

CREATE TABLE macrostrat_xdd.model (
    id integer NOT NULL,
    name text NOT NULL,
    description text,
    url text
);


ALTER TABLE macrostrat_xdd.model OWNER TO "xdd-writer";

--
-- Name: publication; Type: TABLE; Schema: macrostrat_xdd; Owner: xdd-writer
--

CREATE TABLE macrostrat_xdd.publication (
    paper_id text NOT NULL,
    doi text,
    citation jsonb NOT NULL,
    url text
);


ALTER TABLE macrostrat_xdd.publication OWNER TO "xdd-writer";

--
-- Name: entity_id_seq; Type: SEQUENCE; Schema: macrostrat_xdd; Owner: xdd-writer
--

CREATE SEQUENCE macrostrat_xdd.entity_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE macrostrat_xdd.entity_id_seq OWNER TO "xdd-writer";

--
-- Name: entity_id_seq; Type: SEQUENCE OWNED BY; Schema: macrostrat_xdd; Owner: xdd-writer
--

ALTER SEQUENCE macrostrat_xdd.entity_id_seq OWNED BY macrostrat_xdd.entity.id;


--
-- Name: entity_type_id_seq; Type: SEQUENCE; Schema: macrostrat_xdd; Owner: xdd-writer
--

CREATE SEQUENCE macrostrat_xdd.entity_type_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE macrostrat_xdd.entity_type_id_seq OWNER TO "xdd-writer";

--
-- Name: entity_type_id_seq; Type: SEQUENCE OWNED BY; Schema: macrostrat_xdd; Owner: xdd-writer
--

ALTER SEQUENCE macrostrat_xdd.entity_type_id_seq OWNED BY macrostrat_xdd.entity_type.id;


--
-- Name: extraction_feedback_note_id_seq; Type: SEQUENCE; Schema: macrostrat_xdd; Owner: macrostrat-admin
--

CREATE SEQUENCE macrostrat_xdd.extraction_feedback_note_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE macrostrat_xdd.extraction_feedback_note_id_seq OWNER TO "macrostrat-admin";

--
-- Name: extraction_feedback_note_id_seq; Type: SEQUENCE OWNED BY; Schema: macrostrat_xdd; Owner: macrostrat-admin
--

ALTER SEQUENCE macrostrat_xdd.extraction_feedback_note_id_seq OWNED BY macrostrat_xdd.extraction_feedback.note_id;


--
-- Name: extraction_feedback_type_type_id_seq; Type: SEQUENCE; Schema: macrostrat_xdd; Owner: macrostrat-admin
--

CREATE SEQUENCE macrostrat_xdd.extraction_feedback_type_type_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE macrostrat_xdd.extraction_feedback_type_type_id_seq OWNER TO "macrostrat-admin";

--
-- Name: extraction_feedback_type_type_id_seq; Type: SEQUENCE OWNED BY; Schema: macrostrat_xdd; Owner: macrostrat-admin
--

ALTER SEQUENCE macrostrat_xdd.extraction_feedback_type_type_id_seq OWNED BY macrostrat_xdd.extraction_feedback_type.type_id;


--
-- Name: latest_run_per_text; Type: VIEW; Schema: macrostrat_xdd; Owner: xdd-writer
--

CREATE VIEW macrostrat_xdd.latest_run_per_text AS
 WITH latest_run AS (
         SELECT all_runs_1.source_text_id AS src_text_id,
            max(all_runs_1."timestamp") AS latest_timestamp
           FROM macrostrat_xdd.all_runs all_runs_1
          GROUP BY all_runs_1.source_text_id
        )
 SELECT all_runs.id AS latest_run_id,
    all_runs.source_text_id,
    all_runs."timestamp",
    all_runs.supersedes
   FROM macrostrat_xdd.all_runs all_runs,
    latest_run
  WHERE ((all_runs.source_text_id = latest_run.src_text_id) AND (all_runs."timestamp" = latest_run.latest_timestamp));


ALTER TABLE macrostrat_xdd.latest_run_per_text OWNER TO "xdd-writer";

--
-- Name: model_run_id_seq; Type: SEQUENCE; Schema: macrostrat_xdd; Owner: xdd-writer
--

CREATE SEQUENCE macrostrat_xdd.model_run_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE macrostrat_xdd.model_run_id_seq OWNER TO "xdd-writer";

--
-- Name: model_run_id_seq; Type: SEQUENCE OWNED BY; Schema: macrostrat_xdd; Owner: xdd-writer
--

ALTER SEQUENCE macrostrat_xdd.model_run_id_seq OWNED BY macrostrat_xdd.all_runs.id;


--
-- Name: model_version; Type: TABLE; Schema: macrostrat_xdd; Owner: xdd-writer
--

CREATE TABLE macrostrat_xdd.model_version (
    id integer NOT NULL,
    name text NOT NULL,
    description text,
    model_id integer NOT NULL
);


ALTER TABLE macrostrat_xdd.model_version OWNER TO "xdd-writer";

--
-- Name: model_versions_version_id_seq; Type: SEQUENCE; Schema: macrostrat_xdd; Owner: xdd-writer
--

ALTER TABLE macrostrat_xdd.model_version ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME macrostrat_xdd.model_versions_version_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: models_model_id_seq; Type: SEQUENCE; Schema: macrostrat_xdd; Owner: xdd-writer
--

ALTER TABLE macrostrat_xdd.model ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME macrostrat_xdd.models_model_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: relationship_id_seq; Type: SEQUENCE; Schema: macrostrat_xdd; Owner: xdd-writer
--

CREATE SEQUENCE macrostrat_xdd.relationship_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE macrostrat_xdd.relationship_id_seq OWNER TO "xdd-writer";

--
-- Name: relationship_id_seq; Type: SEQUENCE OWNED BY; Schema: macrostrat_xdd; Owner: xdd-writer
--

ALTER SEQUENCE macrostrat_xdd.relationship_id_seq OWNED BY macrostrat_xdd.relationship.id;


--
-- Name: relationship_type; Type: TABLE; Schema: macrostrat_xdd; Owner: xdd-writer
--

CREATE TABLE macrostrat_xdd.relationship_type (
    name text NOT NULL,
    description text,
    id integer NOT NULL
);


ALTER TABLE macrostrat_xdd.relationship_type OWNER TO "xdd-writer";

--
-- Name: relationship_type_id_seq; Type: SEQUENCE; Schema: macrostrat_xdd; Owner: xdd-writer
--

CREATE SEQUENCE macrostrat_xdd.relationship_type_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE macrostrat_xdd.relationship_type_id_seq OWNER TO "xdd-writer";

--
-- Name: relationship_type_id_seq; Type: SEQUENCE OWNED BY; Schema: macrostrat_xdd; Owner: xdd-writer
--

ALTER SEQUENCE macrostrat_xdd.relationship_type_id_seq OWNED BY macrostrat_xdd.relationship_type.id;


--
-- Name: source_text_id_seq; Type: SEQUENCE; Schema: macrostrat_xdd; Owner: xdd-writer
--

CREATE SEQUENCE macrostrat_xdd.source_text_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE macrostrat_xdd.source_text_id_seq OWNER TO "xdd-writer";

--
-- Name: source_text_id_seq; Type: SEQUENCE OWNED BY; Schema: macrostrat_xdd; Owner: xdd-writer
--

ALTER SEQUENCE macrostrat_xdd.source_text_id_seq OWNED BY macrostrat_xdd.source_text.id;


--
-- Name: users; Type: TABLE; Schema: macrostrat_xdd; Owner: xdd-writer
--

CREATE TABLE macrostrat_xdd.users (
    internal_user_id uuid DEFAULT gen_random_uuid() NOT NULL,
    external_user_id text NOT NULL
);


ALTER TABLE macrostrat_xdd.users OWNER TO "xdd-writer";

--
-- Name: all_runs id; Type: DEFAULT; Schema: macrostrat_xdd; Owner: xdd-writer
--

ALTER TABLE ONLY macrostrat_xdd.all_runs ALTER COLUMN id SET DEFAULT nextval('macrostrat_xdd.model_run_id_seq'::regclass);


--
-- Name: entity id; Type: DEFAULT; Schema: macrostrat_xdd; Owner: xdd-writer
--

ALTER TABLE ONLY macrostrat_xdd.entity ALTER COLUMN id SET DEFAULT nextval('macrostrat_xdd.entity_id_seq'::regclass);


--
-- Name: entity_type id; Type: DEFAULT; Schema: macrostrat_xdd; Owner: xdd-writer
--

ALTER TABLE ONLY macrostrat_xdd.entity_type ALTER COLUMN id SET DEFAULT nextval('macrostrat_xdd.entity_type_id_seq'::regclass);


--
-- Name: extraction_feedback note_id; Type: DEFAULT; Schema: macrostrat_xdd; Owner: macrostrat-admin
--

ALTER TABLE ONLY macrostrat_xdd.extraction_feedback ALTER COLUMN note_id SET DEFAULT nextval('macrostrat_xdd.extraction_feedback_note_id_seq'::regclass);


--
-- Name: extraction_feedback_type type_id; Type: DEFAULT; Schema: macrostrat_xdd; Owner: macrostrat-admin
--

ALTER TABLE ONLY macrostrat_xdd.extraction_feedback_type ALTER COLUMN type_id SET DEFAULT nextval('macrostrat_xdd.extraction_feedback_type_type_id_seq'::regclass);


--
-- Name: relationship id; Type: DEFAULT; Schema: macrostrat_xdd; Owner: xdd-writer
--

ALTER TABLE ONLY macrostrat_xdd.relationship ALTER COLUMN id SET DEFAULT nextval('macrostrat_xdd.relationship_id_seq'::regclass);


--
-- Name: relationship_type id; Type: DEFAULT; Schema: macrostrat_xdd; Owner: xdd-writer
--

ALTER TABLE ONLY macrostrat_xdd.relationship_type ALTER COLUMN id SET DEFAULT nextval('macrostrat_xdd.relationship_type_id_seq'::regclass);


--
-- Name: source_text id; Type: DEFAULT; Schema: macrostrat_xdd; Owner: xdd-writer
--

ALTER TABLE ONLY macrostrat_xdd.source_text ALTER COLUMN id SET DEFAULT nextval('macrostrat_xdd.source_text_id_seq'::regclass);


--
-- Name: entity entity_pkey; Type: CONSTRAINT; Schema: macrostrat_xdd; Owner: xdd-writer
--

ALTER TABLE ONLY macrostrat_xdd.entity
    ADD CONSTRAINT entity_pkey PRIMARY KEY (id);


--
-- Name: entity_type entity_type_name_key; Type: CONSTRAINT; Schema: macrostrat_xdd; Owner: xdd-writer
--

ALTER TABLE ONLY macrostrat_xdd.entity_type
    ADD CONSTRAINT entity_type_name_key UNIQUE (name);


--
-- Name: entity_type entity_type_pkey; Type: CONSTRAINT; Schema: macrostrat_xdd; Owner: xdd-writer
--

ALTER TABLE ONLY macrostrat_xdd.entity_type
    ADD CONSTRAINT entity_type_pkey PRIMARY KEY (id);


--
-- Name: extraction_feedback extraction_feedback_pkey; Type: CONSTRAINT; Schema: macrostrat_xdd; Owner: macrostrat-admin
--

ALTER TABLE ONLY macrostrat_xdd.extraction_feedback
    ADD CONSTRAINT extraction_feedback_pkey PRIMARY KEY (note_id);


--
-- Name: extraction_feedback_type extraction_feedback_type_pkey; Type: CONSTRAINT; Schema: macrostrat_xdd; Owner: macrostrat-admin
--

ALTER TABLE ONLY macrostrat_xdd.extraction_feedback_type
    ADD CONSTRAINT extraction_feedback_type_pkey PRIMARY KEY (type_id);


--
-- Name: lookup_extraction_type lookup_extraction_type_pkey; Type: CONSTRAINT; Schema: macrostrat_xdd; Owner: macrostrat-admin
--

ALTER TABLE ONLY macrostrat_xdd.lookup_extraction_type
    ADD CONSTRAINT lookup_extraction_type_pkey PRIMARY KEY (note_id, type_id);


--
-- Name: all_runs model_run_pkey; Type: CONSTRAINT; Schema: macrostrat_xdd; Owner: xdd-writer
--

ALTER TABLE ONLY macrostrat_xdd.all_runs
    ADD CONSTRAINT model_run_pkey PRIMARY KEY (id);


--
-- Name: model_version model_versions_pkey; Type: CONSTRAINT; Schema: macrostrat_xdd; Owner: xdd-writer
--

ALTER TABLE ONLY macrostrat_xdd.model_version
    ADD CONSTRAINT model_versions_pkey PRIMARY KEY (id);


--
-- Name: model models_model_name_key; Type: CONSTRAINT; Schema: macrostrat_xdd; Owner: xdd-writer
--

ALTER TABLE ONLY macrostrat_xdd.model
    ADD CONSTRAINT models_model_name_key UNIQUE (name);


--
-- Name: model models_pkey; Type: CONSTRAINT; Schema: macrostrat_xdd; Owner: xdd-writer
--

ALTER TABLE ONLY macrostrat_xdd.model
    ADD CONSTRAINT models_pkey PRIMARY KEY (id);


--
-- Name: all_runs no_duplicate_runs; Type: CONSTRAINT; Schema: macrostrat_xdd; Owner: xdd-writer
--

ALTER TABLE ONLY macrostrat_xdd.all_runs
    ADD CONSTRAINT no_duplicate_runs UNIQUE (user_id, model_id, version_id, model_job_id, extraction_pipeline_id, source_text_id, supersedes);


--
-- Name: publication publication_pkey; Type: CONSTRAINT; Schema: macrostrat_xdd; Owner: xdd-writer
--

ALTER TABLE ONLY macrostrat_xdd.publication
    ADD CONSTRAINT publication_pkey PRIMARY KEY (paper_id);


--
-- Name: relationship relationship_pkey; Type: CONSTRAINT; Schema: macrostrat_xdd; Owner: xdd-writer
--

ALTER TABLE ONLY macrostrat_xdd.relationship
    ADD CONSTRAINT relationship_pkey PRIMARY KEY (id);


--
-- Name: relationship_type relationship_type_name_key; Type: CONSTRAINT; Schema: macrostrat_xdd; Owner: xdd-writer
--

ALTER TABLE ONLY macrostrat_xdd.relationship_type
    ADD CONSTRAINT relationship_type_name_key UNIQUE (name);


--
-- Name: relationship_type relationship_type_pkey; Type: CONSTRAINT; Schema: macrostrat_xdd; Owner: xdd-writer
--

ALTER TABLE ONLY macrostrat_xdd.relationship_type
    ADD CONSTRAINT relationship_type_pkey PRIMARY KEY (id);


--
-- Name: source_text source_text_pkey; Type: CONSTRAINT; Schema: macrostrat_xdd; Owner: xdd-writer
--

ALTER TABLE ONLY macrostrat_xdd.source_text
    ADD CONSTRAINT source_text_pkey PRIMARY KEY (id);


--
-- Name: users user_pkey; Type: CONSTRAINT; Schema: macrostrat_xdd; Owner: xdd-writer
--

ALTER TABLE ONLY macrostrat_xdd.users
    ADD CONSTRAINT user_pkey PRIMARY KEY (internal_user_id);


--
-- Name: users users_unique_enforcement; Type: CONSTRAINT; Schema: macrostrat_xdd; Owner: xdd-writer
--

ALTER TABLE ONLY macrostrat_xdd.users
    ADD CONSTRAINT users_unique_enforcement UNIQUE (external_user_id);


--
-- Name: duplicate_id_check; Type: INDEX; Schema: macrostrat_xdd; Owner: xdd-writer
--

CREATE UNIQUE INDEX duplicate_id_check ON macrostrat_xdd.source_text USING btree (weaviate_id, map_legend_id);


--
-- Name: duplicate_relationships; Type: INDEX; Schema: macrostrat_xdd; Owner: xdd-writer
--

CREATE UNIQUE INDEX duplicate_relationships ON macrostrat_xdd.relationship USING btree (run_id, src_entity_id, dst_entity_id, relationship_type_id);


--
-- Name: duplicate_text_check; Type: INDEX; Schema: macrostrat_xdd; Owner: xdd-writer
--

CREATE UNIQUE INDEX duplicate_text_check ON macrostrat_xdd.source_text USING btree (source_text_type, hashed_text);


--
-- Name: unique_entities; Type: INDEX; Schema: macrostrat_xdd; Owner: xdd-writer
--

CREATE UNIQUE INDEX unique_entities ON macrostrat_xdd.entity USING btree (name, run_id, entity_type_id, start_index, end_index);


--
-- Name: unique_versions; Type: INDEX; Schema: macrostrat_xdd; Owner: xdd-writer
--

CREATE UNIQUE INDEX unique_versions ON macrostrat_xdd.model_version USING btree (model_id, name);


--
-- Name: all_runs Model version check; Type: FK CONSTRAINT; Schema: macrostrat_xdd; Owner: xdd-writer
--

ALTER TABLE ONLY macrostrat_xdd.all_runs
    ADD CONSTRAINT "Model version check" FOREIGN KEY (version_id) REFERENCES macrostrat_xdd.model_version(id) ON DELETE CASCADE;


--
-- Name: source_text Paper Details; Type: FK CONSTRAINT; Schema: macrostrat_xdd; Owner: xdd-writer
--

ALTER TABLE ONLY macrostrat_xdd.source_text
    ADD CONSTRAINT "Paper Details" FOREIGN KEY (paper_id) REFERENCES macrostrat_xdd.publication(paper_id) ON DELETE CASCADE;


--
-- Name: all_runs Previous Run; Type: FK CONSTRAINT; Schema: macrostrat_xdd; Owner: xdd-writer
--

ALTER TABLE ONLY macrostrat_xdd.all_runs
    ADD CONSTRAINT "Previous Run" FOREIGN KEY (supersedes) REFERENCES macrostrat_xdd.all_runs(id) ON DELETE CASCADE;


--
-- Name: relationship Relationship Type Check; Type: FK CONSTRAINT; Schema: macrostrat_xdd; Owner: xdd-writer
--

ALTER TABLE ONLY macrostrat_xdd.relationship
    ADD CONSTRAINT "Relationship Type Check" FOREIGN KEY (relationship_type_id) REFERENCES macrostrat_xdd.relationship_type(id) ON DELETE RESTRICT;


--
-- Name: all_runs Source Text Id; Type: FK CONSTRAINT; Schema: macrostrat_xdd; Owner: xdd-writer
--

ALTER TABLE ONLY macrostrat_xdd.all_runs
    ADD CONSTRAINT "Source Text Id" FOREIGN KEY (source_text_id) REFERENCES macrostrat_xdd.source_text(id) ON DELETE CASCADE;


--
-- Name: entity entity type check; Type: FK CONSTRAINT; Schema: macrostrat_xdd; Owner: xdd-writer
--

ALTER TABLE ONLY macrostrat_xdd.entity
    ADD CONSTRAINT "entity type check" FOREIGN KEY (entity_type_id) REFERENCES macrostrat_xdd.entity_type(id) ON DELETE RESTRICT;


--
-- Name: relationship fk_dst_entity_id; Type: FK CONSTRAINT; Schema: macrostrat_xdd; Owner: xdd-writer
--

ALTER TABLE ONLY macrostrat_xdd.relationship
    ADD CONSTRAINT fk_dst_entity_id FOREIGN KEY (dst_entity_id) REFERENCES macrostrat_xdd.entity(id) ON DELETE CASCADE;


--
-- Name: extraction_feedback fk_feedback_id; Type: FK CONSTRAINT; Schema: macrostrat_xdd; Owner: macrostrat-admin
--

ALTER TABLE ONLY macrostrat_xdd.extraction_feedback
    ADD CONSTRAINT fk_feedback_id FOREIGN KEY (feedback_id) REFERENCES macrostrat_xdd.all_runs(id);


--
-- Name: relationship fk_model_run_id; Type: FK CONSTRAINT; Schema: macrostrat_xdd; Owner: xdd-writer
--

ALTER TABLE ONLY macrostrat_xdd.relationship
    ADD CONSTRAINT fk_model_run_id FOREIGN KEY (run_id) REFERENCES macrostrat_xdd.all_runs(id) ON DELETE CASCADE;


--
-- Name: entity fk_model_run_id; Type: FK CONSTRAINT; Schema: macrostrat_xdd; Owner: xdd-writer
--

ALTER TABLE ONLY macrostrat_xdd.entity
    ADD CONSTRAINT fk_model_run_id FOREIGN KEY (run_id) REFERENCES macrostrat_xdd.all_runs(id) ON DELETE CASCADE;


--
-- Name: relationship fk_src_entity_id; Type: FK CONSTRAINT; Schema: macrostrat_xdd; Owner: xdd-writer
--

ALTER TABLE ONLY macrostrat_xdd.relationship
    ADD CONSTRAINT fk_src_entity_id FOREIGN KEY (src_entity_id) REFERENCES macrostrat_xdd.entity(id) ON DELETE CASCADE;


--
-- Name: lookup_extraction_type lookup_extraction_type_note_id_fkey; Type: FK CONSTRAINT; Schema: macrostrat_xdd; Owner: macrostrat-admin
--

ALTER TABLE ONLY macrostrat_xdd.lookup_extraction_type
    ADD CONSTRAINT lookup_extraction_type_note_id_fkey FOREIGN KEY (note_id) REFERENCES macrostrat_xdd.extraction_feedback(note_id) ON DELETE CASCADE;


--
-- Name: lookup_extraction_type lookup_extraction_type_type_id_fkey; Type: FK CONSTRAINT; Schema: macrostrat_xdd; Owner: macrostrat-admin
--

ALTER TABLE ONLY macrostrat_xdd.lookup_extraction_type
    ADD CONSTRAINT lookup_extraction_type_type_id_fkey FOREIGN KEY (type_id) REFERENCES macrostrat_xdd.extraction_feedback_type(type_id) ON DELETE CASCADE;


--
-- Name: all_runs model_id_check; Type: FK CONSTRAINT; Schema: macrostrat_xdd; Owner: xdd-writer
--

ALTER TABLE ONLY macrostrat_xdd.all_runs
    ADD CONSTRAINT model_id_check FOREIGN KEY (model_id) REFERENCES macrostrat_xdd.model(id) ON DELETE CASCADE;


--
-- Name: model_version model_id_check; Type: FK CONSTRAINT; Schema: macrostrat_xdd; Owner: xdd-writer
--

ALTER TABLE ONLY macrostrat_xdd.model_version
    ADD CONSTRAINT model_id_check FOREIGN KEY (model_id) REFERENCES macrostrat_xdd.model(id) ON DELETE CASCADE;


--
-- Name: source_text source_text_legend_legend_id_fk; Type: FK CONSTRAINT; Schema: macrostrat_xdd; Owner: xdd-writer
--

ALTER TABLE ONLY macrostrat_xdd.source_text
    ADD CONSTRAINT source_text_legend_legend_id_fk FOREIGN KEY (map_legend_id) REFERENCES maps.legend(legend_id) ON UPDATE CASCADE ON DELETE SET NULL;


--
-- Name: all_runs user_id_check; Type: FK CONSTRAINT; Schema: macrostrat_xdd; Owner: xdd-writer
--

ALTER TABLE ONLY macrostrat_xdd.all_runs
    ADD CONSTRAINT user_id_check FOREIGN KEY (user_id) REFERENCES macrostrat_xdd.users(internal_user_id);


--
-- Name: TABLE extraction_feedback; Type: ACL; Schema: macrostrat_xdd; Owner: macrostrat-admin
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE macrostrat_xdd.extraction_feedback TO web_anon;


--
-- Name: TABLE extraction_feedback_type; Type: ACL; Schema: macrostrat_xdd; Owner: macrostrat-admin
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE macrostrat_xdd.extraction_feedback_type TO web_anon;


--
-- Name: TABLE lookup_extraction_type; Type: ACL; Schema: macrostrat_xdd; Owner: macrostrat-admin
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE macrostrat_xdd.lookup_extraction_type TO web_anon;


--
-- Name: TABLE all_runs; Type: ACL; Schema: macrostrat_xdd; Owner: xdd-writer
--

GRANT SELECT ON TABLE macrostrat_xdd.all_runs TO web_anon;


--
-- Name: TABLE entity; Type: ACL; Schema: macrostrat_xdd; Owner: xdd-writer
--

GRANT SELECT ON TABLE macrostrat_xdd.entity TO web_anon;


--
-- Name: TABLE entity_type; Type: ACL; Schema: macrostrat_xdd; Owner: xdd-writer
--

GRANT SELECT ON TABLE macrostrat_xdd.entity_type TO web_anon;


--
-- Name: TABLE model_run; Type: ACL; Schema: macrostrat_xdd; Owner: xdd-writer
--

GRANT SELECT ON TABLE macrostrat_xdd.model_run TO web_anon;


--
-- Name: TABLE relationship; Type: ACL; Schema: macrostrat_xdd; Owner: xdd-writer
--

GRANT SELECT ON TABLE macrostrat_xdd.relationship TO web_anon;


--
-- Name: TABLE source_text; Type: ACL; Schema: macrostrat_xdd; Owner: xdd-writer
--

GRANT SELECT ON TABLE macrostrat_xdd.source_text TO web_anon;


--
-- Name: TABLE model; Type: ACL; Schema: macrostrat_xdd; Owner: xdd-writer
--

GRANT SELECT ON TABLE macrostrat_xdd.model TO web_anon;


--
-- Name: TABLE publication; Type: ACL; Schema: macrostrat_xdd; Owner: xdd-writer
--

GRANT SELECT ON TABLE macrostrat_xdd.publication TO web_anon;


--
-- Name: SEQUENCE entity_id_seq; Type: ACL; Schema: macrostrat_xdd; Owner: xdd-writer
--

GRANT SELECT,USAGE ON SEQUENCE macrostrat_xdd.entity_id_seq TO web_user;


--
-- Name: SEQUENCE entity_type_id_seq; Type: ACL; Schema: macrostrat_xdd; Owner: xdd-writer
--

GRANT SELECT,USAGE ON SEQUENCE macrostrat_xdd.entity_type_id_seq TO web_user;


--
-- Name: SEQUENCE extraction_feedback_note_id_seq; Type: ACL; Schema: macrostrat_xdd; Owner: macrostrat-admin
--

GRANT SELECT,USAGE ON SEQUENCE macrostrat_xdd.extraction_feedback_note_id_seq TO web_user;
GRANT SELECT,USAGE ON SEQUENCE macrostrat_xdd.extraction_feedback_note_id_seq TO web_anon;


--
-- Name: SEQUENCE extraction_feedback_type_type_id_seq; Type: ACL; Schema: macrostrat_xdd; Owner: macrostrat-admin
--

GRANT SELECT,USAGE ON SEQUENCE macrostrat_xdd.extraction_feedback_type_type_id_seq TO web_user;


--
-- Name: TABLE latest_run_per_text; Type: ACL; Schema: macrostrat_xdd; Owner: xdd-writer
--

GRANT SELECT ON TABLE macrostrat_xdd.latest_run_per_text TO web_anon;


--
-- Name: SEQUENCE model_run_id_seq; Type: ACL; Schema: macrostrat_xdd; Owner: xdd-writer
--

GRANT SELECT,USAGE ON SEQUENCE macrostrat_xdd.model_run_id_seq TO web_user;


--
-- Name: TABLE model_version; Type: ACL; Schema: macrostrat_xdd; Owner: xdd-writer
--

GRANT SELECT ON TABLE macrostrat_xdd.model_version TO web_anon;


--
-- Name: SEQUENCE model_versions_version_id_seq; Type: ACL; Schema: macrostrat_xdd; Owner: xdd-writer
--

GRANT SELECT,USAGE ON SEQUENCE macrostrat_xdd.model_versions_version_id_seq TO web_user;


--
-- Name: SEQUENCE models_model_id_seq; Type: ACL; Schema: macrostrat_xdd; Owner: xdd-writer
--

GRANT SELECT,USAGE ON SEQUENCE macrostrat_xdd.models_model_id_seq TO web_user;


--
-- Name: SEQUENCE relationship_id_seq; Type: ACL; Schema: macrostrat_xdd; Owner: xdd-writer
--

GRANT SELECT,USAGE ON SEQUENCE macrostrat_xdd.relationship_id_seq TO web_user;


--
-- Name: TABLE relationship_type; Type: ACL; Schema: macrostrat_xdd; Owner: xdd-writer
--

GRANT SELECT ON TABLE macrostrat_xdd.relationship_type TO web_anon;


--
-- Name: SEQUENCE relationship_type_id_seq; Type: ACL; Schema: macrostrat_xdd; Owner: xdd-writer
--

GRANT SELECT,USAGE ON SEQUENCE macrostrat_xdd.relationship_type_id_seq TO web_user;


--
-- Name: SEQUENCE source_text_id_seq; Type: ACL; Schema: macrostrat_xdd; Owner: xdd-writer
--

GRANT SELECT,USAGE ON SEQUENCE macrostrat_xdd.source_text_id_seq TO web_user;


--
-- Name: TABLE users; Type: ACL; Schema: macrostrat_xdd; Owner: xdd-writer
--

GRANT SELECT ON TABLE macrostrat_xdd.users TO web_anon;


--
-- Name: DEFAULT PRIVILEGES FOR SEQUENCES; Type: DEFAULT ACL; Schema: macrostrat_xdd; Owner: macrostrat-admin
--

ALTER DEFAULT PRIVILEGES FOR ROLE "macrostrat-admin" IN SCHEMA macrostrat_xdd GRANT SELECT,USAGE ON SEQUENCES  TO web_user;


--
-- Name: DEFAULT PRIVILEGES FOR TABLES; Type: DEFAULT ACL; Schema: macrostrat_xdd; Owner: macrostrat-admin
--

ALTER DEFAULT PRIVILEGES FOR ROLE "macrostrat-admin" IN SCHEMA macrostrat_xdd GRANT SELECT ON TABLES  TO web_anon;


--
-- PostgreSQL database dump complete
--

