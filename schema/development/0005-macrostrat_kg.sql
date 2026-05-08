

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

CREATE SCHEMA macrostrat_kg;
ALTER SCHEMA macrostrat_kg OWNER TO macrostrat_admin;
SET default_tablespace = '';
SET default_table_access_method = heap;

CREATE TABLE macrostrat_kg.extraction_feedback (
    note_id integer NOT NULL,
    feedback_id integer,
    date timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    custom_note text
);
ALTER TABLE macrostrat_kg.extraction_feedback OWNER TO macrostrat_admin;

CREATE TABLE macrostrat_kg.extraction_feedback_type (
    type_id integer NOT NULL,
    type text NOT NULL
);
ALTER TABLE macrostrat_kg.extraction_feedback_type OWNER TO macrostrat_admin;

CREATE TABLE macrostrat_kg.lookup_extraction_type (
    note_id integer NOT NULL,
    type_id integer NOT NULL
);
ALTER TABLE macrostrat_kg.lookup_extraction_type OWNER TO macrostrat_admin;

CREATE TABLE macrostrat_kg.global_entity (
    global_entity_id BIGSERIAL PRIMARY KEY,
    entity_table TEXT NOT NULL,
    entity_id INTEGER NOT NULL,

    name TEXT NOT NULL,
    normalized_name TEXT NOT NULL,

    CONSTRAINT unique_entity UNIQUE (entity_table, entity_id)
);

ALTER TABLE macrostrat_kg.global_entity OWNER TO xdd_writer;

CREATE TABLE macrostrat_kg.all_runs (
    user_id uuid,
    "timestamp" timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    model_id integer,
    version_id integer,
    id integer NOT NULL,
    model_job_id text,
    extraction_pipeline_id text,
    source_text_id integer NOT NULL,
    supersedes integer,
    root_id BIGINT
);

ALTER TABLE macrostrat_kg.all_runs OWNER TO xdd_writer;

CREATE TABLE macrostrat_kg.entity (
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
    str_match_type text NOT NULL,
    global_entity_id BIGINT
);
ALTER TABLE macrostrat_kg.entity OWNER TO xdd_writer;

CREATE TABLE macrostrat_kg.entity_type (
    name text NOT NULL,
    description text,
    id integer NOT NULL,
    color text
);
ALTER TABLE macrostrat_kg.entity_type OWNER TO xdd_writer;

CREATE VIEW macrostrat_kg.model_run AS
 SELECT all_runs.user_id,
    all_runs."timestamp",
    all_runs.model_id,
    all_runs.version_id,
    all_runs.id,
    all_runs.model_job_id,
    all_runs.extraction_pipeline_id,
    all_runs.source_text_id,
    all_runs.supersedes
   FROM macrostrat_kg.all_runs;
ALTER TABLE macrostrat_kg.model_run OWNER TO xdd_writer;

CREATE TABLE macrostrat_kg.relationship (
    id integer NOT NULL,
    run_id integer NOT NULL,
    src_entity_id integer NOT NULL,
    dst_entity_id integer NOT NULL,
    relationship_type_id integer NOT NULL,
    reasoning text
);
ALTER TABLE macrostrat_kg.relationship OWNER TO xdd_writer;

CREATE TABLE macrostrat_kg.source_text (
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
ALTER TABLE macrostrat_kg.source_text OWNER TO xdd_writer;

CREATE TABLE macrostrat_kg.model (
    id integer NOT NULL,
    name text NOT NULL,
    description text,
    url text
);
ALTER TABLE macrostrat_kg.model OWNER TO xdd_writer;

CREATE TABLE macrostrat_kg.publication (
    paper_id text NOT NULL,
    doi text,
    citation jsonb NOT NULL,
    url text
);
ALTER TABLE macrostrat_kg.publication OWNER TO xdd_writer;

CREATE SEQUENCE macrostrat_kg.entity_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
ALTER TABLE macrostrat_kg.entity_id_seq OWNER TO xdd_writer;

ALTER SEQUENCE macrostrat_kg.entity_id_seq OWNED BY macrostrat_kg.entity.id;

CREATE SEQUENCE macrostrat_kg.entity_type_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
ALTER TABLE macrostrat_kg.entity_type_id_seq OWNER TO xdd_writer;

ALTER SEQUENCE macrostrat_kg.entity_type_id_seq OWNED BY macrostrat_kg.entity_type.id;

CREATE SEQUENCE macrostrat_kg.extraction_feedback_note_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
ALTER TABLE macrostrat_kg.extraction_feedback_note_id_seq OWNER TO macrostrat_admin;

ALTER SEQUENCE macrostrat_kg.extraction_feedback_note_id_seq OWNED BY macrostrat_kg.extraction_feedback.note_id;

CREATE SEQUENCE macrostrat_kg.extraction_feedback_type_type_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
ALTER TABLE macrostrat_kg.extraction_feedback_type_type_id_seq OWNER TO macrostrat_admin;

ALTER SEQUENCE macrostrat_kg.extraction_feedback_type_type_id_seq OWNED BY macrostrat_kg.extraction_feedback_type.type_id;

CREATE VIEW macrostrat_kg.latest_run_per_text AS
 WITH latest_run AS (
         SELECT all_runs_1.source_text_id AS src_text_id,
            max(all_runs_1."timestamp") AS latest_timestamp
           FROM macrostrat_kg.all_runs all_runs_1
          GROUP BY all_runs_1.source_text_id
        )
 SELECT all_runs.id AS latest_run_id,
    all_runs.source_text_id,
    all_runs."timestamp",
    all_runs.supersedes
   FROM macrostrat_kg.all_runs all_runs,
    latest_run
  WHERE ((all_runs.source_text_id = latest_run.src_text_id) AND (all_runs."timestamp" = latest_run.latest_timestamp));
ALTER TABLE macrostrat_kg.latest_run_per_text OWNER TO xdd_writer;

CREATE SEQUENCE macrostrat_kg.model_run_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
ALTER TABLE macrostrat_kg.model_run_id_seq OWNER TO xdd_writer;

ALTER SEQUENCE macrostrat_kg.model_run_id_seq OWNED BY macrostrat_kg.all_runs.id;

CREATE TABLE macrostrat_kg.model_version (
    id integer NOT NULL,
    name text NOT NULL,
    description text,
    model_id integer NOT NULL
);
ALTER TABLE macrostrat_kg.model_version OWNER TO xdd_writer;

ALTER TABLE macrostrat_kg.model_version ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME macrostrat_kg.model_versions_version_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);

ALTER TABLE macrostrat_kg.model ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME macrostrat_kg.models_model_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);

CREATE SEQUENCE macrostrat_kg.relationship_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
ALTER TABLE macrostrat_kg.relationship_id_seq OWNER TO xdd_writer;

ALTER SEQUENCE macrostrat_kg.relationship_id_seq OWNED BY macrostrat_kg.relationship.id;

CREATE TABLE macrostrat_kg.relationship_type (
    name text NOT NULL,
    description text,
    id integer NOT NULL
);
ALTER TABLE macrostrat_kg.relationship_type OWNER TO xdd_writer;

CREATE SEQUENCE macrostrat_kg.relationship_type_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
ALTER TABLE macrostrat_kg.relationship_type_id_seq OWNER TO xdd_writer;

ALTER SEQUENCE macrostrat_kg.relationship_type_id_seq OWNED BY macrostrat_kg.relationship_type.id;

CREATE SEQUENCE macrostrat_kg.source_text_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
ALTER TABLE macrostrat_kg.source_text_id_seq OWNER TO xdd_writer;

ALTER SEQUENCE macrostrat_kg.source_text_id_seq OWNED BY macrostrat_kg.source_text.id;

CREATE TABLE macrostrat_kg.users (
    internal_user_id uuid DEFAULT gen_random_uuid() NOT NULL,
    external_user_id text NOT NULL
);
ALTER TABLE macrostrat_kg.users OWNER TO xdd_writer;

ALTER TABLE ONLY macrostrat_kg.all_runs ALTER COLUMN id SET DEFAULT nextval('macrostrat_kg.model_run_id_seq'::regclass);

ALTER TABLE ONLY macrostrat_kg.entity ALTER COLUMN id SET DEFAULT nextval('macrostrat_kg.entity_id_seq'::regclass);

ALTER TABLE ONLY macrostrat_kg.entity_type ALTER COLUMN id SET DEFAULT nextval('macrostrat_kg.entity_type_id_seq'::regclass);

ALTER TABLE ONLY macrostrat_kg.extraction_feedback ALTER COLUMN note_id SET DEFAULT nextval('macrostrat_kg.extraction_feedback_note_id_seq'::regclass);

ALTER TABLE ONLY macrostrat_kg.extraction_feedback_type ALTER COLUMN type_id SET DEFAULT nextval('macrostrat_kg.extraction_feedback_type_type_id_seq'::regclass);

ALTER TABLE ONLY macrostrat_kg.relationship ALTER COLUMN id SET DEFAULT nextval('macrostrat_kg.relationship_id_seq'::regclass);

ALTER TABLE ONLY macrostrat_kg.relationship_type ALTER COLUMN id SET DEFAULT nextval('macrostrat_kg.relationship_type_id_seq'::regclass);

ALTER TABLE ONLY macrostrat_kg.source_text ALTER COLUMN id SET DEFAULT nextval('macrostrat_kg.source_text_id_seq'::regclass);

ALTER TABLE ONLY macrostrat_kg.entity
    ADD CONSTRAINT entity_pkey PRIMARY KEY (id);

ALTER TABLE ONLY macrostrat_kg.entity_type
    ADD CONSTRAINT entity_type_name_key UNIQUE (name);

ALTER TABLE ONLY macrostrat_kg.entity_type
    ADD CONSTRAINT entity_type_pkey PRIMARY KEY (id);

ALTER TABLE ONLY macrostrat_kg.extraction_feedback
    ADD CONSTRAINT extraction_feedback_pkey PRIMARY KEY (note_id);

ALTER TABLE ONLY macrostrat_kg.extraction_feedback_type
    ADD CONSTRAINT extraction_feedback_type_pkey PRIMARY KEY (type_id);

ALTER TABLE ONLY macrostrat_kg.lookup_extraction_type
    ADD CONSTRAINT lookup_extraction_type_pkey PRIMARY KEY (note_id, type_id);

ALTER TABLE ONLY macrostrat_kg.all_runs
    ADD CONSTRAINT model_run_pkey PRIMARY KEY (id);

ALTER TABLE ONLY macrostrat_kg.model_version
    ADD CONSTRAINT model_versions_pkey PRIMARY KEY (id);

ALTER TABLE ONLY macrostrat_kg.model
    ADD CONSTRAINT models_model_name_key UNIQUE (name);

ALTER TABLE ONLY macrostrat_kg.model
    ADD CONSTRAINT models_pkey PRIMARY KEY (id);

ALTER TABLE ONLY macrostrat_kg.all_runs
    ADD CONSTRAINT no_duplicate_runs UNIQUE (user_id, model_id, version_id, model_job_id, extraction_pipeline_id, source_text_id, supersedes);

ALTER TABLE ONLY macrostrat_kg.publication
    ADD CONSTRAINT publication_pkey PRIMARY KEY (paper_id);

ALTER TABLE ONLY macrostrat_kg.relationship
    ADD CONSTRAINT relationship_pkey PRIMARY KEY (id);

ALTER TABLE ONLY macrostrat_kg.relationship_type
    ADD CONSTRAINT relationship_type_name_key UNIQUE (name);

ALTER TABLE ONLY macrostrat_kg.relationship_type
    ADD CONSTRAINT relationship_type_pkey PRIMARY KEY (id);

ALTER TABLE ONLY macrostrat_kg.source_text
    ADD CONSTRAINT source_text_pkey PRIMARY KEY (id);

ALTER TABLE ONLY macrostrat_kg.users
    ADD CONSTRAINT user_pkey PRIMARY KEY (internal_user_id);

ALTER TABLE ONLY macrostrat_kg.users
    ADD CONSTRAINT users_unique_enforcement UNIQUE (external_user_id);

CREATE UNIQUE INDEX duplicate_id_check ON macrostrat_kg.source_text USING btree (weaviate_id, map_legend_id);

CREATE UNIQUE INDEX duplicate_relationships ON macrostrat_kg.relationship USING btree (run_id, src_entity_id, dst_entity_id, relationship_type_id);

CREATE UNIQUE INDEX duplicate_text_check ON macrostrat_kg.source_text USING btree (source_text_type, hashed_text);

CREATE UNIQUE INDEX unique_entities ON macrostrat_kg.entity USING btree (name, run_id, entity_type_id, start_index, end_index);

CREATE UNIQUE INDEX unique_versions ON macrostrat_kg.model_version USING btree (model_id, name);

ALTER TABLE ONLY macrostrat_kg.all_runs
    ADD CONSTRAINT "Model version check" FOREIGN KEY (version_id) REFERENCES macrostrat_kg.model_version(id) ON DELETE CASCADE;

ALTER TABLE ONLY macrostrat_kg.source_text
    ADD CONSTRAINT "Paper Details" FOREIGN KEY (paper_id) REFERENCES macrostrat_kg.publication(paper_id) ON DELETE CASCADE;

ALTER TABLE ONLY macrostrat_kg.all_runs
    ADD CONSTRAINT "Previous Run" FOREIGN KEY (supersedes) REFERENCES macrostrat_kg.all_runs(id) ON DELETE CASCADE;

ALTER TABLE ONLY macrostrat_kg.relationship
    ADD CONSTRAINT "Relationship Type Check" FOREIGN KEY (relationship_type_id) REFERENCES macrostrat_kg.relationship_type(id) ON DELETE RESTRICT;

ALTER TABLE ONLY macrostrat_kg.all_runs
    ADD CONSTRAINT "Source Text Id" FOREIGN KEY (source_text_id) REFERENCES macrostrat_kg.source_text(id) ON DELETE CASCADE;

ALTER TABLE ONLY macrostrat_kg.entity
    ADD CONSTRAINT "entity type check" FOREIGN KEY (entity_type_id) REFERENCES macrostrat_kg.entity_type(id) ON DELETE RESTRICT;

ALTER TABLE ONLY macrostrat_kg.relationship
    ADD CONSTRAINT fk_dst_entity_id FOREIGN KEY (dst_entity_id) REFERENCES macrostrat_kg.entity(id) ON DELETE CASCADE;

ALTER TABLE ONLY macrostrat_kg.extraction_feedback
    ADD CONSTRAINT fk_feedback_id FOREIGN KEY (feedback_id) REFERENCES macrostrat_kg.all_runs(id);

ALTER TABLE ONLY macrostrat_kg.relationship
    ADD CONSTRAINT fk_model_run_id FOREIGN KEY (run_id) REFERENCES macrostrat_kg.all_runs(id) ON DELETE CASCADE;

ALTER TABLE ONLY macrostrat_kg.entity
    ADD CONSTRAINT fk_model_run_id FOREIGN KEY (run_id) REFERENCES macrostrat_kg.all_runs(id) ON DELETE CASCADE;

ALTER TABLE ONLY macrostrat_kg.entity
    ADD CONSTRAINT fk_global_entity_id FOREIGN KEY (global_entity_id) REFERENCES macrostrat_kg.global_entity(lobal_entity_id) ;

ALTER TABLE ONLY macrostrat_kg.relationship
    ADD CONSTRAINT fk_src_entity_id FOREIGN KEY (src_entity_id) REFERENCES macrostrat_kg.entity(id) ON DELETE CASCADE;

ALTER TABLE ONLY macrostrat_kg.lookup_extraction_type
    ADD CONSTRAINT lookup_extraction_type_note_id_fkey FOREIGN KEY (note_id) REFERENCES macrostrat_kg.extraction_feedback(note_id) ON DELETE CASCADE;

ALTER TABLE ONLY macrostrat_kg.lookup_extraction_type
    ADD CONSTRAINT lookup_extraction_type_type_id_fkey FOREIGN KEY (type_id) REFERENCES macrostrat_kg.extraction_feedback_type(type_id) ON DELETE CASCADE;

ALTER TABLE ONLY macrostrat_kg.all_runs
    ADD CONSTRAINT model_id_check FOREIGN KEY (model_id) REFERENCES macrostrat_kg.model(id) ON DELETE CASCADE;

ALTER TABLE ONLY macrostrat_kg.model_version
    ADD CONSTRAINT model_id_check FOREIGN KEY (model_id) REFERENCES macrostrat_kg.model(id) ON DELETE CASCADE;

ALTER TABLE ONLY macrostrat_kg.source_text
    ADD CONSTRAINT source_text_legend_legend_id_fk FOREIGN KEY (map_legend_id) REFERENCES maps.legend(legend_id) ON UPDATE CASCADE ON DELETE SET NULL;

ALTER TABLE ONLY macrostrat_kg.all_runs
    ADD CONSTRAINT user_id_check FOREIGN KEY (user_id) REFERENCES macrostrat_kg.users(internal_user_id);

ALTER TABLE ONLY macrostrat_kg.all_runs
    ADD CONSTRAINT all_runs_root_id_fkey FOREIGN KEY (root_id) REFERENCES macrostrat_kg.global_entity(global_entity_id) ON DELETE SET NULL;

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE macrostrat_kg.extraction_feedback TO web_anon;

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE macrostrat_kg.extraction_feedback_type TO web_anon;

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE macrostrat_kg.lookup_extraction_type TO web_anon;

GRANT SELECT ON TABLE macrostrat_kg.all_runs TO web_anon;

GRANT SELECT ON TABLE macrostrat_kg.entity TO web_anon;

GRANT SELECT ON TABLE macrostrat_kg.entity_type TO web_anon;

GRANT SELECT ON TABLE macrostrat_kg.model_run TO web_anon;

GRANT SELECT ON TABLE macrostrat_kg.relationship TO web_anon;

GRANT SELECT ON TABLE macrostrat_kg.source_text TO web_anon;

GRANT SELECT ON TABLE macrostrat_kg.model TO web_anon;

GRANT SELECT ON TABLE macrostrat_kg.publication TO web_anon;

GRANT SELECT,USAGE ON SEQUENCE macrostrat_kg.entity_id_seq TO web_user;

GRANT SELECT,USAGE ON SEQUENCE macrostrat_kg.entity_type_id_seq TO web_user;

GRANT SELECT,USAGE ON SEQUENCE macrostrat_kg.extraction_feedback_note_id_seq TO web_user;
GRANT SELECT,USAGE ON SEQUENCE macrostrat_kg.extraction_feedback_note_id_seq TO web_anon;

GRANT SELECT,USAGE ON SEQUENCE macrostrat_kg.extraction_feedback_type_type_id_seq TO web_user;

GRANT SELECT ON TABLE macrostrat_kg.latest_run_per_text TO web_anon;

GRANT SELECT,USAGE ON SEQUENCE macrostrat_kg.model_run_id_seq TO web_user;

GRANT SELECT ON TABLE macrostrat_kg.model_version TO web_anon;

GRANT SELECT,USAGE ON SEQUENCE macrostrat_kg.model_versions_version_id_seq TO web_user;

GRANT SELECT,USAGE ON SEQUENCE macrostrat_kg.models_model_id_seq TO web_user;

GRANT SELECT,USAGE ON SEQUENCE macrostrat_kg.relationship_id_seq TO web_user;

GRANT SELECT ON TABLE macrostrat_kg.relationship_type TO web_anon;

GRANT SELECT,USAGE ON SEQUENCE macrostrat_kg.relationship_type_id_seq TO web_user;

GRANT SELECT,USAGE ON SEQUENCE macrostrat_kg.source_text_id_seq TO web_user;

GRANT SELECT ON TABLE macrostrat_kg.users TO web_anon;

ALTER DEFAULT PRIVILEGES FOR ROLE macrostrat_admin IN SCHEMA macrostrat_kg GRANT SELECT,USAGE ON SEQUENCES  TO web_user;

ALTER DEFAULT PRIVILEGES FOR ROLE macrostrat_admin IN SCHEMA macrostrat_kg GRANT SELECT ON TABLES  TO web_anon;