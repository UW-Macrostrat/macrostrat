--
-- PostgreSQL database dump
--

-- Dumped from database version 14.1 (Debian 14.1-1.pgdg110+1)
-- Dumped by pg_dump version 14.1

-- SET statement_timeout = 0;
-- SET lock_timeout = 0;
-- SET idle_in_transaction_session_timeout = 0;
-- SET client_encoding = 'UTF8';
-- SET standard_conforming_strings = on;
-- SELECT pg_catalog.set_config('search_path', '', false);
-- SET check_function_bodies = false;
-- SET xmloption = content;
-- SET client_min_messages = warning;
-- SET row_security = off;

--
-- Name: macrostrat; Type: SCHEMA; Schema: -; Owner: postgres
--

CREATE SCHEMA macrostrat;


ALTER SCHEMA macrostrat OWNER TO postgres;

--
-- Name: postgis; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS postgis WITH SCHEMA public;


--
-- Name: EXTENSION postgis; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION postgis IS 'PostGIS geometry and geography spatial types and functions';


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: autocomplete; Type: TABLE; Schema: macrostrat; Owner: postgres
--

CREATE TABLE macrostrat.autocomplete (
    id integer NOT NULL,
    name text,
    type text,
    category text
);


ALTER TABLE macrostrat.autocomplete OWNER TO postgres;

--
-- Name: TABLE autocomplete; Type: COMMENT; Schema: macrostrat; Owner: postgres
--

COMMENT ON TABLE macrostrat.autocomplete IS 'Last updated from MariaDB - 2021-08-30 11:28';


--
-- Name: col_areas; Type: TABLE; Schema: macrostrat; Owner: postgres
--

CREATE TABLE macrostrat.col_areas (
    id integer NOT NULL,
    col_id integer,
    col_area public.geometry(Geometry,4326),
    wkt text
);


ALTER TABLE macrostrat.col_areas OWNER TO postgres;

--
-- Name: TABLE col_areas; Type: COMMENT; Schema: macrostrat; Owner: postgres
--

COMMENT ON TABLE macrostrat.col_areas IS 'Last updated from MariaDB - 2021-08-30 11:30';


--
-- Name: col_groups; Type: TABLE; Schema: macrostrat; Owner: postgres
--

CREATE TABLE macrostrat.col_groups (
    id integer NOT NULL,
    col_group character varying(100),
    col_group_long character varying(100)
);


ALTER TABLE macrostrat.col_groups OWNER TO postgres;

--
-- Name: TABLE col_groups; Type: COMMENT; Schema: macrostrat; Owner: postgres
--

COMMENT ON TABLE macrostrat.col_groups IS 'Last updated from MariaDB - 2021-08-30 11:28';


--
-- Name: col_refs; Type: TABLE; Schema: macrostrat; Owner: postgres
--

CREATE TABLE macrostrat.col_refs (
    id integer NOT NULL,
    col_id integer,
    ref_id integer
);


ALTER TABLE macrostrat.col_refs OWNER TO postgres;

--
-- Name: TABLE col_refs; Type: COMMENT; Schema: macrostrat; Owner: postgres
--

COMMENT ON TABLE macrostrat.col_refs IS 'Last updated from MariaDB - 2021-08-30 11:25';


--
-- Name: cols; Type: TABLE; Schema: macrostrat; Owner: postgres
--

CREATE TABLE macrostrat.cols (
    id integer NOT NULL,
    col_group_id smallint,
    project_id smallint,
    col_type text,
    status_code character varying(25),
    col_position character varying(25),
    col numeric,
    col_name character varying(100),
    lat numeric,
    lng numeric,
    col_area numeric,
    coordinate public.geometry(Geometry,4326),
    wkt text,
    created text,
    poly_geom public.geometry(Geometry,4326)
);


ALTER TABLE macrostrat.cols OWNER TO postgres;

--
-- Name: TABLE cols; Type: COMMENT; Schema: macrostrat; Owner: postgres
--

COMMENT ON TABLE macrostrat.cols IS 'Last updated from MariaDB - 2021-08-30 12:02';


--
-- Name: concepts_places; Type: TABLE; Schema: macrostrat; Owner: postgres
--

CREATE TABLE macrostrat.concepts_places (
    concept_id integer NOT NULL,
    place_id integer NOT NULL
);


ALTER TABLE macrostrat.concepts_places OWNER TO postgres;

--
-- Name: TABLE concepts_places; Type: COMMENT; Schema: macrostrat; Owner: postgres
--

COMMENT ON TABLE macrostrat.concepts_places IS 'Last updated from MariaDB - 2021-08-30 11:25';


--
-- Name: econs; Type: TABLE; Schema: macrostrat; Owner: postgres
--

CREATE TABLE macrostrat.econs (
    id integer NOT NULL,
    econ text,
    econ_type text,
    econ_class text,
    econ_color text
);


ALTER TABLE macrostrat.econs OWNER TO postgres;

--
-- Name: TABLE econs; Type: COMMENT; Schema: macrostrat; Owner: postgres
--

COMMENT ON TABLE macrostrat.econs IS 'Last updated from MariaDB - 2021-08-30 11:25';


--
-- Name: environs; Type: TABLE; Schema: macrostrat; Owner: postgres
--

CREATE TABLE macrostrat.environs (
    id integer NOT NULL,
    environ text,
    environ_type text,
    environ_class text,
    environ_color text
);


ALTER TABLE macrostrat.environs OWNER TO postgres;

--
-- Name: TABLE environs; Type: COMMENT; Schema: macrostrat; Owner: postgres
--

COMMENT ON TABLE macrostrat.environs IS 'Last updated from MariaDB - 2021-08-30 11:30';


--
-- Name: grainsize; Type: TABLE; Schema: macrostrat; Owner: postgres
--

CREATE TABLE macrostrat.grainsize (
    grain_id integer NOT NULL,
    grain_symbol text,
    grain_name text,
    grain_group text,
    soil_group text,
    min_size numeric,
    max_size numeric,
    classification text
);


ALTER TABLE macrostrat.grainsize OWNER TO postgres;

--
-- Name: intervals; Type: TABLE; Schema: macrostrat; Owner: postgres
--

CREATE TABLE macrostrat.intervals (
    id integer NOT NULL,
    age_bottom numeric,
    age_top numeric,
    interval_name character varying(200),
    interval_abbrev character varying(50),
    interval_type character varying(50),
    interval_color character varying(20),
    rank integer
);


ALTER TABLE macrostrat.intervals OWNER TO postgres;

--
-- Name: TABLE intervals; Type: COMMENT; Schema: macrostrat; Owner: postgres
--

COMMENT ON TABLE macrostrat.intervals IS 'Last updated from MariaDB - 2021-08-30 11:29';


--
-- Name: intervals_new_id_seq1; Type: SEQUENCE; Schema: macrostrat; Owner: postgres
--

CREATE SEQUENCE macrostrat.intervals_new_id_seq1
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE macrostrat.intervals_new_id_seq1 OWNER TO postgres;

--
-- Name: intervals_new_id_seq1; Type: SEQUENCE OWNED BY; Schema: macrostrat; Owner: postgres
--

ALTER SEQUENCE macrostrat.intervals_new_id_seq1 OWNED BY macrostrat.intervals.id;


--
-- Name: lith_atts; Type: TABLE; Schema: macrostrat; Owner: postgres
--

CREATE TABLE macrostrat.lith_atts (
    id integer NOT NULL,
    lith_att character varying(75),
    att_type character varying(25),
    lith_att_fill integer
);


ALTER TABLE macrostrat.lith_atts OWNER TO postgres;

--
-- Name: TABLE lith_atts; Type: COMMENT; Schema: macrostrat; Owner: postgres
--

COMMENT ON TABLE macrostrat.lith_atts IS 'Last updated from MariaDB - 2021-08-30 11:26';


--
-- Name: liths; Type: TABLE; Schema: macrostrat; Owner: postgres
--

CREATE TABLE macrostrat.liths (
    id integer NOT NULL,
    lith character varying(75),
    lith_group text,
    lith_type character varying(50),
    lith_class character varying(50),
    lith_equiv integer,
    lith_fill integer,
    comp_coef numeric,
    initial_porosity numeric,
    bulk_density numeric,
    lith_color character varying(12)
);


ALTER TABLE macrostrat.liths OWNER TO postgres;

--
-- Name: TABLE liths; Type: COMMENT; Schema: macrostrat; Owner: postgres
--

COMMENT ON TABLE macrostrat.liths IS 'Last updated from MariaDB - 2021-08-30 11:29';


--
-- Name: lookup_strat_names; Type: TABLE; Schema: macrostrat; Owner: postgres
--

CREATE TABLE macrostrat.lookup_strat_names (
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


ALTER TABLE macrostrat.lookup_strat_names OWNER TO postgres;

--
-- Name: TABLE lookup_strat_names; Type: COMMENT; Schema: macrostrat; Owner: postgres
--

COMMENT ON TABLE macrostrat.lookup_strat_names IS 'Last updated from MariaDB - 2021-08-30 11:59';


--
-- Name: lookup_unit_attrs_api; Type: TABLE; Schema: macrostrat; Owner: postgres
--

CREATE TABLE macrostrat.lookup_unit_attrs_api (
    unit_id integer,
    lith json,
    environ json,
    econ json,
    measure_short json,
    measure_long json
);


ALTER TABLE macrostrat.lookup_unit_attrs_api OWNER TO postgres;

--
-- Name: TABLE lookup_unit_attrs_api; Type: COMMENT; Schema: macrostrat; Owner: postgres
--

COMMENT ON TABLE macrostrat.lookup_unit_attrs_api IS 'Last updated from MariaDB - 2021-08-30 11:30';


--
-- Name: lookup_unit_intervals; Type: TABLE; Schema: macrostrat; Owner: postgres
--

CREATE TABLE macrostrat.lookup_unit_intervals (
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


ALTER TABLE macrostrat.lookup_unit_intervals OWNER TO postgres;

--
-- Name: TABLE lookup_unit_intervals; Type: COMMENT; Schema: macrostrat; Owner: postgres
--

COMMENT ON TABLE macrostrat.lookup_unit_intervals IS 'Last updated from MariaDB - 2021-08-30 11:26';


--
-- Name: lookup_unit_liths; Type: TABLE; Schema: macrostrat; Owner: postgres
--

CREATE TABLE macrostrat.lookup_unit_liths (
    unit_id integer,
    lith_class character varying(100),
    lith_type character varying(100),
    lith_short text,
    lith_long text,
    environ_class character varying(100),
    environ_type character varying(100),
    environ character varying(255)
);


ALTER TABLE macrostrat.lookup_unit_liths OWNER TO postgres;

--
-- Name: TABLE lookup_unit_liths; Type: COMMENT; Schema: macrostrat; Owner: postgres
--

COMMENT ON TABLE macrostrat.lookup_unit_liths IS 'Last updated from MariaDB - 2021-08-30 11:24';


--
-- Name: lookup_units; Type: TABLE; Schema: macrostrat; Owner: postgres
--

CREATE TABLE macrostrat.lookup_units (
    unit_id integer NOT NULL,
    col_area numeric NOT NULL,
    project_id integer NOT NULL,
    t_int integer,
    t_int_name text,
    t_int_age numeric,
    t_age numeric,
    t_prop numeric,
    t_plat numeric,
    t_plng numeric,
    b_int integer,
    b_int_name text,
    b_int_age numeric,
    b_age numeric,
    b_prop numeric,
    b_plat numeric,
    b_plng numeric,
    clat numeric,
    clng numeric,
    color text,
    text_color text,
    units_above text,
    units_below text,
    pbdb_collections integer,
    pbdb_occurrences integer,
    age text,
    age_id integer,
    epoch text,
    epoch_id integer,
    period text,
    period_id integer,
    era text,
    era_id integer,
    eon text,
    eon_id integer
);


ALTER TABLE macrostrat.lookup_units OWNER TO postgres;

--
-- Name: TABLE lookup_units; Type: COMMENT; Schema: macrostrat; Owner: postgres
--

COMMENT ON TABLE macrostrat.lookup_units IS 'Last updated from MariaDB - 2021-08-30 11:29';


--
-- Name: measurements_new_id_seq; Type: SEQUENCE; Schema: macrostrat; Owner: postgres
--

CREATE SEQUENCE macrostrat.measurements_new_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE macrostrat.measurements_new_id_seq OWNER TO postgres;

--
-- Name: measuremeta; Type: TABLE; Schema: macrostrat; Owner: postgres
--

CREATE TABLE macrostrat.measuremeta (
    id integer NOT NULL,
    sample_name text NOT NULL,
    lat numeric(8,5),
    lng numeric(8,5),
    sample_geo_unit text NOT NULL,
    sample_lith text,
    lith_id integer NOT NULL,
    lith_att_id bigint NOT NULL,
    age text NOT NULL,
    early_id bigint NOT NULL,
    late_id bigint NOT NULL,
    sample_descrip text,
    ref text NOT NULL,
    ref_id bigint NOT NULL
);


ALTER TABLE macrostrat.measuremeta OWNER TO postgres;

--
-- Name: TABLE measuremeta; Type: COMMENT; Schema: macrostrat; Owner: postgres
--

COMMENT ON TABLE macrostrat.measuremeta IS 'Last updated from MariaDB - 2021-08-30 11:27';


--
-- Name: measuremeta_new_id_seq1; Type: SEQUENCE; Schema: macrostrat; Owner: postgres
--

CREATE SEQUENCE macrostrat.measuremeta_new_id_seq1
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE macrostrat.measuremeta_new_id_seq1 OWNER TO postgres;

--
-- Name: measuremeta_new_id_seq1; Type: SEQUENCE OWNED BY; Schema: macrostrat; Owner: postgres
--

ALTER SEQUENCE macrostrat.measuremeta_new_id_seq1 OWNED BY macrostrat.measuremeta.id;


--
-- Name: measures; Type: TABLE; Schema: macrostrat; Owner: postgres
--

CREATE TABLE macrostrat.measures (
    id integer NOT NULL,
    measuremeta_id integer NOT NULL,
    measurement_id integer NOT NULL,
    sample_no character varying(50),
    measure_phase character varying(100) NOT NULL,
    method character varying(100) NOT NULL,
    units character varying(25) NOT NULL,
    measure_value numeric(10,5),
    v_error numeric(10,5),
    v_error_units character varying(25),
    v_type character varying(100),
    v_n integer
);


ALTER TABLE macrostrat.measures OWNER TO postgres;

--
-- Name: TABLE measures; Type: COMMENT; Schema: macrostrat; Owner: postgres
--

COMMENT ON TABLE macrostrat.measures IS 'Last updated from MariaDB - 2021-08-30 11:58';


--
-- Name: measures_new_id_seq; Type: SEQUENCE; Schema: macrostrat; Owner: postgres
--

CREATE SEQUENCE macrostrat.measures_new_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE macrostrat.measures_new_id_seq OWNER TO postgres;

--
-- Name: measures_new_id_seq; Type: SEQUENCE OWNED BY; Schema: macrostrat; Owner: postgres
--

ALTER SEQUENCE macrostrat.measures_new_id_seq OWNED BY macrostrat.measures.id;


--
-- Name: pbdb_collections; Type: TABLE; Schema: macrostrat; Owner: postgres
--

CREATE TABLE macrostrat.pbdb_collections (
    collection_no integer NOT NULL,
    name text,
    early_age numeric,
    late_age numeric,
    grp text,
    grp_clean text,
    formation text,
    formation_clean text,
    member text,
    member_clean text,
    lithologies text[],
    environment text,
    reference_no integer,
    n_occs integer,
    geom public.geometry(Geometry,4326)
);


ALTER TABLE macrostrat.pbdb_collections OWNER TO postgres;

--
-- Name: TABLE pbdb_collections; Type: COMMENT; Schema: macrostrat; Owner: postgres
--

COMMENT ON TABLE macrostrat.pbdb_collections IS 'Last updated from MariaDB - 2021-08-30 12:01';


--
-- Name: pbdb_collections_strat_names; Type: TABLE; Schema: macrostrat; Owner: postgres
--

CREATE TABLE macrostrat.pbdb_collections_strat_names (
    collection_no integer NOT NULL,
    strat_name_id integer NOT NULL,
    basis_col text
);


ALTER TABLE macrostrat.pbdb_collections_strat_names OWNER TO postgres;

--
-- Name: places; Type: TABLE; Schema: macrostrat; Owner: postgres
--

CREATE TABLE macrostrat.places (
    place_id integer NOT NULL,
    name text,
    abbrev text,
    postal text,
    country text,
    country_abbrev text,
    geom public.geometry(Geometry,4326)
);


ALTER TABLE macrostrat.places OWNER TO postgres;

--
-- Name: TABLE places; Type: COMMENT; Schema: macrostrat; Owner: postgres
--

COMMENT ON TABLE macrostrat.places IS 'Last updated from MariaDB - 2021-08-30 11:59';


--
-- Name: projects; Type: TABLE; Schema: macrostrat; Owner: postgres
--

CREATE TABLE macrostrat.projects (
    id integer NOT NULL,
    project text,
    descrip text,
    timescale_id integer
);


ALTER TABLE macrostrat.projects OWNER TO postgres;

--
-- Name: projects_id_seq; Type: SEQUENCE; Schema: macrostrat; Owner: postgres
--

CREATE SEQUENCE macrostrat.projects_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE macrostrat.projects_id_seq OWNER TO postgres;

--
-- Name: projects_id_seq; Type: SEQUENCE OWNED BY; Schema: macrostrat; Owner: postgres
--

ALTER SEQUENCE macrostrat.projects_id_seq OWNED BY macrostrat.projects.id;


--
-- Name: refs; Type: TABLE; Schema: macrostrat; Owner: postgres
--

CREATE TABLE macrostrat.refs (
    id integer NOT NULL,
    pub_year integer,
    author character varying(255),
    ref text,
    doi character varying(40),
    compilation_code character varying(100),
    url text,
    rgeom public.geometry(Geometry,4326)
);


ALTER TABLE macrostrat.refs OWNER TO postgres;

--
-- Name: TABLE refs; Type: COMMENT; Schema: macrostrat; Owner: postgres
--

COMMENT ON TABLE macrostrat.refs IS 'Last updated from MariaDB - 2021-08-30 11:25';


--
-- Name: strat_name_footprints; Type: TABLE; Schema: macrostrat; Owner: postgres
--

CREATE TABLE macrostrat.strat_name_footprints (
    strat_name_id integer,
    name_no_lith character varying(100),
    rank_name character varying(200),
    concept_id integer,
    concept_names integer[],
    geom public.geometry(Geometry,4326),
    best_t_age numeric,
    best_b_age numeric
);


ALTER TABLE macrostrat.strat_name_footprints OWNER TO postgres;

--
-- Name: strat_names; Type: TABLE; Schema: macrostrat; Owner: postgres
--

CREATE TABLE macrostrat.strat_names (
    id integer NOT NULL,
    strat_name character varying(100) NOT NULL,
    rank character varying(50),
    ref_id integer NOT NULL,
    concept_id integer
);


ALTER TABLE macrostrat.strat_names OWNER TO postgres;

--
-- Name: TABLE strat_names; Type: COMMENT; Schema: macrostrat; Owner: postgres
--

COMMENT ON TABLE macrostrat.strat_names IS 'Last updated from MariaDB - 2021-08-30 11:31';


--
-- Name: strat_names_meta; Type: TABLE; Schema: macrostrat; Owner: postgres
--

CREATE TABLE macrostrat.strat_names_meta (
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


ALTER TABLE macrostrat.strat_names_meta OWNER TO postgres;

--
-- Name: TABLE strat_names_meta; Type: COMMENT; Schema: macrostrat; Owner: postgres
--

COMMENT ON TABLE macrostrat.strat_names_meta IS 'Last updated from MariaDB - 2021-08-30 11:28';


--
-- Name: strat_names_new_id_seq; Type: SEQUENCE; Schema: macrostrat; Owner: postgres
--

CREATE SEQUENCE macrostrat.strat_names_new_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE macrostrat.strat_names_new_id_seq OWNER TO postgres;

--
-- Name: strat_names_new_id_seq; Type: SEQUENCE OWNED BY; Schema: macrostrat; Owner: postgres
--

ALTER SEQUENCE macrostrat.strat_names_new_id_seq OWNED BY macrostrat.strat_names.id;


--
-- Name: strat_names_places; Type: TABLE; Schema: macrostrat; Owner: postgres
--

CREATE TABLE macrostrat.strat_names_places (
    strat_name_id integer NOT NULL,
    place_id integer NOT NULL
);


ALTER TABLE macrostrat.strat_names_places OWNER TO postgres;

--
-- Name: TABLE strat_names_places; Type: COMMENT; Schema: macrostrat; Owner: postgres
--

COMMENT ON TABLE macrostrat.strat_names_places IS 'Last updated from MariaDB - 2021-08-30 11:30';


--
-- Name: timescales; Type: TABLE; Schema: macrostrat; Owner: postgres
--

CREATE TABLE macrostrat.timescales (
    id integer NOT NULL,
    timescale character varying(100),
    ref_id integer
);


ALTER TABLE macrostrat.timescales OWNER TO postgres;

--
-- Name: TABLE timescales; Type: COMMENT; Schema: macrostrat; Owner: postgres
--

COMMENT ON TABLE macrostrat.timescales IS 'Last updated from MariaDB - 2021-08-30 11:29';


--
-- Name: timescales_intervals; Type: TABLE; Schema: macrostrat; Owner: postgres
--

CREATE TABLE macrostrat.timescales_intervals (
    timescale_id integer,
    interval_id integer
);


ALTER TABLE macrostrat.timescales_intervals OWNER TO postgres;

--
-- Name: TABLE timescales_intervals; Type: COMMENT; Schema: macrostrat; Owner: postgres
--

COMMENT ON TABLE macrostrat.timescales_intervals IS 'Last updated from MariaDB - 2021-08-30 11:30';


--
-- Name: unit_econs; Type: TABLE; Schema: macrostrat; Owner: postgres
--

CREATE TABLE macrostrat.unit_econs (
    id integer NOT NULL,
    unit_id integer,
    econ_id integer,
    ref_id integer,
    date_mod text
);


ALTER TABLE macrostrat.unit_econs OWNER TO postgres;

--
-- Name: TABLE unit_econs; Type: COMMENT; Schema: macrostrat; Owner: postgres
--

COMMENT ON TABLE macrostrat.unit_econs IS 'Last updated from MariaDB - 2021-08-30 11:25';


--
-- Name: unit_environs; Type: TABLE; Schema: macrostrat; Owner: postgres
--

CREATE TABLE macrostrat.unit_environs (
    id integer NOT NULL,
    unit_id integer,
    environ_id integer,
    ref_id integer,
    date_mod text
);


ALTER TABLE macrostrat.unit_environs OWNER TO postgres;

--
-- Name: TABLE unit_environs; Type: COMMENT; Schema: macrostrat; Owner: postgres
--

COMMENT ON TABLE macrostrat.unit_environs IS 'Last updated from MariaDB - 2021-08-30 11:25';


--
-- Name: unit_lith_atts; Type: TABLE; Schema: macrostrat; Owner: postgres
--

CREATE TABLE macrostrat.unit_lith_atts (
    id integer NOT NULL,
    unit_lith_id integer,
    lith_att_id integer,
    ref_id integer,
    date_mod text
);


ALTER TABLE macrostrat.unit_lith_atts OWNER TO postgres;

--
-- Name: TABLE unit_lith_atts; Type: COMMENT; Schema: macrostrat; Owner: postgres
--

COMMENT ON TABLE macrostrat.unit_lith_atts IS 'Last updated from MariaDB - 2021-08-30 11:25';


--
-- Name: unit_liths; Type: TABLE; Schema: macrostrat; Owner: postgres
--

CREATE TABLE macrostrat.unit_liths (
    id integer NOT NULL,
    lith_id integer,
    unit_id integer,
    prop text,
    dom text,
    comp_prop numeric,
    mod_prop numeric,
    toc numeric,
    ref_id integer,
    date_mod text
);


ALTER TABLE macrostrat.unit_liths OWNER TO postgres;

--
-- Name: TABLE unit_liths; Type: COMMENT; Schema: macrostrat; Owner: postgres
--

COMMENT ON TABLE macrostrat.unit_liths IS 'Last updated from MariaDB - 2021-08-30 11:29';


--
-- Name: unit_measures; Type: TABLE; Schema: macrostrat; Owner: postgres
--

CREATE TABLE macrostrat.unit_measures (
    id integer NOT NULL,
    measuremeta_id integer NOT NULL,
    unit_id integer NOT NULL,
    strat_name_id integer NOT NULL,
    match_basis character varying(10) NOT NULL,
    rel_position numeric(6,5)
);


ALTER TABLE macrostrat.unit_measures OWNER TO postgres;

--
-- Name: TABLE unit_measures; Type: COMMENT; Schema: macrostrat; Owner: postgres
--

COMMENT ON TABLE macrostrat.unit_measures IS 'Last updated from MariaDB - 2018-09-25 10:40';


--
-- Name: unit_measures_new_id_seq; Type: SEQUENCE; Schema: macrostrat; Owner: postgres
--

CREATE SEQUENCE macrostrat.unit_measures_new_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE macrostrat.unit_measures_new_id_seq OWNER TO postgres;

--
-- Name: unit_measures_new_id_seq; Type: SEQUENCE OWNED BY; Schema: macrostrat; Owner: postgres
--

ALTER SEQUENCE macrostrat.unit_measures_new_id_seq OWNED BY macrostrat.unit_measures.id;


--
-- Name: unit_strat_names; Type: TABLE; Schema: macrostrat; Owner: postgres
--

CREATE TABLE macrostrat.unit_strat_names (
    id integer NOT NULL,
    unit_id integer NOT NULL,
    strat_name_id integer NOT NULL
);


ALTER TABLE macrostrat.unit_strat_names OWNER TO postgres;

--
-- Name: TABLE unit_strat_names; Type: COMMENT; Schema: macrostrat; Owner: postgres
--

COMMENT ON TABLE macrostrat.unit_strat_names IS 'Last updated from MariaDB - 2021-08-30 11:25';


--
-- Name: unit_strat_names_new_id_seq1; Type: SEQUENCE; Schema: macrostrat; Owner: postgres
--

CREATE SEQUENCE macrostrat.unit_strat_names_new_id_seq1
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE macrostrat.unit_strat_names_new_id_seq1 OWNER TO postgres;

--
-- Name: unit_strat_names_new_id_seq1; Type: SEQUENCE OWNED BY; Schema: macrostrat; Owner: postgres
--

ALTER SEQUENCE macrostrat.unit_strat_names_new_id_seq1 OWNED BY macrostrat.unit_strat_names.id;


--
-- Name: units; Type: TABLE; Schema: macrostrat; Owner: postgres
--

CREATE TABLE macrostrat.units (
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


ALTER TABLE macrostrat.units OWNER TO postgres;

--
-- Name: TABLE units; Type: COMMENT; Schema: macrostrat; Owner: postgres
--

COMMENT ON TABLE macrostrat.units IS 'Last updated from MariaDB - 2021-08-30 11:31';


--
-- Name: units_sections; Type: TABLE; Schema: macrostrat; Owner: postgres
--

CREATE TABLE macrostrat.units_sections (
    id integer NOT NULL,
    unit_id integer NOT NULL,
    section_id integer NOT NULL,
    col_id integer NOT NULL
);


ALTER TABLE macrostrat.units_sections OWNER TO postgres;

--
-- Name: TABLE units_sections; Type: COMMENT; Schema: macrostrat; Owner: postgres
--

COMMENT ON TABLE macrostrat.units_sections IS 'Last updated from MariaDB - 2021-08-30 11:59';


--
-- Name: units_sections_new_id_seq1; Type: SEQUENCE; Schema: macrostrat; Owner: postgres
--

CREATE SEQUENCE macrostrat.units_sections_new_id_seq1
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE macrostrat.units_sections_new_id_seq1 OWNER TO postgres;

--
-- Name: units_sections_new_id_seq1; Type: SEQUENCE OWNED BY; Schema: macrostrat; Owner: postgres
--

ALTER SEQUENCE macrostrat.units_sections_new_id_seq1 OWNED BY macrostrat.units_sections.id;


--
-- Name: intervals id; Type: DEFAULT; Schema: macrostrat; Owner: postgres
--

ALTER TABLE ONLY macrostrat.intervals ALTER COLUMN id SET DEFAULT nextval('macrostrat.intervals_new_id_seq1'::regclass);


--
-- Name: measuremeta id; Type: DEFAULT; Schema: macrostrat; Owner: postgres
--

ALTER TABLE ONLY macrostrat.measuremeta ALTER COLUMN id SET DEFAULT nextval('macrostrat.measuremeta_new_id_seq1'::regclass);


--
-- Name: measures id; Type: DEFAULT; Schema: macrostrat; Owner: postgres
--

ALTER TABLE ONLY macrostrat.measures ALTER COLUMN id SET DEFAULT nextval('macrostrat.measures_new_id_seq'::regclass);


--
-- Name: projects id; Type: DEFAULT; Schema: macrostrat; Owner: postgres
--

ALTER TABLE ONLY macrostrat.projects ALTER COLUMN id SET DEFAULT nextval('macrostrat.projects_id_seq'::regclass);


--
-- Name: strat_names id; Type: DEFAULT; Schema: macrostrat; Owner: postgres
--

ALTER TABLE ONLY macrostrat.strat_names ALTER COLUMN id SET DEFAULT nextval('macrostrat.strat_names_new_id_seq'::regclass);


--
-- Name: unit_measures id; Type: DEFAULT; Schema: macrostrat; Owner: postgres
--

ALTER TABLE ONLY macrostrat.unit_measures ALTER COLUMN id SET DEFAULT nextval('macrostrat.unit_measures_new_id_seq'::regclass);


--
-- Name: unit_strat_names id; Type: DEFAULT; Schema: macrostrat; Owner: postgres
--

ALTER TABLE ONLY macrostrat.unit_strat_names ALTER COLUMN id SET DEFAULT nextval('macrostrat.unit_strat_names_new_id_seq1'::regclass);


--
-- Name: units_sections id; Type: DEFAULT; Schema: macrostrat; Owner: postgres
--

ALTER TABLE ONLY macrostrat.units_sections ALTER COLUMN id SET DEFAULT nextval('macrostrat.units_sections_new_id_seq1'::regclass);


--
-- Name: col_areas col_areas_new_pkey; Type: CONSTRAINT; Schema: macrostrat; Owner: postgres
--

ALTER TABLE ONLY macrostrat.col_areas
    ADD CONSTRAINT col_areas_new_pkey PRIMARY KEY (id);


--
-- Name: col_groups col_groups_new_pkey1; Type: CONSTRAINT; Schema: macrostrat; Owner: postgres
--

ALTER TABLE ONLY macrostrat.col_groups
    ADD CONSTRAINT col_groups_new_pkey1 PRIMARY KEY (id);


--
-- Name: col_refs col_refs_new_pkey1; Type: CONSTRAINT; Schema: macrostrat; Owner: postgres
--

ALTER TABLE ONLY macrostrat.col_refs
    ADD CONSTRAINT col_refs_new_pkey1 PRIMARY KEY (id);


--
-- Name: cols cols_new_pkey1; Type: CONSTRAINT; Schema: macrostrat; Owner: postgres
--

ALTER TABLE ONLY macrostrat.cols
    ADD CONSTRAINT cols_new_pkey1 PRIMARY KEY (id);


--
-- Name: econs econs_new_pkey; Type: CONSTRAINT; Schema: macrostrat; Owner: postgres
--

ALTER TABLE ONLY macrostrat.econs
    ADD CONSTRAINT econs_new_pkey PRIMARY KEY (id);


--
-- Name: environs environs_new_pkey1; Type: CONSTRAINT; Schema: macrostrat; Owner: postgres
--

ALTER TABLE ONLY macrostrat.environs
    ADD CONSTRAINT environs_new_pkey1 PRIMARY KEY (id);


--
-- Name: grainsize grainsize_pkey; Type: CONSTRAINT; Schema: macrostrat; Owner: postgres
--

ALTER TABLE ONLY macrostrat.grainsize
    ADD CONSTRAINT grainsize_pkey PRIMARY KEY (grain_id);


--
-- Name: intervals intervals_pkey; Type: CONSTRAINT; Schema: macrostrat; Owner: postgres
--

ALTER TABLE ONLY macrostrat.intervals
    ADD CONSTRAINT intervals_pkey PRIMARY KEY (id);


--
-- Name: lith_atts lith_atts_new_pkey1; Type: CONSTRAINT; Schema: macrostrat; Owner: postgres
--

ALTER TABLE ONLY macrostrat.lith_atts
    ADD CONSTRAINT lith_atts_new_pkey1 PRIMARY KEY (id);


--
-- Name: liths liths_new_pkey1; Type: CONSTRAINT; Schema: macrostrat; Owner: postgres
--

ALTER TABLE ONLY macrostrat.liths
    ADD CONSTRAINT liths_new_pkey1 PRIMARY KEY (id);


--
-- Name: lookup_units lookup_units_new_pkey1; Type: CONSTRAINT; Schema: macrostrat; Owner: postgres
--

ALTER TABLE ONLY macrostrat.lookup_units
    ADD CONSTRAINT lookup_units_new_pkey1 PRIMARY KEY (unit_id);


--
-- Name: measuremeta measuremeta_new_pkey; Type: CONSTRAINT; Schema: macrostrat; Owner: postgres
--

ALTER TABLE ONLY macrostrat.measuremeta
    ADD CONSTRAINT measuremeta_new_pkey PRIMARY KEY (id);


--
-- Name: places places_new_pkey1; Type: CONSTRAINT; Schema: macrostrat; Owner: postgres
--

ALTER TABLE ONLY macrostrat.places
    ADD CONSTRAINT places_new_pkey1 PRIMARY KEY (place_id);


--
-- Name: projects projects_pkey; Type: CONSTRAINT; Schema: macrostrat; Owner: postgres
--

ALTER TABLE ONLY macrostrat.projects
    ADD CONSTRAINT projects_pkey PRIMARY KEY (id);


--
-- Name: refs refs_new_pkey1; Type: CONSTRAINT; Schema: macrostrat; Owner: postgres
--

ALTER TABLE ONLY macrostrat.refs
    ADD CONSTRAINT refs_new_pkey1 PRIMARY KEY (id);


--
-- Name: strat_names_meta strat_names_meta_new_pkey1; Type: CONSTRAINT; Schema: macrostrat; Owner: postgres
--

ALTER TABLE ONLY macrostrat.strat_names_meta
    ADD CONSTRAINT strat_names_meta_new_pkey1 PRIMARY KEY (concept_id);


--
-- Name: strat_names strat_names_new_pkey; Type: CONSTRAINT; Schema: macrostrat; Owner: postgres
--

ALTER TABLE ONLY macrostrat.strat_names
    ADD CONSTRAINT strat_names_new_pkey PRIMARY KEY (id);


--
-- Name: timescales timescales_new_pkey1; Type: CONSTRAINT; Schema: macrostrat; Owner: postgres
--

ALTER TABLE ONLY macrostrat.timescales
    ADD CONSTRAINT timescales_new_pkey1 PRIMARY KEY (id);


--
-- Name: unit_econs unit_econs_new_pkey1; Type: CONSTRAINT; Schema: macrostrat; Owner: postgres
--

ALTER TABLE ONLY macrostrat.unit_econs
    ADD CONSTRAINT unit_econs_new_pkey1 PRIMARY KEY (id);


--
-- Name: unit_environs unit_environs_new_pkey1; Type: CONSTRAINT; Schema: macrostrat; Owner: postgres
--

ALTER TABLE ONLY macrostrat.unit_environs
    ADD CONSTRAINT unit_environs_new_pkey1 PRIMARY KEY (id);


--
-- Name: unit_lith_atts unit_lith_atts_new_pkey1; Type: CONSTRAINT; Schema: macrostrat; Owner: postgres
--

ALTER TABLE ONLY macrostrat.unit_lith_atts
    ADD CONSTRAINT unit_lith_atts_new_pkey1 PRIMARY KEY (id);


--
-- Name: unit_liths unit_liths_new_pkey1; Type: CONSTRAINT; Schema: macrostrat; Owner: postgres
--

ALTER TABLE ONLY macrostrat.unit_liths
    ADD CONSTRAINT unit_liths_new_pkey1 PRIMARY KEY (id);


--
-- Name: unit_measures unit_measures_new_pkey; Type: CONSTRAINT; Schema: macrostrat; Owner: postgres
--

ALTER TABLE ONLY macrostrat.unit_measures
    ADD CONSTRAINT unit_measures_new_pkey PRIMARY KEY (id);


--
-- Name: unit_strat_names unit_strat_names_new_pkey1; Type: CONSTRAINT; Schema: macrostrat; Owner: postgres
--

ALTER TABLE ONLY macrostrat.unit_strat_names
    ADD CONSTRAINT unit_strat_names_new_pkey1 PRIMARY KEY (id);


--
-- Name: units units_new_pkey; Type: CONSTRAINT; Schema: macrostrat; Owner: postgres
--

ALTER TABLE ONLY macrostrat.units
    ADD CONSTRAINT units_new_pkey PRIMARY KEY (id);


--
-- Name: units_sections units_sections_new_pkey1; Type: CONSTRAINT; Schema: macrostrat; Owner: postgres
--

ALTER TABLE ONLY macrostrat.units_sections
    ADD CONSTRAINT units_sections_new_pkey1 PRIMARY KEY (id);


--
-- Name: autocomplete_new_category_idx1; Type: INDEX; Schema: macrostrat; Owner: postgres
--

CREATE INDEX autocomplete_new_category_idx1 ON macrostrat.autocomplete USING btree (category);


--
-- Name: autocomplete_new_id_idx1; Type: INDEX; Schema: macrostrat; Owner: postgres
--

CREATE INDEX autocomplete_new_id_idx1 ON macrostrat.autocomplete USING btree (id);


--
-- Name: autocomplete_new_name_idx1; Type: INDEX; Schema: macrostrat; Owner: postgres
--

CREATE INDEX autocomplete_new_name_idx1 ON macrostrat.autocomplete USING btree (name);


--
-- Name: autocomplete_new_type_idx1; Type: INDEX; Schema: macrostrat; Owner: postgres
--

CREATE INDEX autocomplete_new_type_idx1 ON macrostrat.autocomplete USING btree (type);


--
-- Name: col_areas_new_col_area_idx; Type: INDEX; Schema: macrostrat; Owner: postgres
--

CREATE INDEX col_areas_new_col_area_idx ON macrostrat.col_areas USING gist (col_area);


--
-- Name: col_areas_new_col_id_idx; Type: INDEX; Schema: macrostrat; Owner: postgres
--

CREATE INDEX col_areas_new_col_id_idx ON macrostrat.col_areas USING btree (col_id);


--
-- Name: col_groups_new_id_idx1; Type: INDEX; Schema: macrostrat; Owner: postgres
--

CREATE INDEX col_groups_new_id_idx1 ON macrostrat.col_groups USING btree (id);


--
-- Name: col_refs_new_col_id_idx1; Type: INDEX; Schema: macrostrat; Owner: postgres
--

CREATE INDEX col_refs_new_col_id_idx1 ON macrostrat.col_refs USING btree (col_id);


--
-- Name: col_refs_new_ref_id_idx1; Type: INDEX; Schema: macrostrat; Owner: postgres
--

CREATE INDEX col_refs_new_ref_id_idx1 ON macrostrat.col_refs USING btree (ref_id);


--
-- Name: cols_new_col_group_id_idx1; Type: INDEX; Schema: macrostrat; Owner: postgres
--

CREATE INDEX cols_new_col_group_id_idx1 ON macrostrat.cols USING btree (col_group_id);


--
-- Name: cols_new_coordinate_idx1; Type: INDEX; Schema: macrostrat; Owner: postgres
--

CREATE INDEX cols_new_coordinate_idx1 ON macrostrat.cols USING gist (coordinate);


--
-- Name: cols_new_poly_geom_idx1; Type: INDEX; Schema: macrostrat; Owner: postgres
--

CREATE INDEX cols_new_poly_geom_idx1 ON macrostrat.cols USING gist (poly_geom);


--
-- Name: cols_new_project_id_idx1; Type: INDEX; Schema: macrostrat; Owner: postgres
--

CREATE INDEX cols_new_project_id_idx1 ON macrostrat.cols USING btree (project_id);


--
-- Name: cols_new_status_code_idx1; Type: INDEX; Schema: macrostrat; Owner: postgres
--

CREATE INDEX cols_new_status_code_idx1 ON macrostrat.cols USING btree (status_code);


--
-- Name: concepts_places_new_concept_id_idx; Type: INDEX; Schema: macrostrat; Owner: postgres
--

CREATE INDEX concepts_places_new_concept_id_idx ON macrostrat.concepts_places USING btree (concept_id);


--
-- Name: concepts_places_new_place_id_idx; Type: INDEX; Schema: macrostrat; Owner: postgres
--

CREATE INDEX concepts_places_new_place_id_idx ON macrostrat.concepts_places USING btree (place_id);


--
-- Name: intervals_new_age_bottom_idx1; Type: INDEX; Schema: macrostrat; Owner: postgres
--

CREATE INDEX intervals_new_age_bottom_idx1 ON macrostrat.intervals USING btree (age_bottom);


--
-- Name: intervals_new_age_top_idx1; Type: INDEX; Schema: macrostrat; Owner: postgres
--

CREATE INDEX intervals_new_age_top_idx1 ON macrostrat.intervals USING btree (age_top);


--
-- Name: intervals_new_id_idx1; Type: INDEX; Schema: macrostrat; Owner: postgres
--

CREATE INDEX intervals_new_id_idx1 ON macrostrat.intervals USING btree (id);


--
-- Name: intervals_new_interval_name_idx1; Type: INDEX; Schema: macrostrat; Owner: postgres
--

CREATE INDEX intervals_new_interval_name_idx1 ON macrostrat.intervals USING btree (interval_name);


--
-- Name: intervals_new_interval_type_idx1; Type: INDEX; Schema: macrostrat; Owner: postgres
--

CREATE INDEX intervals_new_interval_type_idx1 ON macrostrat.intervals USING btree (interval_type);


--
-- Name: lith_atts_new_att_type_idx1; Type: INDEX; Schema: macrostrat; Owner: postgres
--

CREATE INDEX lith_atts_new_att_type_idx1 ON macrostrat.lith_atts USING btree (att_type);


--
-- Name: lith_atts_new_lith_att_idx1; Type: INDEX; Schema: macrostrat; Owner: postgres
--

CREATE INDEX lith_atts_new_lith_att_idx1 ON macrostrat.lith_atts USING btree (lith_att);


--
-- Name: liths_new_lith_class_idx1; Type: INDEX; Schema: macrostrat; Owner: postgres
--

CREATE INDEX liths_new_lith_class_idx1 ON macrostrat.liths USING btree (lith_class);


--
-- Name: liths_new_lith_idx1; Type: INDEX; Schema: macrostrat; Owner: postgres
--

CREATE INDEX liths_new_lith_idx1 ON macrostrat.liths USING btree (lith);


--
-- Name: liths_new_lith_type_idx1; Type: INDEX; Schema: macrostrat; Owner: postgres
--

CREATE INDEX liths_new_lith_type_idx1 ON macrostrat.liths USING btree (lith_type);


--
-- Name: lookup_strat_names_new_bed_id_idx1; Type: INDEX; Schema: macrostrat; Owner: postgres
--

CREATE INDEX lookup_strat_names_new_bed_id_idx1 ON macrostrat.lookup_strat_names USING btree (bed_id);


--
-- Name: lookup_strat_names_new_concept_id_idx1; Type: INDEX; Schema: macrostrat; Owner: postgres
--

CREATE INDEX lookup_strat_names_new_concept_id_idx1 ON macrostrat.lookup_strat_names USING btree (concept_id);


--
-- Name: lookup_strat_names_new_fm_id_idx1; Type: INDEX; Schema: macrostrat; Owner: postgres
--

CREATE INDEX lookup_strat_names_new_fm_id_idx1 ON macrostrat.lookup_strat_names USING btree (fm_id);


--
-- Name: lookup_strat_names_new_gp_id_idx1; Type: INDEX; Schema: macrostrat; Owner: postgres
--

CREATE INDEX lookup_strat_names_new_gp_id_idx1 ON macrostrat.lookup_strat_names USING btree (gp_id);


--
-- Name: lookup_strat_names_new_mbr_id_idx1; Type: INDEX; Schema: macrostrat; Owner: postgres
--

CREATE INDEX lookup_strat_names_new_mbr_id_idx1 ON macrostrat.lookup_strat_names USING btree (mbr_id);


--
-- Name: lookup_strat_names_new_sgp_id_idx1; Type: INDEX; Schema: macrostrat; Owner: postgres
--

CREATE INDEX lookup_strat_names_new_sgp_id_idx1 ON macrostrat.lookup_strat_names USING btree (sgp_id);


--
-- Name: lookup_strat_names_new_strat_name_id_idx1; Type: INDEX; Schema: macrostrat; Owner: postgres
--

CREATE INDEX lookup_strat_names_new_strat_name_id_idx1 ON macrostrat.lookup_strat_names USING btree (strat_name_id);


--
-- Name: lookup_strat_names_new_strat_name_idx1; Type: INDEX; Schema: macrostrat; Owner: postgres
--

CREATE INDEX lookup_strat_names_new_strat_name_idx1 ON macrostrat.lookup_strat_names USING btree (strat_name);


--
-- Name: lookup_unit_attrs_api_new_unit_id_idx1; Type: INDEX; Schema: macrostrat; Owner: postgres
--

CREATE INDEX lookup_unit_attrs_api_new_unit_id_idx1 ON macrostrat.lookup_unit_attrs_api USING btree (unit_id);


--
-- Name: lookup_unit_intervals_new_best_interval_id_idx; Type: INDEX; Schema: macrostrat; Owner: postgres
--

CREATE INDEX lookup_unit_intervals_new_best_interval_id_idx ON macrostrat.lookup_unit_intervals USING btree (best_interval_id);


--
-- Name: lookup_unit_intervals_new_unit_id_idx; Type: INDEX; Schema: macrostrat; Owner: postgres
--

CREATE INDEX lookup_unit_intervals_new_unit_id_idx ON macrostrat.lookup_unit_intervals USING btree (unit_id);


--
-- Name: lookup_unit_liths_new_unit_id_idx; Type: INDEX; Schema: macrostrat; Owner: postgres
--

CREATE INDEX lookup_unit_liths_new_unit_id_idx ON macrostrat.lookup_unit_liths USING btree (unit_id);


--
-- Name: lookup_units_new_b_int_idx1; Type: INDEX; Schema: macrostrat; Owner: postgres
--

CREATE INDEX lookup_units_new_b_int_idx1 ON macrostrat.lookup_units USING btree (b_int);


--
-- Name: lookup_units_new_project_id_idx1; Type: INDEX; Schema: macrostrat; Owner: postgres
--

CREATE INDEX lookup_units_new_project_id_idx1 ON macrostrat.lookup_units USING btree (project_id);


--
-- Name: lookup_units_new_t_int_idx1; Type: INDEX; Schema: macrostrat; Owner: postgres
--

CREATE INDEX lookup_units_new_t_int_idx1 ON macrostrat.lookup_units USING btree (t_int);


--
-- Name: measuremeta_new_lith_att_id_idx1; Type: INDEX; Schema: macrostrat; Owner: postgres
--

CREATE INDEX measuremeta_new_lith_att_id_idx1 ON macrostrat.measuremeta USING btree (lith_att_id);


--
-- Name: measuremeta_new_lith_id_idx1; Type: INDEX; Schema: macrostrat; Owner: postgres
--

CREATE INDEX measuremeta_new_lith_id_idx1 ON macrostrat.measuremeta USING btree (lith_id);


--
-- Name: measuremeta_new_ref_id_idx1; Type: INDEX; Schema: macrostrat; Owner: postgres
--

CREATE INDEX measuremeta_new_ref_id_idx1 ON macrostrat.measuremeta USING btree (ref_id);


--
-- Name: measures_new_measurement_id_idx; Type: INDEX; Schema: macrostrat; Owner: postgres
--

CREATE INDEX measures_new_measurement_id_idx ON macrostrat.measures USING btree (measurement_id);


--
-- Name: measures_new_measuremeta_id_idx; Type: INDEX; Schema: macrostrat; Owner: postgres
--

CREATE INDEX measures_new_measuremeta_id_idx ON macrostrat.measures USING btree (measuremeta_id);


--
-- Name: pbdb_collections_new_collection_no_idx; Type: INDEX; Schema: macrostrat; Owner: postgres
--

CREATE INDEX pbdb_collections_new_collection_no_idx ON macrostrat.pbdb_collections USING btree (collection_no);


--
-- Name: pbdb_collections_new_early_age_idx; Type: INDEX; Schema: macrostrat; Owner: postgres
--

CREATE INDEX pbdb_collections_new_early_age_idx ON macrostrat.pbdb_collections USING btree (early_age);


--
-- Name: pbdb_collections_new_geom_idx; Type: INDEX; Schema: macrostrat; Owner: postgres
--

CREATE INDEX pbdb_collections_new_geom_idx ON macrostrat.pbdb_collections USING gist (geom);


--
-- Name: pbdb_collections_new_late_age_idx; Type: INDEX; Schema: macrostrat; Owner: postgres
--

CREATE INDEX pbdb_collections_new_late_age_idx ON macrostrat.pbdb_collections USING btree (late_age);


--
-- Name: places_new_geom_idx1; Type: INDEX; Schema: macrostrat; Owner: postgres
--

CREATE INDEX places_new_geom_idx1 ON macrostrat.places USING gist (geom);


--
-- Name: refs_new_rgeom_idx1; Type: INDEX; Schema: macrostrat; Owner: postgres
--

CREATE INDEX refs_new_rgeom_idx1 ON macrostrat.refs USING gist (rgeom);


--
-- Name: strat_name_footprints_new_geom_idx; Type: INDEX; Schema: macrostrat; Owner: postgres
--

CREATE INDEX strat_name_footprints_new_geom_idx ON macrostrat.strat_name_footprints USING gist (geom);


--
-- Name: strat_name_footprints_new_strat_name_id_idx; Type: INDEX; Schema: macrostrat; Owner: postgres
--

CREATE INDEX strat_name_footprints_new_strat_name_id_idx ON macrostrat.strat_name_footprints USING btree (strat_name_id);


--
-- Name: strat_names_meta_new_b_int_idx1; Type: INDEX; Schema: macrostrat; Owner: postgres
--

CREATE INDEX strat_names_meta_new_b_int_idx1 ON macrostrat.strat_names_meta USING btree (b_int);


--
-- Name: strat_names_meta_new_interval_id_idx1; Type: INDEX; Schema: macrostrat; Owner: postgres
--

CREATE INDEX strat_names_meta_new_interval_id_idx1 ON macrostrat.strat_names_meta USING btree (interval_id);


--
-- Name: strat_names_meta_new_ref_id_idx1; Type: INDEX; Schema: macrostrat; Owner: postgres
--

CREATE INDEX strat_names_meta_new_ref_id_idx1 ON macrostrat.strat_names_meta USING btree (ref_id);


--
-- Name: strat_names_meta_new_t_int_idx1; Type: INDEX; Schema: macrostrat; Owner: postgres
--

CREATE INDEX strat_names_meta_new_t_int_idx1 ON macrostrat.strat_names_meta USING btree (t_int);


--
-- Name: strat_names_new_concept_id_idx; Type: INDEX; Schema: macrostrat; Owner: postgres
--

CREATE INDEX strat_names_new_concept_id_idx ON macrostrat.strat_names USING btree (concept_id);


--
-- Name: strat_names_new_rank_idx; Type: INDEX; Schema: macrostrat; Owner: postgres
--

CREATE INDEX strat_names_new_rank_idx ON macrostrat.strat_names USING btree (rank);


--
-- Name: strat_names_new_ref_id_idx; Type: INDEX; Schema: macrostrat; Owner: postgres
--

CREATE INDEX strat_names_new_ref_id_idx ON macrostrat.strat_names USING btree (ref_id);


--
-- Name: strat_names_new_strat_name_idx; Type: INDEX; Schema: macrostrat; Owner: postgres
--

CREATE INDEX strat_names_new_strat_name_idx ON macrostrat.strat_names USING btree (strat_name);


--
-- Name: strat_names_places_new_place_id_idx1; Type: INDEX; Schema: macrostrat; Owner: postgres
--

CREATE INDEX strat_names_places_new_place_id_idx1 ON macrostrat.strat_names_places USING btree (place_id);


--
-- Name: strat_names_places_new_strat_name_id_idx1; Type: INDEX; Schema: macrostrat; Owner: postgres
--

CREATE INDEX strat_names_places_new_strat_name_id_idx1 ON macrostrat.strat_names_places USING btree (strat_name_id);


--
-- Name: timescales_intervals_new_interval_id_idx1; Type: INDEX; Schema: macrostrat; Owner: postgres
--

CREATE INDEX timescales_intervals_new_interval_id_idx1 ON macrostrat.timescales_intervals USING btree (interval_id);


--
-- Name: timescales_intervals_new_timescale_id_idx1; Type: INDEX; Schema: macrostrat; Owner: postgres
--

CREATE INDEX timescales_intervals_new_timescale_id_idx1 ON macrostrat.timescales_intervals USING btree (timescale_id);


--
-- Name: timescales_new_ref_id_idx1; Type: INDEX; Schema: macrostrat; Owner: postgres
--

CREATE INDEX timescales_new_ref_id_idx1 ON macrostrat.timescales USING btree (ref_id);


--
-- Name: timescales_new_timescale_idx1; Type: INDEX; Schema: macrostrat; Owner: postgres
--

CREATE INDEX timescales_new_timescale_idx1 ON macrostrat.timescales USING btree (timescale);


--
-- Name: unit_econs_new_econ_id_idx1; Type: INDEX; Schema: macrostrat; Owner: postgres
--

CREATE INDEX unit_econs_new_econ_id_idx1 ON macrostrat.unit_econs USING btree (econ_id);


--
-- Name: unit_econs_new_ref_id_idx1; Type: INDEX; Schema: macrostrat; Owner: postgres
--

CREATE INDEX unit_econs_new_ref_id_idx1 ON macrostrat.unit_econs USING btree (ref_id);


--
-- Name: unit_econs_new_unit_id_idx1; Type: INDEX; Schema: macrostrat; Owner: postgres
--

CREATE INDEX unit_econs_new_unit_id_idx1 ON macrostrat.unit_econs USING btree (unit_id);


--
-- Name: unit_environs_new_environ_id_idx1; Type: INDEX; Schema: macrostrat; Owner: postgres
--

CREATE INDEX unit_environs_new_environ_id_idx1 ON macrostrat.unit_environs USING btree (environ_id);


--
-- Name: unit_environs_new_ref_id_idx1; Type: INDEX; Schema: macrostrat; Owner: postgres
--

CREATE INDEX unit_environs_new_ref_id_idx1 ON macrostrat.unit_environs USING btree (ref_id);


--
-- Name: unit_environs_new_unit_id_idx1; Type: INDEX; Schema: macrostrat; Owner: postgres
--

CREATE INDEX unit_environs_new_unit_id_idx1 ON macrostrat.unit_environs USING btree (unit_id);


--
-- Name: unit_lith_atts_new_lith_att_id_idx1; Type: INDEX; Schema: macrostrat; Owner: postgres
--

CREATE INDEX unit_lith_atts_new_lith_att_id_idx1 ON macrostrat.unit_lith_atts USING btree (lith_att_id);


--
-- Name: unit_lith_atts_new_ref_id_idx1; Type: INDEX; Schema: macrostrat; Owner: postgres
--

CREATE INDEX unit_lith_atts_new_ref_id_idx1 ON macrostrat.unit_lith_atts USING btree (ref_id);


--
-- Name: unit_lith_atts_new_unit_lith_id_idx1; Type: INDEX; Schema: macrostrat; Owner: postgres
--

CREATE INDEX unit_lith_atts_new_unit_lith_id_idx1 ON macrostrat.unit_lith_atts USING btree (unit_lith_id);


--
-- Name: unit_liths_new_lith_id_idx1; Type: INDEX; Schema: macrostrat; Owner: postgres
--

CREATE INDEX unit_liths_new_lith_id_idx1 ON macrostrat.unit_liths USING btree (lith_id);


--
-- Name: unit_liths_new_ref_id_idx1; Type: INDEX; Schema: macrostrat; Owner: postgres
--

CREATE INDEX unit_liths_new_ref_id_idx1 ON macrostrat.unit_liths USING btree (ref_id);


--
-- Name: unit_liths_new_unit_id_idx1; Type: INDEX; Schema: macrostrat; Owner: postgres
--

CREATE INDEX unit_liths_new_unit_id_idx1 ON macrostrat.unit_liths USING btree (unit_id);


--
-- Name: unit_measures_new_measuremeta_id_idx; Type: INDEX; Schema: macrostrat; Owner: postgres
--

CREATE INDEX unit_measures_new_measuremeta_id_idx ON macrostrat.unit_measures USING btree (measuremeta_id);


--
-- Name: unit_measures_new_strat_name_id_idx; Type: INDEX; Schema: macrostrat; Owner: postgres
--

CREATE INDEX unit_measures_new_strat_name_id_idx ON macrostrat.unit_measures USING btree (strat_name_id);


--
-- Name: unit_measures_new_unit_id_idx; Type: INDEX; Schema: macrostrat; Owner: postgres
--

CREATE INDEX unit_measures_new_unit_id_idx ON macrostrat.unit_measures USING btree (unit_id);


--
-- Name: unit_strat_names_new_strat_name_id_idx1; Type: INDEX; Schema: macrostrat; Owner: postgres
--

CREATE INDEX unit_strat_names_new_strat_name_id_idx1 ON macrostrat.unit_strat_names USING btree (strat_name_id);


--
-- Name: unit_strat_names_new_unit_id_idx1; Type: INDEX; Schema: macrostrat; Owner: postgres
--

CREATE INDEX unit_strat_names_new_unit_id_idx1 ON macrostrat.unit_strat_names USING btree (unit_id);


--
-- Name: units_new_col_id_idx; Type: INDEX; Schema: macrostrat; Owner: postgres
--

CREATE INDEX units_new_col_id_idx ON macrostrat.units USING btree (col_id);


--
-- Name: units_new_color_idx; Type: INDEX; Schema: macrostrat; Owner: postgres
--

CREATE INDEX units_new_color_idx ON macrostrat.units USING btree (color);


--
-- Name: units_new_section_id_idx; Type: INDEX; Schema: macrostrat; Owner: postgres
--

CREATE INDEX units_new_section_id_idx ON macrostrat.units USING btree (section_id);


--
-- Name: units_new_strat_name_idx; Type: INDEX; Schema: macrostrat; Owner: postgres
--

CREATE INDEX units_new_strat_name_idx ON macrostrat.units USING btree (strat_name);


--
-- Name: units_sections_new_col_id_idx1; Type: INDEX; Schema: macrostrat; Owner: postgres
--

CREATE INDEX units_sections_new_col_id_idx1 ON macrostrat.units_sections USING btree (col_id);


--
-- Name: units_sections_new_section_id_idx1; Type: INDEX; Schema: macrostrat; Owner: postgres
--

CREATE INDEX units_sections_new_section_id_idx1 ON macrostrat.units_sections USING btree (section_id);


--
-- Name: units_sections_new_unit_id_idx1; Type: INDEX; Schema: macrostrat; Owner: postgres
--

CREATE INDEX units_sections_new_unit_id_idx1 ON macrostrat.units_sections USING btree (unit_id);


--
-- Name: col_areas col_areas_col_id_fkey; Type: FK CONSTRAINT; Schema: macrostrat; Owner: postgres
--

ALTER TABLE ONLY macrostrat.col_areas
    ADD CONSTRAINT col_areas_col_id_fkey FOREIGN KEY (col_id) REFERENCES macrostrat.cols(id) ON DELETE CASCADE;


--
-- Name: col_refs col_refs_col_id_fkey; Type: FK CONSTRAINT; Schema: macrostrat; Owner: postgres
--

ALTER TABLE ONLY macrostrat.col_refs
    ADD CONSTRAINT col_refs_col_id_fkey FOREIGN KEY (col_id) REFERENCES macrostrat.cols(id) ON DELETE CASCADE;


--
-- Name: col_refs col_refs_ref_id_fkey; Type: FK CONSTRAINT; Schema: macrostrat; Owner: postgres
--

ALTER TABLE ONLY macrostrat.col_refs
    ADD CONSTRAINT col_refs_ref_id_fkey FOREIGN KEY (ref_id) REFERENCES macrostrat.refs(id) ON DELETE CASCADE;


--
-- Name: cols cols_col_group_id_fkey; Type: FK CONSTRAINT; Schema: macrostrat; Owner: postgres
--

ALTER TABLE ONLY macrostrat.cols
    ADD CONSTRAINT cols_col_group_id_fkey FOREIGN KEY (col_group_id) REFERENCES macrostrat.col_groups(id) ON DELETE CASCADE;


--
-- Name: concepts_places concepts_places_place_id_fkey; Type: FK CONSTRAINT; Schema: macrostrat; Owner: postgres
--

ALTER TABLE ONLY macrostrat.concepts_places
    ADD CONSTRAINT concepts_places_place_id_fkey FOREIGN KEY (place_id) REFERENCES macrostrat.places(place_id) ON DELETE CASCADE;


--
-- Name: projects projects_timescale_id_fkey; Type: FK CONSTRAINT; Schema: macrostrat; Owner: postgres
--

ALTER TABLE ONLY macrostrat.projects
    ADD CONSTRAINT projects_timescale_id_fkey FOREIGN KEY (timescale_id) REFERENCES macrostrat.timescales(id);


--
-- Name: strat_names_places strat_names_places_place_id_fkey; Type: FK CONSTRAINT; Schema: macrostrat; Owner: postgres
--

ALTER TABLE ONLY macrostrat.strat_names_places
    ADD CONSTRAINT strat_names_places_place_id_fkey FOREIGN KEY (place_id) REFERENCES macrostrat.places(place_id) ON DELETE CASCADE;


--
-- Name: strat_names_places strat_names_places_strat_name_id_fkey; Type: FK CONSTRAINT; Schema: macrostrat; Owner: postgres
--

ALTER TABLE ONLY macrostrat.strat_names_places
    ADD CONSTRAINT strat_names_places_strat_name_id_fkey FOREIGN KEY (strat_name_id) REFERENCES macrostrat.strat_names(id) ON DELETE CASCADE;


--
-- Name: timescales_intervals timescales_intervals_interval_id_fkey; Type: FK CONSTRAINT; Schema: macrostrat; Owner: postgres
--

ALTER TABLE ONLY macrostrat.timescales_intervals
    ADD CONSTRAINT timescales_intervals_interval_id_fkey FOREIGN KEY (interval_id) REFERENCES macrostrat.intervals(id) ON DELETE CASCADE;


--
-- Name: timescales_intervals timescales_intervals_timescale_id_fkey; Type: FK CONSTRAINT; Schema: macrostrat; Owner: postgres
--

ALTER TABLE ONLY macrostrat.timescales_intervals
    ADD CONSTRAINT timescales_intervals_timescale_id_fkey FOREIGN KEY (timescale_id) REFERENCES macrostrat.timescales(id) ON DELETE CASCADE;


--
-- Name: unit_econs unit_econs_econ_id_fkey; Type: FK CONSTRAINT; Schema: macrostrat; Owner: postgres
--

ALTER TABLE ONLY macrostrat.unit_econs
    ADD CONSTRAINT unit_econs_econ_id_fkey FOREIGN KEY (econ_id) REFERENCES macrostrat.econs(id) ON DELETE CASCADE;


--
-- Name: unit_econs unit_econs_ref_id_fkey; Type: FK CONSTRAINT; Schema: macrostrat; Owner: postgres
--

ALTER TABLE ONLY macrostrat.unit_econs
    ADD CONSTRAINT unit_econs_ref_id_fkey FOREIGN KEY (ref_id) REFERENCES macrostrat.refs(id) ON DELETE CASCADE;


--
-- Name: unit_econs unit_econs_unit_id_fkey; Type: FK CONSTRAINT; Schema: macrostrat; Owner: postgres
--

ALTER TABLE ONLY macrostrat.unit_econs
    ADD CONSTRAINT unit_econs_unit_id_fkey FOREIGN KEY (unit_id) REFERENCES macrostrat.units(id) ON DELETE CASCADE;


--
-- Name: unit_environs unit_environs_environ_id_fkey; Type: FK CONSTRAINT; Schema: macrostrat; Owner: postgres
--

ALTER TABLE ONLY macrostrat.unit_environs
    ADD CONSTRAINT unit_environs_environ_id_fkey FOREIGN KEY (environ_id) REFERENCES macrostrat.environs(id) ON DELETE CASCADE;


--
-- Name: unit_environs unit_environs_ref_id_fkey; Type: FK CONSTRAINT; Schema: macrostrat; Owner: postgres
--

ALTER TABLE ONLY macrostrat.unit_environs
    ADD CONSTRAINT unit_environs_ref_id_fkey FOREIGN KEY (ref_id) REFERENCES macrostrat.refs(id) ON DELETE CASCADE;


--
-- Name: unit_environs unit_environs_unit_id_fkey; Type: FK CONSTRAINT; Schema: macrostrat; Owner: postgres
--

ALTER TABLE ONLY macrostrat.unit_environs
    ADD CONSTRAINT unit_environs_unit_id_fkey FOREIGN KEY (unit_id) REFERENCES macrostrat.units(id) ON DELETE CASCADE;


--
-- Name: unit_lith_atts unit_lith_atts_lith_att_id_fkey; Type: FK CONSTRAINT; Schema: macrostrat; Owner: postgres
--

ALTER TABLE ONLY macrostrat.unit_lith_atts
    ADD CONSTRAINT unit_lith_atts_lith_att_id_fkey FOREIGN KEY (lith_att_id) REFERENCES macrostrat.lith_atts(id) ON DELETE CASCADE;


--
-- Name: unit_lith_atts unit_lith_atts_unit_lith_id_fkey; Type: FK CONSTRAINT; Schema: macrostrat; Owner: postgres
--

ALTER TABLE ONLY macrostrat.unit_lith_atts
    ADD CONSTRAINT unit_lith_atts_unit_lith_id_fkey FOREIGN KEY (unit_lith_id) REFERENCES macrostrat.unit_liths(id) ON DELETE CASCADE;


--
-- Name: unit_liths unit_liths_lith_id_fkey; Type: FK CONSTRAINT; Schema: macrostrat; Owner: postgres
--

ALTER TABLE ONLY macrostrat.unit_liths
    ADD CONSTRAINT unit_liths_lith_id_fkey FOREIGN KEY (lith_id) REFERENCES macrostrat.liths(id) ON DELETE CASCADE;


--
-- Name: unit_liths unit_liths_unit_id_fkey; Type: FK CONSTRAINT; Schema: macrostrat; Owner: postgres
--

ALTER TABLE ONLY macrostrat.unit_liths
    ADD CONSTRAINT unit_liths_unit_id_fkey FOREIGN KEY (unit_id) REFERENCES macrostrat.units(id) ON DELETE CASCADE;


--
-- Name: unit_strat_names unit_strat_names_strat_name_id_fkey; Type: FK CONSTRAINT; Schema: macrostrat; Owner: postgres
--

ALTER TABLE ONLY macrostrat.unit_strat_names
    ADD CONSTRAINT unit_strat_names_strat_name_id_fkey FOREIGN KEY (strat_name_id) REFERENCES macrostrat.strat_names(id) ON DELETE CASCADE;


--
-- Name: unit_strat_names unit_strat_names_unit_id_fkey; Type: FK CONSTRAINT; Schema: macrostrat; Owner: postgres
--

ALTER TABLE ONLY macrostrat.unit_strat_names
    ADD CONSTRAINT unit_strat_names_unit_id_fkey FOREIGN KEY (unit_id) REFERENCES macrostrat.units(id) ON DELETE CASCADE;


--
-- Name: units units_col_id_fkey; Type: FK CONSTRAINT; Schema: macrostrat; Owner: postgres
--

ALTER TABLE ONLY macrostrat.units
    ADD CONSTRAINT units_col_id_fkey FOREIGN KEY (col_id) REFERENCES macrostrat.cols(id);


--
-- PostgreSQL database dump complete
--
