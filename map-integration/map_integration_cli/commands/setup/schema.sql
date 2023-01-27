--
-- PostgreSQL database dump
--

-- Dumped from database version 9.5.3
-- Dumped by pg_dump version 9.5.3

SET statement_timeout = 0;
SET lock_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SET check_function_bodies = false;
SET client_min_messages = warning;
SET row_security = off;

SET search_path = carto, pg_catalog;

SET default_tablespace = '';

SET default_with_oids = false;


CREATE EXTENSION postgis;
CREATE EXTENSION postgis_topology;

DROP AGGREGATE IF EXISTS array_agg_mult (anyarray);
CREATE AGGREGATE array_agg_mult (anyarray)  (
    SFUNC     = array_cat
   ,STYPE     = anyarray
   ,INITCOND  = '{}'
);

--
-- Name: carto; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA carto;


--
-- Name: geologic_boundaries; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA geologic_boundaries;


--
-- Name: lines; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA lines;


--
-- Name: macrostrat; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA macrostrat;


--
-- Name: maps; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA maps;


--
-- Name: points; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA points;


SET search_path = maps, pg_catalog;

SET default_tablespace = '';

SET default_with_oids = false;

--
-- Name: sources; Type: TABLE; Schema: maps; Owner: -
--

CREATE TABLE sources (
    source_id integer NOT NULL,
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
    priority boolean DEFAULT false,
    rgeom public.geometry,
    display_scales text[]
);


--
-- Name: sources_source_id_seq; Type: SEQUENCE; Schema: maps; Owner: -
--

CREATE SEQUENCE sources_source_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: sources_source_id_seq; Type: SEQUENCE OWNED BY; Schema: maps; Owner: -
--

ALTER SEQUENCE sources_source_id_seq OWNED BY sources.source_id;


SET search_path = geologic_boundaries, pg_catalog;

--
-- Name: sources; Type: TABLE; Schema: geologic_boundaries; Owner: -
--

CREATE TABLE sources (
    source_id integer DEFAULT nextval('maps.sources_source_id_seq'::regclass) NOT NULL,
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
    rgeom public.geometry
);


SET search_path = lines, pg_catalog;

--
-- Name: large; Type: TABLE; Schema: lines; Owner: -
--

CREATE TABLE large (
    line_id integer DEFAULT nextval('public.line_ids'::regclass) NOT NULL,
    orig_id integer,
    source_id integer,
    name character varying(255),
    type character varying(100),
    direction character varying(40),
    descrip text,
    geom public.geometry(Geometry,4326) NOT NULL,
    new_type character varying(100),
    new_direction character varying(40),
    CONSTRAINT "ST_IsValid(geom)" CHECK (public.st_isvalid(geom))
);


--
-- Name: medium; Type: TABLE; Schema: lines; Owner: -
--

CREATE TABLE medium (
    line_id integer DEFAULT nextval('public.line_ids'::regclass) NOT NULL,
    orig_id integer,
    source_id integer,
    name character varying(255),
    type character varying(100),
    direction character varying(20),
    descrip text,
    geom public.geometry(Geometry,4326) NOT NULL,
    new_type character varying(100),
    new_direction character varying(20),
    CONSTRAINT enforce_valid_geom_lines_medium CHECK (public.st_isvalid(geom))
);


--
-- Name: small; Type: TABLE; Schema: lines; Owner: -
--

CREATE TABLE small (
    line_id integer DEFAULT nextval('public.line_ids'::regclass) NOT NULL,
    orig_id integer,
    source_id integer,
    name character varying(255),
    type character varying(100),
    direction character varying(20),
    descrip text,
    geom public.geometry(Geometry,4326) NOT NULL,
    new_type character varying(100),
    new_direction character varying(20),
    CONSTRAINT enforce_valid_geom_lines_small CHECK (public.st_isvalid(geom))
);


--
-- Name: tiny; Type: TABLE; Schema: lines; Owner: -
--

CREATE TABLE tiny (
    line_id integer DEFAULT nextval('public.line_ids'::regclass) NOT NULL,
    orig_id integer,
    source_id integer,
    name character varying(255),
    type character varying(100),
    direction character varying(20),
    descrip text,
    geom public.geometry(Geometry,4326) NOT NULL,
    new_type character varying(100),
    new_direction character varying(20),
    CONSTRAINT isvalid CHECK (public.st_isvalid(geom))
);


SET search_path = macrostrat, pg_catalog;

--
-- Name: col_areas; Type: TABLE; Schema: macrostrat; Owner: -
--

CREATE TABLE col_areas (
    id integer NOT NULL,
    col_id integer,
    col_area public.geometry,
    wkt text
);


--
-- Name: col_groups; Type: TABLE; Schema: macrostrat; Owner: -
--

CREATE TABLE col_groups (
    id integer NOT NULL,
    col_group character varying(100),
    col_group_long character varying(100)
);


--
-- Name: col_refs; Type: TABLE; Schema: macrostrat; Owner: -
--

CREATE TABLE col_refs (
    id integer NOT NULL,
    col_id integer,
    ref_id integer
);


--
-- Name: cols; Type: TABLE; Schema: macrostrat; Owner: -
--

CREATE TABLE cols (
    id integer NOT NULL,
    col_group_id smallint,
    project_id smallint,
    status_code character varying(25),
    col_position character varying(25),
    col numeric,
    col_name character varying(100),
    lat numeric,
    lng numeric,
    col_area numeric,
    coordinate public.geometry,
    wkt text,
    created text,
    poly_geom public.geometry
);


--
-- Name: concepts_places; Type: TABLE; Schema: macrostrat; Owner: -
--

CREATE TABLE concepts_places (
    concept_id integer NOT NULL,
    place_id integer NOT NULL
);


--
-- Name: intervals; Type: TABLE; Schema: macrostrat; Owner: -
--

CREATE TABLE intervals (
    id integer NOT NULL,
    age_bottom numeric,
    age_top numeric,
    interval_name character varying(200),
    interval_abbrev character varying(50),
    interval_type character varying(50),
    interval_color character varying(20),
    rank integer
);


--
-- Name: intervals_id_seq; Type: SEQUENCE; Schema: macrostrat; Owner: -
--

CREATE SEQUENCE intervals_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: intervals_id_seq; Type: SEQUENCE OWNED BY; Schema: macrostrat; Owner: -
--

ALTER SEQUENCE intervals_id_seq OWNED BY intervals.id;


--
-- Name: lith_atts; Type: TABLE; Schema: macrostrat; Owner: -
--

CREATE TABLE lith_atts (
    id integer NOT NULL,
    lith_att character varying(75),
    att_type character varying(25),
    lith_att_fill integer
);


--
-- Name: liths; Type: TABLE; Schema: macrostrat; Owner: -
--

CREATE TABLE liths (
    id integer NOT NULL,
    lith character varying(75),
    lith_type character varying(50),
    lith_class character varying(50),
    lith_fill integer,
    comp_coef numeric,
    initial_porosity numeric,
    bulk_density numeric,
    lith_color character varying(12)
);


--
-- Name: lookup_strat_names; Type: TABLE; Schema: macrostrat; Owner: -
--

CREATE TABLE lookup_strat_names (
    strat_name_id integer,
    strat_name character varying(100),
    rank character varying(20),
    concept_id integer,
    rank_name character varying(200),
    bed_id integer,
    bed_name character varying(100),
    mbr_id integer,
    mbr_name character varying(100),
    fm_id integer,
    fm_name character varying(100),
    gp_id integer,
    gp_name character varying(100),
    sgp_id integer,
    sgp_name character varying(100),
    early_age numeric,
    late_age numeric,
    gsc_lexicon character varying(20),
    b_period character varying(100),
    t_period character varying(100),
    c_interval character varying(100),
    name_no_lith character varying(100)
);


--
-- Name: lookup_unit_intervals; Type: TABLE; Schema: macrostrat; Owner: -
--

CREATE TABLE lookup_unit_intervals (
    unit_id integer,
    fo_age numeric,
    b_age numeric,
    fo_interval character varying(50),
    fo_period character varying(50),
    lo_age numeric,
    t_age numeric,
    lo_interval character varying(50),
    lo_period character varying(50),
    age character varying(50),
    age_id integer,
    epoch character varying(50),
    epoch_id integer,
    period character varying(50),
    period_id integer,
    era character varying(50),
    era_id integer,
    eon character varying(50),
    eon_id integer,
    best_interval_id integer
);


--
-- Name: lookup_unit_liths; Type: TABLE; Schema: macrostrat; Owner: -
--

CREATE TABLE lookup_unit_liths (
    unit_id integer,
    lith_class character varying(100),
    lith_type character varying(100),
    lith_short text,
    lith_long text,
    environ_class character varying(100),
    environ_type character varying(100),
    environ character varying(255)
);


--
-- Name: places; Type: TABLE; Schema: macrostrat; Owner: -
--

CREATE TABLE places (
    place_id integer NOT NULL,
    name text,
    abbrev text,
    postal text,
    country text,
    country_abbrev text,
    geom public.geometry
);


--
-- Name: refs; Type: TABLE; Schema: macrostrat; Owner: -
--

CREATE TABLE refs (
    id integer NOT NULL,
    pub_year integer,
    author character varying(255),
    ref text,
    doi character varying(40),
    compilation_code character varying(100),
    url text,
    rgeom public.geometry
);


--
-- Name: strat_name_footprints; Type: TABLE; Schema: macrostrat; Owner: -
--

CREATE TABLE strat_name_footprints (
    strat_name_id integer,
    name_no_lith character varying(100),
    rank_name character varying(200),
    concept_id integer,
    concept_names integer[],
    geom public.geometry,
    best_t_age numeric,
    best_b_age numeric
);


--
-- Name: strat_names; Type: TABLE; Schema: macrostrat; Owner: -
--

CREATE TABLE strat_names (
    id integer NOT NULL,
    strat_name character varying(100) NOT NULL,
    rank character varying(50),
    ref_id integer NOT NULL,
    concept_id integer
);


--
-- Name: strat_names_id_seq; Type: SEQUENCE; Schema: macrostrat; Owner: -
--

CREATE SEQUENCE strat_names_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: strat_names_id_seq; Type: SEQUENCE OWNED BY; Schema: macrostrat; Owner: -
--

ALTER SEQUENCE strat_names_id_seq OWNED BY strat_names.id;


--
-- Name: strat_names_meta; Type: TABLE; Schema: macrostrat; Owner: -
--

CREATE TABLE strat_names_meta (
    concept_id integer NOT NULL,
    orig_id integer NOT NULL,
    name character varying(40),
    geologic_age text,
    interval_id integer NOT NULL,
    b_int integer NOT NULL,
    t_int integer NOT NULL,
    usage_notes text,
    other text,
    province text,
    url character varying(150),
    ref_id integer NOT NULL
);


--
-- Name: strat_names_places; Type: TABLE; Schema: macrostrat; Owner: -
--

CREATE TABLE strat_names_places (
    strat_name_id integer NOT NULL,
    place_id integer NOT NULL
);


--
-- Name: timescales; Type: TABLE; Schema: macrostrat; Owner: -
--

CREATE TABLE timescales (
    id integer NOT NULL,
    timescale character varying(100),
    ref_id integer
);


--
-- Name: timescales_intervals; Type: TABLE; Schema: macrostrat; Owner: -
--

CREATE TABLE timescales_intervals (
    timescale_id integer,
    interval_id integer
);


--
-- Name: unit_liths; Type: TABLE; Schema: macrostrat; Owner: -
--

CREATE TABLE unit_liths (
    id integer NOT NULL,
    lith_id integer,
    unit_id integer,
    prop text,
    dom character varying(10),
    comp_prop numeric,
    mod_prop numeric,
    toc numeric,
    ref_id integer
);


--
-- Name: unit_strat_names; Type: TABLE; Schema: macrostrat; Owner: -
--

CREATE TABLE unit_strat_names (
    id integer NOT NULL,
    unit_id integer NOT NULL,
    strat_name_id integer NOT NULL
);


--
-- Name: unit_strat_names_id_seq; Type: SEQUENCE; Schema: macrostrat; Owner: -
--

CREATE SEQUENCE unit_strat_names_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: unit_strat_names_id_seq; Type: SEQUENCE OWNED BY; Schema: macrostrat; Owner: -
--

ALTER SEQUENCE unit_strat_names_id_seq OWNED BY unit_strat_names.id;


--
-- Name: units; Type: TABLE; Schema: macrostrat; Owner: -
--

CREATE TABLE units (
    id integer NOT NULL,
    strat_name character varying(150),
    color character varying(20),
    outcrop character varying(20),
    fo integer,
    fo_h integer,
    lo integer,
    lo_h integer,
    position_bottom numeric,
    position_top numeric,
    max_thick numeric,
    min_thick numeric,
    section_id integer,
    col_id integer
);


--
-- Name: units_sections; Type: TABLE; Schema: macrostrat; Owner: -
--

CREATE TABLE units_sections (
    id integer NOT NULL,
    unit_id integer NOT NULL,
    section_id integer NOT NULL,
    col_id integer NOT NULL
);


--
-- Name: units_sections_id_seq; Type: SEQUENCE; Schema: macrostrat; Owner: -
--

CREATE SEQUENCE units_sections_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: units_sections_id_seq; Type: SEQUENCE OWNED BY; Schema: macrostrat; Owner: -
--

ALTER SEQUENCE units_sections_id_seq OWNED BY units_sections.id;


SET search_path = maps, pg_catalog;

--
-- Name: large; Type: TABLE; Schema: maps; Owner: -
--

CREATE TABLE large (
    map_id integer DEFAULT nextval('public.map_ids'::regclass) NOT NULL,
    orig_id integer,
    source_id integer,
    name text,
    strat_name text,
    age character varying(255),
    lith text,
    descrip text,
    comments text,
    t_interval integer,
    b_interval integer,
    geom public.geometry(Geometry,4326) NOT NULL,
    CONSTRAINT enforce_geom_type_large CHECK (((public.st_geometrytype(geom) <> 'ST_GeometryCollection'::text) AND (public.st_geometrytype(geom) IS NOT NULL))),
    CONSTRAINT enforce_valid_geom_large CHECK (public.st_isvalid(geom))
);


--
-- Name: manual_matches; Type: TABLE; Schema: maps; Owner: -
--

CREATE TABLE manual_matches (
    match_id integer NOT NULL,
    map_id integer NOT NULL,
    strat_name_id integer,
    unit_id integer,
    addition boolean DEFAULT false,
    removal boolean DEFAULT false,
    type character varying(20)
);


--
-- Name: manual_matches_match_id_seq; Type: SEQUENCE; Schema: maps; Owner: -
--

CREATE SEQUENCE manual_matches_match_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: manual_matches_match_id_seq; Type: SEQUENCE OWNED BY; Schema: maps; Owner: -
--

ALTER SEQUENCE manual_matches_match_id_seq OWNED BY manual_matches.match_id;


--
-- Name: map_liths; Type: TABLE; Schema: maps; Owner: -
--

CREATE TABLE map_liths (
    map_id integer NOT NULL,
    lith_id integer NOT NULL,
    basis_col character varying(50)
);


--
-- Name: map_strat_names; Type: TABLE; Schema: maps; Owner: -
--

CREATE TABLE map_strat_names (
    map_id integer NOT NULL,
    strat_name_id integer NOT NULL,
    basis_col character varying(50)
);


--
-- Name: map_units; Type: TABLE; Schema: maps; Owner: -
--

CREATE TABLE map_units (
    map_id integer NOT NULL,
    unit_id integer NOT NULL,
    basis_col character varying(50)
);


--
-- Name: medium; Type: TABLE; Schema: maps; Owner: -
--

CREATE TABLE medium (
    map_id integer DEFAULT nextval('public.map_ids'::regclass) NOT NULL,
    orig_id integer,
    source_id integer,
    name text,
    strat_name text,
    age character varying(255),
    lith text,
    descrip text,
    comments text,
    t_interval integer,
    b_interval integer,
    geom public.geometry(Geometry,4326) NOT NULL,
    CONSTRAINT enforce_geom_type_medium CHECK (((public.st_geometrytype(geom) <> 'ST_GeometryCollection'::text) AND (public.st_geometrytype(geom) IS NOT NULL))),
    CONSTRAINT enforce_valid_geom_medium CHECK (public.st_isvalid(geom))
);


--
-- Name: small; Type: TABLE; Schema: maps; Owner: -
--

CREATE TABLE small (
    map_id integer DEFAULT nextval('public.map_ids'::regclass) NOT NULL,
    orig_id integer,
    source_id integer,
    name text,
    strat_name text,
    age character varying(255),
    lith text,
    descrip text,
    comments text,
    t_interval integer,
    b_interval integer,
    geom public.geometry(Geometry,4326) NOT NULL,
    CONSTRAINT enforce_geom_type_small CHECK (((public.st_geometrytype(geom) <> 'ST_GeometryCollection'::text) AND (public.st_geometrytype(geom) IS NOT NULL))),
    CONSTRAINT enforce_valid_geom_small CHECK (public.st_isvalid(geom))
);


--
-- Name: temp_fidelity_map; Type: TABLE; Schema: maps; Owner: -
--

CREATE TABLE temp_fidelity_map (
    map_id integer,
    color character varying(20),
    geom public.geometry(Geometry,4326)
);


--
-- Name: tiny; Type: TABLE; Schema: maps; Owner: -
--

CREATE TABLE tiny (
    map_id integer DEFAULT nextval('public.map_ids'::regclass) NOT NULL,
    orig_id integer,
    source_id integer,
    name text,
    strat_name text,
    age character varying(255),
    lith text,
    descrip text,
    comments text,
    t_interval integer,
    b_interval integer,
    geom public.geometry(Geometry,4326) NOT NULL,
    CONSTRAINT enforce_geom_type_tiny CHECK (((public.st_geometrytype(geom) <> 'ST_GeometryCollection'::text) AND (public.st_geometrytype(geom) IS NOT NULL))),
    CONSTRAINT enforce_valid_geom_medium CHECK (public.st_isvalid(geom))
);


SET search_path = points, pg_catalog;

--
-- Name: points; Type: TABLE; Schema: points; Owner: -
--

CREATE TABLE points (
    source_id integer NOT NULL,
    strike integer,
    dip integer,
    dip_dir integer,
    point_type character varying(100),
    certainty character varying(100),
    comments text,
    geom public.geometry(Geometry,4326),
    CONSTRAINT dip_lt_90 CHECK ((dip <= 90)),
    CONSTRAINT dip_positive CHECK ((dip >= 0)),
    CONSTRAINT direction_lt_360 CHECK ((dip_dir <= 360)),
    CONSTRAINT direction_positive CHECK ((dip_dir >= 0)),
    CONSTRAINT enforce_point_geom CHECK (public.st_isvalid(geom)),
    CONSTRAINT strike_lt_360 CHECK ((strike <= 360)),
    CONSTRAINT strike_positive CHECK ((strike >= 0))
);


SET search_path = macrostrat, pg_catalog;

--
-- Name: id; Type: DEFAULT; Schema: macrostrat; Owner: -
--

ALTER TABLE ONLY intervals ALTER COLUMN id SET DEFAULT nextval('intervals_id_seq'::regclass);


--
-- Name: id; Type: DEFAULT; Schema: macrostrat; Owner: -
--

ALTER TABLE ONLY strat_names ALTER COLUMN id SET DEFAULT nextval('strat_names_id_seq'::regclass);


--
-- Name: id; Type: DEFAULT; Schema: macrostrat; Owner: -
--

ALTER TABLE ONLY unit_strat_names ALTER COLUMN id SET DEFAULT nextval('unit_strat_names_id_seq'::regclass);


--
-- Name: id; Type: DEFAULT; Schema: macrostrat; Owner: -
--

ALTER TABLE ONLY units_sections ALTER COLUMN id SET DEFAULT nextval('units_sections_id_seq'::regclass);


SET search_path = maps, pg_catalog;

--
-- Name: match_id; Type: DEFAULT; Schema: maps; Owner: -
--

ALTER TABLE ONLY manual_matches ALTER COLUMN match_id SET DEFAULT nextval('manual_matches_match_id_seq'::regclass);


--
-- Name: source_id; Type: DEFAULT; Schema: maps; Owner: -
--

ALTER TABLE ONLY sources ALTER COLUMN source_id SET DEFAULT nextval('sources_source_id_seq'::regclass);


SET search_path = geologic_boundaries, pg_catalog;

--
-- Name: sources_pkey; Type: CONSTRAINT; Schema: geologic_boundaries; Owner: -
--

ALTER TABLE ONLY sources
    ADD CONSTRAINT sources_pkey PRIMARY KEY (source_id);


SET search_path = lines, pg_catalog;

--
-- Name: large_pkey; Type: CONSTRAINT; Schema: lines; Owner: -
--

ALTER TABLE ONLY large
    ADD CONSTRAINT large_pkey PRIMARY KEY (line_id);


--
-- Name: medium_pkey; Type: CONSTRAINT; Schema: lines; Owner: -
--

ALTER TABLE ONLY medium
    ADD CONSTRAINT medium_pkey PRIMARY KEY (line_id);


--
-- Name: small_pkey; Type: CONSTRAINT; Schema: lines; Owner: -
--

ALTER TABLE ONLY small
    ADD CONSTRAINT small_pkey PRIMARY KEY (line_id);


--
-- Name: tiny_pkey; Type: CONSTRAINT; Schema: lines; Owner: -
--

ALTER TABLE ONLY tiny
    ADD CONSTRAINT tiny_pkey PRIMARY KEY (line_id);


SET search_path = macrostrat, pg_catalog;

--
-- Name: col_areas_pkey; Type: CONSTRAINT; Schema: macrostrat; Owner: -
--

ALTER TABLE ONLY col_areas
    ADD CONSTRAINT col_areas_pkey PRIMARY KEY (id);


--
-- Name: col_groups_pkey; Type: CONSTRAINT; Schema: macrostrat; Owner: -
--

ALTER TABLE ONLY col_groups
    ADD CONSTRAINT col_groups_pkey PRIMARY KEY (id);


--
-- Name: col_refs_pkey; Type: CONSTRAINT; Schema: macrostrat; Owner: -
--

ALTER TABLE ONLY col_refs
    ADD CONSTRAINT col_refs_pkey PRIMARY KEY (id);


--
-- Name: cols_pkey; Type: CONSTRAINT; Schema: macrostrat; Owner: -
--

ALTER TABLE ONLY cols
    ADD CONSTRAINT cols_pkey PRIMARY KEY (id);


--
-- Name: lith_atts_pkey; Type: CONSTRAINT; Schema: macrostrat; Owner: -
--

ALTER TABLE ONLY lith_atts
    ADD CONSTRAINT lith_atts_pkey PRIMARY KEY (id);


--
-- Name: liths_pkey; Type: CONSTRAINT; Schema: macrostrat; Owner: -
--

ALTER TABLE ONLY liths
    ADD CONSTRAINT liths_pkey PRIMARY KEY (id);


--
-- Name: places_pkey; Type: CONSTRAINT; Schema: macrostrat; Owner: -
--

ALTER TABLE ONLY places
    ADD CONSTRAINT places_pkey PRIMARY KEY (place_id);


--
-- Name: refs_pkey; Type: CONSTRAINT; Schema: macrostrat; Owner: -
--

ALTER TABLE ONLY refs
    ADD CONSTRAINT refs_pkey PRIMARY KEY (id);


--
-- Name: strat_names_meta_pkey; Type: CONSTRAINT; Schema: macrostrat; Owner: -
--

ALTER TABLE ONLY strat_names_meta
    ADD CONSTRAINT strat_names_meta_pkey PRIMARY KEY (concept_id);


--
-- Name: strat_names_pkey; Type: CONSTRAINT; Schema: macrostrat; Owner: -
--

ALTER TABLE ONLY strat_names
    ADD CONSTRAINT strat_names_pkey PRIMARY KEY (id);


--
-- Name: timescales_pkey; Type: CONSTRAINT; Schema: macrostrat; Owner: -
--

ALTER TABLE ONLY timescales
    ADD CONSTRAINT timescales_pkey PRIMARY KEY (id);


--
-- Name: unit_liths_pkey; Type: CONSTRAINT; Schema: macrostrat; Owner: -
--

ALTER TABLE ONLY unit_liths
    ADD CONSTRAINT unit_liths_pkey PRIMARY KEY (id);


--
-- Name: unit_strat_names_pkey; Type: CONSTRAINT; Schema: macrostrat; Owner: -
--

ALTER TABLE ONLY unit_strat_names
    ADD CONSTRAINT unit_strat_names_pkey PRIMARY KEY (id);


--
-- Name: units_pkey; Type: CONSTRAINT; Schema: macrostrat; Owner: -
--

ALTER TABLE ONLY units
    ADD CONSTRAINT units_pkey PRIMARY KEY (id);


--
-- Name: units_sections_pkey; Type: CONSTRAINT; Schema: macrostrat; Owner: -
--

ALTER TABLE ONLY units_sections
    ADD CONSTRAINT units_sections_pkey PRIMARY KEY (id);


SET search_path = maps, pg_catalog;

--
-- Name: large_pkey; Type: CONSTRAINT; Schema: maps; Owner: -
--

ALTER TABLE ONLY large
    ADD CONSTRAINT large_pkey PRIMARY KEY (map_id);


--
-- Name: medium_pkey; Type: CONSTRAINT; Schema: maps; Owner: -
--

ALTER TABLE ONLY medium
    ADD CONSTRAINT medium_pkey PRIMARY KEY (map_id);


--
-- Name: small_pkey; Type: CONSTRAINT; Schema: maps; Owner: -
--

ALTER TABLE ONLY small
    ADD CONSTRAINT small_pkey PRIMARY KEY (map_id);


--
-- Name: sources_source_id_key; Type: CONSTRAINT; Schema: maps; Owner: -
--

ALTER TABLE ONLY sources
    ADD CONSTRAINT sources_source_id_key UNIQUE (source_id);


--
-- Name: tiny_pkey; Type: CONSTRAINT; Schema: maps; Owner: -
--

ALTER TABLE ONLY tiny
    ADD CONSTRAINT tiny_pkey PRIMARY KEY (map_id);


SET search_path = lines, pg_catalog;

--
-- Name: large_geom_idx; Type: INDEX; Schema: lines; Owner: -
--

CREATE INDEX large_geom_idx ON large USING gist (geom);


--
-- Name: large_line_id_idx; Type: INDEX; Schema: lines; Owner: -
--

CREATE INDEX large_line_id_idx ON large USING btree (line_id);


--
-- Name: large_orig_id_idx; Type: INDEX; Schema: lines; Owner: -
--

CREATE INDEX large_orig_id_idx ON large USING btree (orig_id);


--
-- Name: large_source_id_idx; Type: INDEX; Schema: lines; Owner: -
--

CREATE INDEX large_source_id_idx ON large USING btree (source_id);


--
-- Name: medium_geom_idx; Type: INDEX; Schema: lines; Owner: -
--

CREATE INDEX medium_geom_idx ON medium USING gist (geom);


--
-- Name: medium_line_id_idx; Type: INDEX; Schema: lines; Owner: -
--

CREATE INDEX medium_line_id_idx ON medium USING btree (line_id);


--
-- Name: medium_orig_id_idx; Type: INDEX; Schema: lines; Owner: -
--

CREATE INDEX medium_orig_id_idx ON medium USING btree (orig_id);


--
-- Name: medium_source_id_idx; Type: INDEX; Schema: lines; Owner: -
--

CREATE INDEX medium_source_id_idx ON medium USING btree (source_id);


--
-- Name: small_geom_idx; Type: INDEX; Schema: lines; Owner: -
--

CREATE INDEX small_geom_idx ON small USING gist (geom);


--
-- Name: small_source_id_idx; Type: INDEX; Schema: lines; Owner: -
--

CREATE INDEX small_source_id_idx ON small USING btree (source_id);


--
-- Name: tiny_geom_idx; Type: INDEX; Schema: lines; Owner: -
--

CREATE INDEX tiny_geom_idx ON tiny USING gist (geom);


--
-- Name: tiny_source_id_idx; Type: INDEX; Schema: lines; Owner: -
--

CREATE INDEX tiny_source_id_idx ON tiny USING btree (source_id);


SET search_path = macrostrat, pg_catalog;

--
-- Name: col_areas_col_area_idx; Type: INDEX; Schema: macrostrat; Owner: -
--

CREATE INDEX col_areas_col_area_idx ON col_areas USING gist (col_area);


--
-- Name: col_areas_col_id_idx; Type: INDEX; Schema: macrostrat; Owner: -
--

CREATE INDEX col_areas_col_id_idx ON col_areas USING btree (col_id);


--
-- Name: col_refs_col_id_idx; Type: INDEX; Schema: macrostrat; Owner: -
--

CREATE INDEX col_refs_col_id_idx ON col_refs USING btree (col_id);


--
-- Name: col_refs_ref_id_idx; Type: INDEX; Schema: macrostrat; Owner: -
--

CREATE INDEX col_refs_ref_id_idx ON col_refs USING btree (ref_id);


--
-- Name: cols_col_group_id_idx; Type: INDEX; Schema: macrostrat; Owner: -
--

CREATE INDEX cols_col_group_id_idx ON cols USING btree (col_group_id);


--
-- Name: cols_coordinate_idx; Type: INDEX; Schema: macrostrat; Owner: -
--

CREATE INDEX cols_coordinate_idx ON cols USING gist (coordinate);


--
-- Name: cols_poly_geom_idx; Type: INDEX; Schema: macrostrat; Owner: -
--

CREATE INDEX cols_poly_geom_idx ON cols USING gist (poly_geom);


--
-- Name: cols_project_id_idx; Type: INDEX; Schema: macrostrat; Owner: -
--

CREATE INDEX cols_project_id_idx ON cols USING btree (project_id);


--
-- Name: cols_status_code_idx; Type: INDEX; Schema: macrostrat; Owner: -
--

CREATE INDEX cols_status_code_idx ON cols USING btree (status_code);


--
-- Name: concepts_places_concept_id_idx; Type: INDEX; Schema: macrostrat; Owner: -
--

CREATE INDEX concepts_places_concept_id_idx ON concepts_places USING btree (concept_id);


--
-- Name: concepts_places_place_id_idx; Type: INDEX; Schema: macrostrat; Owner: -
--

CREATE INDEX concepts_places_place_id_idx ON concepts_places USING btree (place_id);


--
-- Name: intervals_age_bottom_idx; Type: INDEX; Schema: macrostrat; Owner: -
--

CREATE INDEX intervals_age_bottom_idx ON intervals USING btree (age_bottom);


--
-- Name: intervals_age_top_idx; Type: INDEX; Schema: macrostrat; Owner: -
--

CREATE INDEX intervals_age_top_idx ON intervals USING btree (age_top);


--
-- Name: intervals_id_idx; Type: INDEX; Schema: macrostrat; Owner: -
--

CREATE INDEX intervals_id_idx ON intervals USING btree (id);


--
-- Name: intervals_interval_name_idx; Type: INDEX; Schema: macrostrat; Owner: -
--

CREATE INDEX intervals_interval_name_idx ON intervals USING btree (interval_name);


--
-- Name: intervals_interval_type_idx; Type: INDEX; Schema: macrostrat; Owner: -
--

CREATE INDEX intervals_interval_type_idx ON intervals USING btree (interval_type);


--
-- Name: lith_atts_att_type_idx; Type: INDEX; Schema: macrostrat; Owner: -
--

CREATE INDEX lith_atts_att_type_idx ON lith_atts USING btree (att_type);


--
-- Name: lith_atts_lith_att_idx; Type: INDEX; Schema: macrostrat; Owner: -
--

CREATE INDEX lith_atts_lith_att_idx ON lith_atts USING btree (lith_att);


--
-- Name: liths_lith_class_idx; Type: INDEX; Schema: macrostrat; Owner: -
--

CREATE INDEX liths_lith_class_idx ON liths USING btree (lith_class);


--
-- Name: liths_lith_idx; Type: INDEX; Schema: macrostrat; Owner: -
--

CREATE INDEX liths_lith_idx ON liths USING btree (lith);


--
-- Name: liths_lith_type_idx; Type: INDEX; Schema: macrostrat; Owner: -
--

CREATE INDEX liths_lith_type_idx ON liths USING btree (lith_type);


--
-- Name: lookup_strat_names_bed_id_idx; Type: INDEX; Schema: macrostrat; Owner: -
--

CREATE INDEX lookup_strat_names_bed_id_idx ON lookup_strat_names USING btree (bed_id);


--
-- Name: lookup_strat_names_concept_id_idx; Type: INDEX; Schema: macrostrat; Owner: -
--

CREATE INDEX lookup_strat_names_concept_id_idx ON lookup_strat_names USING btree (concept_id);


--
-- Name: lookup_strat_names_fm_id_idx; Type: INDEX; Schema: macrostrat; Owner: -
--

CREATE INDEX lookup_strat_names_fm_id_idx ON lookup_strat_names USING btree (fm_id);


--
-- Name: lookup_strat_names_gp_id_idx; Type: INDEX; Schema: macrostrat; Owner: -
--

CREATE INDEX lookup_strat_names_gp_id_idx ON lookup_strat_names USING btree (gp_id);


--
-- Name: lookup_strat_names_mbr_id_idx; Type: INDEX; Schema: macrostrat; Owner: -
--

CREATE INDEX lookup_strat_names_mbr_id_idx ON lookup_strat_names USING btree (mbr_id);


--
-- Name: lookup_strat_names_sgp_id_idx; Type: INDEX; Schema: macrostrat; Owner: -
--

CREATE INDEX lookup_strat_names_sgp_id_idx ON lookup_strat_names USING btree (sgp_id);


--
-- Name: lookup_strat_names_strat_name_id_idx; Type: INDEX; Schema: macrostrat; Owner: -
--

CREATE INDEX lookup_strat_names_strat_name_id_idx ON lookup_strat_names USING btree (strat_name_id);


--
-- Name: lookup_strat_names_strat_name_idx; Type: INDEX; Schema: macrostrat; Owner: -
--

CREATE INDEX lookup_strat_names_strat_name_idx ON lookup_strat_names USING btree (strat_name);


--
-- Name: lookup_unit_intervals_best_interval_id_idx; Type: INDEX; Schema: macrostrat; Owner: -
--

CREATE INDEX lookup_unit_intervals_best_interval_id_idx ON lookup_unit_intervals USING btree (best_interval_id);


--
-- Name: lookup_unit_intervals_unit_id_idx; Type: INDEX; Schema: macrostrat; Owner: -
--

CREATE INDEX lookup_unit_intervals_unit_id_idx ON lookup_unit_intervals USING btree (unit_id);


--
-- Name: lookup_unit_liths_unit_id_idx; Type: INDEX; Schema: macrostrat; Owner: -
--

CREATE INDEX lookup_unit_liths_unit_id_idx ON lookup_unit_liths USING btree (unit_id);


--
-- Name: places_geom_idx; Type: INDEX; Schema: macrostrat; Owner: -
--

CREATE INDEX places_geom_idx ON places USING gist (geom);


--
-- Name: refs_rgeom_idx; Type: INDEX; Schema: macrostrat; Owner: -
--

CREATE INDEX refs_rgeom_idx ON refs USING gist (rgeom);


--
-- Name: strat_name_footprints_geom_idx; Type: INDEX; Schema: macrostrat; Owner: -
--

CREATE INDEX strat_name_footprints_geom_idx ON strat_name_footprints USING gist (geom);


--
-- Name: strat_name_footprints_strat_name_id_idx; Type: INDEX; Schema: macrostrat; Owner: -
--

CREATE INDEX strat_name_footprints_strat_name_id_idx ON strat_name_footprints USING btree (strat_name_id);


--
-- Name: strat_names_concept_id_idx; Type: INDEX; Schema: macrostrat; Owner: -
--

CREATE INDEX strat_names_concept_id_idx ON strat_names USING btree (concept_id);


--
-- Name: strat_names_meta_b_int_idx; Type: INDEX; Schema: macrostrat; Owner: -
--

CREATE INDEX strat_names_meta_b_int_idx ON strat_names_meta USING btree (b_int);


--
-- Name: strat_names_meta_interval_id_idx; Type: INDEX; Schema: macrostrat; Owner: -
--

CREATE INDEX strat_names_meta_interval_id_idx ON strat_names_meta USING btree (interval_id);


--
-- Name: strat_names_meta_ref_id_idx; Type: INDEX; Schema: macrostrat; Owner: -
--

CREATE INDEX strat_names_meta_ref_id_idx ON strat_names_meta USING btree (ref_id);


--
-- Name: strat_names_meta_t_int_idx; Type: INDEX; Schema: macrostrat; Owner: -
--

CREATE INDEX strat_names_meta_t_int_idx ON strat_names_meta USING btree (t_int);


--
-- Name: strat_names_places_place_id_idx; Type: INDEX; Schema: macrostrat; Owner: -
--

CREATE INDEX strat_names_places_place_id_idx ON strat_names_places USING btree (place_id);


--
-- Name: strat_names_places_strat_name_id_idx; Type: INDEX; Schema: macrostrat; Owner: -
--

CREATE INDEX strat_names_places_strat_name_id_idx ON strat_names_places USING btree (strat_name_id);


--
-- Name: strat_names_rank_idx; Type: INDEX; Schema: macrostrat; Owner: -
--

CREATE INDEX strat_names_rank_idx ON strat_names USING btree (rank);


--
-- Name: strat_names_ref_id_idx; Type: INDEX; Schema: macrostrat; Owner: -
--

CREATE INDEX strat_names_ref_id_idx ON strat_names USING btree (ref_id);


--
-- Name: strat_names_strat_name_idx; Type: INDEX; Schema: macrostrat; Owner: -
--

CREATE INDEX strat_names_strat_name_idx ON strat_names USING btree (strat_name);


--
-- Name: timescales_intervals_interval_id_idx; Type: INDEX; Schema: macrostrat; Owner: -
--

CREATE INDEX timescales_intervals_interval_id_idx ON timescales_intervals USING btree (interval_id);


--
-- Name: timescales_intervals_timescale_id_idx; Type: INDEX; Schema: macrostrat; Owner: -
--

CREATE INDEX timescales_intervals_timescale_id_idx ON timescales_intervals USING btree (timescale_id);


--
-- Name: timescales_ref_id_idx; Type: INDEX; Schema: macrostrat; Owner: -
--

CREATE INDEX timescales_ref_id_idx ON timescales USING btree (ref_id);


--
-- Name: timescales_timescale_idx; Type: INDEX; Schema: macrostrat; Owner: -
--

CREATE INDEX timescales_timescale_idx ON timescales USING btree (timescale);


--
-- Name: unit_liths_lith_id_idx; Type: INDEX; Schema: macrostrat; Owner: -
--

CREATE INDEX unit_liths_lith_id_idx ON unit_liths USING btree (lith_id);


--
-- Name: unit_liths_ref_id_idx; Type: INDEX; Schema: macrostrat; Owner: -
--

CREATE INDEX unit_liths_ref_id_idx ON unit_liths USING btree (ref_id);


--
-- Name: unit_liths_unit_id_idx; Type: INDEX; Schema: macrostrat; Owner: -
--

CREATE INDEX unit_liths_unit_id_idx ON unit_liths USING btree (unit_id);


--
-- Name: unit_strat_names_strat_name_id_idx; Type: INDEX; Schema: macrostrat; Owner: -
--

CREATE INDEX unit_strat_names_strat_name_id_idx ON unit_strat_names USING btree (strat_name_id);


--
-- Name: unit_strat_names_unit_id_idx; Type: INDEX; Schema: macrostrat; Owner: -
--

CREATE INDEX unit_strat_names_unit_id_idx ON unit_strat_names USING btree (unit_id);


--
-- Name: units_col_id_idx; Type: INDEX; Schema: macrostrat; Owner: -
--

CREATE INDEX units_col_id_idx ON units USING btree (col_id);


--
-- Name: units_color_idx; Type: INDEX; Schema: macrostrat; Owner: -
--

CREATE INDEX units_color_idx ON units USING btree (color);


--
-- Name: units_section_id_idx; Type: INDEX; Schema: macrostrat; Owner: -
--

CREATE INDEX units_section_id_idx ON units USING btree (section_id);


--
-- Name: units_sections_col_id_idx; Type: INDEX; Schema: macrostrat; Owner: -
--

CREATE INDEX units_sections_col_id_idx ON units_sections USING btree (col_id);


--
-- Name: units_sections_section_id_idx; Type: INDEX; Schema: macrostrat; Owner: -
--

CREATE INDEX units_sections_section_id_idx ON units_sections USING btree (section_id);


--
-- Name: units_sections_unit_id_idx; Type: INDEX; Schema: macrostrat; Owner: -
--

CREATE INDEX units_sections_unit_id_idx ON units_sections USING btree (unit_id);


--
-- Name: units_strat_name_idx; Type: INDEX; Schema: macrostrat; Owner: -
--

CREATE INDEX units_strat_name_idx ON units USING btree (strat_name);


SET search_path = maps, pg_catalog;

--
-- Name: large_b_interval_idx; Type: INDEX; Schema: maps; Owner: -
--

CREATE INDEX large_b_interval_idx ON large USING btree (b_interval);


--
-- Name: large_geom_idx; Type: INDEX; Schema: maps; Owner: -
--

CREATE INDEX large_geom_idx ON large USING gist (geom);


--
-- Name: large_map_id_idx; Type: INDEX; Schema: maps; Owner: -
--

CREATE INDEX large_map_id_idx ON large USING btree (map_id);


--
-- Name: large_orig_id_idx; Type: INDEX; Schema: maps; Owner: -
--

CREATE INDEX large_orig_id_idx ON large USING btree (orig_id);


--
-- Name: large_source_id_idx; Type: INDEX; Schema: maps; Owner: -
--

CREATE INDEX large_source_id_idx ON large USING btree (source_id);


--
-- Name: large_t_interval_idx; Type: INDEX; Schema: maps; Owner: -
--

CREATE INDEX large_t_interval_idx ON large USING btree (t_interval);


--
-- Name: manual_matches_map_id_idx; Type: INDEX; Schema: maps; Owner: -
--

CREATE INDEX manual_matches_map_id_idx ON manual_matches USING btree (map_id);


--
-- Name: manual_matches_strat_name_id_idx; Type: INDEX; Schema: maps; Owner: -
--

CREATE INDEX manual_matches_strat_name_id_idx ON manual_matches USING btree (strat_name_id);


--
-- Name: manual_matches_unit_id_idx; Type: INDEX; Schema: maps; Owner: -
--

CREATE INDEX manual_matches_unit_id_idx ON manual_matches USING btree (unit_id);


--
-- Name: map_liths_lith_id_idx; Type: INDEX; Schema: maps; Owner: -
--

CREATE INDEX map_liths_lith_id_idx ON map_liths USING btree (lith_id);


--
-- Name: map_liths_map_id_idx; Type: INDEX; Schema: maps; Owner: -
--

CREATE INDEX map_liths_map_id_idx ON map_liths USING btree (map_id);


--
-- Name: map_strat_names_map_id_idx; Type: INDEX; Schema: maps; Owner: -
--

CREATE INDEX map_strat_names_map_id_idx ON map_strat_names USING btree (map_id);


--
-- Name: map_strat_names_strat_name_id_idx; Type: INDEX; Schema: maps; Owner: -
--

CREATE INDEX map_strat_names_strat_name_id_idx ON map_strat_names USING btree (strat_name_id);


--
-- Name: map_units_map_id_idx; Type: INDEX; Schema: maps; Owner: -
--

CREATE INDEX map_units_map_id_idx ON map_units USING btree (map_id);


--
-- Name: map_units_unit_id_idx; Type: INDEX; Schema: maps; Owner: -
--

CREATE INDEX map_units_unit_id_idx ON map_units USING btree (unit_id);


--
-- Name: medium_b_interval_idx; Type: INDEX; Schema: maps; Owner: -
--

CREATE INDEX medium_b_interval_idx ON medium USING btree (b_interval);


--
-- Name: medium_geom_idx; Type: INDEX; Schema: maps; Owner: -
--

CREATE INDEX medium_geom_idx ON medium USING gist (geom);


--
-- Name: medium_map_id_idx; Type: INDEX; Schema: maps; Owner: -
--

CREATE INDEX medium_map_id_idx ON medium USING btree (map_id);


--
-- Name: medium_orig_id_idx; Type: INDEX; Schema: maps; Owner: -
--

CREATE INDEX medium_orig_id_idx ON medium USING btree (orig_id);


--
-- Name: medium_source_id_idx; Type: INDEX; Schema: maps; Owner: -
--

CREATE INDEX medium_source_id_idx ON medium USING btree (source_id);


--
-- Name: medium_t_interval_idx; Type: INDEX; Schema: maps; Owner: -
--

CREATE INDEX medium_t_interval_idx ON medium USING btree (t_interval);


--
-- Name: small_b_interval_idx; Type: INDEX; Schema: maps; Owner: -
--

CREATE INDEX small_b_interval_idx ON small USING btree (b_interval);


--
-- Name: small_geom_idx; Type: INDEX; Schema: maps; Owner: -
--

CREATE INDEX small_geom_idx ON small USING gist (geom);


--
-- Name: small_map_id_idx; Type: INDEX; Schema: maps; Owner: -
--

CREATE INDEX small_map_id_idx ON small USING btree (map_id);


--
-- Name: small_orig_id_idx; Type: INDEX; Schema: maps; Owner: -
--

CREATE INDEX small_orig_id_idx ON small USING btree (orig_id);


--
-- Name: small_source_id_idx; Type: INDEX; Schema: maps; Owner: -
--

CREATE INDEX small_source_id_idx ON small USING btree (source_id);


--
-- Name: small_t_interval_idx; Type: INDEX; Schema: maps; Owner: -
--

CREATE INDEX small_t_interval_idx ON small USING btree (t_interval);


--
-- Name: sources_rgeom_idx; Type: INDEX; Schema: maps; Owner: -
--

CREATE INDEX sources_rgeom_idx ON sources USING gist (rgeom);


--
-- Name: sources_source_id_idx; Type: INDEX; Schema: maps; Owner: -
--

CREATE INDEX sources_source_id_idx ON sources USING btree (source_id);


--
-- Name: tiny_b_interval_idx; Type: INDEX; Schema: maps; Owner: -
--

CREATE INDEX tiny_b_interval_idx ON tiny USING btree (b_interval);


--
-- Name: tiny_geom_idx; Type: INDEX; Schema: maps; Owner: -
--

CREATE INDEX tiny_geom_idx ON tiny USING gist (geom);


--
-- Name: tiny_map_id_idx; Type: INDEX; Schema: maps; Owner: -
--

CREATE INDEX tiny_map_id_idx ON tiny USING btree (map_id);


--
-- Name: tiny_orig_id_idx; Type: INDEX; Schema: maps; Owner: -
--

CREATE INDEX tiny_orig_id_idx ON tiny USING btree (orig_id);


--
-- Name: tiny_source_id_idx; Type: INDEX; Schema: maps; Owner: -
--

CREATE INDEX tiny_source_id_idx ON tiny USING btree (source_id);


--
-- Name: tiny_t_interval_idx; Type: INDEX; Schema: maps; Owner: -
--

CREATE INDEX tiny_t_interval_idx ON tiny USING btree (t_interval);


SET search_path = points, pg_catalog;

--
-- Name: points_geom_idx; Type: INDEX; Schema: points; Owner: -
--

CREATE INDEX points_geom_idx ON points USING gist (geom);


--
-- Name: points_source_id_idx; Type: INDEX; Schema: points; Owner: -
--

CREATE INDEX points_source_id_idx ON points USING btree (source_id);




--
-- Name: large; Type: TABLE; Schema: carto; Owner: -
--

CREATE TABLE large (
    map_id integer,
    scale text,
    source_id integer,
    name text,
    strat_name text,
    age character varying,
    lith text,
    descrip text,
    comments text,
    best_age_top numeric,
    best_age_bottom numeric,
    t_int character varying(200),
    b_int character varying(200),
    color character varying(20),
    geom public.geometry
);


--
-- Name: lines_large; Type: TABLE; Schema: carto; Owner: -
--

CREATE TABLE lines_large (
    line_id integer,
    geom public.geometry(Geometry,4326),
    scale text,
    source_id integer,
    name character varying,
    type character varying,
    direction character varying,
    descrip text
);


--
-- Name: lines_medium; Type: TABLE; Schema: carto; Owner: -
--

CREATE TABLE lines_medium (
    line_id integer,
    geom public.geometry(Geometry,4326),
    scale text,
    source_id integer,
    name character varying,
    type character varying,
    direction character varying,
    descrip text
);


--
-- Name: lines_small; Type: TABLE; Schema: carto; Owner: -
--

CREATE TABLE lines_small (
    line_id integer,
    geom public.geometry(Geometry,4326),
    scale text,
    source_id integer,
    name character varying,
    type character varying,
    direction character varying,
    descrip text
);


--
-- Name: lines_tiny; Type: TABLE; Schema: carto; Owner: -
--

CREATE TABLE lines_tiny (
    line_id integer,
    geom public.geometry(Geometry,4326),
    scale text,
    source_id integer,
    name character varying,
    type character varying,
    direction character varying,
    descrip text
);


--
-- Name: medium; Type: TABLE; Schema: carto; Owner: -
--

CREATE TABLE medium (
    map_id integer,
    scale text,
    source_id integer,
    name text,
    strat_name text,
    age character varying,
    lith text,
    descrip text,
    comments text,
    best_age_top numeric,
    best_age_bottom numeric,
    t_int character varying(200),
    b_int character varying(200),
    color character varying(20),
    geom public.geometry
);


--
-- Name: small; Type: TABLE; Schema: carto; Owner: -
--

CREATE TABLE small (
    map_id integer,
    scale text,
    source_id integer,
    name text,
    strat_name text,
    age character varying(255),
    lith text,
    descrip text,
    comments text,
    best_age_top numeric,
    best_age_bottom numeric,
    t_int character varying(200),
    b_int character varying(200),
    color character varying(20),
    geom public.geometry
);


--
-- Name: tiny; Type: TABLE; Schema: carto; Owner: -
--

CREATE TABLE tiny (
    map_id integer,
    scale text,
    source_id integer,
    name text,
    strat_name text,
    age character varying,
    lith text,
    descrip text,
    comments text,
    best_age_top numeric,
    best_age_bottom numeric,
    t_int character varying(200),
    b_int character varying(200),
    color character varying(20),
    geom public.geometry
);


SET search_path = public, pg_catalog;

--
-- Name: lookup_large; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE lookup_large (
    map_id integer,
    unit_ids integer[],
    strat_name_ids integer[],
    lith_ids integer[],
    best_age_top numeric,
    best_age_bottom numeric,
    color character varying(20)
);


--
-- Name: lookup_medium; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE lookup_medium (
    map_id integer,
    unit_ids integer[],
    strat_name_ids integer[],
    lith_ids integer[],
    best_age_top numeric,
    best_age_bottom numeric,
    color character varying(20)
);


--
-- Name: lookup_small; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE lookup_small (
    map_id integer,
    unit_ids integer[],
    strat_name_ids integer[],
    lith_ids integer[],
    best_age_top numeric,
    best_age_bottom numeric,
    color character varying(20)
);


--
-- Name: lookup_tiny; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE lookup_tiny (
    map_id integer,
    unit_ids integer[],
    strat_name_ids integer[],
    lith_ids integer[],
    best_age_top numeric,
    best_age_bottom numeric,
    color character varying(20)
);


SET search_path = carto, pg_catalog;

--
-- Name: large_geom_idx; Type: INDEX; Schema: carto; Owner: -
--

CREATE INDEX large_geom_idx ON large USING gist (geom);


--
-- Name: large_map_id_idx; Type: INDEX; Schema: carto; Owner: -
--

CREATE INDEX large_map_id_idx ON large USING btree (map_id);


--
-- Name: lines_large_new_geom_idx; Type: INDEX; Schema: carto; Owner: -
--

CREATE INDEX lines_large_new_geom_idx ON lines_large USING gist (geom);


--
-- Name: lines_large_new_line_id_idx; Type: INDEX; Schema: carto; Owner: -
--

CREATE INDEX lines_large_new_line_id_idx ON lines_large USING btree (line_id);


--
-- Name: lines_medium_new_geom_idx; Type: INDEX; Schema: carto; Owner: -
--

CREATE INDEX lines_medium_new_geom_idx ON lines_medium USING gist (geom);


--
-- Name: lines_medium_new_line_id_idx; Type: INDEX; Schema: carto; Owner: -
--

CREATE INDEX lines_medium_new_line_id_idx ON lines_medium USING btree (line_id);


--
-- Name: lines_small_new_geom_idx; Type: INDEX; Schema: carto; Owner: -
--

CREATE INDEX lines_small_new_geom_idx ON lines_small USING gist (geom);


--
-- Name: lines_small_new_line_id_idx; Type: INDEX; Schema: carto; Owner: -
--

CREATE INDEX lines_small_new_line_id_idx ON lines_small USING btree (line_id);


--
-- Name: lines_tiny_new_geom_idx1; Type: INDEX; Schema: carto; Owner: -
--

CREATE INDEX lines_tiny_new_geom_idx1 ON lines_tiny USING gist (geom);


--
-- Name: lines_tiny_new_line_id_idx1; Type: INDEX; Schema: carto; Owner: -
--

CREATE INDEX lines_tiny_new_line_id_idx1 ON lines_tiny USING btree (line_id);


--
-- Name: medium_geom_idx; Type: INDEX; Schema: carto; Owner: -
--

CREATE INDEX medium_geom_idx ON medium USING gist (geom);


--
-- Name: medium_map_id_idx; Type: INDEX; Schema: carto; Owner: -
--

CREATE INDEX medium_map_id_idx ON medium USING btree (map_id);


--
-- Name: small_geom_idx; Type: INDEX; Schema: carto; Owner: -
--

CREATE INDEX small_geom_idx ON small USING gist (geom);


--
-- Name: small_map_id_idx; Type: INDEX; Schema: carto; Owner: -
--

CREATE INDEX small_map_id_idx ON small USING btree (map_id);


--
-- Name: tiny_geom_idx; Type: INDEX; Schema: carto; Owner: -
--

CREATE INDEX tiny_geom_idx ON tiny USING gist (geom);


--
-- Name: tiny_map_id_idx; Type: INDEX; Schema: carto; Owner: -
--

CREATE INDEX tiny_map_id_idx ON tiny USING btree (map_id);


SET search_path = public, pg_catalog;

--
-- Name: lookup_large_map_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX lookup_large_map_id_idx ON lookup_large USING btree (map_id);


--
-- Name: lookup_medium_map_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX lookup_medium_map_id_idx ON lookup_medium USING btree (map_id);


--
-- Name: lookup_small_map_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX lookup_small_map_id_idx ON lookup_small USING btree (map_id);


--
-- Name: lookup_tiny_map_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX lookup_tiny_map_id_idx ON lookup_tiny USING btree (map_id);


--
-- PostgreSQL database dump complete
--
