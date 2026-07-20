CREATE SCHEMA geologic_boundaries;

CREATE TABLE geologic_boundaries.boundaries (
    boundary_id integer NOT NULL,
    orig_id integer NOT NULL,
    source_id integer NOT NULL,
    name text,
    boundary_group text,
    boundary_type text,
    boundary_class text,
    descrip text,
    wiki_link text,
    geom public.geometry(Geometry,4326)
);

CREATE SEQUENCE geologic_boundaries.boundaries_boundary_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE geologic_boundaries.boundaries_boundary_id_seq OWNED BY geologic_boundaries.boundaries.boundary_id;

CREATE TABLE geologic_boundaries.sources (
    source_id integer DEFAULT nextval('public.geologic_boundary_source_seq'::regclass) NOT NULL,
    name character varying(255),
    primary_table character varying(255),
    url character varying(255),
    ref_title text,
    authors character varying(255),
    ref_year text,
    ref_source character varying(255),
    isbn_doi character varying(100),
    scale character varying(20),
    primary_line_table character varying(50),
    licence character varying(100),
    features integer,
    area integer,
    priority boolean,
    rgeom public.geometry,
    display_scales text[],
    web_geom public.geometry
);

ALTER TABLE ONLY geologic_boundaries.boundaries ALTER COLUMN boundary_id SET DEFAULT nextval('geologic_boundaries.boundaries_boundary_id_seq'::regclass);

ALTER TABLE ONLY geologic_boundaries.sources
    ADD CONSTRAINT sources_pkey PRIMARY KEY (source_id);

CREATE INDEX boundaries_boundary_class_idx ON geologic_boundaries.boundaries USING btree (boundary_class);

CREATE INDEX boundaries_boundary_id_idx ON geologic_boundaries.boundaries USING btree (boundary_id);

CREATE INDEX boundaries_geom_idx ON geologic_boundaries.boundaries USING gist (geom);

CREATE INDEX boundaries_orig_id_idx ON geologic_boundaries.boundaries USING btree (orig_id);

CREATE INDEX boundaries_source_id_idx ON geologic_boundaries.boundaries USING btree (source_id);


