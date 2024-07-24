-- Type: boundary_status

-- DROP TYPE IF EXISTS macrostrat.boundary_status;

CREATE TYPE macrostrat.boundary_status AS ENUM
    ('', 'modeled', 'relative', 'absolute', 'spike');

ALTER TYPE macrostrat.boundary_status
    OWNER TO macrostrat;

-- Type: boundary_type

-- DROP TYPE IF EXISTS macrostrat.boundary_type;

CREATE TYPE macrostrat.boundary_type AS ENUM
    ('', 'unconformity', 'conformity', 'fault', 'disconformity', 'non-conformity', 'angular unconformity');

ALTER TYPE macrostrat.boundary_type
    OWNER TO macrostrat;

-- Type: ingest_state

-- DROP TYPE IF EXISTS macrostrat.ingest_state;

CREATE TYPE macrostrat.ingest_state AS ENUM
    ('pending', 'ingested', 'prepared', 'failed', 'abandoned');

ALTER TYPE macrostrat.ingest_state
    OWNER TO macrostrat;

-- Type: ingest_type

-- DROP TYPE IF EXISTS macrostrat.ingest_type;

CREATE TYPE macrostrat.ingest_type AS ENUM
    ('raster', 'ta1_output');

ALTER TYPE macrostrat.ingest_type
    OWNER TO macrostrat;

-- Type: map_scale

-- DROP TYPE IF EXISTS macrostrat.map_scale;

CREATE TYPE macrostrat.map_scale AS ENUM
    ('tiny', 'small', 'medium', 'large');

ALTER TYPE macrostrat.map_scale
    OWNER TO macrostrat;


-- Type: schemeenum

-- DROP TYPE IF EXISTS macrostrat.schemeenum;

CREATE TYPE macrostrat.schemeenum AS ENUM
    ('http', 's3');

ALTER TYPE macrostrat.schemeenum
    OWNER TO macrostrat;

--
-- macrostrat.ingest_process
--
CREATE TABLE IF NOT EXISTS macrostrat.ingest_process
(
    id BIGSERIAL,
    state macrostrat.ingest_state,
    comments text COLLATE pg_catalog."default",
    source_id integer,
    access_group_id integer,
    object_group_id integer NOT NULL,
    created_on timestamp with time zone NOT NULL DEFAULT now(),
    completed_on timestamp with time zone,
    CONSTRAINT ingest_process_pkey PRIMARY KEY (id),
    CONSTRAINT ingest_process_access_group_id_fkey FOREIGN KEY (access_group_id)
        REFERENCES macrostrat_auth."group" (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION,
    CONSTRAINT ingest_process_object_group_id_fkey FOREIGN KEY (object_group_id)
        REFERENCES storage.object_group (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION,
    CONSTRAINT ingest_process_source_id_fkey FOREIGN KEY (source_id)
        REFERENCES maps.sources (source_id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION
)

TABLESPACE pg_default;

ALTER TABLE IF EXISTS macrostrat.ingest_process
    OWNER to macrostrat;

--
-- macrostrat.projects
--

CREATE TABLE IF NOT EXISTS macrostrat.projects
(
    id BIGSERIAL,
    project text COLLATE pg_catalog."default",
    descrip text COLLATE pg_catalog."default",
    timescale_id integer,
    CONSTRAINT projects_new_pkey PRIMARY KEY (id)
)

TABLESPACE pg_default;

ALTER TABLE IF EXISTS macrostrat.projects
    OWNER to macrostrat;

COMMENT ON TABLE macrostrat.projects
    IS 'Last updated from MariaDB - 2023-07-28 16:57';
CREATE INDEX IF NOT EXISTS projects_new_project_idx
    ON macrostrat.projects USING btree
    (project COLLATE pg_catalog."default" ASC NULLS LAST)
    TABLESPACE pg_default;
CREATE INDEX IF NOT EXISTS projects_new_timescale_id_idx
    ON macrostrat.projects USING btree
    (timescale_id ASC NULLS LAST)
    TABLESPACE pg_default;

--
-- macrostrat.sections
--

CREATE TABLE IF NOT EXISTS macrostrat.sections
(
    id BIGSERIAL,
    col_id integer,
    CONSTRAINT sections_new_pkey1 PRIMARY KEY (id)
)

TABLESPACE pg_default;

ALTER TABLE IF EXISTS macrostrat.sections
    OWNER to macrostrat;

COMMENT ON TABLE macrostrat.sections
    IS 'Last updated from MariaDB - 2023-07-28 18:11';
CREATE INDEX IF NOT EXISTS sections_new_col_id_idx1
    ON macrostrat.sections USING btree
    (col_id ASC NULLS LAST)
    TABLESPACE pg_default;
CREATE INDEX IF NOT EXISTS sections_new_id_idx1
    ON macrostrat.sections USING btree
    (id ASC NULLS LAST)
    TABLESPACE pg_default;


--
-- macrostrat.strat_tree
--

CREATE TABLE IF NOT EXISTS macrostrat.strat_tree
(
    id BIGSERIAL,
    parent integer,
    child integer,
    ref_id integer,
    CONSTRAINT strat_tree_new_pkey1 PRIMARY KEY (id)
)

TABLESPACE pg_default;

ALTER TABLE IF EXISTS macrostrat.strat_tree
    OWNER to macrostrat;

COMMENT ON TABLE macrostrat.strat_tree
    IS 'Last updated from MariaDB - 2023-07-28 18:06';
CREATE INDEX IF NOT EXISTS strat_tree_new_child_idx1
    ON macrostrat.strat_tree USING btree
    (child ASC NULLS LAST)
    TABLESPACE pg_default;
CREATE INDEX IF NOT EXISTS strat_tree_new_parent_idx1
    ON macrostrat.strat_tree USING btree
    (parent ASC NULLS LAST)
    TABLESPACE pg_default;
CREATE INDEX IF NOT EXISTS strat_tree_new_ref_id_idx1
    ON macrostrat.strat_tree USING btree
    (ref_id ASC NULLS LAST)
    TABLESPACE pg_default;

--
-- macrostrat.unit_boundaries
--

CREATE TABLE IF NOT EXISTS macrostrat.unit_boundaries
(
    id BIGSERIAL,
    t1 numeric NOT NULL,
    t1_prop numeric(6,5) NOT NULL,
    t1_age numeric(8,4) NOT NULL,
    unit_id integer NOT NULL,
    unit_id_2 integer NOT NULL,
    section_id integer NOT NULL,
    boundary_position numeric(6,2) DEFAULT NULL::numeric,
    boundary_type macrostrat.boundary_type NOT NULL DEFAULT ''::macrostrat.boundary_type,
    boundary_status macrostrat.boundary_status NOT NULL DEFAULT 'modeled'::macrostrat.boundary_status,
    paleo_lat numeric(8,5),
    paleo_lng numeric(8,5),
    ref_id integer NOT NULL DEFAULT 217,
    CONSTRAINT unit_boundaries_pkey PRIMARY KEY (id)
)

TABLESPACE pg_default;

ALTER TABLE IF EXISTS macrostrat.unit_boundaries
    OWNER to macrostrat;
CREATE INDEX IF NOT EXISTS unit_boundaries_section_id_idx
    ON macrostrat.unit_boundaries USING btree
    (section_id ASC NULLS LAST)
    TABLESPACE pg_default;
CREATE INDEX IF NOT EXISTS unit_boundaries_t1_idx
    ON macrostrat.unit_boundaries USING btree
    (t1 ASC NULLS LAST)
    TABLESPACE pg_default;
CREATE INDEX IF NOT EXISTS unit_boundaries_unit_id_2_idx
    ON macrostrat.unit_boundaries USING btree
    (unit_id_2 ASC NULLS LAST)
    TABLESPACE pg_default;
CREATE INDEX IF NOT EXISTS unit_boundaries_unit_id_idx
    ON macrostrat.unit_boundaries USING btree
    (unit_id ASC NULLS LAST)
    TABLESPACE pg_default;
