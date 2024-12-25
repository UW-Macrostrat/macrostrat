-- Dumped from database version 15.3
-- Dumped by pg_dump version 15.6

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

CREATE SCHEMA carto;


CREATE SCHEMA carto_new;


CREATE SCHEMA detrital_zircon;


CREATE SCHEMA geologic_boundaries;


CREATE SCHEMA hexgrids;


CREATE SCHEMA lines;


CREATE SCHEMA macrostrat;


CREATE SCHEMA maps;


CREATE SCHEMA points;


CREATE SCHEMA sources;


CREATE SCHEMA topology;


CREATE EXTENSION IF NOT EXISTS pg_stat_statements WITH SCHEMA public;


CREATE EXTENSION IF NOT EXISTS pgaudit WITH SCHEMA public;


CREATE EXTENSION IF NOT EXISTS postgis WITH SCHEMA public;


CREATE EXTENSION IF NOT EXISTS postgis_raster WITH SCHEMA public;


CREATE EXTENSION IF NOT EXISTS postgis_topology WITH SCHEMA topology;


CREATE EXTENSION IF NOT EXISTS postgres_fdw WITH SCHEMA public;


CREATE TYPE public.measurement_class AS ENUM (
    '',
    'geophysical',
    'geochemical',
    'sedimentological'
);


CREATE TYPE public.measurement_class_new AS ENUM (
    '',
    'geophysical',
    'geochemical',
    'sedimentological'
);


CREATE TYPE public.measurement_type AS ENUM (
    '',
    'material properties',
    'geochronological',
    'major elements',
    'minor elements',
    'radiogenic isotopes',
    'stable isotopes',
    'petrologic',
    'environmental'
);


CREATE TYPE public.measurement_type_new AS ENUM (
    '',
    'material properties',
    'geochronological',
    'major elements',
    'minor elements',
    'radiogenic isotopes',
    'stable isotopes',
    'petrologic',
    'environmental'
);


CREATE FUNCTION public.count_estimate(query text) RETURNS integer
    LANGUAGE plpgsql STRICT
    AS $$
DECLARE
  rec   record;
  rows  integer;
BEGIN
  FOR rec IN EXECUTE 'EXPLAIN ' || query LOOP
    rows := substring(rec."QUERY PLAN" FROM ' rows=([[:digit:]]+)');
    EXIT WHEN rows IS NOT NULL;
  END LOOP;
  RETURN rows;
END;
$$;


CREATE AGGREGATE public.array_agg_mult(anycompatiblearray) (
    SFUNC = array_cat,
    STYPE = anycompatiblearray,
    INITCOND = '{}'
);


CREATE SERVER elevation FOREIGN DATA WRAPPER postgres_fdw OPTIONS (
    dbname 'elevation',
    host 'localhost',
    port '5432',
    use_remote_estimate 'true'
);


SET default_tablespace = '';

SET default_table_access_method = heap;

CREATE TABLE carto.flat_large (
    map_id integer,
    geom public.geometry
);


CREATE TABLE carto.flat_medium (
    map_id integer,
    geom public.geometry
);


CREATE TABLE carto.large (
    map_id integer,
    orig_id integer,
    source_id integer,
    scale text,
    name text,
    strat_name text,
    age text,
    lith text,
    descrip text,
    comments text,
    t_int_id integer,
    t_int text,
    best_age_top numeric,
    b_int_id integer,
    b_int text,
    best_age_bottom numeric,
    color text,
    unit_ids integer[],
    strat_name_ids integer[],
    lith_ids integer[],
    geom public.geometry
);


CREATE TABLE carto.lines_large (
    line_id integer,
    scale text,
    source_id integer,
    name text,
    type text,
    direction text,
    descrip text,
    geom public.geometry
);


CREATE TABLE carto.lines_medium (
    line_id integer,
    scale text,
    source_id integer,
    name text,
    type text,
    direction text,
    descrip text,
    geom public.geometry
);


CREATE TABLE carto.lines_small (
    line_id integer,
    scale text,
    source_id integer,
    name text,
    type text,
    direction text,
    descrip text,
    geom public.geometry
);


CREATE TABLE carto.lines_tiny (
    line_id integer,
    geom public.geometry(Geometry,4326),
    scale text,
    source_id integer,
    name character varying,
    type character varying,
    direction character varying,
    descrip text
);


CREATE TABLE carto.medium (
    map_id integer,
    orig_id integer,
    source_id integer,
    scale text,
    name text,
    strat_name text,
    age text,
    lith text,
    descrip text,
    comments text,
    t_int_id integer,
    t_int text,
    best_age_top numeric,
    b_int_id integer,
    b_int text,
    best_age_bottom numeric,
    color text,
    unit_ids integer[],
    strat_name_ids integer[],
    lith_ids integer[],
    geom public.geometry
);


CREATE TABLE carto.small (
    map_id integer,
    orig_id integer,
    source_id integer,
    scale text,
    name text,
    strat_name text,
    age text,
    lith text,
    descrip text,
    comments text,
    t_int_id integer,
    t_int text,
    best_age_top numeric,
    b_int_id integer,
    b_int text,
    best_age_bottom numeric,
    color text,
    unit_ids integer[],
    strat_name_ids integer[],
    lith_ids integer[],
    geom public.geometry
);


CREATE TABLE carto.tiny (
    map_id integer,
    orig_id integer,
    source_id integer,
    scale text,
    name text,
    strat_name text,
    age character varying,
    lith text,
    descrip text,
    comments text,
    t_int_id integer,
    t_int character varying(200),
    best_age_top numeric,
    b_int_id integer,
    b_int character varying(200),
    best_age_bottom numeric,
    color character varying(20),
    unit_ids integer[],
    strat_name_ids integer[],
    lith_ids integer[],
    geom public.geometry
);


CREATE TABLE carto_new.hex_index (
    map_id integer NOT NULL,
    scale text,
    hex_id integer
);


CREATE TABLE carto_new.large (
    map_id integer,
    source_id integer,
    scale text,
    geom public.geometry
);


CREATE TABLE carto_new.lines_large (
    line_id integer,
    source_id integer,
    scale text,
    geom public.geometry
);


CREATE TABLE carto_new.lines_medium (
    line_id integer,
    source_id integer,
    scale text,
    geom public.geometry
);


CREATE TABLE carto_new.lines_small (
    line_id integer,
    source_id integer,
    scale text,
    geom public.geometry
);


CREATE TABLE carto_new.lines_tiny (
    line_id integer,
    source_id integer,
    scale text,
    geom public.geometry(Geometry,4326)
);


CREATE TABLE carto_new.medium (
    map_id integer,
    source_id integer,
    scale text,
    geom public.geometry
);


CREATE TABLE carto_new.pbdb_hex_index (
    collection_no integer NOT NULL,
    scale text,
    hex_id integer
);


CREATE TABLE carto_new.small (
    map_id integer,
    source_id integer,
    scale text,
    geom public.geometry
);


CREATE TABLE carto_new.tiny (
    map_id integer,
    source_id integer,
    scale text,
    geom public.geometry
);


CREATE TABLE detrital_zircon.located_query_bounds (
    id integer NOT NULL,
    geometry public.geometry(MultiPolygon,4326) NOT NULL,
    name text,
    notes text
);


CREATE SEQUENCE detrital_zircon.located_query_bounds_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE detrital_zircon.located_query_bounds_id_seq OWNED BY detrital_zircon.located_query_bounds.id;


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


CREATE SEQUENCE public.geologic_boundary_source_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


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


CREATE TABLE hexgrids.bedrock_index (
    legend_id integer NOT NULL,
    hex_id integer NOT NULL,
    coverage numeric
);


CREATE TABLE hexgrids.hexgrids (
    hex_id integer NOT NULL,
    res integer,
    geom public.geometry
);


CREATE TABLE hexgrids.pbdb_index (
    collection_no integer NOT NULL,
    hex_id integer NOT NULL
);


CREATE TABLE hexgrids.r10 (
    hex_id integer NOT NULL,
    geom public.geometry(MultiPolygon,4326),
    web_geom public.geometry
);


CREATE SEQUENCE hexgrids.r10_ogc_fid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE hexgrids.r10_ogc_fid_seq OWNED BY hexgrids.r10.hex_id;


CREATE TABLE hexgrids.r11 (
    hex_id integer NOT NULL,
    geom public.geometry(MultiPolygon,4326),
    web_geom public.geometry
);


CREATE SEQUENCE hexgrids.r11_ogc_fid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE hexgrids.r11_ogc_fid_seq OWNED BY hexgrids.r11.hex_id;


CREATE TABLE hexgrids.r12 (
    hex_id integer NOT NULL,
    geom public.geometry(MultiPolygon,4326),
    web_geom public.geometry
);


CREATE SEQUENCE hexgrids.r12_ogc_fid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE hexgrids.r12_ogc_fid_seq OWNED BY hexgrids.r12.hex_id;


CREATE TABLE hexgrids.r5 (
    hex_id integer NOT NULL,
    geom public.geometry(MultiPolygon,4326),
    web_geom public.geometry
);


CREATE SEQUENCE hexgrids.r5_ogc_fid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE hexgrids.r5_ogc_fid_seq OWNED BY hexgrids.r5.hex_id;


CREATE TABLE hexgrids.r6 (
    hex_id integer NOT NULL,
    geom public.geometry(MultiPolygon,4326),
    web_geom public.geometry
);


CREATE SEQUENCE hexgrids.r6_ogc_fid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE hexgrids.r6_ogc_fid_seq OWNED BY hexgrids.r6.hex_id;


CREATE TABLE hexgrids.r7 (
    hex_id integer NOT NULL,
    geom public.geometry(MultiPolygon,4326),
    web_geom public.geometry
);


CREATE SEQUENCE hexgrids.r7_ogc_fid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE hexgrids.r7_ogc_fid_seq OWNED BY hexgrids.r7.hex_id;


CREATE TABLE hexgrids.r8 (
    hex_id integer NOT NULL,
    geom public.geometry(MultiPolygon,4326),
    web_geom public.geometry
);


CREATE SEQUENCE hexgrids.r8_ogc_fid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE hexgrids.r8_ogc_fid_seq OWNED BY hexgrids.r8.hex_id;


CREATE TABLE hexgrids.r9 (
    hex_id integer NOT NULL,
    geom public.geometry(MultiPolygon,4326),
    web_geom public.geometry
);


CREATE SEQUENCE hexgrids.r9_ogc_fid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE hexgrids.r9_ogc_fid_seq OWNED BY hexgrids.r9.hex_id;


CREATE SEQUENCE public.line_ids
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


CREATE TABLE lines.large (
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


CREATE TABLE lines.medium (
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


CREATE TABLE lines.small (
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


CREATE TABLE lines.tiny (
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


CREATE TABLE macrostrat.autocomplete (
    id integer NOT NULL,
    name text,
    type text,
    category text
);


CREATE TABLE macrostrat.col_areas (
    id integer NOT NULL,
    col_id integer,
    col_area public.geometry,
    wkt text
);


CREATE TABLE macrostrat.col_groups (
    id integer NOT NULL,
    col_group character varying(100),
    col_group_long character varying(100)
);


CREATE TABLE macrostrat.col_refs (
    id integer NOT NULL,
    col_id integer,
    ref_id integer
);


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
    coordinate public.geometry,
    wkt text,
    created text,
    poly_geom public.geometry
);


CREATE TABLE macrostrat.concepts_places (
    concept_id integer NOT NULL,
    place_id integer NOT NULL
);


CREATE TABLE macrostrat.econs (
    id integer NOT NULL,
    econ text,
    econ_type text,
    econ_class text,
    econ_color text
);


CREATE TABLE macrostrat.environs (
    id integer NOT NULL,
    environ text,
    environ_type text,
    environ_class text,
    environ_color text
);


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


CREATE SEQUENCE macrostrat.intervals_new_id_seq1
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE macrostrat.intervals_new_id_seq1 OWNED BY macrostrat.intervals.id;


CREATE TABLE macrostrat.lith_atts (
    id integer NOT NULL,
    lith_att character varying(75),
    att_type character varying(25),
    lith_att_fill integer
);


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


CREATE TABLE macrostrat.lookup_unit_attrs_api (
    unit_id integer,
    lith json,
    environ json,
    econ json,
    measure_short json,
    measure_long json
);


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


CREATE TABLE macrostrat.measurements (
    id integer NOT NULL,
    measurement_class public.measurement_class NOT NULL,
    measurement_type public.measurement_type NOT NULL,
    measurement text NOT NULL
);


CREATE SEQUENCE macrostrat.measurements_new_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE macrostrat.measurements_new_id_seq OWNED BY macrostrat.measurements.id;


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


CREATE SEQUENCE macrostrat.measuremeta_new_id_seq1
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE macrostrat.measuremeta_new_id_seq1 OWNED BY macrostrat.measuremeta.id;


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


CREATE SEQUENCE macrostrat.measures_new_id_seq1
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE macrostrat.measures_new_id_seq1 OWNED BY macrostrat.measures.id;


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
    geom public.geometry
);


CREATE TABLE macrostrat.pbdb_collections_strat_names (
    collection_no integer NOT NULL,
    strat_name_id integer NOT NULL,
    basis_col text
);


CREATE TABLE macrostrat.places (
    place_id integer NOT NULL,
    name text,
    abbrev text,
    postal text,
    country text,
    country_abbrev text,
    geom public.geometry
);


CREATE TABLE macrostrat.refs (
    id integer NOT NULL,
    pub_year integer,
    author character varying(255),
    ref text,
    doi character varying(40),
    compilation_code character varying(100),
    url text,
    rgeom public.geometry
);


CREATE TABLE macrostrat.strat_name_footprints (
    strat_name_id integer,
    name_no_lith character varying(100),
    rank_name character varying(200),
    concept_id integer,
    concept_names integer[],
    geom public.geometry,
    best_t_age numeric,
    best_b_age numeric
);


CREATE TABLE macrostrat.strat_names (
    id integer NOT NULL,
    strat_name character varying(100) NOT NULL,
    rank character varying(50),
    ref_id integer NOT NULL,
    concept_id integer
);


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


CREATE SEQUENCE macrostrat.strat_names_new_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE macrostrat.strat_names_new_id_seq OWNED BY macrostrat.strat_names.id;


CREATE TABLE macrostrat.strat_names_places (
    strat_name_id integer NOT NULL,
    place_id integer NOT NULL
);


CREATE TABLE macrostrat.timescales (
    id integer NOT NULL,
    timescale character varying(100),
    ref_id integer
);


CREATE TABLE macrostrat.timescales_intervals (
    timescale_id integer,
    interval_id integer
);


CREATE TABLE macrostrat.unit_econs (
    id integer NOT NULL,
    unit_id integer,
    econ_id integer,
    ref_id integer,
    date_mod text
);


CREATE TABLE macrostrat.unit_environs (
    id integer NOT NULL,
    unit_id integer,
    environ_id integer,
    ref_id integer,
    date_mod text
);


CREATE TABLE macrostrat.unit_lith_atts (
    id integer NOT NULL,
    unit_lith_id integer,
    lith_att_id integer,
    ref_id integer,
    date_mod text
);


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


CREATE TABLE macrostrat.unit_measures (
    id integer NOT NULL,
    measuremeta_id integer NOT NULL,
    unit_id integer NOT NULL,
    strat_name_id integer NOT NULL,
    match_basis character varying(10) NOT NULL,
    rel_position numeric(6,5)
);


CREATE SEQUENCE macrostrat.unit_measures_new_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE macrostrat.unit_measures_new_id_seq OWNED BY macrostrat.unit_measures.id;


CREATE TABLE macrostrat.unit_strat_names (
    id integer NOT NULL,
    unit_id integer NOT NULL,
    strat_name_id integer NOT NULL
);


CREATE SEQUENCE macrostrat.unit_strat_names_new_id_seq1
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE macrostrat.unit_strat_names_new_id_seq1 OWNED BY macrostrat.unit_strat_names.id;


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


CREATE TABLE macrostrat.units_sections (
    id integer NOT NULL,
    unit_id integer NOT NULL,
    section_id integer NOT NULL,
    col_id integer NOT NULL
);


CREATE SEQUENCE macrostrat.units_sections_new_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE macrostrat.units_sections_new_id_seq OWNED BY macrostrat.units_sections.id;


CREATE SEQUENCE public.map_ids
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


CREATE TABLE maps.large (
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


CREATE TABLE maps.legend (
    legend_id integer NOT NULL,
    source_id integer NOT NULL,
    name text,
    strat_name text,
    age text,
    lith text,
    descrip text,
    comments text,
    b_interval integer,
    t_interval integer,
    best_age_bottom numeric,
    best_age_top numeric,
    color text,
    unit_ids integer[],
    concept_ids integer[],
    strat_name_ids integer[],
    strat_name_children integer[],
    lith_ids integer[],
    lith_types text[],
    lith_classes text[],
    all_lith_ids integer[],
    all_lith_types text[],
    all_lith_classes text[],
    area numeric,
    tiny_area numeric,
    small_area numeric,
    medium_area numeric,
    large_area numeric
);


CREATE SEQUENCE maps.legend_legend_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE maps.legend_legend_id_seq OWNED BY maps.legend.legend_id;


CREATE TABLE maps.legend_liths (
    legend_id integer NOT NULL,
    lith_id integer NOT NULL,
    basis_col text NOT NULL
);


CREATE TABLE maps.manual_matches (
    match_id integer NOT NULL,
    map_id integer NOT NULL,
    strat_name_id integer,
    unit_id integer,
    addition boolean DEFAULT false,
    removal boolean DEFAULT false,
    type character varying(20)
);


CREATE SEQUENCE maps.manual_matches_match_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE maps.manual_matches_match_id_seq OWNED BY maps.manual_matches.match_id;


CREATE TABLE maps.map_legend (
    legend_id integer NOT NULL,
    map_id integer NOT NULL
);


CREATE TABLE maps.map_liths (
    map_id integer NOT NULL,
    lith_id integer NOT NULL,
    basis_col character varying(50)
);


CREATE TABLE maps.map_strat_names (
    map_id integer NOT NULL,
    strat_name_id integer NOT NULL,
    basis_col character varying(50)
);


CREATE TABLE maps.map_units (
    map_id integer NOT NULL,
    unit_id integer NOT NULL,
    basis_col character varying(50)
);


CREATE TABLE maps.medium (
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


CREATE TABLE maps.small (
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


CREATE TABLE maps.sources (
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
    display_scales text[],
    web_geom public.geometry,
    new_priority integer DEFAULT 0,
    status_code text DEFAULT 'active'::text
);


CREATE SEQUENCE maps.sources_source_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE maps.sources_source_id_seq OWNED BY maps.sources.source_id;


CREATE TABLE maps.tiny (
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


CREATE TABLE points.points (
    source_id integer NOT NULL,
    strike integer,
    dip integer,
    dip_dir integer,
    point_type character varying(100),
    certainty character varying(100),
    comments text,
    geom public.geometry(Geometry,4326),
    point_id integer NOT NULL,
    orig_id integer,
    CONSTRAINT dip_lt_90 CHECK ((dip <= 90)),
    CONSTRAINT dip_positive CHECK ((dip >= 0)),
    CONSTRAINT direction_lt_360 CHECK ((dip_dir <= 360)),
    CONSTRAINT direction_positive CHECK ((dip_dir >= 0)),
    CONSTRAINT enforce_point_geom CHECK (public.st_isvalid(geom)),
    CONSTRAINT strike_lt_360 CHECK ((strike <= 360)),
    CONSTRAINT strike_positive CHECK ((strike >= 0))
);


CREATE SEQUENCE points.points_point_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE points.points_point_id_seq OWNED BY points.points.point_id;


CREATE TABLE public.agebzepllj (
    id integer,
    geom public.geometry
);


CREATE TABLE public.aofhmuuyjq (
    id integer,
    geom public.geometry
);


CREATE TABLE public.bmbtwjmdgn (
    id integer,
    geom public.geometry
);


CREATE TABLE public.emma5k5jzl (
    id integer,
    geom public.geometry
);


CREATE TABLE public.i9kzotjhgr (
    id integer,
    geom public.geometry
);


CREATE TABLE public.impervious (
    rid integer NOT NULL,
    rast public.raster
);


CREATE SEQUENCE public.impervious_rid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.impervious_rid_seq OWNED BY public.impervious.rid;


CREATE TABLE public.land (
    gid integer NOT NULL,
    scalerank numeric(10,0),
    featurecla character varying(32),
    geom public.geometry(MultiPolygon,4326)
);


CREATE SEQUENCE public.land_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.land_gid_seq OWNED BY public.land.gid;


CREATE TABLE public.lookup_large (
    map_id integer,
    unit_ids integer[],
    strat_name_ids integer[],
    lith_ids integer[],
    best_age_top numeric,
    best_age_bottom numeric,
    color character varying(20),
    lith_types text[],
    lith_classes text[],
    concept_ids integer[],
    strat_name_children integer[],
    legend_id integer
);


CREATE TABLE public.lookup_medium (
    map_id integer,
    unit_ids integer[],
    strat_name_ids integer[],
    lith_ids integer[],
    best_age_top numeric,
    best_age_bottom numeric,
    color character varying(20),
    lith_types text[],
    lith_classes text[],
    concept_ids integer[],
    strat_name_children integer[],
    legend_id integer
);


CREATE TABLE public.lookup_small (
    map_id integer,
    unit_ids integer[],
    strat_name_ids integer[],
    lith_ids integer[],
    best_age_top numeric,
    best_age_bottom numeric,
    color character varying(20),
    lith_types text[],
    lith_classes text[],
    concept_ids integer[],
    strat_name_children integer[],
    legend_id integer
);


CREATE TABLE public.lookup_tiny (
    map_id integer,
    unit_ids integer[],
    strat_name_ids integer[],
    lith_ids integer[],
    best_age_top numeric,
    best_age_bottom numeric,
    color character varying(20),
    lith_types text[],
    lith_classes text[],
    concept_ids integer[],
    strat_name_children integer[],
    legend_id integer
);


CREATE TABLE public.macrostrat_union (
    id integer NOT NULL,
    geom public.geometry
);


CREATE SEQUENCE public.macrostrat_union_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.macrostrat_union_id_seq OWNED BY public.macrostrat_union.id;


CREATE TABLE public.npb9s0ubia (
    id integer,
    geom public.geometry
);


CREATE TABLE public.ref_boundaries (
    ref_id integer,
    ref text,
    geom public.geometry
);


CREATE FOREIGN TABLE public.srtm1 (
    rid integer,
    rast public.raster
)
SERVER elevation
OPTIONS (
    schema_name 'sources',
    table_name 'srtm1'
);


CREATE TABLE public.temp_containers (
    geom public.geometry,
    row_no bigint
);


CREATE TABLE public.temp_names (
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


CREATE TABLE public.temp_rings (
    geom public.geometry,
    row_no bigint
);


CREATE TABLE public.temp_rocks (
    map_ids integer[],
    name text,
    orig_strat_name text[],
    strat_name text,
    strat_name_clean text,
    age character varying(255),
    lith text,
    descrip text,
    comments text,
    t_interval integer,
    b_interval integer,
    envelope public.geometry
);


CREATE TABLE public.test_rgeom (
    gid integer NOT NULL,
    fid smallint,
    geom public.geometry(MultiPolygon,4326)
);


CREATE SEQUENCE public.test_rgeom_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.test_rgeom_gid_seq OWNED BY public.test_rgeom.gid;


CREATE TABLE public.units (
    mapunit text,
    description text
);


CREATE TABLE public.zphuctzzhp (
    id integer,
    geom public.geometry
);


CREATE TABLE sources.ab_spray (
    gid integer NOT NULL,
    map_theme character varying(50),
    feature character varying(50),
    map_unit character varying(100),
    parents character varying(254),
    max_age character varying(50),
    min_age character varying(50),
    lith_list character varying(100),
    genesis character varying(100),
    remarks character varying(254),
    label character varying(30),
    reference character varying(254),
    source_ref character varying(254),
    map_id character varying(254),
    symbol character varying(100),
    shape_leng numeric,
    shape_area numeric,
    geom public.geometry(MultiPolygon,4326),
    early_id integer,
    late_id integer,
    use_age text,
    strat_name text,
    hierarchy text,
    descrip text
);


CREATE SEQUENCE sources.ab_spray_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.ab_spray_gid_seq OWNED BY sources.ab_spray.gid;


CREATE TABLE sources.ab_spray_lines (
    gid integer NOT NULL,
    map_theme character varying(50),
    feature character varying(75),
    subfeature character varying(50),
    attitude character varying(50),
    confidence character varying(15),
    generation character varying(25),
    max_age character varying(50),
    min_age character varying(50),
    name character varying(254),
    properties character varying(254),
    movement character varying(254),
    hwall_dir character varying(254),
    remarks character varying(254),
    reference character varying(254),
    source_ref character varying(254),
    map_id character varying(254),
    symbol character varying(100),
    shape_leng numeric,
    geom public.geometry(MultiLineString,4326),
    new_type text,
    descrip text
);


CREATE SEQUENCE sources.ab_spray_lines_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.ab_spray_lines_gid_seq OWNED BY sources.ab_spray_lines.gid;


CREATE TABLE sources.ab_spray_points (
    gid integer NOT NULL,
    map_theme character varying(50),
    feature character varying(50),
    planar_id character varying(50),
    subfeature character varying(50),
    fab_elem character varying(254),
    attitude character varying(50),
    young_evid character varying(50),
    generation character varying(50),
    method character varying(50),
    dip_dir integer,
    strike integer,
    dip integer,
    strain character varying(50),
    flattening character varying(50),
    lith_id character varying(50),
    station_id character varying(50),
    linear_id character varying(100),
    planar_id2 character varying(100),
    remarks character varying(254),
    reference character varying(254),
    source_ref character varying(254),
    map_id character varying(254),
    symbol character varying(100),
    geom public.geometry(Point,4326),
    point_type text
);


CREATE SEQUENCE sources.ab_spray_points_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.ab_spray_points_gid_seq OWNED BY sources.ab_spray_points.gid;


CREATE TABLE sources.ab_stimson (
    gid integer NOT NULL,
    map_theme character varying(50),
    feature character varying(50),
    map_unit character varying(100),
    parents character varying(254),
    max_age character varying(50),
    min_age character varying(50),
    lith_list character varying(100),
    genesis character varying(100),
    remarks character varying(254),
    label character varying(30),
    reference character varying(254),
    source_ref character varying(254),
    map_id character varying(254),
    symbol character varying(100),
    shape_leng numeric,
    shape_area numeric,
    geom public.geometry(MultiPolygon,4326),
    early_id integer,
    late_id integer,
    use_age text,
    strat_name text,
    hierarchy text,
    descrip text
);


CREATE SEQUENCE sources.ab_stimson_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.ab_stimson_gid_seq OWNED BY sources.ab_stimson.gid;


CREATE TABLE sources.ab_stimson_lines (
    gid integer NOT NULL,
    map_theme character varying(50),
    feature character varying(50),
    subfeature character varying(50),
    attitude character varying(50),
    confidence character varying(15),
    generation character varying(25),
    max_age character varying(50),
    min_age character varying(50),
    name character varying(254),
    properties character varying(254),
    movement character varying(254),
    hwall_dir character varying(254),
    remarks character varying(254),
    reference character varying(254),
    source_ref character varying(254),
    map_id character varying(254),
    pub_scale numeric,
    include_hc character varying(5),
    symbol character varying(100),
    shape_leng numeric,
    geom public.geometry(MultiLineString,4326),
    new_type text,
    descrip text
);


CREATE SEQUENCE sources.ab_stimson_lines_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.ab_stimson_lines_gid_seq OWNED BY sources.ab_stimson_lines.gid;


CREATE TABLE sources.ab_stimson_points (
    gid integer NOT NULL,
    map_theme character varying(50),
    feature character varying(50),
    planar_id character varying(50),
    subfeature character varying(50),
    fab_elem character varying(254),
    attitude character varying(50),
    young_evid character varying(50),
    generation character varying(50),
    method character varying(50),
    dip_dir integer,
    strike integer,
    dip integer,
    strain character varying(50),
    flattening character varying(50),
    lith_id character varying(50),
    station_id character varying(50),
    linear_id character varying(100),
    planar_id2 character varying(100),
    remarks character varying(254),
    reference character varying(254),
    source_ref character varying(254),
    map_id character varying(254),
    symbol character varying(100),
    geom public.geometry(Point,4326),
    trend integer,
    plunge text,
    point_type text
);


CREATE SEQUENCE sources.ab_stimson_points_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.ab_stimson_points_gid_seq OWNED BY sources.ab_stimson_points.gid;


CREATE TABLE sources.afghan (
    gid integer NOT NULL,
    number character varying(8),
    time_end character varying(8),
    time_begin character varying(10),
    time_name character varying(40),
    unit_symbo character varying(13),
    lithology character varying(30),
    narrative text,
    gen_age character varying(8),
    index integer,
    symbol_gen character varying(10),
    geom public.geometry(MultiPolygon,4326),
    early_id integer,
    late_id integer
);


CREATE SEQUENCE sources.afghan_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.afghan_gid_seq OWNED BY sources.afghan.gid;


CREATE TABLE sources.afghan_lines (
    gid integer NOT NULL,
    id integer,
    length double precision,
    type character varying(25),
    line_type integer,
    geom public.geometry(MultiLineString,4326),
    new_type character varying(100)
);


CREATE SEQUENCE sources.afghan_lines_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.afghan_lines_gid_seq OWNED BY sources.afghan_lines.gid;


CREATE TABLE sources.africa (
    gid integer NOT NULL,
    code character varying(254),
    code_leg character varying(254),
    strati character varying(254),
    age character varying(254),
    notation character varying(254),
    litho character varying(254),
    geom public.geometry(MultiPolygon,4326),
    early_id integer,
    late_id integer
);


CREATE SEQUENCE sources.africa_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.africa_gid_seq OWNED BY sources.africa.gid;


CREATE TABLE sources.africa_lines (
    gid integer NOT NULL,
    code character varying(254),
    descr character varying(254),
    geom public.geometry(MultiLineString,4326),
    new_type text
);


CREATE TABLE sources.ak (
    gid integer NOT NULL,
    class numeric(10,0),
    qclass numeric(10,0),
    source character varying(8),
    nsaclass numeric(10,0),
    nsasub numeric(10,0),
    nsamod character varying(10),
    sourceclas character varying(15),
    state_symb numeric(10,0),
    state_labe character varying(10),
    state_la_1 character varying(10),
    state_unit character varying(254),
    age_range character varying(254),
    sequence character varying(50),
    shape_leng numeric,
    shape_area numeric,
    geom public.geometry(MultiPolygon,4326),
    descrip text,
    fossils text,
    early_id integer,
    late_id integer,
    age2 character varying(100),
    lith character varying(100),
    u_name character varying(255)
);


CREATE SEQUENCE sources.ak_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.ak_gid_seq OWNED BY sources.ak.gid;


CREATE TABLE sources.ak_lines (
    gid integer NOT NULL,
    arc_code integer,
    arc_para1 integer,
    source character varying(50),
    lineid character varying(50),
    left_label character varying(10),
    right_labe character varying(10),
    line_type character varying(100),
    shape_leng numeric,
    geom public.geometry(MultiLineString,4326),
    type character varying(100),
    direct character varying(100)
);


CREATE SEQUENCE sources.ak_lines_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.ak_lines_gid_seq OWNED BY sources.ak_lines.gid;


CREATE TABLE sources.al_greenwood (
    gid integer NOT NULL,
    shape_leng numeric,
    shape_area numeric,
    mapunit character varying(10),
    unit character varying(100),
    age character varying(254),
    geom public.geometry(MultiPolygon,4326),
    description text,
    early_id integer,
    late_id integer,
    name text,
    strat_name text,
    hierarchy text
);


CREATE TABLE sources.al_greenwood_lines (
    gid integer NOT NULL,
    linetype text,
    name text,
    shape_leng numeric,
    geom public.geometry(MultiLineString,4326),
    new_type text
);


CREATE TABLE sources.al_greenwood_points (
    gid integer NOT NULL,
    pointtype character varying(50),
    strike smallint,
    dip smallint,
    geom public.geometry(Point,4326),
    point_type text,
    dip_dir integer
);


CREATE TABLE sources.ca_alameda_lines (
    gid integer NOT NULL,
    fnode_ numeric(10,0),
    tnode_ numeric(10,0),
    lpoly_ numeric(10,0),
    rpoly_ numeric(10,0),
    length double precision,
    al_um_flt0 numeric(10,0),
    al_um_fl_1 numeric(10,0),
    ltype character varying(55),
    sel smallint,
    symb smallint,
    geom public.geometry(MultiLineString,4326),
    fname text,
    new_type text,
    new_direction text
);


CREATE SEQUENCE sources.alam_fault_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.alam_fault_gid_seq OWNED BY sources.ca_alameda_lines.gid;


CREATE TABLE sources.ca_alameda (
    gid integer NOT NULL,
    __gid numeric(10,0),
    area numeric,
    perimeter numeric,
    al_um_py0_ numeric(10,0),
    al_um_py01 numeric(10,0),
    ptype character varying(35),
    name character varying(254),
    age character varying(254),
    description text,
    assemblage character varying(254),
    early_id numeric(10,0),
    late_id numeric(10,0),
    geom public.geometry(MultiPolygon,4326)
);


CREATE SEQUENCE sources.alamedageology2_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.alamedageology2_gid_seq OWNED BY sources.ca_alameda.gid;


CREATE TABLE sources.endikai_lines (
    gid integer NOT NULL,
    objectid integer,
    linetype character varying(50),
    linecode character varying(50),
    shape_leng numeric,
    geom public.geometry(MultiLineString,4326),
    new_type text,
    new_direction text,
    name text,
    maptype text
);


CREATE SEQUENCE sources.albanel_lines_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.albanel_lines_gid_seq OWNED BY sources.endikai_lines.gid;


CREATE TABLE sources.alberta (
    gid integer NOT NULL,
    rgb character varying(20),
    colorgroup character varying(50),
    unit_name character varying(100),
    lithology character varying(50),
    environ character varying(100),
    age character varying(50),
    geolregion character varying(50),
    geom public.geometry(MultiPolygon,4326),
    early_id integer,
    late_id integer
);


CREATE TABLE sources.alberta_faults (
    gid integer NOT NULL,
    type character varying(30),
    geom public.geometry(MultiLineString,4326)
);


CREATE SEQUENCE sources.alberta_faults_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.alberta_faults_gid_seq OWNED BY sources.alberta_faults.gid;


CREATE SEQUENCE sources.alberta_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.alberta_gid_seq OWNED BY sources.alberta.gid;


CREATE TABLE sources.ar_buffalo_nriver (
    gid integer NOT NULL,
    unit character varying(10),
    descriptio character varying(150),
    age character varying(150),
    shape_leng numeric,
    shape_area numeric,
    geom public.geometry(MultiPolygon,4326),
    descrip text,
    early_id integer,
    late_id integer,
    strat_name text
);


CREATE SEQUENCE sources.ar_buffalo_nriver_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.ar_buffalo_nriver_gid_seq OWNED BY sources.ar_buffalo_nriver.gid;


CREATE TABLE sources.ar_buffalo_nriver_lines (
    gid integer NOT NULL,
    descriptio character varying(150),
    fault_name character varying(200),
    shape_leng numeric,
    geom public.geometry(MultiLineString,4326),
    new_type text,
    new_direction text
);


CREATE SEQUENCE sources.ar_buffalo_nriver_lines_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.ar_buffalo_nriver_lines_gid_seq OWNED BY sources.ar_buffalo_nriver_lines.gid;


CREATE TABLE sources.ar_hasty (
    gid integer NOT NULL,
    area numeric,
    perimeter numeric,
    hast24k_ integer,
    hast24k_id integer,
    geol character varying(25),
    label character varying(25),
    name character varying(100),
    geom public.geometry(MultiPolygon,4326),
    age text,
    description text,
    comments text,
    early_id integer,
    late_id integer,
    strat_name text,
    hierarchy text
);


CREATE TABLE sources.ar_hasty_lines (
    gid integer NOT NULL,
    length double precision,
    symbol integer,
    descriptio character varying(100),
    elevation integer,
    geom public.geometry(MultiLineString,4326),
    new_type text,
    new_direction text
);


CREATE TABLE sources.ar_hasty_points (
    gid integer NOT NULL,
    area double precision,
    perimeter double precision,
    hastpnt_ integer,
    hastpnt_id integer,
    symbol integer,
    azimuth integer,
    dip0 integer,
    descriptio character varying(100),
    fdipaz integer,
    fdip integer,
    rakeaz integer,
    rakeangle integer,
    geom public.geometry(Point,4326),
    point_type text,
    strike integer,
    dip integer,
    dip_dir integer,
    comments text,
    certainty text
);


CREATE TABLE sources.ar_hotsprings_np (
    gid integer NOT NULL,
    objectid numeric(10,0),
    fuid numeric(10,0),
    glg_sym character varying(12),
    src_sym character varying(12),
    sort_no numeric,
    notes character varying(254),
    lbl character varying(60),
    gmap_id numeric(10,0),
    "shape leng" numeric,
    shape_area numeric,
    objectid_1 integer,
    glg_sym_1 character varying(12),
    glg_name character varying(100),
    age character varying(100),
    mj_lith character varying(254),
    geom public.geometry(MultiPolygon,4326),
    description text,
    early_id integer,
    late_id integer,
    strat_name text
);


CREATE TABLE sources.ar_hotsprings_np_lines (
    gid integer NOT NULL,
    objectid numeric(10,0),
    fuid numeric(10,0),
    ftype integer,
    fsubtype integer,
    fname character varying(60),
    notes character varying(254),
    lbl character varying(60),
    gmap_id numeric(10,0),
    shape_leng numeric,
    pos character varying(254),
    subtype character varying(254),
    type character varying(254),
    geom public.geometry(MultiLineString,4326),
    age text,
    src_sym text,
    glg_sym text,
    plunge text,
    _plunge text,
    new_type text,
    new_direction text
);


CREATE TABLE sources.ar_hotsprings_np_points (
    gid integer NOT NULL,
    objectid numeric(10,0),
    fuid numeric(10,0),
    ftype integer,
    fsubtype integer,
    pos integer,
    st integer,
    dp integer,
    notes character varying(254),
    am_rot integer,
    lbl character varying(60),
    gmap_id numeric(10,0),
    type character varying(254),
    subtype character varying(254),
    accuracy character varying(254),
    sourcemap character varying(254),
    geom public.geometry(Point,4326),
    strike integer,
    dip integer,
    point_type text,
    dip_dir integer
);


CREATE TABLE sources.ar_jasper (
    gid integer NOT NULL,
    area numeric,
    perimeter numeric,
    jsp24k_ double precision,
    jsp24k_id double precision,
    geology character varying(10),
    color smallint,
    hatch numeric(10,0),
    specgeo character varying(10),
    geom public.geometry(MultiPolygon,4326),
    name text,
    age text,
    description text,
    early_id integer,
    late_id integer
);


CREATE TABLE sources.ar_jasper_lines (
    gid integer NOT NULL,
    fnode_ double precision,
    tnode_ double precision,
    lpoly_ double precision,
    rpoly_ double precision,
    length numeric,
    jsp24k_ double precision,
    jsp24k_id double precision,
    descriptio character varying(25),
    linecode integer,
    geom public.geometry(MultiLineString,4326),
    new_type text,
    new_direction text
);


CREATE TABLE sources.ar_ponca (
    gid integer NOT NULL,
    area numeric,
    perimeter numeric,
    ponc24k_ double precision,
    ponc24k_id double precision,
    unit character varying(10),
    label character varying(10),
    name character varying(100),
    cyan smallint,
    magenta smallint,
    yellow smallint,
    black smallint,
    geom public.geometry(MultiPolygon,4326),
    description text,
    age text,
    early_id integer,
    late_id integer
);


CREATE TABLE sources.ar_ponca_lines (
    gid integer NOT NULL,
    symbol integer,
    description character varying(100),
    symset character varying(10),
    name character varying(100),
    geom public.geometry(MultiLineString,4326),
    new_type text,
    new_direction text
);


CREATE TABLE sources.arctic (
    gid integer NOT NULL,
    objectid integer,
    shape_leng numeric,
    shape_area numeric,
    map_label character varying(10),
    age_code character varying(4),
    age_descri character varying(80),
    eon character varying(30),
    era character varying(60),
    period character varying(40),
    epoch character varying(60),
    age_ics character varying(40),
    max_age_ab numeric,
    min_age_ab numeric,
    setting_co character varying(4),
    setting_ty character varying(25),
    setting character varying(50),
    lithology character varying(225),
    met_code character varying(4),
    metamorphi character varying(50),
    dom_reg_co character varying(4),
    domain_reg character varying(10),
    domain_r_1 character varying(50),
    domain_r_2 character varying(80),
    domain_r_3 character varying(50),
    location character varying(10),
    source_lab character varying(4),
    source_loc character varying(110),
    compilatio character varying(200),
    ipy_code character varying(10),
    colour character varying(20),
    colour_cmy character varying(20),
    shape_le_1 numeric,
    shape_ar_1 numeric,
    geom public.geometry(MultiPolygon,4326),
    early_id integer,
    late_id integer,
    lith_trim character varying(225),
    age character varying(60)
);


CREATE TABLE sources.arctic_orig (
    gid integer NOT NULL,
    objectid integer,
    shape_leng numeric,
    shape_area numeric,
    map_label character varying(10),
    age_code character varying(4),
    age_descri character varying(80),
    eon character varying(30),
    era character varying(60),
    period character varying(40),
    epoch character varying(60),
    age_ics character varying(40),
    max_age_ab numeric,
    min_age_ab numeric,
    setting_co character varying(4),
    setting_ty character varying(25),
    setting character varying(50),
    lithology character varying(225),
    met_code character varying(4),
    metamorphi character varying(50),
    dom_reg_co character varying(4),
    domain_reg character varying(10),
    domain_r_1 character varying(50),
    domain_r_2 character varying(80),
    domain_r_3 character varying(50),
    location character varying(10),
    source_lab character varying(4),
    source_loc character varying(110),
    compilatio character varying(200),
    ipy_code character varying(10),
    colour character varying(20),
    colour_cmy character varying(20),
    geom public.geometry(MultiPolygon,4326),
    age character varying(60),
    early_id integer,
    late_id integer,
    lith_trim character varying(255)
);


CREATE SEQUENCE sources.arctic_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.arctic_gid_seq OWNED BY sources.arctic_orig.gid;


CREATE TABLE sources.arctic_lines (
    gid integer NOT NULL,
    objectid integer,
    type character varying(40),
    movement character varying(30),
    confidence character varying(30),
    descriptio character varying(50),
    location character varying(10),
    source_lab character varying(4),
    source_loc character varying(110),
    compilatio character varying(250),
    code character varying(4),
    line_symbo character varying(80),
    ornament_s character varying(10),
    shape_leng numeric,
    geom public.geometry(MultiLineString,4326),
    new_type text,
    new_direction text
);


CREATE SEQUENCE sources.arctic_newgeom_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.arctic_newgeom_gid_seq OWNED BY sources.arctic.gid;


CREATE SEQUENCE sources.arcticrus_lines_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.arcticrus_lines_gid_seq OWNED BY sources.arctic_lines.gid;


CREATE TABLE sources.australia (
    gid integer NOT NULL,
    geodb_oid double precision,
    objectid double precision,
    mapsymbol character varying(20),
    plotsymbol character varying(8),
    stratno double precision,
    name character varying(254),
    descr character varying(254),
    typename character varying(50),
    type_uri character varying(254),
    geolhist character varying(254),
    repage_uri character varying(254),
    yngage_uri character varying(254),
    oldage_uri character varying(254),
    lithology character varying(254),
    replth_uri character varying(254),
    morphology character varying(50),
    obsmethod character varying(50),
    confidence character varying(50),
    source character varying(254),
    metadata character varying(254),
    use_age character varying(254),
    resscale double precision,
    captdate date,
    moddate date,
    plotrank integer,
    featureid character varying(254),
    geolunitid character varying(254),
    shape_leng numeric,
    shape_area numeric,
    geom public.geometry(MultiPolygon,4326),
    early_id integer,
    late_id integer
);


CREATE TABLE sources.australia2 (
    gid integer NOT NULL,
    mapsymbol character varying(20),
    plotsymbol character varying(8),
    stratno numeric(10,0),
    name character varying(254),
    descr character varying(254),
    typename character varying(50),
    type_uri character varying(254),
    geolhist character varying(254),
    repage_uri character varying(254),
    yngage_uri character varying(254),
    oldage_uri character varying(254),
    lithology character varying(254),
    replith_ur character varying(254),
    morphology character varying(50),
    obsmethod character varying(50),
    confidence character varying(50),
    source character varying(254),
    metadata character varying(254),
    frame character varying(254),
    resscale numeric(10,0),
    captdate date,
    moddate date,
    plotrank integer,
    featureid character varying(254),
    geolunitid character varying(254),
    shape_area numeric,
    shape_len numeric,
    geom public.geometry(MultiPolygon,4326),
    early_id integer,
    late_id integer
);


CREATE TABLE sources.australia2_faults (
    gid integer NOT NULL,
    typename character varying(50),
    type_uri character varying(254),
    fltname character varying(254),
    descr character varying(254),
    exposure character varying(50),
    faultfill character varying(50),
    defrmstyle character varying(50),
    defrm_uri character varying(254),
    mvttype character varying(50),
    mvttyp_uri character varying(254),
    mvtsense character varying(50),
    dsplcmnt character varying(254),
    dip integer,
    dipdirn integer,
    width numeric(10,0),
    geolhist character varying(254),
    repage_uri character varying(254),
    yngage_uri character varying(254),
    oldage_uri character varying(254),
    fltsys character varying(254),
    fltsysid character varying(254),
    obsmethod character varying(50),
    confidence character varying(50),
    posacc_m numeric(10,0),
    source character varying(254),
    metadata character varying(254),
    frame character varying(254),
    resscale numeric(10,0),
    captscale numeric(10,0),
    captdate date,
    moddate date,
    plotrank integer,
    featcode character varying(12),
    featureid character varying(254),
    faultid character varying(254),
    shape_len numeric,
    geom public.geometry(MultiLineString,4326)
);


CREATE SEQUENCE sources.australia2_faults_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.australia2_faults_gid_seq OWNED BY sources.australia2_faults.gid;


CREATE SEQUENCE sources.australia2_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.australia2_gid_seq OWNED BY sources.australia2.gid;


CREATE TABLE sources.australia_faults (
    gid integer NOT NULL,
    typename character varying(50),
    type_uri character varying(254),
    fltname character varying(254),
    descr character varying(254),
    exposure character varying(50),
    faultfill character varying(50),
    defrmstyle character varying(50),
    defrm_uri character varying(254),
    mvttype character varying(50),
    mvttyp_uri character varying(254),
    mvtsense character varying(50),
    dsplcmnt character varying(254),
    dip integer,
    dipdirn integer,
    width numeric(10,0),
    geolhist character varying(254),
    repage_uri character varying(254),
    yngage_uri character varying(254),
    oldage_uri character varying(254),
    fltsys character varying(254),
    fltsysid character varying(254),
    obsmethod character varying(50),
    confidence character varying(50),
    posacc_m numeric(10,0),
    source character varying(254),
    metadata character varying(254),
    frame character varying(254),
    resscale numeric(10,0),
    captscale numeric(10,0),
    captdate date,
    moddate date,
    plotrank integer,
    featcode character varying(12),
    featureid character varying(254),
    faultid character varying(254),
    shape_len numeric,
    geom public.geometry(MultiLineString,4326)
);


CREATE SEQUENCE sources.australia_faults_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.australia_faults_gid_seq OWNED BY sources.australia_faults.gid;


CREATE SEQUENCE sources.australia_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.australia_gid_seq OWNED BY sources.australia.gid;


CREATE TABLE sources.az_fredonia (
    gid integer NOT NULL,
    geofnt100k character varying(50),
    geofnt24k character varying(50),
    ptype100k character varying(50),
    ptype24k character varying(12),
    shape_leng numeric,
    shape_area numeric,
    geom public.geometry(MultiPolygon,4326),
    name text,
    age text,
    description text,
    strat_name text,
    hierarchy text,
    early_id integer,
    late_id integer
);


CREATE TABLE sources.az_fredonia_lines (
    gid integer NOT NULL,
    ltype24k character varying(150),
    ltype character varying(150),
    pttype character varying(35),
    flt_nm character varying(50),
    shape_leng numeric,
    geom public.geometry(MultiLineString,4326),
    new_type text
);


CREATE SEQUENCE sources.az_fredonia_lines_one_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.az_fredonia_lines_one_gid_seq OWNED BY sources.az_fredonia_lines.gid;


CREATE TABLE sources.az_fredonia_points (
    gid integer NOT NULL,
    pttype character varying(35),
    pttype100k character varying(50),
    dip smallint,
    strike smallint,
    flt_off_ft smallint,
    flt_off_m smallint,
    geom public.geometry(Point,4326),
    point_type text,
    dip_dir integer
);


CREATE SEQUENCE sources.az_fredonia_point_two_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.az_fredonia_point_two_gid_seq OWNED BY sources.az_fredonia_points.gid;


CREATE SEQUENCE sources.az_fredonia_polygon_one_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.az_fredonia_polygon_one_gid_seq OWNED BY sources.az_fredonia.gid;


CREATE TABLE sources.az_mohave (
    gid integer NOT NULL,
    ptype100k character varying(35),
    geofnt100k character varying(35),
    shape_leng numeric,
    shape_area numeric,
    geom public.geometry(MultiPolygon,4326),
    name text,
    age text,
    description text,
    lithology text,
    classification text,
    early_id integer,
    late_id integer
);


CREATE TABLE sources.az_mohave_lines (
    gid integer NOT NULL,
    ltype100k character varying(35),
    flt_nm character varying(35),
    pttype character varying(50),
    shape_leng numeric,
    geom public.geometry(MultiLineString,4326),
    new_type text,
    new_direction text,
    comments character varying(250)
);


CREATE TABLE sources.az_peachsprings (
    gid integer NOT NULL,
    ptype100k character varying(254),
    geofnt100k character varying(254),
    shape_leng numeric,
    shape_area numeric,
    geom public.geometry(MultiPolygon,4326),
    name text,
    age text,
    description text,
    lithology text,
    classification text,
    early_id integer,
    late_id integer
);


CREATE TABLE sources.az_peachsprings_lines (
    gid integer NOT NULL,
    ltype character varying(50),
    shape_leng numeric,
    pttype character varying(35),
    name character varying(35),
    geom public.geometry(MultiLineString,4326),
    new_type text,
    new_direction text,
    descrip character varying(75)
);


CREATE TABLE sources.az_prescott (
    gid integer NOT NULL,
    area numeric,
    perimeter numeric,
    pnf_ integer,
    pnf_id integer,
    label character varying(10),
    name character varying(125),
    color_cmy smallint,
    color_cmyk smallint,
    youngest_age character varying(21),
    oldest_age character varying(21),
    "group" character varying(100),
    delta smallint,
    geom public.geometry(MultiPolygon,4326),
    age text,
    description text,
    early_id integer,
    late_id integer,
    comments text
);


CREATE TABLE sources.az_prescott_lines (
    gid integer NOT NULL,
    fnode_ integer,
    tnode_ integer,
    lpoly_ integer,
    rpoly_ integer,
    length numeric,
    pnf_ integer,
    pnf_id integer,
    type character varying(65),
    geolines smallint,
    delta smallint,
    geom public.geometry(MultiLineString,4326),
    new_type text,
    new_direction text
);


CREATE TABLE sources.az_whitehills (
    gid integer NOT NULL,
    objectid numeric,
    mapunit character varying(10),
    identityco character varying(50),
    ruleid bigint,
    override character varying(254),
    shape_leng numeric,
    shape_area numeric,
    geom public.geometry(MultiPolygon,4326),
    descrip text,
    strat_name text,
    age text,
    early_id integer,
    late_id integer,
    name text,
    lith text,
    geom_mod public.geometry(MultiPolygon,4326)
);


CREATE SEQUENCE sources.az_whitehills_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.az_whitehills_gid_seq OWNED BY sources.az_whitehills.gid;


CREATE TABLE sources.az_whitehills_lines (
    gid integer NOT NULL,
    objectid numeric,
    type character varying(254),
    isconceale character varying(30),
    existencec character varying(50),
    identityco character varying(50),
    label character varying(50),
    locatabili character varying(50),
    ruleid bigint,
    override character varying(254),
    shape_leng numeric,
    geom public.geometry(MultiLineString,4326),
    new_type text,
    new_direction text
);


CREATE SEQUENCE sources.az_whitehills_lines_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.az_whitehills_lines_gid_seq OWNED BY sources.az_whitehills_lines.gid;


CREATE TABLE sources.az_whitehills_points (
    gid integer NOT NULL,
    objectid numeric,
    type character varying(254),
    mapunit character varying(10),
    azimuth numeric,
    inclinatio numeric,
    symbolrota numeric,
    ruleid bigint,
    override character varying(254),
    geom public.geometry(Point,4326),
    point_type text,
    dip_dir integer
);


CREATE SEQUENCE sources.az_whitehills_points_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.az_whitehills_points_gid_seq OWNED BY sources.az_whitehills_points.gid;


CREATE TABLE sources.az_winslow (
    gid integer NOT NULL,
    objectid numeric(10,0),
    mapunit character varying(75),
    shape_leng numeric,
    shape_area numeric,
    geoage character varying(50),
    geom public.geometry(MultiPolygon,4326),
    name text,
    age text,
    description text,
    strat_name text,
    hierarchy text,
    comments text,
    early_id integer,
    late_id integer
);


CREATE SEQUENCE sources.az_winslow_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.az_winslow_gid_seq OWNED BY sources.az_winslow.gid;


CREATE TABLE sources.az_winslow_lines (
    gid integer NOT NULL,
    objectid numeric(10,0),
    linetype character varying(50),
    shape_leng numeric,
    geom public.geometry(MultiLineString,4326),
    new_type text,
    descrip text
);


CREATE SEQUENCE sources.az_winslow_lines_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.az_winslow_lines_gid_seq OWNED BY sources.az_winslow_lines.gid;


CREATE TABLE sources.az_winslow_points (
    gid integer NOT NULL,
    objectid numeric(10,0),
    pointtype character varying(50),
    name character varying(50),
    geom public.geometry(Point,4326),
    dip integer,
    strike integer,
    dip_dir integer,
    point_type text
);


CREATE SEQUENCE sources.az_winslow_points_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.az_winslow_points_gid_seq OWNED BY sources.az_winslow_points.gid;


CREATE TABLE sources.bc (
    gid integer NOT NULL,
    pid character varying(25),
    area_m2 double precision,
    strat_unit character varying(12),
    era character varying(35),
    period character varying(35),
    strat_age character varying(50),
    strat_name character varying(254),
    gp_suite character varying(100),
    fm_lithodm character varying(100),
    mem_phase character varying(100),
    rock_class character varying(25),
    rock_type character varying(100),
    rock_code character varying(5),
    original_d character varying(254),
    age_max character varying(30),
    age_min character varying(30),
    age_max_ma double precision,
    age_min_ma double precision,
    belt character varying(30),
    terrane character varying(50),
    terr_code character varying(254),
    basin character varying(50),
    basin_age character varying(50),
    project character varying(50),
    remarks character varying(254),
    edit_ref character varying(50),
    source_ref character varying(254),
    geom public.geometry(MultiPolygon,4326),
    early_id integer,
    late_id integer,
    name character varying(254)
);


CREATE TABLE sources.bc_2017 (
    gid integer NOT NULL,
    __gid double precision,
    upid character varying(8),
    area_m2 numeric,
    strat_unit character varying(12),
    era character varying(24),
    period character varying(31),
    strat_age character varying(39),
    strat_name character varying(88),
    gp_suite character varying(48),
    fm_lithodm character varying(74),
    mem_phase character varying(38),
    rock_class character varying(30),
    rock_type character varying(78),
    rk_char character varying(31),
    unit_desc character varying(254),
    age_max character varying(36),
    age_min character varying(36),
    belt character varying(15),
    terrane character varying(33),
    basin character varying(36),
    basin_age character varying(34),
    project character varying(50),
    src_url character varying(176),
    src_ref_s character varying(99),
    map_comp character varying(38),
    edit_date character varying(10),
    pub_org character varying(34),
    geom public.geometry(MultiPolygon,4326),
    early_id integer,
    late_id integer,
    use_strat_name text
);


CREATE SEQUENCE sources.bc_2017_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.bc_2017_gid_seq OWNED BY sources.bc_2017.gid;


CREATE TABLE sources.bc_2017_lines (
    gid integer NOT NULL,
    __gid double precision,
    ulid character varying(8),
    fault_type character varying(21),
    confidence character varying(11),
    fault_name character varying(36),
    length_m numeric,
    edit_date character varying(10),
    pub_org character varying(34),
    geom public.geometry(MultiLineString,4326),
    new_type text,
    new_direction text
);


CREATE SEQUENCE sources.bc_2017_lines_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.bc_2017_lines_gid_seq OWNED BY sources.bc_2017_lines.gid;


CREATE TABLE sources.bc_2017_quat (
    gid integer NOT NULL,
    __gid double precision,
    label character varying(3),
    area_m2 numeric,
    perimeter numeric,
    edit_date character varying(10),
    pub_org character varying(34),
    geom public.geometry(MultiPolygon,4326),
    use_name text,
    lith text,
    early_id integer,
    late_id integer,
    age_name text
);


CREATE SEQUENCE sources.bc_2017_quat_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.bc_2017_quat_gid_seq OWNED BY sources.bc_2017_quat.gid;


CREATE TABLE sources.bc_abruzzi (
    gid integer NOT NULL,
    map_theme character varying(50),
    feature character varying(50),
    map_unit character varying(100),
    parents character varying(254),
    max_age character varying(50),
    min_age character varying(50),
    lith_list character varying(100),
    genesis character varying(100),
    remarks character varying(254),
    label character varying(30),
    reference character varying(254),
    source_ref character varying(254),
    map_id character varying(254),
    style_id character varying(100),
    shape_leng numeric,
    shape_area numeric,
    geom public.geometry(MultiPolygon,4326),
    early_id integer,
    late_id integer,
    use_age text,
    strat_name text,
    descrip text,
    hierarchy text
);


CREATE SEQUENCE sources.bc_abruzzi_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.bc_abruzzi_gid_seq OWNED BY sources.bc_abruzzi.gid;


CREATE TABLE sources.bc_abruzzi_lines (
    gid integer NOT NULL,
    map_theme character varying(50),
    feature character varying(75),
    subfeature character varying(50),
    attitude character varying(50),
    confidence character varying(15),
    generation character varying(10),
    max_age character varying(50),
    min_age character varying(50),
    foldtrend character varying(20),
    foldplunge character varying(20),
    name character varying(254),
    properties character varying(254),
    remarks character varying(254),
    reference character varying(254),
    source_ref character varying(254),
    map_id character varying(254),
    arrow_dir character varying(20),
    symbol character varying(20),
    shape_leng numeric,
    geom public.geometry(MultiLineString,4326),
    new_type text,
    descrip text
);


CREATE SEQUENCE sources.bc_abruzzi_lines_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.bc_abruzzi_lines_gid_seq OWNED BY sources.bc_abruzzi_lines.gid;


CREATE TABLE sources.bc_abruzzi_points (
    gid integer NOT NULL,
    map_theme character varying(50),
    feature character varying(50),
    planar_id character varying(50),
    subfeature character varying(50),
    fab_elem character varying(254),
    attitude character varying(50),
    young_evid character varying(50),
    generation character varying(50),
    method character varying(50),
    dip_dir integer,
    strike integer,
    dip integer,
    strain character varying(50),
    flattening character varying(50),
    lith_id character varying(50),
    map_unit character varying(100),
    station_id character varying(50),
    linear_id character varying(100),
    planar_id2 character varying(100),
    remarks character varying(254),
    reference character varying(254),
    source_ref character varying(254),
    map_id character varying(254),
    symbol character varying(20),
    geom public.geometry(Point,4326),
    trend integer,
    plunge integer,
    point_type text,
    dip_dir_yn text
);


CREATE SEQUENCE sources.bc_abruzzi_points_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.bc_abruzzi_points_gid_seq OWNED BY sources.bc_abruzzi_points.gid;


CREATE TABLE sources.bc_assini (
    gid integer NOT NULL,
    map_theme character varying(50),
    feature character varying(50),
    map_unit character varying(100),
    parents character varying(254),
    max_age character varying(50),
    min_age character varying(50),
    lith_list character varying(100),
    genesis character varying(100),
    remarks character varying(254),
    label character varying(30),
    reference character varying(254),
    source_ref character varying(254),
    map_id character varying(254),
    style_id character varying(50),
    shape_leng numeric,
    shape_area numeric,
    geom public.geometry(MultiPolygon,4326),
    early_id integer,
    late_id integer,
    use_age text,
    strat_name text,
    hierarchy text,
    descrip text
);


CREATE SEQUENCE sources.bc_assini_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.bc_assini_gid_seq OWNED BY sources.bc_assini.gid;


CREATE TABLE sources.bc_assini_lines (
    gid integer NOT NULL,
    map_theme character varying(50),
    feature character varying(50),
    subfeature character varying(50),
    attitude character varying(50),
    confidence character varying(15),
    generation character varying(10),
    max_age character varying(50),
    min_age character varying(50),
    name character varying(254),
    properties character varying(254),
    movement character varying(20),
    hwall_dir character varying(20),
    remarks character varying(254),
    reference character varying(254),
    source_ref character varying(254),
    map_id character varying(254),
    symbol character varying(20),
    shape_leng numeric,
    geom public.geometry(MultiLineString,4326),
    new_type text,
    descrip text
);


CREATE SEQUENCE sources.bc_assini_lines_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.bc_assini_lines_gid_seq OWNED BY sources.bc_assini_lines.gid;


CREATE TABLE sources.bc_assini_points (
    gid integer NOT NULL,
    map_theme character varying(50),
    feature character varying(50),
    planar_id character varying(50),
    subfeature character varying(50),
    fab_elem character varying(254),
    attitude character varying(50),
    young_evid character varying(50),
    generation character varying(50),
    method character varying(50),
    dip_dir integer,
    strike integer,
    dip integer,
    strain character varying(50),
    flattening character varying(50),
    lith_id character varying(50),
    map_unit character varying(100),
    station_id character varying(50),
    related_id character varying(100),
    linear_id character varying(100),
    planar_id2 character varying(100),
    remarks character varying(254),
    reference character varying(254),
    source_ref character varying(254),
    map_id character varying(254),
    symbol character varying(20),
    geom public.geometry(Point,4326),
    trend integer,
    plunge integer,
    point_type text
);


CREATE SEQUENCE sources.bc_assini_points_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.bc_assini_points_gid_seq OWNED BY sources.bc_assini_points.gid;


CREATE TABLE sources.bc_chinook (
    gid integer NOT NULL,
    map_theme character varying(50),
    feature character varying(50),
    map_unit character varying(100),
    parents character varying(254),
    max_age character varying(50),
    min_age character varying(50),
    lith_list character varying(100),
    genesis character varying(100),
    remarks character varying(254),
    label character varying(30),
    reference character varying(254),
    source_ref character varying(254),
    map_id character varying(254),
    include_hc character varying(5),
    symbol character varying(100),
    shape_leng numeric,
    shape_area numeric,
    geom public.geometry(MultiPolygon,4326),
    early_id integer,
    late_id integer,
    strat_name text,
    descrip text,
    use_age text
);


CREATE SEQUENCE sources.bc_chinook_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.bc_chinook_gid_seq OWNED BY sources.bc_chinook.gid;


CREATE TABLE sources.bc_chinook_lines (
    gid integer NOT NULL,
    map_theme character varying(50),
    feature character varying(50),
    subfeature character varying(50),
    attitude character varying(50),
    confidence character varying(15),
    generation character varying(25),
    max_age character varying(50),
    min_age character varying(50),
    name character varying(254),
    properties character varying(254),
    movement character varying(254),
    hwall_dir character varying(254),
    remarks character varying(254),
    reference character varying(254),
    source_ref character varying(254),
    map_id character varying(254),
    include_hc character varying(5),
    symbol character varying(100),
    symbol_100 character varying(100),
    shape_leng numeric,
    geom public.geometry(MultiLineString,4326),
    new_type text,
    new_direction text
);


CREATE SEQUENCE sources.bc_chinook_lines_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.bc_chinook_lines_gid_seq OWNED BY sources.bc_chinook_lines.gid;


CREATE TABLE sources.bc_chinook_points (
    gid integer NOT NULL,
    map_theme character varying(50),
    feature character varying(50),
    planar_id character varying(50),
    subfeature character varying(50),
    fab_elem character varying(254),
    attitude character varying(50),
    young_evid character varying(50),
    generation character varying(50),
    method character varying(50),
    dip_dir integer,
    strike integer,
    dip integer,
    strain character varying(50),
    flattening character varying(50),
    lith_id character varying(50),
    station_id character varying(50),
    linear_id character varying(100),
    planar_id2 character varying(100),
    remarks character varying(254),
    reference character varying(254),
    source_ref character varying(254),
    map_id character varying(254),
    include_hc character varying(5),
    symbol character varying(100),
    geom public.geometry(Point,4326),
    point_type text
);


CREATE SEQUENCE sources.bc_chinook_points_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.bc_chinook_points_gid_seq OWNED BY sources.bc_chinook_points.gid;


CREATE TABLE sources.bc_eight (
    gid integer NOT NULL,
    map_theme character varying(50),
    feature character varying(50),
    map_unit character varying(100),
    parents character varying(254),
    max_age character varying(50),
    min_age character varying(50),
    lith_list character varying(100),
    genesis character varying(100),
    remarks character varying(254),
    label character varying(30),
    reference character varying(254),
    source_ref character varying(254),
    map_id character varying(254),
    symbol character varying(100),
    shape_leng numeric,
    shape_area numeric,
    geom public.geometry(MultiPolygon,4326),
    early_id integer,
    late_id integer,
    use_age text,
    strat_name text,
    descrip text,
    hierarchy text
);


CREATE SEQUENCE sources.bc_eight_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.bc_eight_gid_seq OWNED BY sources.bc_eight.gid;


CREATE TABLE sources.bc_eight_lines (
    gid integer NOT NULL,
    map_theme character varying(50),
    feature character varying(50),
    subfeature character varying(50),
    attitude character varying(50),
    confidence character varying(15),
    generation character varying(25),
    max_age character varying(50),
    min_age character varying(50),
    foldtrend character varying(20),
    foldplunge character varying(20),
    name character varying(254),
    properties character varying(254),
    remarks character varying(254),
    reference character varying(254),
    source_ref character varying(254),
    map_id character varying(254),
    arrow_dir character varying(20),
    symbol character varying(100),
    shape_leng numeric,
    geom public.geometry(MultiLineString,4326),
    new_type text,
    descrip text
);


CREATE SEQUENCE sources.bc_eight_lines_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.bc_eight_lines_gid_seq OWNED BY sources.bc_eight_lines.gid;


CREATE TABLE sources.bc_eight_points (
    gid integer NOT NULL,
    map_theme character varying(50),
    feature character varying(50),
    planar_id character varying(50),
    subfeature character varying(50),
    fab_elem character varying(254),
    attitude character varying(50),
    young_evid character varying(50),
    generation character varying(50),
    method character varying(50),
    dip_dir integer,
    strike integer,
    dip integer,
    strain character varying(50),
    flattening character varying(50),
    lith_id character varying(50),
    station_id character varying(50),
    linear_id character varying(100),
    planar_id2 character varying(100),
    remarks character varying(254),
    reference character varying(254),
    source_ref character varying(254),
    map_id character varying(254),
    symbol character varying(100),
    geom public.geometry(Point,4326),
    point_type text
);


CREATE SEQUENCE sources.bc_eight_points_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.bc_eight_points_gid_seq OWNED BY sources.bc_eight_points.gid;


CREATE TABLE sources.bc_faults (
    gid integer NOT NULL,
    lid character varying(35),
    fault_type character varying(50),
    confidence character varying(35),
    fault_name character varying(100),
    length_m double precision,
    edit_ref character varying(50),
    geom public.geometry(MultiLineString,4326)
);


CREATE SEQUENCE sources.bc_faults_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.bc_faults_gid_seq OWNED BY sources.bc_faults.gid;


CREATE TABLE sources.bc_fernie (
    gid integer NOT NULL,
    map_theme character varying(50),
    feature character varying(50),
    map_unit character varying(50),
    parent character varying(254),
    max_age character varying(50),
    min_age character varying(50),
    age character varying(100),
    descrip text,
    unit_notes character varying(254),
    strat_name text,
    remarks character varying(254),
    label character varying(50),
    legend_ord character varying(50),
    reference character varying(254),
    source_ref character varying(254),
    study_area character varying(254),
    symbol character varying(50),
    shape_leng numeric,
    shape_area numeric,
    geom public.geometry(MultiPolygon,4326),
    early_id integer,
    late_id integer,
    use_name text
);


CREATE SEQUENCE sources.bc_fernie_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.bc_fernie_gid_seq OWNED BY sources.bc_fernie.gid;


CREATE TABLE sources.bc_fernie_lines (
    gid integer NOT NULL,
    map_theme character varying(50),
    feature character varying(50),
    subfeature character varying(50),
    attitude character varying(50),
    confidence character varying(50),
    generation character varying(50),
    max_age character varying(50),
    min_age character varying(50),
    activity character varying(50),
    name character varying(254),
    geometry character varying(254),
    movement character varying(254),
    hwall_dir character varying(50),
    remarks character varying(254),
    reference character varying(254),
    source_ref character varying(254),
    study_area character varying(254),
    symbol character varying(50),
    fgdc smallint,
    shape_leng numeric,
    geom public.geometry(MultiLineString,4326),
    new_type text,
    new_direction text
);


CREATE SEQUENCE sources.bc_fernie_lines_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.bc_fernie_lines_gid_seq OWNED BY sources.bc_fernie_lines.gid;


CREATE TABLE sources.bc_fernie_points (
    gid integer NOT NULL,
    map_theme character varying(50),
    planar_id character varying(50),
    feature character varying(50),
    subfeature character varying(50),
    fab_elem character varying(50),
    attitude character varying(50),
    young_dir character varying(50),
    generation character varying(50),
    method character varying(50),
    strike smallint,
    dip smallint,
    dip_dir smallint,
    lithology character varying(50),
    map_unit character varying(50),
    station_id character varying(50),
    linear_id character varying(50),
    planar_id2 character varying(50),
    remarks character varying(254),
    reference character varying(254),
    source_ref character varying(254),
    study_area character varying(254),
    release character varying(50),
    authority character varying(254),
    symbol character varying(50),
    exclude_hc character varying(5),
    geom public.geometry(Point,4326)
);


CREATE SEQUENCE sources.bc_fernie_points_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.bc_fernie_points_gid_seq OWNED BY sources.bc_fernie_points.gid;


CREATE SEQUENCE sources.bc_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.bc_gid_seq OWNED BY sources.bc.gid;


CREATE TABLE sources.bc_grayling (
    gid integer NOT NULL,
    map_theme character varying(50),
    feature character varying(50),
    map_unit character varying(100),
    parents character varying(254),
    max_age character varying(50),
    min_age character varying(50),
    lith_list character varying(100),
    genesis character varying(100),
    remarks character varying(254),
    label character varying(30),
    reference character varying(254),
    source_ref character varying(254),
    map_id character varying(254),
    symbol character varying(100),
    shape_area numeric,
    shape_len numeric,
    geom public.geometry(MultiPolygon,4326),
    early_id integer,
    late_id integer,
    use_age text,
    strat_name text,
    descrip text,
    hierarchy text
);


CREATE SEQUENCE sources.bc_grayling_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.bc_grayling_gid_seq OWNED BY sources.bc_grayling.gid;


CREATE TABLE sources.bc_grayling_lines (
    gid integer NOT NULL,
    map_theme character varying(50),
    feature character varying(50),
    subfeature character varying(50),
    attitude character varying(50),
    confidence character varying(15),
    generation character varying(25),
    max_age character varying(50),
    min_age character varying(50),
    foldtrend character varying(20),
    foldplunge character varying(20),
    name character varying(254),
    properties character varying(254),
    remarks character varying(254),
    reference character varying(254),
    source_ref character varying(254),
    map_id character varying(254),
    arrow_dir character varying(20),
    symbol character varying(100),
    shape_len numeric,
    geom public.geometry(MultiLineString,4326),
    new_type text,
    descrip text
);


CREATE SEQUENCE sources.bc_grayling_lines_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.bc_grayling_lines_gid_seq OWNED BY sources.bc_grayling_lines.gid;


CREATE TABLE sources.bc_grayling_points (
    gid integer NOT NULL,
    map_theme character varying(50),
    feature character varying(50),
    planar_id character varying(50),
    subfeature character varying(50),
    fab_elem character varying(254),
    attitude character varying(50),
    young_evid character varying(50),
    generation character varying(50),
    method character varying(50),
    dip_dir bigint,
    strike bigint,
    dip bigint,
    strain character varying(50),
    flattening character varying(50),
    lith_id character varying(50),
    station_id character varying(50),
    linear_id character varying(100),
    planar_id2 character varying(100),
    remarks character varying(254),
    reference character varying(254),
    source_ref character varying(254),
    map_id character varying(254),
    symbol character varying(100),
    geom public.geometry(Point,4326),
    point_type text
);


CREATE SEQUENCE sources.bc_grayling_points_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.bc_grayling_points_gid_seq OWNED BY sources.bc_grayling_points.gid;


CREATE TABLE sources.bc_kananaskis (
    gid integer NOT NULL,
    map_theme character varying(50),
    feature character varying(50),
    map_unit character varying(100),
    parents character varying(254),
    max_age character varying(50),
    min_age character varying(50),
    lith_list character varying(100),
    genesis character varying(100),
    remarks character varying(254),
    label character varying(30),
    reference character varying(254),
    source_ref character varying(254),
    map_id character varying(254),
    symbol character varying(100),
    anno character varying(100),
    shape_leng numeric,
    shape_area numeric,
    geom public.geometry(MultiPolygon,4326),
    early_id integer,
    late_id integer,
    use_age text,
    strat_name text,
    hierarchy text,
    descrip text
);


CREATE SEQUENCE sources.bc_kananaskis_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.bc_kananaskis_gid_seq OWNED BY sources.bc_kananaskis.gid;


CREATE TABLE sources.bc_kananaskis_lines (
    gid integer NOT NULL,
    map_theme character varying(50),
    feature character varying(75),
    subfeature character varying(50),
    attitude character varying(50),
    confidence character varying(15),
    generation character varying(25),
    max_age character varying(50),
    min_age character varying(50),
    name character varying(254),
    properties character varying(254),
    movement character varying(254),
    hwall_dir character varying(254),
    remarks character varying(254),
    reference character varying(254),
    source_ref character varying(254),
    map_id character varying(254),
    symbol character varying(100),
    shape_leng numeric,
    geom public.geometry(MultiLineString,4326),
    new_type text,
    descrip text
);


CREATE SEQUENCE sources.bc_kananaskis_lines_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.bc_kananaskis_lines_gid_seq OWNED BY sources.bc_kananaskis_lines.gid;


CREATE TABLE sources.bc_kananaskis_points (
    gid integer NOT NULL,
    map_theme character varying(50),
    feature character varying(50),
    planar_id character varying(50),
    subfeature character varying(50),
    fab_elem character varying(254),
    attitude character varying(50),
    young_evid character varying(50),
    generation character varying(50),
    method character varying(50),
    dip_dir integer,
    strike integer,
    dip integer,
    strain character varying(50),
    flattening character varying(50),
    lith_id character varying(50),
    station_id character varying(50),
    linear_id character varying(100),
    planar_id2 character varying(100),
    remarks character varying(254),
    reference character varying(254),
    source_ref character varying(254),
    map_id character varying(254),
    symbol character varying(100),
    geom public.geometry(Point,4326),
    point_type text
);


CREATE SEQUENCE sources.bc_kananaskis_points_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.bc_kananaskis_points_gid_seq OWNED BY sources.bc_kananaskis_points.gid;


CREATE TABLE sources.bc_prudence (
    gid integer NOT NULL,
    map_theme character varying(50),
    feature character varying(50),
    map_unit character varying(100),
    parents character varying(254),
    max_age character varying(50),
    min_age character varying(50),
    lith_list character varying(100),
    genesis character varying(100),
    remarks character varying(254),
    label character varying(30),
    reference character varying(254),
    source_ref character varying(254),
    map_id character varying(254),
    symbol character varying(100),
    shape_leng numeric,
    shape_area numeric,
    geom public.geometry(MultiPolygon,4326),
    early_id integer,
    late_id integer,
    use_age text,
    strat_name text,
    descrip text
);


CREATE SEQUENCE sources.bc_prudence_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.bc_prudence_gid_seq OWNED BY sources.bc_prudence.gid;


CREATE TABLE sources.bc_prudence_lines (
    gid integer NOT NULL,
    map_theme character varying(50),
    feature character varying(50),
    subfeature character varying(50),
    attitude character varying(50),
    confidence character varying(15),
    generation character varying(25),
    max_age character varying(50),
    min_age character varying(50),
    foldtrend character varying(20),
    foldplunge character varying(20),
    name character varying(254),
    properties character varying(254),
    remarks character varying(254),
    reference character varying(254),
    source_ref character varying(254),
    map_id character varying(254),
    arrow_dir character varying(20),
    symbol character varying(100),
    shape_leng numeric,
    geom public.geometry(MultiLineString,4326),
    new_type text,
    descrip text
);


CREATE SEQUENCE sources.bc_prudence_lines_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.bc_prudence_lines_gid_seq OWNED BY sources.bc_prudence_lines.gid;


CREATE TABLE sources.bc_prudence_points (
    gid integer NOT NULL,
    map_theme character varying(50),
    feature character varying(50),
    planar_id character varying(50),
    subfeature character varying(50),
    fab_elem character varying(254),
    attitude character varying(50),
    young_evid character varying(50),
    generation character varying(50),
    method character varying(50),
    dip_dir integer,
    strike integer,
    dip integer,
    strain character varying(50),
    flattening character varying(50),
    lith_id character varying(50),
    station_id character varying(50),
    linear_id character varying(100),
    planar_id2 character varying(100),
    remarks character varying(254),
    reference character varying(254),
    source_ref character varying(254),
    map_id character varying(254),
    symbol character varying(100),
    geom public.geometry(Point,4326),
    trend integer,
    plunge integer,
    point_type text
);


CREATE SEQUENCE sources.bc_prudence_points_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.bc_prudence_points_gid_seq OWNED BY sources.bc_prudence_points.gid;


CREATE TABLE sources.bc_redfern (
    gid integer NOT NULL,
    area double precision,
    perimeter double precision,
    una94g5_ double precision,
    una94g5_id double precision,
    label character varying(20),
    group_r character varying(30),
    formation character varying(30),
    member character varying(30),
    gen_descr character varying(254),
    nts_map character varying(13),
    chron_age character varying(30),
    geom public.geometry(MultiPolygon,4326),
    max_age text,
    min_age text,
    early_id integer,
    late_id integer,
    use_age text,
    strat_name text,
    hierarchy text
);


CREATE SEQUENCE sources.bc_redfern_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.bc_redfern_gid_seq OWNED BY sources.bc_redfern.gid;


CREATE TABLE sources.bc_redfern_lines (
    gid integer NOT NULL,
    fnode_ double precision,
    tnode_ double precision,
    lpoly_ double precision,
    rpoly_ double precision,
    length numeric,
    gel94g5_ double precision,
    gel94g5_id double precision,
    type character varying(30),
    subtype character varying(80),
    direction character varying(30),
    nts_map character varying(20),
    geom public.geometry(MultiLineString,4326),
    descrip text,
    new_type text
);


CREATE SEQUENCE sources.bc_redfern_lines_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.bc_redfern_lines_gid_seq OWNED BY sources.bc_redfern_lines.gid;


CREATE TABLE sources.bc_redfern_points (
    gid integer NOT NULL,
    area double precision,
    perimeter double precision,
    srp94g5_ double precision,
    srp94g5_id double precision,
    planar_id character varying(30),
    planar_typ character varying(50),
    modifier character varying(50),
    strike numeric,
    dip numeric,
    location character varying(100),
    trend character varying(11),
    plunge character varying(11),
    linear_typ character varying(50),
    comment character varying(250),
    lithology character varying(50),
    station_id character varying(30),
    nts_map character varying(12),
    disp_ang numeric,
    geom public.geometry(Point,4326),
    point_type text,
    dip_dir integer
);


CREATE SEQUENCE sources.bc_redfern_points_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.bc_redfern_points_gid_seq OWNED BY sources.bc_redfern_points.gid;


CREATE TABLE sources.bc_tangle (
    gid integer NOT NULL,
    map_theme character varying(50),
    feature character varying(50),
    map_unit character varying(100),
    parents character varying(254),
    max_age character varying(50),
    min_age character varying(50),
    lith_list character varying(100),
    genesis character varying(100),
    remarks character varying(254),
    label character varying(30),
    reference character varying(254),
    source_ref character varying(254),
    map_id character varying(254),
    style_id character varying(50),
    shape_leng numeric,
    shape_area numeric,
    geom public.geometry(MultiPolygon,4326),
    early_id integer,
    late_id integer,
    use_age text,
    strat_name text,
    hierarchy text,
    descrip text
);


CREATE SEQUENCE sources.bc_tangle_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.bc_tangle_gid_seq OWNED BY sources.bc_tangle.gid;


CREATE TABLE sources.bc_tangle_lines (
    gid integer NOT NULL,
    map_theme character varying(50),
    feature character varying(50),
    subfeature character varying(50),
    attitude character varying(50),
    confidence character varying(15),
    generation character varying(10),
    max_age character varying(50),
    min_age character varying(50),
    name character varying(254),
    properties character varying(254),
    movement character varying(20),
    hwall_dir character varying(20),
    remarks character varying(254),
    reference character varying(254),
    source_ref character varying(254),
    map_id character varying(254),
    symbol character varying(20),
    shape_leng numeric,
    geom public.geometry(MultiLineString,4326),
    new_type text,
    descrip text
);


CREATE SEQUENCE sources.bc_tangle_lines_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.bc_tangle_lines_gid_seq OWNED BY sources.bc_tangle_lines.gid;


CREATE TABLE sources.bc_tangle_points (
    gid integer NOT NULL,
    map_theme character varying(50),
    feature character varying(50),
    planar_id character varying(50),
    subfeature character varying(50),
    fab_elem character varying(254),
    attitude character varying(50),
    young_evid character varying(50),
    generation character varying(50),
    method character varying(50),
    dip_dir integer,
    strike integer,
    dip integer,
    strain character varying(50),
    flattening character varying(50),
    lith_id character varying(50),
    map_unit character varying(100),
    station_id character varying(50),
    related_id character varying(100),
    linear_id character varying(100),
    planar_id2 character varying(100),
    remarks character varying(500),
    reference character varying(254),
    source_ref character varying(254),
    map_id character varying(254),
    symbol character varying(20),
    geom public.geometry(Point,4326),
    trend integer,
    plunge integer,
    point_type text
);


CREATE SEQUENCE sources.bc_tangle_points_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.bc_tangle_points_gid_seq OWNED BY sources.bc_tangle_points.gid;


CREATE TABLE sources.bc_toad (
    gid integer NOT NULL,
    map_theme character varying(50),
    feature character varying(50),
    map_unit character varying(100),
    parents character varying(254),
    max_age character varying(50),
    min_age character varying(50),
    lith_list character varying(100),
    descrip character varying(254),
    genesis character varying(100),
    remarks character varying(254),
    label character varying(30),
    reference character varying(254),
    source_ref character varying(254),
    map_id character varying(254),
    pub_scale numeric,
    include_hc character varying(5),
    symbol character varying(100),
    shape_leng numeric,
    shape_area numeric,
    geom public.geometry(MultiPolygon,4326),
    early_id integer,
    late_id integer,
    strat_name text,
    hierarchy text,
    use_age text
);


CREATE SEQUENCE sources.bc_toad_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.bc_toad_gid_seq OWNED BY sources.bc_toad.gid;


CREATE TABLE sources.bc_toad_lines (
    gid integer NOT NULL,
    map_theme character varying(50),
    feature character varying(50),
    subfeature character varying(50),
    attitude character varying(50),
    confidence character varying(15),
    generation character varying(25),
    max_age character varying(50),
    min_age character varying(50),
    foldtrend character varying(20),
    foldplunge character varying(20),
    name character varying(254),
    properties character varying(254),
    remarks character varying(254),
    reference character varying(254),
    source_ref character varying(254),
    map_id character varying(254),
    pub_scale numeric,
    include_hc character varying(5),
    arrow_dir character varying(20),
    symbol character varying(100),
    shape_leng numeric,
    geom public.geometry(MultiLineString,4326),
    new_type text,
    descrip text
);


CREATE SEQUENCE sources.bc_toad_lines_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.bc_toad_lines_gid_seq OWNED BY sources.bc_toad_lines.gid;


CREATE TABLE sources.bc_toad_ne (
    gid integer NOT NULL,
    map_theme character varying(50),
    feature character varying(50),
    map_unit character varying(100),
    parents character varying(254),
    max_age character varying(50),
    min_age character varying(50),
    lith_list character varying(100),
    genesis character varying(100),
    remarks character varying(254),
    label character varying(30),
    reference character varying(254),
    source_ref character varying(254),
    map_id character varying(254),
    symbol character varying(100),
    shape_area numeric,
    shape_len numeric,
    geom public.geometry(MultiPolygon,4326),
    early_id integer,
    late_id integer,
    use_age text,
    strat_name text,
    hierarchy text,
    descrip text
);


CREATE SEQUENCE sources.bc_toad_ne_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.bc_toad_ne_gid_seq OWNED BY sources.bc_toad_ne.gid;


CREATE TABLE sources.bc_toad_ne_lines (
    gid integer NOT NULL,
    map_theme character varying(50),
    feature character varying(50),
    subfeature character varying(50),
    attitude character varying(50),
    confidence character varying(15),
    generation character varying(25),
    max_age character varying(50),
    min_age character varying(50),
    foldtrend character varying(20),
    foldplunge character varying(20),
    name character varying(254),
    properties character varying(254),
    remarks character varying(254),
    reference character varying(254),
    source_ref character varying(254),
    map_id character varying(254),
    arrow_dir character varying(20),
    symbol character varying(100),
    shape_len numeric,
    geom public.geometry(MultiLineString,4326),
    new_type text,
    descrip text
);


CREATE SEQUENCE sources.bc_toad_ne_lines_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.bc_toad_ne_lines_gid_seq OWNED BY sources.bc_toad_ne_lines.gid;


CREATE TABLE sources.bc_toad_ne_points (
    gid integer NOT NULL,
    map_theme character varying(50),
    feature character varying(50),
    planar_id character varying(50),
    subfeature character varying(50),
    fab_elem character varying(254),
    attitude character varying(50),
    young_evid character varying(50),
    generation character varying(50),
    method character varying(50),
    dip_dir bigint,
    strike bigint,
    dip bigint,
    strain character varying(50),
    flattening character varying(50),
    lith_id character varying(50),
    station_id character varying(50),
    linear_id character varying(100),
    planar_id2 character varying(100),
    remarks character varying(254),
    reference character varying(254),
    source_ref character varying(254),
    map_id character varying(254),
    symbol character varying(100),
    geom public.geometry(Point,4326),
    point_type text
);


CREATE SEQUENCE sources.bc_toad_ne_points_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.bc_toad_ne_points_gid_seq OWNED BY sources.bc_toad_ne_points.gid;


CREATE TABLE sources.bc_toad_points (
    gid integer NOT NULL,
    map_theme character varying(50),
    feature character varying(50),
    planar_id character varying(50),
    subfeature character varying(50),
    fab_elem character varying(254),
    attitude character varying(50),
    young_evid character varying(50),
    generation character varying(50),
    method character varying(50),
    dip_dir integer,
    strike integer,
    dip integer,
    strain character varying(50),
    flattening character varying(50),
    lith_id character varying(50),
    station_id character varying(50),
    related_id character varying(100),
    linear_id character varying(100),
    planar_id2 character varying(100),
    remarks character varying(254),
    reference character varying(254),
    source_ref character varying(254),
    map_id character varying(254),
    release character varying(30),
    authority character varying(100),
    include_hc character varying(5),
    symbol character varying(100),
    geom public.geometry(Point,4326),
    point_type text
);


CREATE SEQUENCE sources.bc_toad_points_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.bc_toad_points_gid_seq OWNED BY sources.bc_toad_points.gid;


CREATE TABLE sources.bc_ware (
    gid integer NOT NULL,
    map_theme character varying(50),
    feature character varying(50),
    map_unit character varying(50),
    parent character varying(254),
    max_age character varying(50),
    min_age character varying(50),
    lith_list character varying(100),
    genesis character varying(100),
    remarks character varying(254),
    label character varying(30),
    reference character varying(254),
    map_id character varying(254),
    symbol character varying(20),
    shape_leng numeric,
    shape_area numeric,
    geom public.geometry(MultiPolygon,4326),
    early_id integer,
    late_id integer,
    use_age text,
    strat_name text,
    descrip text,
    hierarchy text
);


CREATE SEQUENCE sources.bc_ware_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.bc_ware_gid_seq OWNED BY sources.bc_ware.gid;


CREATE TABLE sources.bc_ware_lines (
    gid integer NOT NULL,
    map_theme character varying(50),
    feature character varying(50),
    subfeature character varying(50),
    attitude character varying(50),
    confidence character varying(15),
    generation character varying(10),
    max_age character varying(50),
    min_age character varying(50),
    name character varying(254),
    properties character varying(254),
    movement character varying(20),
    hwall_dir character varying(20),
    remarks character varying(254),
    reference character varying(254),
    map_id character varying(254),
    symbol character varying(20),
    shape_leng numeric,
    geom public.geometry(MultiLineString,4326),
    new_type text
);


CREATE SEQUENCE sources.bc_ware_lines_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.bc_ware_lines_gid_seq OWNED BY sources.bc_ware_lines.gid;


CREATE TABLE sources.bigbend (
    gid integer NOT NULL,
    unit character varying(15),
    desc_ character varying(200),
    shape_leng numeric,
    shape_area numeric,
    geom public.geometry(MultiPolygon,4326),
    age character varying(200),
    unit_name character varying(200),
    descrip text,
    early_id integer,
    late_id integer
);


CREATE SEQUENCE sources.bigbend_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.bigbend_gid_seq OWNED BY sources.bigbend.gid;


CREATE TABLE sources.bigbend_lines (
    gid integer NOT NULL,
    desc_ text,
    shape_leng numeric,
    geom public.geometry(MultiLineString,4326),
    new_type character varying(100),
    new_direction character varying(100),
    name_ character varying(100)
);


CREATE SEQUENCE sources.bigbend_lines_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.bigbend_lines_gid_seq OWNED BY sources.bigbend_lines.gid;


CREATE TABLE sources.blackhills (
    gid integer NOT NULL,
    area numeric,
    perimeter numeric,
    blk_poly1_ integer,
    blk_poly11 integer,
    unit character varying(25),
    name character varying(120),
    youngestage character varying(25),
    oldestage character varying(29),
    geom public.geometry(MultiPolygon,4326),
    description text,
    early_id integer,
    late_id integer,
    age text
);


CREATE TABLE sources.blackhills_lines (
    gid integer NOT NULL,
    fnode_ integer,
    tnode_ integer,
    lpoly_ integer,
    rpoly_ integer,
    length numeric,
    blk_line2_ integer,
    blk_line21 integer,
    type character varying(50),
    age character varying(50),
    name character varying(50),
    downthrown character varying(3),
    upthrown_s character varying(3),
    lat_displa character varying(5),
    fold_age character varying(10),
    dip_dir character varying(3),
    plunge_dir character varying(5),
    accuracy character varying(35),
    x_sect character varying(4),
    geom public.geometry(MultiLineString,4326),
    new_type text,
    new_direction text,
    descrip character varying(70)
);


CREATE SEQUENCE sources.blackhills_foldsfaults_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.blackhills_foldsfaults_gid_seq OWNED BY sources.blackhills_lines.gid;


CREATE SEQUENCE sources.blackhillsgeology_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.blackhillsgeology_gid_seq OWNED BY sources.blackhills.gid;


CREATE TABLE sources.boulder (
    gid integer NOT NULL,
    label character varying(10),
    mlabel character varying(10),
    des character varying(180),
    symbol smallint,
    pattern smallint,
    name character varying(254),
    age character varying(254),
    descrip character varying(254),
    geom public.geometry(MultiPolygon,4326),
    early_id integer,
    late_id integer,
    strat_name text
);


CREATE SEQUENCE sources.boulder_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.boulder_gid_seq OWNED BY sources.boulder.gid;


CREATE TABLE sources.boulder_lines (
    gid integer NOT NULL,
    fnode_ double precision,
    tnode_ double precision,
    lpoly_ double precision,
    rpoly_ double precision,
    length numeric,
    boulder_ double precision,
    boulder_id double precision,
    linecode smallint,
    name character varying(80),
    source smallint,
    symbol smallint,
    geom public.geometry(MultiLineString,4326)
);


CREATE SEQUENCE sources.boulder_lines_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.boulder_lines_gid_seq OWNED BY sources.boulder_lines.gid;


CREATE TABLE sources.brazil (
    gid integer NOT NULL,
    sigla_unid character varying(25),
    siglas_ant character varying(254),
    nome_unida character varying(254),
    cod_uni_es character varying(254),
    hierarquia character varying(254),
    idade_max numeric(10,0),
    erro_max numeric(10,0),
    eon_idad_m character varying(254),
    era_maxima character varying(254),
    periodo_ma character varying(254),
    epoca_max character varying(254),
    sistema_ge character varying(254),
    metodo_geo character varying(254),
    qlde_infer character varying(254),
    idade_min numeric(10,0),
    erro_min numeric(10,0),
    eon_idad_1 character varying(254),
    era_minima character varying(254),
    periodo_mi character varying(254),
    epoca_min character varying(254),
    sistema__1 character varying(254),
    metodo_g_1 character varying(254),
    qlde_inf_1 character varying(254),
    ambsedimen character varying(254),
    sistsedime character varying(254),
    tipo_depos character varying(254),
    assoc_magm character varying(254),
    nivel_crus character varying(254),
    textura_ig character varying(254),
    fonte_magm character varying(254),
    morfologia character varying(254),
    ambiente_t character varying(254),
    metamorfis character varying(254),
    metodo_g_2 character varying(254),
    temp_pico numeric(10,0),
    erro_temp_ numeric(10,0),
    pressao_pi numeric,
    erro_press numeric(10,0),
    tipo_baric character varying(254),
    trajetoria character varying(254),
    ambiente_1 character varying(254),
    litotipo1 character varying(254),
    litotipo2 character varying(254),
    classe_roc character varying(254),
    classe_r_1 character varying(254),
    bb_subclas character varying(254),
    bb_subcl_1 character varying(254),
    geom public.geometry(MultiPolygon,4326),
    early_id integer,
    late_id integer,
    age_max character varying(100),
    lith character varying(254),
    use_name character varying(254),
    litotipo1_eng character varying(254),
    use_name_eng character varying(254),
    geom_mod public.geometry(MultiPolygon,4326),
    strat_name text,
    age_min text,
    use_age text
);


CREATE SEQUENCE sources.brazil_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.brazil_gid_seq OWNED BY sources.brazil.gid;


CREATE TABLE sources.brazil_lines (
    gid integer NOT NULL,
    sigla_unid character varying(25),
    nome character varying(96),
    hierarquia character varying(34),
    idade_max double precision,
    eon_id_max character varying(12),
    era_maxima character varying(17),
    period_max character varying(19),
    epoca_max character varying(30),
    idade_min double precision,
    eon_id_min character varying(12),
    era_minima character varying(17),
    periodo_mi character varying(19),
    epoca_min character varying(30),
    assoc_magm character varying(77),
    nivel_crus character varying(33),
    text_ignea character varying(63),
    tipo character varying(255),
    litotipo1 character varying(216),
    classe_rx1 character varying(48),
    subcla_rx1 character varying(80),
    geom public.geometry(MultiLineString,4326),
    max_period text,
    min_period text,
    max_epoch text,
    min_epoch text,
    max_eon text,
    class_1 text,
    subclass_1 text,
    type text,
    age_max double precision,
    age_min double precision,
    hierarchy text,
    max_era text,
    min_era text,
    name text,
    descrip text,
    text_igneo text,
    min_eon text,
    lithtype_1 text,
    regime_tec text,
    evento_oro text,
    ang_norte integer,
    sentido_de text,
    trend text,
    legenda text,
    movement text,
    legend text,
    new_type text,
    geotec text,
    litotipo2 text,
    classe_rx2 text,
    lithtype_2 text,
    class_2 text,
    subclass_2 text,
    subcla_rx2 text,
    origem text,
    dip integer,
    age_desl integer,
    new_direction text
);


CREATE TABLE sources.brazil_sp (
    gid integer NOT NULL,
    sigla_unid character varying(30),
    siglas_ant character varying(254),
    nome_unida character varying(254),
    hierarquia character varying(254),
    idade_max numeric(10,0),
    erro_max numeric(10,0),
    eon_idad_m character varying(254),
    era_maxima character varying(254),
    periodo_ma character varying(254),
    epoca_max character varying(254),
    sistema_ge character varying(254),
    metodo_geo character varying(254),
    qlde_infer character varying(254),
    idade_min numeric(10,0),
    erro_min numeric(10,0),
    eon_idad_1 character varying(254),
    era_minima character varying(254),
    periodo_mi character varying(254),
    epoca_min character varying(254),
    sistema__1 character varying(254),
    metodo_g_1 character varying(254),
    qlde_inf_1 character varying(254),
    ambsedimen character varying(254),
    sistsedime character varying(254),
    tipo_depos character varying(254),
    assoc_magm character varying(254),
    nivel_crus character varying(254),
    textura_ig character varying(254),
    fonte_magm character varying(254),
    morfologia character varying(254),
    ambiente_t character varying(254),
    metamorfis character varying(254),
    metodo_g_2 character varying(254),
    temp_pico numeric(10,0),
    erro_temp_ numeric(10,0),
    pressao_pi numeric,
    erro_press numeric(10,0),
    tipo_baric character varying(254),
    trajetoria character varying(254),
    ambiente_1 character varying(254),
    litotipo1 character varying(254),
    litotipo2 character varying(254),
    classe_roc character varying(254),
    classe_r_1 character varying(254),
    bb_subclas character varying(254),
    bb_subcl_1 character varying(254),
    geom public.geometry(MultiPolygon,4326)
);


CREATE SEQUENCE sources.brazil_sp_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.brazil_sp_gid_seq OWNED BY sources.brazil_sp.gid;


CREATE TABLE sources.brycecanyon_lines (
    gid integer NOT NULL,
    objectid numeric(10,0),
    fuid numeric(10,0),
    name character varying(60),
    label character varying(60),
    shape_leng numeric,
    type character varying(254),
    subtype character varying(254),
    positionalaccuracy character varying(254),
    geom public.geometry(MultiLineString,4326),
    plunge text,
    age text,
    mjlith text,
    description text,
    new_type text,
    new_direction text
);


CREATE SEQUENCE sources.brycecanyon_faults_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.brycecanyon_faults_gid_seq OWNED BY sources.brycecanyon_lines.gid;


CREATE TABLE sources.brycecanyonnationalparkgeology (
    gid integer NOT NULL,
    objectid numeric(10,0),
    fuid numeric(10,0),
    glg_sym character varying(12),
    src_sym character varying(12),
    sort_no numeric,
    notes character varying(254),
    lbl character varying(60),
    gmap_id numeric(10,0),
    shape_leng numeric,
    shape_area numeric,
    objectid_1 integer,
    glg_sym_1 character varying(12),
    glg_name character varying(100),
    age character varying(100),
    mj_lith character varying(254),
    geom public.geometry(MultiPolygon,4326),
    description text,
    early_id integer,
    late_id integer
);


CREATE SEQUENCE sources.brycecanyonnationalparkgeology_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.brycecanyonnationalparkgeology_gid_seq OWNED BY sources.brycecanyonnationalparkgeology.gid;


CREATE TABLE sources.ca_cambria (
    gid integer NOT NULL,
    objectid numeric(10,0),
    area double precision,
    perimeter double precision,
    unit character varying(35),
    name text,
    age character varying(50),
    shape_leng numeric,
    shape_area numeric,
    geom public.geometry(MultiPolygon,4326),
    early_id integer,
    late_id integer,
    description text
);


CREATE TABLE sources.ca_cambria_lines (
    gid integer NOT NULL,
    objectid numeric(10,0),
    fnode_ numeric(10,0),
    tnode_ numeric(10,0),
    length double precision,
    type character varying(35),
    show_teeth character varying(5),
    shape_leng numeric,
    geom public.geometry(MultiLineString,4326),
    symb_vis text,
    new_type text,
    new_direction text
);


CREATE TABLE sources.ca_carizoplain_lines (
    gid integer NOT NULL,
    fnode_ numeric(10,0),
    tnode_ numeric(10,0),
    lpoly_ numeric(10,0),
    rpoly_ numeric(10,0),
    length double precision,
    of99_14_3a numeric(10,0),
    of99_14__1 numeric(10,0),
    ltype character varying(75),
    sel smallint,
    symb smallint,
    geom public.geometry(MultiLineString,4326),
    new_type text,
    name text,
    new_direction text
);


CREATE SEQUENCE sources.ca_carizonplains_geo_arc_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.ca_carizonplains_geo_arc_gid_seq OWNED BY sources.ca_carizoplain_lines.gid;


CREATE TABLE sources.ca_carizoplain (
    gid integer NOT NULL,
    area double precision,
    perimeter double precision,
    of99_14_3a numeric(10,0),
    of99_14__1 numeric(10,0),
    ptype character varying(35),
    sel smallint,
    symb smallint,
    geom public.geometry(MultiPolygon,4326),
    name text,
    age text,
    description text,
    strat_name text,
    hierarchy text,
    early_id integer,
    late_id integer
);


CREATE SEQUENCE sources.ca_carizonplains_geo_polygon_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.ca_carizonplains_geo_polygon_gid_seq OWNED BY sources.ca_carizoplain.gid;


CREATE TABLE sources.ca_carizoplain_points (
    gid integer NOT NULL,
    area double precision,
    perimeter double precision,
    of99_14_3b numeric(10,0),
    of99_14__1 numeric(10,0),
    pttype character varying(65),
    dip smallint,
    strike smallint,
    sel smallint,
    symb smallint,
    dipquery smallint,
    f_polygoni numeric(10,0),
    f_scale double precision,
    f_angle double precision,
    geom public.geometry(Point,4326),
    point_type text,
    dip_dir integer
);


CREATE SEQUENCE sources.ca_carizonplains_point_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.ca_carizonplains_point_gid_seq OWNED BY sources.ca_carizoplain_points.gid;


CREATE TABLE sources.ca_contracosta (
    gid integer NOT NULL,
    arcids character varying(254),
    area double precision,
    perimeter double precision,
    "cc_utm#" integer,
    "cc_utm-id" integer,
    ptype character varying(35),
    sel smallint,
    symb smallint,
    geom public.geometry(MultiPolygon,4326),
    name text,
    description text,
    "grouping" text,
    assemblage text,
    age text,
    early_id integer,
    late_id integer
);


CREATE TABLE sources.ca_contracosta_lines (
    gid integer NOT NULL,
    ltype character varying(55),
    geom public.geometry(MultiLineString,4326),
    name text,
    new_type text,
    new_direction text
);


CREATE TABLE sources.ca_elcajon (
    gid integer NOT NULL,
    area numeric,
    perimeter numeric,
    ec1_geo0_ numeric(10,0),
    ec1_geo0_i numeric(10,0),
    labl character varying(25),
    plabl character varying(25),
    name character varying(50),
    shd smallint,
    shdfil smallint,
    geom public.geometry(MultiPolygon,4326),
    age text,
    description text,
    strat_name text,
    hierarchy text,
    early_id integer,
    late_id integer
);


CREATE TABLE sources.ca_elcajon_lines (
    gid integer NOT NULL,
    fnode_ numeric(10,0),
    tnode_ numeric(10,0),
    lpoly_ numeric(10,0),
    rpoly_ numeric(10,0),
    length numeric,
    ec1_geo0_ numeric(10,0),
    ec1_geo0_i numeric(10,0),
    l_symb smallint,
    ltype text,
    geom public.geometry(MultiLineString,4326),
    new_type text
);


CREATE SEQUENCE sources.ca_elcajon_geo_arc_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.ca_elcajon_geo_arc_gid_seq OWNED BY sources.ca_elcajon_lines.gid;


CREATE SEQUENCE sources.ca_elcajon_geo_polygon_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.ca_elcajon_geo_polygon_gid_seq OWNED BY sources.ca_elcajon.gid;


CREATE TABLE sources.ca_funeralmtns (
    gid integer NOT NULL,
    unit character varying(15),
    "group" character varying(254),
    assemblage character varying(254),
    descriptio character varying(254),
    age character varying(254),
    shape_leng numeric,
    shape_area numeric,
    geom public.geometry(MultiPolygon,4326),
    descrip text,
    strat_name text,
    early_id integer,
    late_id integer
);


CREATE SEQUENCE sources.ca_funeralmtns_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.ca_funeralmtns_gid_seq OWNED BY sources.ca_funeralmtns.gid;


CREATE TABLE sources.ca_funeralmtns_lines (
    gid integer NOT NULL,
    descriptio character varying(100),
    shape_leng numeric,
    geom public.geometry(MultiLineString,4326),
    new_type text,
    new_direction text
);


CREATE SEQUENCE sources.ca_funeralmtns_lines_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.ca_funeralmtns_lines_gid_seq OWNED BY sources.ca_funeralmtns_lines.gid;


CREATE TABLE sources.ca_funeralmtns_points (
    gid integer NOT NULL,
    azimuth integer,
    dip integer,
    descriptio character varying(50),
    geom public.geometry(Point,4326),
    point_type text,
    dip_dir integer
);


CREATE SEQUENCE sources.ca_funeralmtns_points_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.ca_funeralmtns_points_gid_seq OWNED BY sources.ca_funeralmtns_points.gid;


CREATE TABLE sources.ca_long_beach (
    gid integer NOT NULL,
    objectid numeric(10,0),
    ptype character varying(50),
    feature_na character varying(100),
    descriptio character varying(100),
    author character varying(100),
    year_ integer,
    citation character varying(100),
    scale numeric(10,0),
    ref_ptype character varying(50),
    digital_pr character varying(50),
    base_map character varying(50),
    comments0 character varying(254),
    shape_leng numeric,
    shape_area numeric,
    geom public.geometry(MultiPolygon,4326),
    name text,
    description text,
    age text,
    comments text,
    strat_name text,
    hierarchy text,
    early_id integer,
    late_id integer
);


CREATE TABLE sources.ca_long_beach_lines (
    gid integer NOT NULL,
    objectid numeric(10,0),
    ltype character varying(65),
    feature_na character varying(85),
    author character varying(50),
    year_ integer,
    citation character varying(50),
    scale numeric(10,0),
    ref_ltype character varying(50),
    digital_pr character varying(50),
    base_map character varying(50),
    comments character varying(50),
    shape_leng numeric,
    geom public.geometry(MultiLineString,4326),
    new_type text,
    new_direction text
);


CREATE TABLE sources.ca_long_beach_points (
    gid integer NOT NULL,
    objectid numeric(10,0),
    pttype character varying(35),
    dip0 integer,
    strike0 integer,
    author character varying(50),
    year_ integer,
    citation character varying(50),
    scale numeric(10,0),
    ref_pttype character varying(50),
    comments character varying(254),
    geom public.geometry(Point,4326),
    point_type text,
    strike integer,
    dip integer,
    dip_dir integer
);


CREATE TABLE sources.ca_los_angeles (
    gid integer NOT NULL,
    area numeric,
    perimeter numeric,
    la1_geo0_ numeric(10,0),
    la1_geo0_i numeric(10,0),
    labl character varying(15),
    plabl character varying(20),
    shd smallint,
    shdfil smallint,
    name character varying(200),
    subunit character varying(100),
    geom public.geometry(MultiPolygon,4326),
    age text,
    description text,
    early_id integer,
    late_id integer,
    strat_name text,
    comments text,
    hierarchy text
);


CREATE TABLE sources.ca_los_angeles_lines (
    gid integer NOT NULL,
    fnode_ numeric(10,0),
    tnode_ numeric(10,0),
    lpoly_ numeric(10,0),
    rpoly_ numeric(10,0),
    length numeric,
    la1_geo0_ numeric(10,0),
    la1_geo0_i numeric(10,0),
    ltype character varying(45),
    l_name character varying(50),
    l_symb smallint,
    geom public.geometry(MultiLineString,4326),
    new_type text,
    new_direction text
);


CREATE TABLE sources.ca_marin (
    gid integer NOT NULL,
    area double precision,
    perimeter double precision,
    ma_geol0_ numeric(10,0),
    ma_geol0_i numeric(10,0),
    ptype character varying(35),
    geom public.geometry(MultiPolygon,4326),
    name character varying(155),
    age character varying(100),
    descrip text,
    early_id integer,
    late_id integer
);


CREATE TABLE sources.ca_marin_fixed (
    gid integer,
    area double precision,
    perimeter double precision,
    ma_geol0_ numeric(10,0),
    ma_geol0_i numeric(10,0),
    ptype character varying(35),
    geom public.geometry(MultiPolygon,4326),
    name character varying(155),
    age character varying(100),
    descrip text,
    early_id integer,
    late_id integer,
    strat_name text
);


CREATE TABLE sources.ca_marin_lines (
    gid integer NOT NULL,
    length double precision,
    ltype character varying(35),
    geom public.geometry(MultiLineString,4326),
    new_type text,
    new_direction text
);


CREATE TABLE sources.ca_marin_lines_fixed (
    gid integer,
    userid numeric(10,0),
    fnode_ numeric(10,0),
    tnode_ numeric(10,0),
    lpoly_ numeric(10,0),
    rpoly_ numeric(10,0),
    length double precision,
    ma_terr3_ integer,
    ma_terr3_i integer,
    ltype character varying(35),
    ma_geol5_ integer,
    ma_geol5_i integer,
    geom public.geometry(MultiLineString,4326),
    new_type text,
    new_direction text
);


CREATE TABLE sources.ca_marin_lines_nad27 (
    gid integer NOT NULL,
    userid numeric(10,0),
    fnode_ numeric(10,0),
    tnode_ numeric(10,0),
    lpoly_ numeric(10,0),
    rpoly_ numeric(10,0),
    length double precision,
    ma_terr3_ integer,
    ma_terr3_i integer,
    ltype character varying(35),
    ma_geol5_ integer,
    ma_geol5_i integer,
    geom public.geometry(MultiLineString,4326)
);


CREATE SEQUENCE sources.ca_marin_lines_nad27_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.ca_marin_lines_nad27_gid_seq OWNED BY sources.ca_marin_lines_nad27.gid;


CREATE TABLE sources.ca_marin_nad27 (
    gid integer NOT NULL,
    area double precision,
    perimeter double precision,
    ma_geol0_ numeric(10,0),
    ma_geol0_i numeric(10,0),
    ptype character varying(35),
    geom public.geometry(MultiPolygon,4326)
);


CREATE SEQUENCE sources.ca_marin_nad27_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.ca_marin_nad27_gid_seq OWNED BY sources.ca_marin_nad27.gid;


CREATE TABLE sources.ca_monterey (
    gid integer NOT NULL,
    ptype character varying(35),
    shape_leng numeric,
    shape_area numeric,
    geom public.geometry(MultiPolygon,4326),
    name text,
    age text,
    description text,
    strat_name text,
    hierarchy text,
    early_id integer,
    late_id integer
);


CREATE TABLE sources.ca_monterey_lines (
    ltype character varying(35),
    shape_leng numeric,
    geom public.geometry(MultiLineString,4326),
    new_type text,
    gid integer NOT NULL
);


CREATE SEQUENCE sources.ca_monterey_lines_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.ca_monterey_lines_gid_seq OWNED BY sources.ca_monterey_lines.gid;


CREATE SEQUENCE sources.ca_monterrey_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.ca_monterrey_gid_seq OWNED BY sources.ca_monterey.gid;


CREATE TABLE sources.ca_napa (
    gid integer NOT NULL,
    objectid numeric,
    ptype character varying(35),
    author character varying(50),
    year_ numeric(10,0),
    citation character varying(50),
    scale numeric(10,0),
    ref_ptype character varying(35),
    digital_pr character varying(50),
    base_map character varying(50),
    comments character varying(50),
    ptype_100k character varying(35),
    label_100k character varying(35),
    orig_fid numeric(10,0),
    shape_leng numeric,
    shape_area numeric,
    geom public.geometry(MultiPolygon,4326),
    name text,
    strat_name text,
    hierarchy text,
    age text,
    description text,
    early_id integer,
    late_id integer
);


CREATE SEQUENCE sources.ca_napa_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.ca_napa_gid_seq OWNED BY sources.ca_napa.gid;


CREATE TABLE sources.ca_napa_lines (
    objectid numeric,
    ltype character varying(50),
    feature_na character varying(50),
    author character varying(50),
    year_ numeric(10,0),
    citation character varying(50),
    scale numeric(10,0),
    ref_ltype character varying(50),
    digital_pr character varying(50),
    base_map character varying(50),
    comments character varying(50),
    shape_leng numeric,
    geom public.geometry(MultiLineString,4326),
    new_direction text,
    new_type text,
    gid integer NOT NULL
);


CREATE SEQUENCE sources.ca_napa_lines_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.ca_napa_lines_gid_seq OWNED BY sources.ca_napa_lines.gid;


CREATE TABLE sources.ca_napa_points (
    gid integer NOT NULL,
    objectid numeric,
    pttype character varying(35),
    dip numeric(10,0),
    strike numeric(10,0),
    author character varying(50),
    year_ numeric(10,0),
    citation character varying(50),
    scale numeric(10,0),
    ref_pttype character varying(50),
    comments character varying(254),
    display_10 character varying(1),
    sel numeric(10,0),
    symb numeric(10,0),
    orig_fid numeric(10,0),
    geom public.geometry(Point,4326),
    point_type text,
    dip_dir integer
);


CREATE SEQUENCE sources.ca_napa_points_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.ca_napa_points_gid_seq OWNED BY sources.ca_napa_points.gid;


CREATE TABLE sources.ca_north_santabarb (
    gid integer NOT NULL,
    area numeric,
    perimeter numeric,
    geo1_ double precision,
    geo1_id double precision,
    ru_labl character varying(10),
    ru_name character varying(200),
    member character varying(200),
    subunit character varying(200),
    plabl character varying(10),
    shd_wpgcmy smallint,
    age character varying(50),
    domain text,
    geom public.geometry(MultiPolygon,4326),
    description text,
    comments text,
    early_id integer,
    late_id integer
);


CREATE TABLE sources.ca_north_santabarb_lines (
    gid integer NOT NULL,
    name character varying(150),
    descr character varying(200),
    geom public.geometry(MultiLineString,4326),
    ru_labl text,
    ru_name text,
    member text,
    new_type text,
    new_direction text
);


CREATE TABLE sources.ca_northeastsanfran (
    ptype character varying(35),
    name text,
    age text,
    description text,
    assemblage text,
    early_id integer,
    late_id integer,
    geom public.geometry,
    gid integer NOT NULL
);


CREATE TABLE sources.ca_northeastsanfran_lines (
    gid integer NOT NULL,
    ltype character varying(55),
    geom public.geometry(MultiLineString,4326),
    new_type text,
    new_direction text
);


CREATE SEQUENCE sources.ca_northeastsanfran_union_gid_new_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.ca_northeastsanfran_union_gid_new_seq OWNED BY sources.ca_northeastsanfran.gid;


CREATE TABLE sources.ca_northofsanfran (
    gid integer NOT NULL,
    area double precision,
    perimeter double precision,
    wso_geol0_ numeric(10,0),
    wso_geol01 numeric(10,0),
    ptype character varying(35),
    geom public.geometry(MultiPolygon,4326),
    name text,
    age text,
    description text,
    early_id integer,
    late_id integer
);


CREATE TABLE sources.ca_northofsanfran_lines (
    gid integer NOT NULL,
    length double precision,
    ltype character varying(35),
    faultname character varying(35),
    geom public.geometry(MultiLineString,4326),
    new_type text,
    new_direction text
);


CREATE TABLE sources.ca_oakland (
    gid integer NOT NULL,
    area double precision,
    perimeter double precision,
    ri_geol0_ numeric(10,0),
    ri_geol0_i numeric(10,0),
    ptype character varying(100),
    geom public.geometry(MultiPolygon,4326),
    descrip text,
    age text,
    gruping text,
    title text,
    early_id integer,
    late_id integer
);


CREATE TABLE sources.ca_oakland_lines (
    gid integer,
    fnode_ numeric(10,0),
    tnode_ numeric(10,0),
    lpoly_ numeric(10,0),
    rpoly_ numeric(10,0),
    length double precision,
    bv_geol0_ numeric(10,0),
    bv_geol0_i numeric(10,0),
    ltype character varying(55),
    new_type text,
    new_direction text,
    name character varying(65),
    geom public.geometry
);


CREATE TABLE sources.ca_oakland_unioned (
    descrip text,
    age text,
    gruping text,
    title text,
    early_id integer,
    late_id integer,
    geom public.geometry,
    gid integer NOT NULL
);


CREATE SEQUENCE sources.ca_oakland_unioned_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.ca_oakland_unioned_gid_seq OWNED BY sources.ca_oakland_unioned.gid;


CREATE TABLE sources.ca_oceanside (
    gid integer NOT NULL,
    ptype character varying(50),
    shape_leng numeric,
    shape_area numeric,
    geom public.geometry(MultiPolygon,4326),
    name text,
    description text,
    strat_name text,
    hierarchy text,
    age text,
    early_id integer,
    late_id integer
);


CREATE TABLE sources.ca_oceanside_lines (
    gid integer NOT NULL,
    ltype character varying(50),
    citation character varying(50),
    shape_leng numeric,
    geom public.geometry(MultiLineString,4326),
    new_type text,
    new_direction text
);


CREATE TABLE sources.ca_oceanside_points (
    gid integer NOT NULL,
    pttype character varying(60),
    dip smallint,
    strike smallint,
    geom public.geometry(Point,4326),
    point_type text,
    dip_dir integer
);


CREATE TABLE sources.ca_point_reyes (
    gid integer NOT NULL,
    area double precision,
    perimeter double precision,
    pr_geol0_ numeric(10,0),
    pr_geol0_i numeric(10,0),
    ptype character varying(35),
    sel smallint,
    symb smallint,
    geom public.geometry(MultiPolygon,4326),
    name text,
    age text,
    age_bottom text,
    age_top text,
    comments text,
    descrip text,
    strat_name text,
    late_id integer,
    early_id integer
);


CREATE SEQUENCE sources.ca_point_reyes_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.ca_point_reyes_gid_seq OWNED BY sources.ca_point_reyes.gid;


CREATE TABLE sources.ca_point_reyes_lines (
    gid integer,
    pr_strc0_ numeric(10,0),
    ltype character varying(65),
    sel smallint,
    symb smallint,
    geom public.geometry(MultiLineString,4326),
    new_type character varying(65),
    new_direction character varying(65),
    name character varying(65)
);


CREATE TABLE sources.ca_providence_mtns (
    gid integer NOT NULL,
    ptype character varying(254),
    geofnt character varying(254),
    shape_leng numeric,
    shape_area numeric,
    geom public.geometry(MultiPolygon,4326),
    name text,
    strat_name text,
    age text,
    descrip text,
    early_id integer,
    late_id integer
);


CREATE SEQUENCE sources.ca_providence_mtns_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.ca_providence_mtns_gid_seq OWNED BY sources.ca_providence_mtns.gid;


CREATE TABLE sources.ca_providence_mtns_lines (
    gid integer NOT NULL,
    ltype character varying(35),
    shape_leng numeric,
    geom public.geometry(MultiLineString,4326),
    new_type text,
    new_dir text,
    descrip text
);


CREATE SEQUENCE sources.ca_providence_mtns_lines_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.ca_providence_mtns_lines_gid_seq OWNED BY sources.ca_providence_mtns_lines.gid;


CREATE TABLE sources.ca_providence_mtns_points (
    gid integer NOT NULL,
    dip smallint,
    strike smallint,
    pttype character varying(35),
    geom public.geometry(Point,4326),
    point_type text,
    dip_dir integer
);


CREATE SEQUENCE sources.ca_providence_mtns_points_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.ca_providence_mtns_points_gid_seq OWNED BY sources.ca_providence_mtns_points.gid;


CREATE TABLE sources.ca_providencemountains (
    gid integer NOT NULL,
    ptype character varying(254),
    geofnt character varying(254),
    shape_leng numeric,
    shape_area numeric,
    geom public.geometry(MultiPolygon,4326),
    name text,
    age text,
    description text,
    strat_name text,
    hierarchy text,
    early_id integer,
    late_id integer
);


CREATE TABLE sources.ca_providencemountains_lines (
    gid integer NOT NULL,
    ltype character varying(35),
    shape_leng numeric,
    geom public.geometry(MultiLineString,4326),
    new_type text,
    descrip text
);


CREATE SEQUENCE sources.ca_providencemountains_arc_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.ca_providencemountains_arc_gid_seq OWNED BY sources.ca_providencemountains_lines.gid;


CREATE SEQUENCE sources.ca_providencemountains_polygon_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.ca_providencemountains_polygon_gid_seq OWNED BY sources.ca_providencemountains.gid;


CREATE TABLE sources.ca_san_diego (
    gid integer,
    objectid numeric,
    ptype character varying(35),
    name text,
    age text,
    description text,
    geom public.geometry(MultiPolygon,4326),
    strat_name text,
    early_id integer,
    late_id integer
);


CREATE TABLE sources.ca_san_diego_lines (
    gid integer NOT NULL,
    objectid numeric,
    ltype character varying(35),
    source character varying(35),
    geom public.geometry(MultiLineString,4326),
    new_type text,
    new_direction text
);


CREATE TABLE sources.ca_san_diego_points (
    gid integer NOT NULL,
    objectid numeric,
    pttype character varying(35),
    dip numeric(10,0),
    strike numeric(10,0),
    geom public.geometry(Point,4326),
    point_type text
);


CREATE TABLE sources.ca_sanberno (
    gid integer NOT NULL,
    area numeric,
    perimeter numeric,
    sasb_geo_ double precision,
    sasb_geo_i double precision,
    ru_labl character varying(35),
    ru_name character varying(200),
    subunit character varying(100),
    grain_size character varying(100),
    grsize_lab character varying(10),
    plabl character varying(35),
    assemblage character varying(200),
    maparea_id character varying(100),
    geom public.geometry(MultiPolygon,4326),
    early_id integer,
    late_id integer,
    age text,
    descrip text
);


CREATE TABLE sources.ca_sanberno_lines (
    gid integer NOT NULL,
    fnode_ double precision,
    tnode_ double precision,
    lpoly_ double precision,
    rpoly_ double precision,
    length numeric,
    sasb_geo_ double precision,
    sasb_geo_i double precision,
    l_symb smallint,
    descr character varying(150),
    l_name character varying(200),
    lith_descr character varying(240),
    geom public.geometry(MultiLineString,4326),
    type character varying(150),
    direction character varying(150)
);


CREATE TABLE sources.ca_sanjose (
    gid integer NOT NULL,
    area double precision,
    perimeter double precision,
    sj_geold_ double precision,
    sj_geold_i double precision,
    ptype character varying(35),
    geom public.geometry(MultiPolygon,4326),
    name text,
    age text,
    description text,
    block text,
    early_id integer,
    late_id integer
);


CREATE TABLE sources.ca_sanjose_lines (
    gid integer NOT NULL,
    fnode_ double precision,
    tnode_ double precision,
    lpoly_ double precision,
    rpoly_ double precision,
    length double precision,
    sj_geold_ double precision,
    sj_geold_i double precision,
    ltype character varying(35),
    geom public.geometry(MultiLineString,4326),
    new_type text,
    new_direction text
);


CREATE TABLE sources.ca_sanmateo (
    gid integer NOT NULL,
    area double precision,
    perimeter double precision,
    sm_um_py0_ numeric(10,0),
    sm_um_py01 numeric(10,0),
    ptype character varying(35),
    sel smallint,
    symb smallint,
    geom public.geometry(MultiPolygon,4326),
    name text,
    age text,
    description text,
    early_id integer,
    late_id integer
);


CREATE TABLE sources.ca_sanmateo_lines (
    gid integer NOT NULL,
    length double precision,
    ltype character varying(55),
    sel smallint,
    symb smallint,
    geom public.geometry(MultiLineString,4326),
    new_type text,
    new_direction text,
    name text
);


CREATE TABLE sources.ca_santabarbara (
    gid integer NOT NULL,
    objectid numeric,
    ptype character varying(35),
    author character varying(50),
    year_ numeric(10,0),
    citation character varying(50),
    scale numeric(10,0),
    ref_ptype character varying(35),
    digital_pr character varying(50),
    base_map character varying(50),
    comments character varying(50),
    orig_fid numeric(10,0),
    shape_leng numeric,
    shape_area numeric,
    geom public.geometry(MultiPolygon,4326),
    name text,
    age text,
    description text,
    strat_name text,
    hierarchy text,
    early_id integer,
    late_id integer
);


CREATE TABLE sources.ca_santabarbara_lines (
    gid integer NOT NULL,
    objectid numeric,
    ltype character varying(50),
    feature_na character varying(50),
    author character varying(50),
    year_ numeric(10,0),
    citation character varying(50),
    scale numeric(10,0),
    ref_ltype character varying(50),
    digital_pr character varying(50),
    base_map character varying(50),
    comments character varying(254),
    shape_leng numeric,
    geom public.geometry(MultiLineString,4326),
    new_type text
);


CREATE SEQUENCE sources.ca_santabarbara_geol_arc_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.ca_santabarbara_geol_arc_gid_seq OWNED BY sources.ca_santabarbara_lines.gid;


CREATE SEQUENCE sources.ca_santabarbara_geol_polygon_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.ca_santabarbara_geol_polygon_gid_seq OWNED BY sources.ca_santabarbara.gid;


CREATE TABLE sources.ca_santabarbara_points (
    gid integer NOT NULL,
    objectid numeric,
    pttype character varying(35),
    dip numeric(10,0),
    strike numeric(10,0),
    author character varying(50),
    year_ numeric(10,0),
    citation character varying(50),
    scale numeric(10,0),
    ref_pttype character varying(50),
    comments character varying(254),
    display_10 numeric(10,0),
    dib_dip numeric(10,0),
    dib_strike numeric(10,0),
    dib_dist numeric,
    geom public.geometry(Point,4326),
    point_type text,
    dip_dir integer
);


CREATE SEQUENCE sources.ca_santabarbara_structure_point_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.ca_santabarbara_structure_point_gid_seq OWNED BY sources.ca_santabarbara_points.gid;


CREATE TABLE sources.ca_santacruz (
    gid integer NOT NULL,
    area double precision,
    perimeter double precision,
    geology_ numeric(10,0),
    geology_id numeric(10,0),
    ptype character varying(35),
    sel smallint,
    symb smallint,
    geom public.geometry(MultiPolygon,4326),
    name character varying(55),
    age character varying(35),
    descrip text,
    early_id integer,
    late_id integer,
    strat_name text
);


CREATE TABLE sources.ca_santacruz_lines (
    gid integer NOT NULL,
    ltype character varying(35),
    geom public.geometry(MultiLineString,4326),
    new_type text,
    new_direction text
);


CREATE TABLE sources.ca_southsanfran (
    gid integer NOT NULL,
    area numeric,
    perimeter numeric,
    sfs_geol0_ numeric(10,0),
    sfs_geol01 numeric(10,0),
    ptype character varying(35),
    sel smallint,
    symb smallint,
    geom public.geometry(MultiPolygon,4326),
    name text,
    age text,
    description text,
    "grouping" text,
    early_id integer,
    late_id integer
);


CREATE TABLE sources.ca_southsanfran_lines (
    gid integer NOT NULL,
    __gid numeric(10,0),
    length numeric,
    ltype character varying(55),
    name character varying(254),
    new_type character varying(254),
    new_direction character varying(254),
    geom public.geometry(MultiLineString,4326)
);


CREATE TABLE sources.ca_yosemite (
    gid integer,
    yosenp0_ numeric(10,0),
    yosenp0_id numeric(10,0),
    ptype character varying(35),
    geom public.geometry(MultiPolygon,4326),
    symbol text,
    name text,
    age text,
    age_top text,
    age_bottom text,
    descrip text,
    comments text,
    late_id integer,
    early_id integer
);


CREATE TABLE sources.ca_yosemite_lines (
    gid integer NOT NULL,
    userid numeric(10,0),
    fnode_ numeric(10,0),
    tnode_ numeric(10,0),
    lpoly_ numeric(10,0),
    rpoly_ numeric(10,0),
    length double precision,
    "geo#" integer,
    "geo-id" integer,
    ltype character varying(20),
    geom public.geometry(MultiLineString,4326),
    new_type character varying(40),
    new_direction character varying(40)
);


CREATE SEQUENCE sources.ca_yosemite_lines_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.ca_yosemite_lines_gid_seq OWNED BY sources.ca_yosemite_lines.gid;


CREATE TABLE sources.ca_yosemite_units (
    gid integer NOT NULL,
    yosenp0_ numeric(10,0),
    yosenp0_id numeric(10,0),
    ptype character varying(35),
    geom public.geometry(MultiPolygon,4326)
);


CREATE SEQUENCE sources.ca_yosemite_units_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.ca_yosemite_units_gid_seq OWNED BY sources.ca_yosemite_units.gid;


CREATE SEQUENCE sources.cambria_faults_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.cambria_faults_gid_seq OWNED BY sources.ca_cambria_lines.gid;


CREATE SEQUENCE sources.cambriacageology_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.cambriacageology_gid_seq OWNED BY sources.ca_cambria.gid;


CREATE TABLE sources.catalunya50k (
    gid integer NOT NULL,
    codi_cas character varying(15),
    descripcio character varying(250),
    claslitoed character varying(250),
    era character varying(50),
    periode character varying(50),
    epoca character varying(50),
    edat character varying(50),
    met character varying(50),
    protolit character varying(15),
    edat_met character varying(50),
    geom public.geometry(MultiPolygonZM,4326),
    descripcio_en text,
    claslitoed_en text,
    age text,
    early_id integer,
    late_id integer,
    strat_name text
);


CREATE TABLE sources.catalunya50k_lines (
    gid integer NOT NULL,
    codi_cas character varying(15),
    descripcio character varying(250),
    geom public.geometry(MultiLineString,4326),
    new_type text,
    description text
);


CREATE SEQUENCE sources.catalunya50k_lines_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.catalunya50k_lines_gid_seq OWNED BY sources.catalunya50k_lines.gid;


CREATE SEQUENCE sources.catalunya50k_redo_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.catalunya50k_redo_gid_seq OWNED BY sources.catalunya50k.gid;


CREATE TABLE sources.co_arkansa_riv (
    gid integer NOT NULL,
    source integer,
    label character varying(10),
    mlabel character varying(10),
    desc_ character varying(150),
    symbol integer,
    pattern integer,
    shape_leng numeric,
    shape_area numeric,
    geom public.geometry(MultiPolygon,4326),
    age text,
    descrip text,
    strat_name text,
    early_id integer,
    late_id integer
);


CREATE SEQUENCE sources.co_arkansa_riv_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.co_arkansa_riv_gid_seq OWNED BY sources.co_arkansa_riv.gid;


CREATE TABLE sources.co_arkansa_riv_lines (
    gid integer NOT NULL,
    linecode bigint,
    name character varying(100),
    source bigint,
    symbol bigint,
    shape_leng numeric,
    geom public.geometry(MultiLineString,4326),
    new_type text,
    new_direction text
);


CREATE SEQUENCE sources.co_arkansa_riv_lines_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.co_arkansa_riv_lines_gid_seq OWNED BY sources.co_arkansa_riv_lines.gid;


CREATE TABLE sources.co_arkansa_riv_points (
    gid integer NOT NULL,
    pttype character varying(100),
    symbol integer,
    strike integer,
    dip integer,
    source integer,
    geom public.geometry(Point,4326),
    point_type text,
    dip_dir integer
);


CREATE SEQUENCE sources.co_arkansa_riv_points_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.co_arkansa_riv_points_gid_seq OWNED BY sources.co_arkansa_riv_points.gid;


CREATE TABLE sources.co_denver (
    gid integer NOT NULL,
    area numeric,
    perimeter numeric,
    denver double precision,
    denver_id double precision,
    source smallint,
    label character varying(10),
    mlabel character varying(10),
    symbol smallint,
    pattern smallint,
    geom public.geometry(MultiPolygon,4326),
    name text,
    age text,
    description text,
    early_id integer,
    late_id integer
);


CREATE TABLE sources.co_ftcollins (
    gid integer NOT NULL,
    objectid numeric,
    shape_leng numeric,
    shape_area numeric,
    mapunit character varying(10),
    identityco character varying(50),
    label character varying(50),
    symbol character varying(254),
    datasource character varying(50),
    notes character varying(254),
    mapunitpol character varying(50),
    name character varying(254),
    fullname character varying(254),
    age character varying(254),
    geom public.geometry(MultiPolygon,4326),
    descrip text,
    strat_name text,
    early_id integer,
    late_id integer,
    lith text
);


CREATE SEQUENCE sources.co_ftcollins_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.co_ftcollins_gid_seq OWNED BY sources.co_ftcollins.gid;


CREATE TABLE sources.co_ftcollins_lines (
    gid integer NOT NULL,
    objectid numeric,
    shape_leng numeric,
    type character varying(254),
    isconceale character varying(1),
    locationco numeric,
    existencec character varying(150),
    identityco character varying(150),
    symbol character varying(254),
    label character varying(150),
    datasource character varying(150),
    notes character varying(254),
    contactsan character varying(150),
    mapunit character varying(150),
    name character varying(254),
    fullname character varying(254),
    age character varying(254),
    geom public.geometry(MultiLineString,4326),
    new_type text,
    new_direction text
);


CREATE SEQUENCE sources.co_ftcollins_lines_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.co_ftcollins_lines_gid_seq OWNED BY sources.co_ftcollins_lines.gid;


CREATE TABLE sources.co_ftcollins_points (
    gid integer NOT NULL,
    objectid numeric,
    type character varying(254),
    azimuth numeric,
    inclinatio numeric,
    symbol character varying(254),
    label character varying(50),
    locationco numeric,
    identityco character varying(50),
    orientatio numeric,
    plotatscal numeric,
    stationid character varying(50),
    mapunit character varying(10),
    locationso character varying(50),
    orientat_1 character varying(50),
    notes character varying(254),
    orientat_2 character varying(50),
    geom public.geometry(Point,4326),
    point_type text,
    dip_dir integer
);


CREATE SEQUENCE sources.co_ftcollins_points_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.co_ftcollins_points_gid_seq OWNED BY sources.co_ftcollins_points.gid;


CREATE TABLE sources.co_grandjunction (
    gid integer NOT NULL,
    area double precision,
    perimeter double precision,
    gran_geo0_ numeric(10,0),
    gran_geo01 numeric(10,0),
    type character varying(32),
    quad character varying(2),
    code character varying(5),
    geom public.geometry(MultiPolygon,4326),
    name text,
    strat_name text,
    hierarchy text,
    description text,
    lithology text,
    age text,
    early_id integer,
    late_id integer
);


CREATE TABLE sources.co_grandjunction_lines (
    gid integer NOT NULL,
    fnode_ numeric(10,0),
    tnode_ numeric(10,0),
    lpoly_ numeric(10,0),
    rpoly_ numeric(10,0),
    length double precision,
    gran_flt0_ numeric(10,0),
    gran_flt01 numeric(10,0),
    type character varying(55),
    geom public.geometry(MultiLineString,4326),
    new_type text
);


CREATE TABLE sources.co_greatsanddunes (
    gid integer NOT NULL,
    objectid integer,
    unit character varying(25),
    notes character varying(50),
    name character varying(254),
    age character varying(254),
    lithology character varying(100),
    shape_leng numeric,
    shape_area numeric,
    geom public.geometry(MultiPolygon,4326),
    strat_name text,
    hierarchy text,
    late_id integer,
    early_id integer,
    description text
);


CREATE TABLE sources.co_greatsanddunes_lines (
    gid integer NOT NULL,
    objectid integer,
    descriptio character varying(100),
    shape_leng numeric,
    geom public.geometry(MultiLineString,4326),
    new_type text
);


CREATE SEQUENCE sources.co_greatsanddunes_lines_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.co_greatsanddunes_lines_gid_seq OWNED BY sources.co_greatsanddunes_lines.gid;


CREATE TABLE sources.co_homestake (
    gid integer NOT NULL,
    mapunit character varying(100) NOT NULL,
    name character varying(250) NOT NULL,
    age character varying(100),
    identityconfidence character varying(50) NOT NULL,
    label character varying(100),
    symbol character varying(50),
    datasourceid character varying(25) DEFAULT 'This Report'::character varying NOT NULL,
    notes character varying(250),
    mapunitpolys_id character varying(25) NOT NULL,
    shape_length double precision,
    shape_area double precision,
    shape public.geometry(MultiPolygon,26713),
    geom public.geometry,
    descrip text,
    early_id integer,
    late_id integer,
    strat_name text
);


CREATE TABLE sources.co_homestake_lines (
    gid integer NOT NULL,
    type character varying(100) NOT NULL,
    isconcealed character varying(5) NOT NULL,
    locationconfidencemeters real DEFAULT '-9'::integer NOT NULL,
    existenceconfidence character varying(50) NOT NULL,
    identityconfidence character varying(50) NOT NULL,
    symbol character varying(50),
    label character varying(250),
    datasourceid character varying(50) NOT NULL,
    notes character varying(250),
    shape_length double precision,
    description character varying(250),
    shape public.geometry(MultiLineString,26713),
    geom public.geometry,
    new_type text
);


CREATE SEQUENCE sources.co_homestake_lines_objectid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.co_homestake_lines_objectid_seq OWNED BY sources.co_homestake_lines.gid;


CREATE SEQUENCE sources.co_homestake_objectid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.co_homestake_objectid_seq OWNED BY sources.co_homestake.gid;


CREATE TABLE sources.co_homestake_points (
    gid integer NOT NULL,
    type character varying(100) NOT NULL,
    azimuth real NOT NULL,
    inclination real NOT NULL,
    symbol character varying(50),
    label character varying(250),
    locationconfidencemeters real NOT NULL,
    identityconfidence character varying(50) NOT NULL,
    orientationconfidencedegrees real NOT NULL,
    stationid character varying(50),
    mapunit character varying(50),
    locationsourceid character varying(50) NOT NULL,
    orientationsourceid character varying(50) NOT NULL,
    notes character varying(250),
    orientationpoints_id character varying(50) NOT NULL,
    datasourceid character varying(25),
    shape public.geometry(MultiPoint,26713),
    geom public.geometry,
    new_type text,
    dip_dir real
);


CREATE SEQUENCE sources.co_homestake_points_objectid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.co_homestake_points_objectid_seq OWNED BY sources.co_homestake_points.gid;


CREATE TABLE sources.colombia (
    gid integer NOT NULL,
    objectid numeric(10,0),
    simbolouc character varying(254),
    descripcio character varying(254),
    edad character varying(254),
    ugintegrad character varying(254),
    "shape.area" numeric,
    "shape.len" numeric,
    comentario character varying(254),
    geom public.geometry(MultiPolygon,4326),
    name_obs text,
    strat_name text,
    hierarchy text,
    age text,
    description text,
    comments text,
    early_id integer,
    late_id integer
);


CREATE TABLE sources.colombia_lines (
    gid integer NOT NULL,
    objectid numeric(10,0),
    "shape.len" numeric,
    tipo character varying(254),
    nombrefall character varying(254),
    geom public.geometry(MultiLineString,4326),
    tectonica text,
    new_type text,
    description text,
    use_type text
);


CREATE SEQUENCE sources.colombia_faults_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.colombia_faults_gid_seq OWNED BY sources.colombia_lines.gid;


CREATE SEQUENCE sources.colombia_geo_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.colombia_geo_gid_seq OWNED BY sources.colombia.gid;


CREATE TABLE sources.congareenationalpark_lines (
    gid integer NOT NULL,
    objectid numeric(10,0),
    fuid numeric(10,0),
    ftype integer,
    fsubtype integer,
    pos integer,
    name character varying(60),
    notes character varying(254),
    label character varying(60),
    gmap_id numeric(10,0),
    shape_leng numeric,
    "position" character varying(254),
    type character varying(254),
    subtype character varying(254),
    geom public.geometry(MultiLineString,4326),
    new_type text,
    new_direction text
);


CREATE SEQUENCE sources.congaree_lines_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.congaree_lines_gid_seq OWNED BY sources.congareenationalpark_lines.gid;


CREATE TABLE sources.congareenationalparkgeology (
    gid integer NOT NULL,
    objectid numeric(10,0),
    fuid numeric(10,0),
    glg_sym character varying(12),
    src_sym character varying(12),
    sort_no numeric,
    notes character varying(254),
    lbl character varying(60),
    gmap_id numeric(10,0),
    shape_leng numeric,
    shape_area numeric,
    glg_name character varying(100),
    age character varying(100),
    mj_lith character varying(3),
    lith_type character varying(254),
    geom public.geometry(MultiPolygon,4326),
    description text,
    early_id integer,
    late_id integer
);


CREATE SEQUENCE sources.congareenationalparkgeology_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.congareenationalparkgeology_gid_seq OWNED BY sources.congareenationalparkgeology.gid;


CREATE SEQUENCE sources.contracostafaults_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.contracostafaults_gid_seq OWNED BY sources.ca_contracosta_lines.gid;


CREATE SEQUENCE sources.contracostageology_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.contracostageology_gid_seq OWNED BY sources.ca_contracosta.gid;


CREATE TABLE sources.dane_co (
    gid integer NOT NULL,
    unitcode character varying(25),
    shape_leng numeric,
    shape_area numeric,
    unitid character varying(25),
    name character varying(254),
    desc_ character varying(254),
    agedisplay character varying(128),
    geom public.geometry(MultiPolygon,4326),
    early_id integer,
    strat_name text,
    hierarchy text
);


CREATE SEQUENCE sources.dane_co_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.dane_co_gid_seq OWNED BY sources.dane_co.gid;


CREATE TABLE sources.dane_faults (
    gid integer NOT NULL,
    type integer,
    feature integer,
    conf integer,
    maptext character varying(250),
    shape_leng numeric,
    geom public.geometry(MultiLineString,4326)
);


CREATE SEQUENCE sources.dane_faults_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.dane_faults_gid_seq OWNED BY sources.dane_faults.gid;


CREATE TABLE sources.dc_bedrock (
    gid integer,
    surficial0 numeric(10,0),
    surficia_1 numeric(10,0),
    mapunit character varying(10),
    symbol smallint,
    bedrock0_ numeric(10,0),
    bedrock0_i numeric(10,0),
    retro_min character varying(45),
    m_age_ref character varying(35),
    namerank character varying(50),
    formal character varying(50),
    description text,
    strat_name character varying(254),
    coa_id numeric(10,0),
    stratseq numeric(10,0),
    minstrat character varying(35),
    maxstrat character varying(35),
    minsource numeric(10,0),
    maxsource numeric(10,0),
    name character varying(60),
    type character varying(254),
    clastlith character varying(254),
    clastrank character varying(254),
    cement character varying(254),
    mineral character varying(254),
    minrank character varying(254),
    rockclass character varying(35),
    province integer,
    age character varying(35),
    fossil character varying(70),
    fossilref character varying(35),
    ageextrap character varying(35),
    origin character varying(60),
    resource character varying(65),
    res_ref character varying(35),
    color character varying(35),
    thickaprx character varying(50),
    thickmin numeric,
    thickmax numeric,
    thickrange character varying(35),
    bedding character varying(60),
    contup character varying(30),
    contlow character varying(30),
    defevent character varying(35),
    geom public.geometry(MultiPolygon,4326),
    rockname text,
    lithclass text,
    lithform text,
    lithrank text,
    rockrank text,
    early_id integer,
    late_id integer,
    sourceid numeric(10,0),
    sourceauthor text,
    sourcedate text,
    organizationid text,
    sourceresolution text,
    sourcescale text,
    sourcetitle text,
    foliation text,
    foliationrank text,
    geochrondate text,
    geochronerror text,
    geochrontech text,
    geochronref text,
    progrademin text,
    geochronall text
);


CREATE TABLE sources.dc_lines (
    gid integer NOT NULL,
    fnode_ numeric(10,0),
    tnode_ numeric(10,0),
    lpoly_ numeric(10,0),
    rpoly_ numeric(10,0),
    length double precision,
    fault_ numeric(10,0),
    fault_id numeric(10,0),
    symbol smallint,
    symbol_arc integer,
    feature character varying(31),
    elevation double precision,
    type_code character varying(10),
    code numeric(10,0),
    quad character varying(2),
    geom public.geometry(MultiLineString,4326),
    type text,
    new_type text,
    new_direction text
);


CREATE SEQUENCE sources.dc_lines_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.dc_lines_gid_seq OWNED BY sources.dc_lines.gid;


CREATE TABLE sources.dc_surficial (
    gid integer,
    surficial0 numeric(10,0),
    surficia_1 numeric(10,0),
    mapunit character varying(10),
    symbol smallint,
    bedrock0_ numeric(10,0),
    bedrock0_i numeric(10,0),
    retro_min character varying(45),
    m_age_ref character varying(35),
    namerank character varying(50),
    formal character varying(50),
    description text,
    strat_name character varying(254),
    coa_id numeric(10,0),
    stratseq numeric(10,0),
    minstrat character varying(35),
    maxstrat character varying(35),
    minsource numeric(10,0),
    maxsource numeric(10,0),
    name character varying(60),
    type character varying(254),
    clastlith character varying(254),
    clastrank character varying(254),
    cement character varying(254),
    mineral character varying(254),
    minrank character varying(254),
    rockclass character varying(35),
    province integer,
    age character varying(35),
    fossil character varying(50),
    fossilref character varying(35),
    ageextrap character varying(35),
    origin character varying(60),
    resource character varying(35),
    res_ref character varying(35),
    color character varying(35),
    thickaprx character varying(50),
    thickmin numeric,
    thickmax numeric,
    thickrange character varying(35),
    bedding character varying(50),
    contup character varying(30),
    contlow character varying(30),
    defevent character varying(35),
    geom public.geometry(MultiPolygon,4326),
    rockname text,
    lithclass text,
    lithform text,
    lithrank text,
    rockrank text,
    early_id integer,
    late_id integer,
    sourceid numeric(10,0),
    sourceauthor text,
    sourcedate text,
    organizationid text,
    sourceresolution text,
    sourcescale text,
    sourcetitle text,
    foliation text,
    foliationrank text,
    geochrondate text,
    geochronerror text,
    geochrontech text,
    geochronref text,
    progrademin text,
    geochronall text
);


CREATE TABLE sources.ut_delta_lines (
    gid integer NOT NULL,
    fnode_ integer,
    tnode_ integer,
    lpoly_ integer,
    rpoly_ integer,
    length numeric,
    geology_ integer,
    geology_id integer,
    type character varying(25),
    subtype character varying(25),
    modifier character varying(30),
    notes character varying(30),
    geom public.geometry(MultiLineString,4326),
    new_type text,
    new_direction text
);


CREATE SEQUENCE sources.delta_faults_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.delta_faults_gid_seq OWNED BY sources.ut_delta_lines.gid;


CREATE TABLE sources.ut_delta (
    gid integer NOT NULL,
    area numeric,
    perimeter numeric,
    geology_ integer,
    geology_id integer,
    unitsymbol character varying(15),
    unitname character varying(150),
    age character varying(50),
    notes text,
    lithology text,
    geom public.geometry(MultiPolygon,4326),
    late_id integer,
    early_id integer
);


CREATE SEQUENCE sources.deltautah_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.deltautah_gid_seq OWNED BY sources.ut_delta.gid;


CREATE TABLE sources.denver (
    gid integer NOT NULL,
    denverw_ge integer,
    denverw__1 integer,
    label character varying(6),
    desc_ character varying(150),
    denver_t_a character varying(254),
    denver_b_a character varying(254),
    denver_nam character varying(254),
    denver_des text,
    denver_fie character varying(254),
    geom public.geometry(MultiPolygon,4326),
    early_id integer,
    late_id integer
);


CREATE SEQUENCE sources.denver_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.denver_gid_seq OWNED BY sources.denver.gid;


CREATE TABLE sources.denver_lines (
    gid integer NOT NULL,
    fnode_ integer,
    tnode_ integer,
    lpoly_ integer,
    rpoly_ integer,
    denverw_fo integer,
    denverw__1 integer,
    descriptio character varying(120),
    denverw_ge integer,
    geom public.geometry(MultiLineString,4326),
    type text
);


CREATE SEQUENCE sources.denver_lines_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.denver_lines_gid_seq OWNED BY sources.denver_lines.gid;


CREATE SEQUENCE sources.denvergeology_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.denvergeology_gid_seq OWNED BY sources.co_denver.gid;


CREATE TABLE sources.devils_tower (
    gid integer NOT NULL,
    objectid_1 integer,
    shape_leng numeric,
    shape_area numeric,
    g_unit character varying(5),
    g_sym character varying(5),
    age text,
    geom public.geometry(MultiPolygon,4326),
    description text,
    name text,
    comments text,
    early_id integer,
    late_id integer,
    strat_name text
);


CREATE SEQUENCE sources.devils_tower_geo_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.devils_tower_geo_gid_seq OWNED BY sources.devils_tower.gid;


CREATE TABLE sources.devils_tower_lines (
    gid integer NOT NULL,
    objectid integer,
    shape_leng numeric,
    name character varying(50),
    type character varying(30),
    geom public.geometry(MultiLineString,4326),
    new_type text,
    new_direction text
);


CREATE SEQUENCE sources.devils_tower_lines_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.devils_tower_lines_gid_seq OWNED BY sources.devils_tower_lines.gid;


CREATE TABLE sources.ut_dutchjohn_lines (
    gid integer NOT NULL,
    fnode_ integer,
    tnode_ integer,
    lpoly_ integer,
    rpoly_ integer,
    length double precision,
    geology_ integer,
    geology_id integer,
    type character varying(25),
    subtype character varying(25),
    modifier character varying(30),
    name character varying(30),
    geom public.geometry(MultiLineString,4326),
    new_type text,
    new_direction text
);


CREATE SEQUENCE sources.dutchjohn_faults_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.dutchjohn_faults_gid_seq OWNED BY sources.ut_dutchjohn_lines.gid;


CREATE TABLE sources.ut_dutchjohn (
    gid integer NOT NULL,
    area double precision,
    perimeter double precision,
    geology_ integer,
    geology_id integer,
    unitsymbol character varying(15),
    unitname character varying(80),
    age character varying(50),
    notes character varying(50),
    geom public.geometry(MultiPolygon,4326),
    litho text,
    early_id integer,
    late_id integer
);


CREATE SEQUENCE sources.dutchjohn_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.dutchjohn_gid_seq OWNED BY sources.ut_dutchjohn.gid;


CREATE TABLE sources.endikai (
    gid integer NOT NULL,
    mapcode numeric(10,0),
    shape_leng numeric,
    shape_area numeric,
    pss character varying(254),
    geom public.geometry(MultiPolygon,4326),
    name text,
    descrip text,
    lith text,
    age text,
    early_id integer,
    late_id integer
);


CREATE SEQUENCE sources.endikai_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.endikai_gid_seq OWNED BY sources.endikai.gid;


CREATE SEQUENCE sources.etopo1_rid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


CREATE TABLE sources.europe_5m (
    gid integer NOT NULL,
    marin numeric(10,0),
    geo numeric(10,0),
    area_id numeric(10,0),
    portr_age character varying(254),
    portr_meta character varying(254),
    portr_igne character varying(254),
    portr_mari character varying(254),
    portr_iceo character varying(254),
    portr_petr character varying(254),
    portr_pe_1 character varying(254),
    portr_pe_2 character varying(254),
    portr_pe_3 character varying(254),
    agename character varying(50),
    regname character varying(254),
    genelement character varying(254),
    ageoldest double precision,
    agenewest double precision,
    shape_star numeric,
    shape_stle numeric,
    geom public.geometry(MultiPolygon,4326),
    descrip text,
    early_age text,
    early_id integer,
    late_age text,
    late_id integer,
    name text,
    lith text,
    comments text,
    strat_name text
);


CREATE SEQUENCE sources.europe_5m_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.europe_5m_gid_seq OWNED BY sources.europe_5m.gid;


CREATE TABLE sources.europe_5m_lines (
    gid integer NOT NULL,
    portr_line character varying(254),
    realm character varying(15),
    geom public.geometry(MultiLineString,4326),
    new_type text,
    new_direction text
);


CREATE SEQUENCE sources.europe_5m_lines_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.europe_5m_lines_gid_seq OWNED BY sources.europe_5m_lines.gid;


CREATE TABLE sources.gmna_faults (
    gid integer NOT NULL,
    objectid double precision,
    type double precision,
    slip_dir character varying(20),
    shape_leng numeric,
    geom public.geometry(MultiLineString,4326),
    type_name character varying(60),
    exposure character varying(40)
);


CREATE SEQUENCE sources.faults_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.faults_gid_seq OWNED BY sources.gmna_faults.gid;


CREATE TABLE sources.florissant (
    gid integer NOT NULL,
    objectid numeric,
    fuid bigint,
    glg_sym character varying(40),
    src_sym character varying(40),
    sort_no numeric,
    notes character varying(254),
    lbl character varying(60),
    gmap_id bigint,
    shape_leng numeric,
    shape_area numeric,
    geom public.geometry(MultiPolygon,4326),
    name text,
    description text,
    age text,
    early_id integer,
    late_id integer,
    strat_name text
);


CREATE TABLE sources.florissant_lines (
    gid integer NOT NULL,
    objectid numeric,
    fuid bigint,
    ftype bigint,
    fsubtype bigint,
    pos bigint,
    fname character varying(60),
    notes character varying(254),
    lbl character varying(60),
    sym character varying(60),
    gmap_id bigint,
    shape_leng numeric,
    geom public.geometry(MultiLineString,4326),
    new_type text
);


CREATE SEQUENCE sources."florissant-lines_gid_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources."florissant-lines_gid_seq" OWNED BY sources.florissant_lines.gid;


CREATE SEQUENCE sources.florissant_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.florissant_gid_seq OWNED BY sources.florissant.gid;


CREATE TABLE sources.france (
    gid integer NOT NULL,
    gmlid character varying(254),
    descriptio character varying(254),
    gu_name character varying(254),
    geologicun character varying(254),
    geologic_1 character varying(254),
    eventproce character varying(254),
    eventpro_1 character varying(254),
    eventenvir character varying(254),
    eventenv_1 character varying(254),
    age_olderl character varying(254),
    age_olde_1 character varying(254),
    age_younge character varying(254),
    age_youn_1 character varying(254),
    representa character varying(254),
    represen_1 character varying(254),
    represen_2 character varying(254),
    represen_3 character varying(254),
    aggregated character varying(254),
    geom public.geometry(MultiPolygon,4326),
    early_id integer,
    late_id integer,
    descrip_eng text,
    use_age text
);


CREATE SEQUENCE sources.france_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.france_gid_seq OWNED BY sources.france.gid;


CREATE TABLE sources.france_lines (
    gid integer NOT NULL,
    gs_id character varying(254),
    gs_name character varying(254),
    gs_faultty character varying(254),
    gs_contact character varying(254),
    mf_obsmeth character varying(254),
    mf_posaccu character varying(254),
    mf_samplin character varying(254),
    gs_obsmeth character varying(254),
    gs_purpose character varying(254),
    ogc_fid character varying(254),
    sav_gs_nam character varying(254),
    geom public.geometry(MultiLineString,4326),
    new_type text,
    new_direction text
);


CREATE SEQUENCE sources.france_lines_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.france_lines_gid_seq OWNED BY sources.france_lines.gid;


CREATE TABLE sources.wv_gauley_river (
    gid integer NOT NULL,
    fuid integer,
    glg_sym character varying(12),
    src_sym character varying(12),
    sort_no numeric,
    notes character varying(254),
    lbl character varying(60),
    gmap_id integer,
    shape_leng numeric,
    shape_area numeric,
    geom public.geometry(MultiPolygon,4326),
    name text,
    age text,
    description text,
    early_id integer,
    late_id integer
);


CREATE SEQUENCE sources.gauleyriver_geo_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.gauleyriver_geo_gid_seq OWNED BY sources.wv_gauley_river.gid;


CREATE TABLE sources.wv_gauley_river_lines (
    gid integer NOT NULL,
    fuid integer,
    fsubtype smallint,
    pos smallint,
    glg_sym character varying(12),
    src_sym character varying(12),
    sort_no numeric,
    notes character varying(254),
    lbl character varying(60),
    gmap_id integer,
    shape_leng numeric,
    geom public.geometry(MultiLineString,4326),
    new_type text,
    new_direction text,
    name text
);


CREATE SEQUENCE sources.gauleyriver_lines_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.gauleyriver_lines_gid_seq OWNED BY sources.wv_gauley_river_lines.gid;


CREATE TABLE sources.geo_lgm (
    gid integer NOT NULL,
    id integer,
    feature character varying(100),
    comment character varying(100),
    geom public.geometry(MultiPolygon,4326)
);


CREATE SEQUENCE sources.geo_ice_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.geo_ice_gid_seq OWNED BY sources.geo_lgm.gid;


CREATE TABLE sources.geo_regions (
    gid integer NOT NULL,
    scalerank numeric,
    featurecla character varying(32),
    name character varying(254),
    namealt character varying(254),
    region character varying(50),
    subregion character varying(50),
    min_zoom double precision,
    max_zoom double precision,
    geom public.geometry(MultiPolygon,4326)
);


CREATE TABLE sources.geo_regions_canada (
    gid integer NOT NULL,
    area double precision,
    perimeter double precision,
    geo_ numeric,
    geo_id numeric,
    geo_type character varying(3),
    geo_sym smallint,
    geo_pat smallint,
    geo_misc character varying(16),
    geo_link numeric,
    code character varying(16),
    code_an character varying(70),
    region_an character varying(40),
    sub_reg_an character varying(40),
    area_an character varying(70),
    division_a character varying(70),
    sub_div_an character varying(70),
    code_fr character varying(70),
    region_fr character varying(40),
    sub_reg_fr character varying(40),
    area_fr character varying(70),
    division_f character varying(70),
    sub_div_fr character varying(70),
    shape_leng numeric,
    shape_area numeric,
    geom public.geometry(MultiPolygon,4326)
);


CREATE SEQUENCE sources.geo_regions_canada_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.geo_regions_canada_gid_seq OWNED BY sources.geo_regions_canada.gid;


CREATE TABLE sources.geo_regions_europe (
    gid integer NOT NULL,
    area numeric,
    perimeter numeric,
    prv4_2l_ integer,
    prv4_2l_id integer,
    code integer,
    name character varying(50),
    type character varying(2),
    reg integer,
    studied character varying(1),
    gor numeric,
    o_g character varying(13),
    cum_oil numeric,
    rem_oil numeric,
    kwn_oil numeric,
    cum_gas numeric,
    rem_gas numeric,
    kwn_gas numeric,
    cum_ngl numeric,
    rem_ngl numeric,
    kwn_ngl numeric,
    cum_pet numeric,
    rem_pet numeric,
    kwn_pet numeric,
    unds_oil numeric,
    unds_gas numeric,
    unds_ngl numeric,
    unds_pet numeric,
    endo_oil numeric,
    endo_gas numeric,
    endo_ngl numeric,
    endo_pet numeric,
    matr_oil numeric,
    matr_gas numeric,
    matr_ngl numeric,
    matr_pet numeric,
    futr_oil numeric,
    futr_gas numeric,
    futr_ngl numeric,
    futr_pet numeric,
    geom public.geometry(MultiPolygon,4326)
);


CREATE SEQUENCE sources.geo_regions_europe_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.geo_regions_europe_gid_seq OWNED BY sources.geo_regions_europe.gid;


CREATE SEQUENCE sources.geo_regions_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.geo_regions_gid_seq OWNED BY sources.geo_regions.gid;


CREATE TABLE sources.geo_regions_us (
    gid integer NOT NULL,
    area double precision,
    perimeter double precision,
    physiodd_ integer,
    physiodd_i integer,
    fcode integer,
    fencode character varying(4),
    division character varying(23),
    province character varying(24),
    section character varying(29),
    provcode integer,
    geom public.geometry(MultiPolygon,4326),
    descrip text,
    new_name text
);


CREATE SEQUENCE sources.geo_regions_us_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.geo_regions_us_gid_seq OWNED BY sources.geo_regions_us.gid;


CREATE TABLE sources.german_nuremburg (
    gid integer NOT NULL,
    shape_leng numeric,
    shape_area numeric,
    geo numeric,
    kombi smallint,
    schicht_1 numeric,
    kuerzel character varying(254),
    t1_kuerzel character varying(254),
    t1_matbez character varying(254),
    t1_gentxt character varying(254),
    t1_pethtxt character varying(254),
    t1_ph_beso character varying(254),
    t1_g_beson character varying(254),
    t1_s_beson character varying(254),
    t1_gruppe character varying(254),
    t1_system character varying(254),
    t1_serie character varying(254),
    t1_stufe character varying(254),
    t1_ustufe character varying(254),
    t1_zone character varying(254),
    geom public.geometry(MultiPolygon,4326),
    t1_matbez_eng text,
    strat_name_eng text,
    t1_gentxt_eng text,
    t1_pethtxt_eng text,
    t1_s_beson_eng text,
    t1_gruppe_eng text,
    t1_system_eng text,
    t1_series_eng text,
    t1_stufe_eng text,
    t1_ustufe_eng text,
    early_id integer,
    late_id integer,
    age_name text
);


CREATE TABLE sources.german_nuremburg_lines (
    gid integer NOT NULL,
    shape_leng numeric,
    geo_line numeric,
    linientyp character varying(100),
    geom public.geometry(MultiLineString,4326),
    new_type text,
    descrip text
);


CREATE SEQUENCE sources.german_nuremburg_lines_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.german_nuremburg_lines_gid_seq OWNED BY sources.german_nuremburg_lines.gid;


CREATE SEQUENCE sources.german_nurenburg_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.german_nurenburg_gid_seq OWNED BY sources.german_nuremburg.gid;


CREATE TABLE sources.germany (
    gid integer NOT NULL,
    area numeric,
    perimeter numeric,
    geo smallint,
    symbol character varying(254),
    stratigrap2 character varying(254),
    strat_sym character varying(254),
    genese character varying(254),
    gen_sym character varying(254),
    petrograph character varying(254),
    pet_sym character varying(254),
    bemerkunge2 character varying(254),
    geom public.geometry(MultiPolygon,4326),
    age text,
    genesis text,
    lithology text,
    comments text,
    description text,
    name text,
    name_eng text,
    bemerkunge1 text,
    early_id integer,
    late_id integer,
    stratigrap1 text
);


CREATE TABLE sources.germany_lines (
    gid integer NOT NULL,
    __gid numeric(10,0),
    length numeric,
    geo_line numeric(10,0),
    linientyp character varying(100),
    new_type character varying(254),
    type character varying(254),
    new_direction character varying(254),
    geom public.geometry(MultiLineString,4326)
);


CREATE SEQUENCE sources.germanygeology_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.germanygeology_gid_seq OWNED BY sources.germany.gid;


CREATE TABLE sources.glacier_np_lines (
    gid integer NOT NULL,
    sort_no numeric,
    notes character varying(254),
    label character varying(60),
    shape_leng numeric,
    name character varying(100),
    age_text character varying(100),
    mj_lith character varying(3),
    geom public.geometry(MultiLineString,4326),
    type text,
    positionalaccuracy text,
    plunge text,
    subtype text,
    new_type text,
    new_direction text
);


CREATE SEQUENCE sources.glacier_dikes_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.glacier_dikes_gid_seq OWNED BY sources.glacier_np_lines.gid;


CREATE TABLE sources.glaciernationalparkgeology (
    gid integer NOT NULL,
    objectid numeric(10,0),
    fuid numeric(10,0),
    glg_sym character varying(12),
    src_sym character varying(12),
    sort_no numeric,
    notes character varying(254),
    lbl character varying(60),
    gmap_id numeric(10,0),
    shape_leng numeric,
    shape_area numeric,
    objectid_1 integer,
    glg_sym_1 character varying(12),
    glg_name character varying(100),
    age character varying(100),
    mj_lith character varying(3),
    geom public.geometry(MultiPolygon,4326),
    description text,
    early_id integer,
    late_id integer
);


CREATE SEQUENCE sources.glaciernationalparkgeology_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.glaciernationalparkgeology_gid_seq OWNED BY sources.glaciernationalparkgeology.gid;


CREATE SEQUENCE sources.glines_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.glines_gid_seq OWNED BY sources.germany_lines.gid;


CREATE TABLE sources.global2 (
    gid integer NOT NULL,
    area character varying(254),
    perimeter character varying(254),
    rxafrgen_ double precision,
    rxafrgen_i double precision,
    runo_id2 numeric(10,0),
    agerxtp character varying(80),
    eon character varying(25),
    era character varying(35),
    rxtyp character varying(40),
    geom public.geometry(MultiPolygon,4326),
    strat_name text,
    comments text,
    metamorph text,
    early_age text,
    early_id integer,
    late_id integer,
    late_age text,
    use_age text
);


CREATE SEQUENCE sources.global2_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.global2_gid_seq OWNED BY sources.global2.gid;


CREATE TABLE sources.global2_lines (
    gid integer NOT NULL,
    ftafragf_i double precision,
    ftno_id2 numeric(10,0),
    ftype character varying(40),
    fdisp character varying(40),
    ageftp character varying(80),
    name character varying(80),
    defzone character varying(45),
    era character varying(35),
    eon character varying(25),
    geom public.geometry(MultiLineString,4326),
    new_type text,
    new_direction text
);


CREATE SEQUENCE sources.global2_lines_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.global2_lines_gid_seq OWNED BY sources.global2_lines.gid;


CREATE TABLE sources.global_ecoregions (
    gid integer NOT NULL,
    eco_id_u integer,
    eco_code character varying(16),
    eco_name character varying(100),
    eco_num smallint,
    ecode_name character varying(120),
    cls_code smallint,
    eco_notes character varying(250),
    wwf_realm character varying(2),
    wwf_realm2 character varying(15),
    wwf_mhtnum smallint,
    wwf_mhtnam character varying(70),
    realmmht character varying(4),
    er_update character varying(15),
    er_date_u character varying(12),
    er_ration character varying(100),
    sourcedata character varying(50),
    geom public.geometry(MultiPolygon,4326)
);


CREATE SEQUENCE sources.global_ecoregions_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.global_ecoregions_gid_seq OWNED BY sources.global_ecoregions.gid;


CREATE TABLE sources.ma_glouster (
    gid integer NOT NULL,
    area numeric,
    perimeter numeric,
    litho_diss integer,
    litho_di_1 integer,
    litho_unit character varying(15),
    descriptio character varying(200),
    shape_leng numeric,
    shape_area numeric,
    geom public.geometry(MultiPolygon,4326),
    comments text,
    age text,
    early_id integer,
    late_id integer,
    name text,
    strat_name text
);


CREATE SEQUENCE sources.gloucester_rockport_geo2_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.gloucester_rockport_geo2_gid_seq OWNED BY sources.ma_glouster.gid;


CREATE TABLE sources.gmna (
    gid integer,
    unit_abbre character varying(8),
    rocktype character varying(40),
    lithology character varying(90),
    lith character varying(75),
    lith_type character varying(50),
    lith_class character varying(50),
    lith_color character varying(12),
    map_unit_n character varying(102),
    min_age numeric,
    min_interval character varying(200),
    max_age numeric,
    max_interval character varying(200),
    containing_interval character varying(200),
    interval_color character varying(20),
    geom public.geometry,
    lith_id integer,
    early_id integer,
    late_id integer,
    lith_name character varying(150),
    age_name character varying(150)
);


CREATE TABLE sources.gmus (
    gid integer,
    state character varying(2),
    unit_link character varying(18),
    source character varying(6),
    unit_age character varying(60),
    rocktype1 character varying(40),
    rocktype2 character varying(40),
    unit_name text,
    unitdesc text,
    strat_unit text,
    unit_com text,
    u_rocktype1 text,
    u_rocktype2 text,
    u_rocktype3 text,
    interval_color character varying(20),
    containing_interval_name character varying(200),
    age_bottom numeric,
    max_interval_name character varying(200),
    age_top numeric,
    min_interval_name character varying(200),
    macro_interval_id integer,
    macro_interval_name character varying(200),
    macro_b_age numeric,
    macro_t_age numeric,
    macro_color character varying(20),
    geom public.geometry(MultiPolygon,4326),
    text_search tsvector,
    early_id integer,
    late_id integer,
    lith_name text,
    lith_name2 text,
    templith text,
    fixlith text
);


CREATE TABLE sources.gmus2 (
    gid integer NOT NULL,
    state character varying(2),
    orig_label character varying(12),
    sgmc_label character varying(16),
    unit_link character varying(18),
    unit_name character varying(254),
    age_min character varying(100),
    age_max character varying(100),
    major1 character varying(50),
    major2 character varying(30),
    major3 character varying(30),
    minor1 character varying(30),
    minor2 character varying(30),
    minor3 character varying(30),
    minor4 character varying(30),
    minor5 character varying(100),
    incidental character varying(175),
    indetermin character varying(150),
    ref_id character varying(6),
    reference character varying(254),
    generalize character varying(100),
    digital_ur character varying(125),
    ngmdb1 character varying(100),
    ngmdb2 character varying(100),
    ngmdb3 character varying(100),
    shape_leng numeric,
    shape_area numeric,
    geom public.geometry(MultiPolygon,4326),
    early_id integer,
    late_id integer,
    age text,
    agemin text[],
    agemax text[],
    agemin_text text,
    agemax_text text,
    descrip text,
    strat_name text,
    unit_comments text,
    major_lith text,
    minor_lith text,
    other_lith text,
    paper_ref text
);


CREATE SEQUENCE sources.gmus2_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.gmus2_gid_seq OWNED BY sources.gmus2.gid;


CREATE TABLE sources.gmus2_lines (
    gid integer NOT NULL,
    state character varying(2),
    descriptio character varying(254),
    misc character varying(75),
    ref_id character varying(6),
    reference character varying(254),
    digital_ur character varying(125),
    ngmdb1 character varying(100),
    ngmdb2 character varying(100),
    ngmdb3 character varying(100),
    shape_leng numeric,
    geom public.geometry(MultiLineString,4326),
    new_type text,
    new_direction text,
    line_name text,
    descrip_mod text
);


CREATE SEQUENCE sources.gmus2_lines_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.gmus2_lines_gid_seq OWNED BY sources.gmus2_lines.gid;


CREATE TABLE sources.gmus_faults (
    fnode_ integer,
    tnode_ integer,
    lpoly_ integer,
    rpoly_ integer,
    length numeric,
    arc_code integer,
    arc_para1 integer,
    arc_para2 integer,
    source character varying(6),
    state character varying(2),
    faults_1 integer,
    faults_d integer,
    the_geom public.geometry,
    fault_type character varying(20),
    descrip text,
    dir character varying(10),
    gid integer NOT NULL,
    CONSTRAINT enforce_dims_the_geom CHECK ((public.st_ndims(the_geom) = 2)),
    CONSTRAINT enforce_geotype_the_geom CHECK (((public.geometrytype(the_geom) = 'MULTILINESTRING'::text) OR (the_geom IS NULL))),
    CONSTRAINT enforce_srid_the_geom CHECK ((public.st_srid(the_geom) = 4326))
);


CREATE TABLE sources.gmus_old (
    gid integer,
    state character varying(2),
    unit_link character varying(18),
    source character varying(6),
    unit_age character varying(60),
    unit_name text,
    unitdesc text,
    strat_unit text,
    unit_com text,
    u_rocktype1 text,
    u_rocktype2 text,
    u_rocktype3 text,
    age_bottom numeric,
    max_interval_name character varying(200),
    age_top numeric,
    min_interval_name character varying(200),
    geom public.geometry(MultiPolygon,4326),
    text_search tsvector,
    early_id integer,
    late_id integer,
    lith_name2 text,
    lith_name3 text
);


CREATE SEQUENCE sources.grand_junction_geo_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.grand_junction_geo_gid_seq OWNED BY sources.co_grandjunction.gid;


CREATE SEQUENCE sources.grand_junction_lines_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.grand_junction_lines_gid_seq OWNED BY sources.co_grandjunction_lines.gid;


CREATE TABLE sources.grandcanyon (
    gid integer NOT NULL,
    oid_ integer,
    ptype character varying(254),
    usgs_sym character varying(254),
    shape_leng numeric,
    shape_area numeric,
    geom public.geometry(MultiPolygon,4326),
    descrip text,
    strat_name text,
    age text,
    early_id integer,
    late_id integer,
    unit_name text,
    hierarchy text
);


CREATE SEQUENCE sources.grandcanyon_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.grandcanyon_gid_seq OWNED BY sources.grandcanyon.gid;


CREATE TABLE sources.grandcanyon_lines (
    gid integer NOT NULL,
    objectid integer,
    name character varying(30),
    ltype character varying(35),
    pttype character varying(35),
    plunge smallint,
    shape_leng numeric,
    geom public.geometry(MultiLineString,4326),
    line_type text
);


CREATE SEQUENCE sources.grandcanyon_lines_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.grandcanyon_lines_gid_seq OWNED BY sources.grandcanyon_lines.gid;


CREATE TABLE sources.grandcanyon_points (
    gid integer NOT NULL,
    objectid integer,
    pttype character varying(35),
    dip smallint,
    strike smallint,
    geom public.geometry(Point,4326),
    use_name character varying(35),
    comments text,
    certainty text
);


CREATE SEQUENCE sources.grandcanyon_points_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.grandcanyon_points_gid_seq OWNED BY sources.grandcanyon_points.gid;


CREATE TABLE sources.greatbasinnationalpark_lines (
    gid integer NOT NULL,
    notes character varying(254),
    shape_leng numeric,
    subtype character varying(254),
    positionalaccuracy character varying(254),
    geom public.geometry(MultiLineString,4326),
    type text,
    label text,
    sourcemap text,
    new_type text,
    new_direction text
);


CREATE SEQUENCE sources.greatbasin_contacts_faults_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.greatbasin_contacts_faults_gid_seq OWNED BY sources.greatbasinnationalpark_lines.gid;


CREATE TABLE sources.greatbasinnationalparkgeology (
    gid integer NOT NULL,
    fuid integer,
    glg_sym character varying(12),
    src_sym character varying(12),
    sort_no numeric,
    notes character varying(254),
    lbl character varying(60),
    gmap_id integer,
    shape_leng numeric,
    shape_area numeric,
    age character varying(254),
    name character varying(254),
    major_lit character varying(254),
    geom public.geometry(MultiPolygon,4326),
    description text,
    early_id integer,
    late_id integer
);


CREATE SEQUENCE sources.greatbasinnationalparkgeology_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.greatbasinnationalparkgeology_gid_seq OWNED BY sources.greatbasinnationalparkgeology.gid;


CREATE SEQUENCE sources.greenwood_lines_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.greenwood_lines_gid_seq OWNED BY sources.al_greenwood_lines.gid;


CREATE SEQUENCE sources.greenwood_points_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.greenwood_points_gid_seq OWNED BY sources.al_greenwood_points.gid;


CREATE SEQUENCE sources.greenwoodalgeology_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.greenwoodalgeology_gid_seq OWNED BY sources.al_greenwood.gid;


CREATE SEQUENCE sources.gsd_co_geology_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.gsd_co_geology_gid_seq OWNED BY sources.co_greatsanddunes.gid;


CREATE TABLE sources.guam (
    gid integer NOT NULL,
    code character varying(10),
    mapunit character varying(100),
    formation character varying(50),
    age character varying(30),
    area_acres double precision,
    area_ha double precision,
    area_m2 integer,
    perimtr_m integer,
    perimtr_mi double precision,
    geom public.geometry(MultiPolygon,4326),
    description text,
    early_id integer,
    late_id integer,
    strat_name text
);


CREATE SEQUENCE sources.guamgeology_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.guamgeology_gid_seq OWNED BY sources.guam.gid;


CREATE TABLE sources.gumo (
    gid integer NOT NULL,
    area numeric,
    perimeter numeric,
    gumoglg_ double precision,
    gumoglg_id double precision,
    glg_idx integer,
    glg_sym character varying(12),
    usgs_sym character varying(12),
    glg_age_no double precision,
    gmap_id integer,
    help_id character varying(12),
    geom public.geometry(MultiPolygon,4326),
    name text,
    age text,
    lith text,
    descrip text,
    early_id integer,
    late_id integer,
    strat_name text
);


CREATE SEQUENCE sources.gumo_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.gumo_gid_seq OWNED BY sources.gumo.gid;


CREATE TABLE sources.gumo_lines (
    gid integer NOT NULL,
    fnode_ double precision,
    tnode_ double precision,
    lpoly_ double precision,
    rpoly_ double precision,
    length numeric,
    gumoflt_ double precision,
    gumoflt_id double precision,
    flt_idx integer,
    flt_seg_n smallint,
    flt_seg_t smallint,
    flt_type smallint,
    flt_lt smallint,
    fltcnt character varying(1),
    flt_nm character varying(60),
    gmap_id integer,
    help_id character varying(12),
    geom public.geometry(MultiLineString,4326),
    new_type text,
    descrip text
);


CREATE SEQUENCE sources.gumo_lines_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.gumo_lines_gid_seq OWNED BY sources.gumo_lines.gid;


CREATE TABLE sources.gumo_points (
    gid integer NOT NULL,
    area numeric,
    perimeter numeric,
    gumoatd_ double precision,
    gumoatd_id double precision,
    atd_idx integer,
    atd_type smallint,
    atd_st smallint,
    atd_dp smallint,
    atd_av_rot smallint,
    atd_am_rot smallint,
    gmap_id integer,
    geom public.geometry(Point,4326),
    point_type text,
    strike integer,
    dip integer,
    dip_dir integer
);


CREATE SEQUENCE sources.gumo_points_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.gumo_points_gid_seq OWNED BY sources.gumo_points.gid;


CREATE SEQUENCE sources.hasty_geo_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.hasty_geo_gid_seq OWNED BY sources.ar_hasty.gid;


CREATE SEQUENCE sources.hasty_points_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.hasty_points_gid_seq OWNED BY sources.ar_hasty_points.gid;


CREATE SEQUENCE sources.hastylines2_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.hastylines2_gid_seq OWNED BY sources.ar_hasty_lines.gid;


CREATE TABLE sources.hawaii (
    gid integer NOT NULL,
    id double precision,
    island character varying(10),
    volcano character varying(4),
    strat_code double precision,
    symbol character varying(10),
    age_group double precision,
    age_range character varying(30),
    name character varying(80),
    name0 character varying(30),
    unit character varying(10),
    rock_type character varying(80),
    lithology character varying(50),
    volc_stage character varying(7),
    compositio character varying(40),
    source character varying(40),
    age_code3_ character varying(254),
    real_interval character varying(254),
    geom public.geometry(MultiPolygon,4326),
    early_id integer,
    late_id integer,
    geom_valid public.geometry(MultiPolygon,4326)
);


CREATE TABLE sources.hawaii_lines (
    gid integer NOT NULL,
    island character varying(10),
    volcano character varying(4),
    symbol character varying(10),
    name character varying(80),
    volc_stage character varying(7),
    description character varying(40),
    source character varying(40),
    geom public.geometry(MultiLineString,4326),
    type text,
    relation text,
    unit text,
    new_type text,
    new_direction text
);


CREATE SEQUENCE sources.hawaii_dikes_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.hawaii_dikes_gid_seq OWNED BY sources.hawaii_lines.gid;


CREATE SEQUENCE sources.hawaii_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.hawaii_gid_seq OWNED BY sources.hawaii.gid;


CREATE TABLE sources.honduras (
    gid integer NOT NULL,
    area double precision,
    perimeter double precision,
    geo_geol_ double precision,
    geo_geol_i double precision,
    type character varying(10),
    unit character varying(254),
    bed_surf character varying(254),
    lith character varying(254),
    era character varying(254),
    system character varying(254),
    rockgroup character varying(254),
    environ character varying(254),
    landslides character varying(254),
    geom public.geometry(MultiPolygon,4326),
    lithology text,
    age text,
    strat_name text,
    hierarchy text,
    description text,
    early_id integer,
    late_id integer
);


CREATE SEQUENCE sources.honduras_geo_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.honduras_geo_gid_seq OWNED BY sources.honduras.gid;


CREATE SEQUENCE sources.hot_springs_lines_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.hot_springs_lines_gid_seq OWNED BY sources.ar_hotsprings_np_lines.gid;


CREATE SEQUENCE sources.hot_springs_points_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.hot_springs_points_gid_seq OWNED BY sources.ar_hotsprings_np_points.gid;


CREATE SEQUENCE sources.hotspringsnationalparkgeology_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.hotspringsnationalparkgeology_gid_seq OWNED BY sources.ar_hotsprings_np.gid;


CREATE TABLE sources.ut_huntington_lines (
    gid integer NOT NULL,
    fnode_ integer,
    tnode_ integer,
    lpoly_ integer,
    rpoly_ integer,
    length numeric,
    geology_ integer,
    geology_id integer,
    type character varying(25),
    subtype character varying(25),
    modifier character varying(30),
    notes character varying(30),
    geom public.geometry(MultiLineString,4326),
    new_type text,
    new_direction text
);


CREATE SEQUENCE sources.huntington_faults_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.huntington_faults_gid_seq OWNED BY sources.ut_huntington_lines.gid;


CREATE TABLE sources.ut_huntington (
    gid integer NOT NULL,
    area numeric,
    perimeter numeric,
    geology_ integer,
    geology_id integer,
    unitsymbol character varying(15),
    unitname character varying(80),
    age character varying(50),
    notes character varying(50),
    geom public.geometry(MultiPolygon,4326),
    description text,
    early_id integer,
    late_id integer
);


CREATE SEQUENCE sources.huntingtonutahgeology_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.huntingtonutahgeology_gid_seq OWNED BY sources.ut_huntington.gid;


CREATE TABLE sources.id_arco (
    gid integer NOT NULL,
    mapunit character varying(255),
    name character varying(255),
    bottom_age character varying(255),
    strat_name character varying(255),
    top_age character varying(255),
    description character varying,
    generallithology character varying(255),
    comments character varying(255),
    igs_lithology character varying(255),
    lith character varying(255),
    shape_length double precision,
    shape_area double precision,
    geom text,
    early_id integer,
    late_id integer,
    use_age text
);


CREATE TABLE sources.id_arco_lines (
    gid integer NOT NULL,
    type character varying(255),
    shape_length double precision,
    name character varying(255),
    new_type character varying(255),
    descrip character varying(50),
    geom public.geometry
);


CREATE SEQUENCE sources.id_arco_lines_objectid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.id_arco_lines_objectid_seq OWNED BY sources.id_arco_lines.gid;


CREATE SEQUENCE sources.id_arco_objectid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.id_arco_objectid_seq OWNED BY sources.id_arco.gid;


CREATE TABLE sources.id_bonners (
    gid integer NOT NULL,
    mapunit character varying(255),
    shape_length double precision,
    shape_area double precision,
    name character varying(255),
    strat_name character varying(255),
    top character varying(255),
    bottom character varying(255),
    generallithology character varying(255),
    description character varying(2999),
    comments character varying(255),
    geom public.geometry,
    early_id integer,
    late_id integer,
    use_age text
);


CREATE TABLE sources.id_bonners_lines (
    gid integer NOT NULL,
    type character varying(255),
    shape_length double precision,
    name character varying(255),
    new_type character varying(255),
    descrip character varying(50),
    geom public.geometry
);


CREATE SEQUENCE sources.id_bonners_lines_objectid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.id_bonners_lines_objectid_seq OWNED BY sources.id_bonners_lines.gid;


CREATE SEQUENCE sources.id_bonners_objectid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.id_bonners_objectid_seq OWNED BY sources.id_bonners.gid;


CREATE TABLE sources.id_deadwood (
    gid integer NOT NULL,
    shape_leng numeric,
    shape_area numeric,
    munpol_id character varying(100),
    handle_1 character varying(16),
    mapunit character varying(254),
    idecon character varying(254),
    featname character varying(254),
    label character varying(254),
    symbol character varying(254),
    datsou_id character varying(254),
    datatileid character varying(254),
    notes character varying(254),
    geom public.geometry(MultiPolygon,4326),
    name text,
    age text,
    description text,
    strat_name text,
    hierarchy text,
    early_id integer,
    late_id integer,
    lith text,
    comments text
);


CREATE SEQUENCE sources.id_deadwood_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.id_deadwood_gid_seq OWNED BY sources.id_deadwood.gid;


CREATE TABLE sources.id_deadwood_lines (
    gid integer NOT NULL,
    fid_polyli integer,
    shape_leng numeric,
    faults_id character varying(100),
    handle_1 character varying(16),
    type character varying(254),
    iscon smallint,
    locconmet numeric,
    exicon character varying(254),
    idecon character varying(254),
    authloccon character varying(254),
    symbol character varying(254),
    label character varying(254),
    datsou_id character varying(254),
    notes character varying(254),
    datatileid character varying(254),
    datsou_id2 character varying(254),
    faulttype character varying(254),
    faulmov character varying(254),
    faulmovcap smallint,
    faultcode character varying(254),
    l_unit character varying(254),
    r_unit character varying(254),
    geom public.geometry(MultiLineString,4326),
    mapunit text,
    new_type text,
    descrip text
);


CREATE SEQUENCE sources.id_deadwood_lines_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.id_deadwood_lines_gid_seq OWNED BY sources.id_deadwood_lines.gid;


CREATE TABLE sources.id_deadwood_points (
    gid integer NOT NULL,
    fid_oripts integer,
    feature character varying(13),
    orig_fid integer,
    fid_munpol integer,
    oripts_id character varying(100),
    handle_1 character varying(254),
    type character varying(254),
    meascat character varying(254),
    stationid character varying(254),
    mapunit character varying(254),
    symbol character varying(254),
    label character varying(254),
    locconmet numeric,
    plotatsca numeric,
    notes character varying(254),
    locsou_id character varying(254),
    datsou_id character varying(254),
    autocadang numeric,
    azimuth numeric,
    inclinatio numeric,
    geoobjtyp character varying(254),
    idecon character varying(254),
    oricondeg numeric,
    oricdegdip numeric,
    datatileid character varying(254),
    datsou_id2 character varying(254),
    geom public.geometry(Point,4326),
    point_type text,
    dip_dir integer
);


CREATE SEQUENCE sources.id_deadwood_points_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.id_deadwood_points_gid_seq OWNED BY sources.id_deadwood_points.gid;


CREATE TABLE sources.id_fairfield (
    gid integer NOT NULL,
    mapunit character varying(255),
    objectid_1 double precision,
    mapunit_1 character varying(255),
    name character varying(255),
    strat_name character varying(255),
    top_age character varying(255),
    bottom_age character varying(255),
    general_lithology character varying(255),
    igs_lithology character varying(255),
    lith character varying(255),
    comments character varying(255),
    desc_ character varying,
    shape_length double precision,
    shape_area double precision,
    wkb_geometry public.geometry(MultiPolygon,26769),
    geom public.geometry,
    early_id integer,
    late_id integer,
    use_age text
);


CREATE TABLE sources.id_fairfield_lines (
    gid integer NOT NULL,
    type character varying(255),
    shape_length double precision,
    name character varying(255),
    new_type character varying(255),
    descrip character varying(50),
    geom public.geometry
);


CREATE SEQUENCE sources.id_fairfield_lines_objectid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.id_fairfield_lines_objectid_seq OWNED BY sources.id_fairfield_lines.gid;


CREATE SEQUENCE sources.id_fairfield_objectid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.id_fairfield_objectid_seq OWNED BY sources.id_fairfield.gid;


CREATE TABLE sources.id_grangeville (
    gid integer NOT NULL,
    mapunit character varying(255),
    name character varying(255),
    strat_name character varying(255),
    bottom_age character varying(255),
    top_age character varying(255),
    description character varying,
    generallithology character varying(255),
    igs_lithology character varying(255),
    comments character varying(255),
    shape_length double precision,
    shape_area double precision,
    geom public.geometry,
    early_id integer,
    late_id integer,
    use_age text
);


CREATE TABLE sources.id_grangeville_lines (
    gid integer NOT NULL,
    fid_polyli integer,
    faults_id character varying(100),
    handle_1 character varying(16),
    type character varying(255),
    isconcealed smallint,
    locationconfidencemeters double precision,
    existenceconfidence character varying(255),
    identityconfidence character varying(255),
    authorlocationconfidence character varying(255),
    symbol character varying(255),
    label character varying(255),
    datasourceid character varying(255),
    notes character varying(255),
    datatileid character varying(255),
    datasourceid2 character varying(255),
    faulttype character varying(255),
    faultmovement character varying(255),
    faultmovecapture smallint,
    faultcode character varying(255),
    l_unit character varying(255),
    r_unit character varying(255),
    shape_length double precision,
    description character varying(50),
    geom public.geometry,
    new_type text
);


CREATE SEQUENCE sources.id_grangeville_lines_objectid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.id_grangeville_lines_objectid_seq OWNED BY sources.id_grangeville_lines.gid;


CREATE SEQUENCE sources.id_grangeville_objectid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.id_grangeville_objectid_seq OWNED BY sources.id_grangeville.gid;


CREATE TABLE sources.id_idahocity (
    gid integer NOT NULL,
    mapunit character varying(255),
    name character varying(255),
    bottom_age character varying(255),
    strat_name character varying(255),
    top_age character varying(255),
    description character varying,
    generallithology character varying(255),
    comments character varying(255),
    igs_lithology character varying(255),
    shape_length double precision,
    shape_area double precision,
    geom public.geometry,
    early_id integer,
    late_id integer,
    use_age text
);


CREATE TABLE sources.id_idahocity_lines (
    gid integer NOT NULL,
    type character varying(255),
    shape_length double precision,
    name character varying(255),
    new_type character varying(255),
    descrip character varying(50),
    geom public.geometry
);


CREATE SEQUENCE sources.id_idahocity_lines_objectid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.id_idahocity_lines_objectid_seq OWNED BY sources.id_idahocity_lines.gid;


CREATE SEQUENCE sources.id_idahocity_objectid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.id_idahocity_objectid_seq OWNED BY sources.id_idahocity.gid;


CREATE TABLE sources.id_murphy (
    gid integer NOT NULL,
    mapunit character varying(255),
    name character varying(255),
    strat_name character varying(255),
    top_age character varying(255),
    b_age character varying(255),
    generallit character varying(255),
    igs_lithol character varying(255),
    description character varying(255),
    comments character varying,
    shape_length double precision,
    shape_area double precision,
    wkb_geometry public.geometry(MultiPolygon,26770),
    geom public.geometry,
    early_id integer,
    late_id integer,
    use_age text
);


CREATE TABLE sources.id_murphy_lines (
    gid integer NOT NULL,
    type character varying(255),
    shape_length double precision,
    name character varying(255),
    new_type character varying(255),
    descrip character varying(50),
    wkb_geometry public.geometry(MultiLineString,26770),
    geom public.geometry
);


CREATE SEQUENCE sources.id_murphy_lines_objectid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.id_murphy_lines_objectid_seq OWNED BY sources.id_murphy_lines.gid;


CREATE SEQUENCE sources.id_murphy_objectid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.id_murphy_objectid_seq OWNED BY sources.id_murphy.gid;


CREATE TABLE sources.id_salmon (
    objectid integer NOT NULL,
    mapunit character varying(255),
    name character varying(255),
    strat_name character varying(255),
    top_age character varying(255),
    b_age character varying(255),
    generallithology character varying(255),
    igs_lithology character varying(255),
    description character varying,
    comments character varying(255),
    shape_length double precision,
    shape_area double precision,
    early_id integer,
    late_id integer,
    gid integer NOT NULL,
    use_age text,
    geom public.geometry
);


CREATE SEQUENCE sources.id_salmon_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.id_salmon_gid_seq OWNED BY sources.id_salmon.gid;


CREATE TABLE sources.id_salmon_lines (
    objectid integer NOT NULL,
    type character varying(255),
    shape_length double precision,
    name character varying(255),
    new_type character varying(255),
    descrip character varying(50),
    gid integer NOT NULL,
    geom public.geometry
);


CREATE SEQUENCE sources.id_salmon_lines_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.id_salmon_lines_gid_seq OWNED BY sources.id_salmon_lines.gid;


CREATE SEQUENCE sources.id_salmon_lines_objectid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.id_salmon_lines_objectid_seq OWNED BY sources.id_salmon_lines.objectid;


CREATE SEQUENCE sources.id_salmon_objectid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.id_salmon_objectid_seq OWNED BY sources.id_salmon.objectid;


CREATE TABLE sources.id_sandpoint (
    gid integer NOT NULL,
    mapunit character varying(255),
    name character varying(255),
    strat_name character varying(255),
    top_age character varying(255),
    bottom_age character varying(255),
    comments character varying(255),
    description character varying,
    general_lithology character varying(255),
    shape_length double precision,
    shape_area double precision,
    wkb_geometry public.geometry(MultiPolygon,26770),
    geom public.geometry,
    early_id integer,
    late_id integer
);


CREATE TABLE sources.id_sandpoint_lines (
    gid integer NOT NULL,
    contactsandfaults_id character varying(100),
    type character varying(255),
    isconcealed smallint,
    locationconfidencemeters double precision,
    existenceconfidence character varying(255),
    identityconfidence character varying(255),
    authorlocationconfidence character varying(255),
    symbol character varying(255),
    label character varying(255),
    datasourceid character varying(255),
    notes character varying(255),
    datatileid character varying(255),
    datasourceid2 character varying(255),
    faulttype character varying(255),
    faultmovement character varying(255),
    faultmovecapture smallint,
    faultcode character varying(255),
    l_unit character varying(255),
    r_unit character varying(255),
    flip smallint DEFAULT 0,
    shape_length double precision,
    wkb_geometry public.geometry(MultiLineString,26770),
    geom public.geometry,
    new_type text,
    new_direction text
);


CREATE SEQUENCE sources.id_sandpoint_lines_objectid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.id_sandpoint_lines_objectid_seq OWNED BY sources.id_sandpoint_lines.gid;


CREATE SEQUENCE sources.id_sandpoint_objectid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.id_sandpoint_objectid_seq OWNED BY sources.id_sandpoint.gid;


CREATE TABLE sources.id_twinfalls (
    gid integer NOT NULL,
    mapunit character varying(255),
    name character varying(255),
    b_age character varying(255),
    strat_name character varying(255),
    top_age character varying(255),
    generallithology character varying(255),
    description character varying,
    igs_lithology character varying(255),
    lith character varying(255),
    comments character varying(255),
    shape_length double precision,
    shape_area double precision,
    wkb_geometry public.geometry(MultiPolygon,26769),
    geom public.geometry,
    early_id integer,
    late_id integer,
    use_age text
);


CREATE TABLE sources.id_twinfalls_lines (
    gid integer NOT NULL,
    type character varying(255),
    shape_length double precision,
    name character varying(255),
    new_type character varying(255),
    descrip character varying(50),
    wkb_geometry public.geometry(MultiLineString,26769),
    geom public.geometry
);


CREATE SEQUENCE sources.id_twinfalls_lines_objectid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.id_twinfalls_lines_objectid_seq OWNED BY sources.id_twinfalls_lines.gid;


CREATE SEQUENCE sources.id_twinfalls_objectid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.id_twinfalls_objectid_seq OWNED BY sources.id_twinfalls.gid;


CREATE TABLE sources.in_allen (
    gid integer NOT NULL,
    area_ numeric,
    perimeter numeric,
    besu_geo_ numeric,
    besu_geo_i numeric,
    unit character varying(7),
    system character varying(50),
    stratigrap character varying(50),
    globalid character varying(38),
    shape_area numeric,
    shape_len numeric,
    unit_desc character varying(254),
    geom public.geometry(MultiPolygon,4326),
    early_id integer,
    late_id integer
);


CREATE SEQUENCE sources.in_allen_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.in_allen_gid_seq OWNED BY sources.in_allen.gid;


CREATE TABLE sources.in_bartholomew (
    gid integer NOT NULL,
    shape_length double precision,
    shape_area double precision,
    mapunitpolys_id character varying(50) NOT NULL,
    mapunit character varying(10) NOT NULL,
    identityconfidence character varying(50) NOT NULL,
    label character varying(50),
    symbol character varying(254),
    notes character varying(254),
    datasourceid character varying(50) NOT NULL,
    created_user character varying(255),
    created_date timestamp with time zone,
    last_edited_user character varying(255),
    last_edited_date timestamp with time zone,
    geom public.geometry(MultiPolygon,4326),
    descrip text,
    strat_name text,
    hierarchy text,
    lithology text,
    early_id integer,
    late_id integer,
    unit_name text,
    age text
);


CREATE TABLE sources.in_lawrence (
    gid integer NOT NULL,
    objectid numeric,
    mapunitpol character varying(50),
    mapunit character varying(10),
    identityco character varying(50),
    label character varying(50),
    symbol character varying(254),
    notes character varying(254),
    datasource character varying(50),
    shape_leng numeric,
    shape_area numeric,
    area_lengt numeric,
    geom public.geometry(MultiPolygon,4326),
    age text,
    unit_name text,
    strat_name text,
    descrip text,
    early_id integer,
    late_id integer
);


CREATE SEQUENCE sources.in_lawrence_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.in_lawrence_gid_seq OWNED BY sources.in_lawrence.gid;


CREATE TABLE sources.in_lawrence_lines (
    gid integer NOT NULL,
    objectid numeric,
    contactsan character varying(50),
    type character varying(254),
    isconceale character varying(1),
    existencec character varying(50),
    identityco character varying(50),
    locationco numeric,
    symbol character varying(254),
    label character varying(50),
    datasource character varying(50),
    notes character varying(254),
    shape_leng numeric,
    geom public.geometry(MultiLineString,4326)
);


CREATE SEQUENCE sources.in_lawrence_lines_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.in_lawrence_lines_gid_seq OWNED BY sources.in_lawrence_lines.gid;


CREATE TABLE sources.in_marion (
    gid integer NOT NULL,
    objectid bigint,
    entity character varying(16),
    bedrock_un character varying(50),
    age character varying(50),
    descriptio text,
    upper_cont character varying(250),
    lower_cont character varying(250),
    thickness_ character varying(50),
    shape_leng numeric,
    shape_area numeric,
    htmldescri character varying(254),
    geom public.geometry(MultiPolygon,4326),
    strat_name text,
    early_id integer,
    late_id integer
);


CREATE SEQUENCE sources.in_marion_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.in_marion_gid_seq OWNED BY sources.in_marion.gid;


CREATE TABLE sources.in_morresville_w (
    gid integer NOT NULL,
    objectid integer,
    shape_leng double precision,
    mapsymbol character varying(10),
    unitdescri character varying(254),
    unitname character varying(50),
    top_age character varying(50),
    bottom_age character varying(50),
    shape_length double precision,
    shape_area double precision,
    early_id integer,
    late_id integer,
    geom public.geometry,
    strat_name text
);


CREATE SEQUENCE sources.in_morresville_w_objectid_1_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.in_morresville_w_objectid_1_seq OWNED BY sources.in_morresville_w.gid;


CREATE TABLE sources.in_swhitleyw (
    gid integer NOT NULL,
    objectid numeric,
    mapunitdes character varying(100),
    objectid_1 bigint,
    mapunitd_1 character varying(254),
    shape_leng numeric,
    shape_area numeric,
    unitname character varying(254),
    unitdescri text,
    formation character varying(254),
    age character varying(254),
    top_age character varying(254),
    bottom_age character varying(254),
    shape_le_1 numeric,
    shape_ar_1 numeric,
    geom public.geometry(MultiPolygon,4326),
    early_id integer,
    late_id integer,
    strat_name text
);


CREATE SEQUENCE sources.in_swhitleyw_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.in_swhitleyw_gid_seq OWNED BY sources.in_swhitleyw.gid;


CREATE TABLE sources.iowa (
    gid integer NOT NULL,
    system character varying(254),
    unitcode character varying(254),
    unitname character varying(254),
    shape_leng numeric,
    shape_area numeric,
    geom public.geometry(MultiPolygon,4326),
    descrip text,
    age character varying(100),
    early_id integer,
    late_id integer
);


CREATE TABLE sources.iowa_co_wi (
    gid integer NOT NULL,
    unitcode character varying(25),
    shape_leng numeric,
    shape_area numeric,
    unitname character varying(75),
    geom public.geometry(MultiPolygon,4326),
    early_id integer,
    late_id integer,
    lith text,
    age character varying(100),
    strat_name text,
    hierarchy text
);


CREATE SEQUENCE sources.iowa_co_wi_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.iowa_co_wi_gid_seq OWNED BY sources.iowa_co_wi.gid;


CREATE SEQUENCE sources.iowa_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.iowa_gid_seq OWNED BY sources.iowa.gid;


CREATE TABLE sources.iowa_lines (
    gid integer NOT NULL,
    faultname character varying(50),
    geom public.geometry(MultiLineString,4326),
    new_type text,
    new_direction text
);


CREATE SEQUENCE sources.iowa_lines2_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.iowa_lines2_gid_seq OWNED BY sources.iowa_lines.gid;


CREATE TABLE sources.iran (
    gid integer NOT NULL,
    geo_unit character varying(254),
    descriptio character varying(254),
    age character varying(254),
    __gid character varying(254),
    geom public.geometry(MultiPolygon,4326),
    strat_name text,
    early_id integer,
    late_id integer
);


CREATE SEQUENCE sources.iran_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.iran_gid_seq OWNED BY sources.iran.gid;


CREATE TABLE sources.iran_lines (
    gid integer NOT NULL,
    layer character varying(254),
    __gid character varying(254),
    geom public.geometry(MultiLineString,4326),
    new_type text
);


CREATE SEQUENCE sources.iran_lines_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.iran_lines_gid_seq OWNED BY sources.iran_lines.gid;


CREATE SEQUENCE sources.jaspergeo_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.jaspergeo_gid_seq OWNED BY sources.ar_jasper.gid;


CREATE SEQUENCE sources.jasperlines_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.jasperlines_gid_seq OWNED BY sources.ar_jasper_lines.gid;


CREATE TABLE sources.joshuatree (
    gid integer NOT NULL,
    mapunitlab character varying(254),
    identityco character varying(254),
    datasource character varying(254),
    sciencenot character varying(254),
    shape_leng numeric,
    shape_area numeric,
    geom public.geometry(MultiPolygon,4326),
    descrip text,
    unitname character varying(150),
    age character varying(150),
    lith character varying(254),
    comments character varying(254),
    early_id integer,
    late_id integer
);


CREATE TABLE sources.joshuatree_faults (
    gid integer NOT NULL,
    geologicfe character varying(254),
    earthmater character varying(254),
    identityex character varying(254),
    observabil character varying(254),
    sciencenot character varying(254),
    name character varying(254),
    descriptor character varying(254),
    faultgroup character varying(254),
    shape_leng numeric,
    geneticcla character varying(254),
    stylerefer character varying(254),
    geom public.geometry(MultiLineString,4326),
    new_type character varying(100),
    new_direction character varying(100)
);


CREATE SEQUENCE sources.joshuatree_faults_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.joshuatree_faults_gid_seq OWNED BY sources.joshuatree_faults.gid;


CREATE SEQUENCE sources.joshuatree_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.joshuatree_gid_seq OWNED BY sources.joshuatree.gid;


CREATE TABLE sources.ky24k (
    gid integer NOT NULL,
    identifier character varying(254),
    name character varying(254),
    descriptio character varying(254),
    geologicun character varying(254),
    rank character varying(254),
    lithology character varying(254),
    geologichi character varying(254),
    observatio character varying(254),
    positional character varying(254),
    source character varying(254),
    geologic_1 character varying(254),
    representa character varying(254),
    represen_1 character varying(254),
    represen_2 character varying(254),
    represen_3 character varying(254),
    specificat character varying(254),
    metadata_u character varying(254),
    genericsym character varying(254),
    objectid numeric(10,0),
    kgs_map_sy character varying(7),
    kgs_format character varying(8),
    kgs_gq_num character varying(5),
    kgs_sort_c numeric(10,0),
    shape_leng numeric,
    shape_area numeric,
    geom public.geometry(MultiPolygon,4326),
    description character varying(254),
    early_id integer,
    late_id integer,
    descrip text
);


CREATE TABLE sources.ky24k_faults (
    gid integer NOT NULL,
    identifier character varying(254),
    name character varying(254),
    descriptio character varying(254),
    faulttype character varying(254),
    movementty character varying(254),
    deformatio character varying(254),
    displaceme character varying(254),
    geologichi character varying(254),
    observatio character varying(254),
    positional character varying(254),
    source character varying(254),
    faulttype_ character varying(254),
    movement_1 character varying(254),
    deformat_1 character varying(254),
    representa character varying(254),
    represen_1 character varying(254),
    represen_2 character varying(254),
    specificat character varying(254),
    metadata_u character varying(254),
    genericsym character varying(254),
    objectid numeric(10,0),
    gqnum numeric(10,0),
    symbolizer character varying(254),
    repruleid numeric(10,0),
    shape_leng numeric,
    geom public.geometry(MultiLineString,4326)
);


CREATE SEQUENCE sources.ky24k_faults_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.ky24k_faults_gid_seq OWNED BY sources.ky24k_faults.gid;


CREATE SEQUENCE sources.ky24k_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.ky24k_gid_seq OWNED BY sources.ky24k.gid;


CREATE TABLE sources.ky_descrip (
    id integer NOT NULL,
    orig_url text,
    new_desc text
);


CREATE SEQUENCE sources.ky_descrip_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.ky_descrip_id_seq OWNED BY sources.ky_descrip.id;


CREATE TABLE sources.wi_lacrosse (
    gid integer NOT NULL,
    area double precision,
    perimeter double precision,
    lc_brg_py2 numeric(10,0),
    lc_brg_p_1 numeric(10,0),
    uname character varying(3),
    geom public.geometry(MultiPolygon,4326),
    name text,
    b_age text,
    t_age text,
    description text,
    comments text,
    early_id integer,
    late_id integer,
    age text,
    strat_name text
);


CREATE SEQUENCE sources.lacrosse_geo_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.lacrosse_geo_gid_seq OWNED BY sources.wi_lacrosse.gid;


CREATE TABLE sources.lake_mead (
    gid integer NOT NULL,
    oid_ numeric(10,0),
    ptype100k character varying(254),
    geofnt100k character varying(254),
    geom public.geometry(MultiPolygon,4326),
    attrs text,
    age text,
    late_age text,
    early_age text,
    late_id integer,
    early_id integer,
    descrip text,
    comments text,
    name text,
    strat_name text
);


CREATE SEQUENCE sources.lake_mead_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.lake_mead_gid_seq OWNED BY sources.lake_mead.gid;


CREATE TABLE sources.lake_mead_lines (
    gid integer,
    objectid numeric(10,0),
    ltype100k character varying(35),
    geom public.geometry(MultiLineString,4326),
    new_type text,
    new_direction text
);


CREATE TABLE sources.laketahoe (
    gid integer NOT NULL,
    ptype character varying(35),
    reference character varying(35),
    ref_unit character varying(35),
    shape_leng numeric,
    shape_area numeric,
    geom public.geometry(MultiPolygon,4326),
    name text,
    strat_name text,
    hierarchy text,
    age text,
    description text,
    early_id integer,
    late_id integer
);


CREATE SEQUENCE sources.laketahoe_geology_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.laketahoe_geology_gid_seq OWNED BY sources.laketahoe.gid;


CREATE TABLE sources.laketahoe_lines (
    gid integer NOT NULL,
    ltype character varying(35),
    reference character varying(35),
    shape_leng numeric,
    geom public.geometry(MultiLineString,4326),
    new_type text,
    new_direction text
);


CREATE SEQUENCE sources.laketahoe_lines_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.laketahoe_lines_gid_seq OWNED BY sources.laketahoe_lines.gid;


CREATE TABLE sources.laketahoe_point (
    gid integer NOT NULL,
    pttype character varying(50),
    dip smallint,
    strike smallint,
    reference character varying(50),
    geom public.geometry(Point,4326),
    point_type text,
    dip_dir integer
);


CREATE SEQUENCE sources.laketahoe_point_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.laketahoe_point_gid_seq OWNED BY sources.laketahoe_point.gid;


CREATE TABLE sources.wy_laramie (
    gid integer NOT NULL,
    objectid integer,
    area numeric,
    perimeter numeric,
    larfinal1_ numeric,
    larfinal11 numeric,
    unit character varying(6),
    code integer,
    shape_leng numeric,
    shape_area numeric,
    geom public.geometry(MultiPolygon,4326),
    name text,
    age text,
    strat_name text,
    hierarchy text,
    early_id integer,
    late_id integer,
    description text
);


CREATE SEQUENCE sources.laramie_geo_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.laramie_geo_gid_seq OWNED BY sources.wy_laramie.gid;


CREATE TABLE sources.wy_laramie_lines (
    gid integer NOT NULL,
    objectid integer,
    fnode_ numeric,
    tnode_ numeric,
    lpoly_ numeric,
    rpoly_ numeric,
    length numeric,
    lfaultdd_ numeric,
    lfaultdd_i numeric,
    type smallint,
    shape_leng numeric,
    ltype character varying(100),
    geom public.geometry(MultiLineString,4326),
    new_type text
);


CREATE SEQUENCE sources.laramie_lines_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.laramie_lines_gid_seq OWNED BY sources.wy_laramie_lines.gid;


CREATE SEQUENCE sources.lines_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.lines_gid_seq OWNED BY sources.africa_lines.gid;


CREATE TABLE sources.lissadellaustralia (
    gid integer NOT NULL,
    feature character varying(12),
    ufi integer,
    map_symb character varying(30),
    plot_symb character varying(8),
    stratno integer,
    unitname character varying(64),
    supergroup character varying(64),
    "group" character varying(64),
    subgroup character varying(64),
    formation character varying(64),
    member character varying(64),
    era character varying(100),
    period character varying(100),
    rocktype character varying(24),
    lith_desc character varying(254),
    plotrank smallint,
    geom public.geometry(MultiPolygon,4326),
    early_id integer,
    late_id integer,
    use_name character varying(64)
);


CREATE SEQUENCE sources.lissadellaustralia_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.lissadellaustralia_gid_seq OWNED BY sources.lissadellaustralia.gid;


CREATE TABLE sources.ut_logan_lines (
    gid integer NOT NULL,
    fnode_ integer,
    tnode_ integer,
    lpoly_ integer,
    rpoly_ integer,
    length numeric,
    geology_ integer,
    geology_id integer,
    type character varying(25),
    subtype character varying(25),
    modifier character varying(30),
    notes character varying(30),
    geom public.geometry(MultiLineString,4326),
    new_type text,
    new_direction text
);


CREATE SEQUENCE sources.logan_faults_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.logan_faults_gid_seq OWNED BY sources.ut_logan_lines.gid;


CREATE SEQUENCE sources.long_beach_ca_geo_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.long_beach_ca_geo_gid_seq OWNED BY sources.ca_long_beach.gid;


CREATE SEQUENCE sources.long_beach_ca_lines_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.long_beach_ca_lines_gid_seq OWNED BY sources.ca_long_beach_lines.gid;


CREATE SEQUENCE sources.long_beach_ca_points_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.long_beach_ca_points_gid_seq OWNED BY sources.ca_long_beach_points.gid;


CREATE SEQUENCE sources.los_angeles_geo_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.los_angeles_geo_gid_seq OWNED BY sources.ca_los_angeles.gid;


CREATE SEQUENCE sources.los_angeles_lines_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.los_angeles_lines_gid_seq OWNED BY sources.ca_los_angeles_lines.gid;


CREATE TABLE sources.ma_glouster_lines (
    gid integer NOT NULL,
    fnode_ integer,
    tnode_ integer,
    lpoly_ integer,
    rpoly_ integer,
    length numeric,
    contact_di integer,
    contact__1 integer,
    class_code smallint,
    shape_leng numeric,
    descriptio text,
    geom public.geometry(MultiLineString,4326),
    new_type text
);


CREATE TABLE sources.manitoba (
    gid integer NOT NULL,
    bedrock_ge numeric(10,0),
    unit_code character varying(8),
    primary_un character varying(8),
    secundary_ character varying(4),
    eon character varying(11),
    era character varying(28),
    period character varying(20),
    epoch character varying(16),
    province character varying(54),
    lithotec character varying(200),
    unit character varying(200),
    subunit character varying(200),
    unit_descr character varying(32),
    geometry_a numeric,
    geometry_l numeric,
    geom public.geometry(MultiPolygon,4326),
    early_id integer,
    late_id integer,
    age text,
    unit_descr_mod text,
    unit_mod text,
    subunit_mod character varying(200)
);


CREATE TABLE sources.manitoba_faults (
    gid integer NOT NULL,
    faults_ln_ numeric(10,0),
    geometry_l numeric,
    geom public.geometry(MultiLineString,4326),
    name character varying(100),
    linetype character varying(50)
);


CREATE SEQUENCE sources.manitoba_faults_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.manitoba_faults_gid_seq OWNED BY sources.manitoba_faults.gid;


CREATE SEQUENCE sources.manitoba_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.manitoba_gid_seq OWNED BY sources.manitoba.gid;


CREATE TABLE sources.ut_manti_lines (
    gid integer NOT NULL,
    fnode_ integer,
    tnode_ integer,
    lpoly_ integer,
    rpoly_ integer,
    length numeric,
    geology_ integer,
    geology_id integer,
    type character varying(25),
    subtype character varying(25),
    modifier character varying(30),
    notes character varying(30),
    geom public.geometry(MultiLineString,4326),
    new_type text,
    new_direction text
);


CREATE SEQUENCE sources.manti_lines_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.manti_lines_gid_seq OWNED BY sources.ut_manti_lines.gid;


CREATE TABLE sources.ut_manti (
    gid integer NOT NULL,
    area numeric,
    perimeter numeric,
    geology_ integer,
    geology_id integer,
    unitsymbol character varying(15),
    unitname character varying(80),
    age character varying(50),
    notes character varying(50),
    geom public.geometry(MultiPolygon,4326),
    description text,
    early_id integer,
    late_id integer
);


CREATE SEQUENCE sources.mantiutgeology_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.mantiutgeology_gid_seq OWNED BY sources.ut_manti.gid;


CREATE TABLE sources.saipan (
    gid integer NOT NULL,
    objectid numeric(10,0),
    fuid numeric(10,0),
    glg_sym character varying(12),
    src_sym character varying(12),
    sort_no numeric,
    notes character varying(254),
    lbl character varying(60),
    gmap_id numeric(10,0),
    shape_leng numeric,
    shape_area numeric,
    objectid_1 integer,
    glg_sym_1 character varying(12),
    glg_name character varying(100),
    age character varying(100),
    mj_lith character varying(254),
    geom public.geometry(MultiPolygon,4326),
    description text,
    early_id integer,
    late_id integer
);


CREATE SEQUENCE sources.marianaislandsgeology_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.marianaislandsgeology_gid_seq OWNED BY sources.saipan.gid;


CREATE SEQUENCE sources.marin_co_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.marin_co_gid_seq OWNED BY sources.ca_marin.gid;


CREATE TABLE sources.md_catocinfurnace (
    gid integer NOT NULL,
    area numeric,
    perimeter numeric,
    catoc_geo_ numeric(10,0),
    catoc_geo1 numeric(10,0),
    unit_label character varying(10),
    anno_label character varying(10),
    unit_name character varying(85),
    coa_id numeric,
    geomap_id numeric,
    quadname character varying(40),
    geom public.geometry(MultiPolygon,4326),
    age text,
    description text,
    strat_name text,
    hierarchy text,
    comments text,
    early_id integer,
    late_id integer
);


CREATE SEQUENCE sources.md_catocinfurnace_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.md_catocinfurnace_gid_seq OWNED BY sources.md_catocinfurnace.gid;


CREATE TABLE sources.md_catocinfurnace_lines (
    gid integer NOT NULL,
    fnode_ numeric(10,0),
    tnode_ numeric(10,0),
    lpoly_ numeric(10,0),
    rpoly_ numeric(10,0),
    length numeric,
    catoc_strl numeric(10,0),
    catoc_st_1 numeric(10,0),
    struct_typ numeric,
    struc_crtn character varying(10),
    type character varying(50),
    modifier character varying(50),
    desc_struc character varying(120),
    geomap_id numeric,
    quadname character varying(40),
    geom public.geometry(MultiLineString,4326),
    new_type text
);


CREATE SEQUENCE sources.md_catocinfurnace_lines_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.md_catocinfurnace_lines_gid_seq OWNED BY sources.md_catocinfurnace_lines.gid;


CREATE TABLE sources.md_catocinfurnace_points (
    gid integer NOT NULL,
    area numeric,
    perimeter numeric,
    catoc_strp numeric(10,0),
    catoc_st_1 numeric(10,0),
    strikequad character varying(2),
    strikedegr numeric(10,0),
    dipdirecti character varying(2),
    dipamount numeric(10,0),
    azimuth numeric(10,0),
    struct_typ numeric,
    type character varying(50),
    modifier character varying(50),
    desc_struc character varying(120),
    geomap_id numeric,
    quadname character varying(40),
    north_sp83 numeric,
    east_sp83m numeric,
    f_polygoni numeric(10,0),
    f_scale numeric,
    f_angle numeric,
    geom public.geometry(Point,4326),
    point_type text,
    dip_dir integer
);


CREATE SEQUENCE sources.md_catocinfurnace_points_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.md_catocinfurnace_points_gid_seq OWNED BY sources.md_catocinfurnace_points.gid;


CREATE TABLE sources.md_catocinfurnace_q (
    gid integer,
    area numeric,
    perimeter numeric,
    catoc_geo_ numeric(10,0),
    catoc_geo1 numeric(10,0),
    unit_label character varying(10),
    anno_label character varying(10),
    unit_name character varying(85),
    coa_id numeric,
    geomap_id numeric,
    quadname character varying(40),
    geom public.geometry(MultiPolygon,4326),
    age text,
    description text,
    strat_name text,
    hierarchy text,
    comments text,
    early_id integer,
    late_id integer
);


CREATE TABLE sources.md_clearspring (
    gid integer NOT NULL,
    objectid integer,
    mapunitabb character varying(16),
    mapunit character varying(254),
    label character varying(254),
    idconf smallint,
    pattern integer,
    datasource integer,
    notes character varying(254),
    geologicag integer,
    mapunitdes integer,
    fc_id integer,
    quad_id integer,
    shape_leng numeric,
    shape_area numeric,
    ruleid integer,
    geom public.geometry(MultiPolygon,4326),
    name text,
    age text,
    description text,
    strat_name text,
    hierarchy text,
    comments text,
    early_id integer,
    late_id integer
);


CREATE SEQUENCE sources.md_clearspring_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.md_clearspring_gid_seq OWNED BY sources.md_clearspring.gid;


CREATE TABLE sources.md_clearspring_lines (
    gid integer NOT NULL,
    objectid integer,
    imp_ftype character varying(254),
    label character varying(254),
    locationco double precision,
    exconf smallint,
    idconf smallint,
    locationme character varying(254),
    datasource integer,
    notes character varying(254),
    ruleid integer,
    fgdcrefno character varying(254),
    fgdcdesc character varying(254),
    fc_id integer,
    shape_leng numeric,
    quad_id integer,
    geom public.geometry(MultiLineString,4326),
    new_type text
);


CREATE SEQUENCE sources.md_clearspring_lines_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.md_clearspring_lines_gid_seq OWNED BY sources.md_clearspring_lines.gid;


CREATE TABLE sources.md_clearspring_points (
    gid integer NOT NULL,
    objectid integer,
    imp_ftype character varying(254),
    azimuth double precision,
    inclinatio double precision,
    symbolrota double precision,
    labelrotat double precision,
    label character varying(254),
    locationco double precision,
    idconf smallint,
    stations_i integer,
    locationso integer,
    datasource integer,
    orientatio double precision,
    mapunit character varying(254),
    notes character varying(254),
    ruleid integer,
    fgdcrefno character varying(16),
    fgdcdesc character varying(254),
    symbolro_1 smallint,
    fc_id integer,
    quad_id integer,
    geom public.geometry(Point,4326),
    dip_dir integer,
    point_type text
);


CREATE SEQUENCE sources.md_clearspring_points_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.md_clearspring_points_gid_seq OWNED BY sources.md_clearspring_points.gid;


CREATE TABLE sources.md_clearspring_q (
    gid integer,
    objectid integer,
    mapunitabb character varying(16),
    mapunit character varying(254),
    label character varying(254),
    idconf smallint,
    pattern integer,
    datasource integer,
    notes character varying(254),
    geologicag integer,
    mapunitdes integer,
    fc_id integer,
    quad_id integer,
    shape_leng numeric,
    shape_area numeric,
    ruleid integer,
    geom public.geometry(MultiPolygon,4326),
    name text,
    age text,
    description text,
    strat_name text,
    hierarchy text,
    comments text,
    early_id integer,
    late_id integer
);


CREATE TABLE sources.md_frederick (
    gid integer NOT NULL,
    area numeric,
    perimeter numeric,
    frede_geo_ numeric(10,0),
    frede_geo1 numeric(10,0),
    unit_label character varying(10),
    anno_label character varying(10),
    unit_name character varying(75),
    coa_id numeric,
    geomap_id numeric,
    quadname character varying(40),
    geom public.geometry(MultiPolygon,4326),
    age text,
    description text,
    strat_name text,
    hierarchy text,
    early_id integer,
    late_id integer,
    comments text
);


CREATE SEQUENCE sources.md_frederick_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.md_frederick_gid_seq OWNED BY sources.md_frederick.gid;


CREATE TABLE sources.md_frederick_lines (
    gid integer NOT NULL,
    fnode_ numeric(10,0),
    tnode_ numeric(10,0),
    lpoly_ numeric(10,0),
    rpoly_ numeric(10,0),
    length numeric,
    frede_strl numeric(10,0),
    frede_st_1 numeric(10,0),
    struct_typ numeric,
    type character varying(50),
    modifier character varying(50),
    desc_struc character varying(90),
    struct_crt character varying(10),
    geomap_id numeric,
    quadname character varying(40),
    geom public.geometry(MultiLineString,4326),
    new_type text
);


CREATE SEQUENCE sources.md_frederick_linestwo_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.md_frederick_linestwo_gid_seq OWNED BY sources.md_frederick_lines.gid;


CREATE TABLE sources.md_frederick_point (
    gid integer NOT NULL,
    area double precision,
    perimeter double precision,
    frede_strp numeric(10,0),
    frede_st_1 numeric(10,0),
    strikequad character varying(2),
    strikedegr numeric(10,0),
    dipdirecti character varying(2),
    dipamount numeric(10,0),
    azimuth numeric(10,0),
    struct_typ numeric,
    type character varying(50),
    modifier character varying(50),
    desc_struc character varying(90),
    geomap_id numeric,
    quadname character varying(40),
    north_sp83 numeric,
    east_sp83m numeric,
    f_polygoni numeric(10,0),
    f_scale double precision,
    f_angle double precision,
    geom public.geometry(Point,4326),
    point_type text,
    dip_dir integer
);


CREATE SEQUENCE sources.md_frederick_point_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.md_frederick_point_gid_seq OWNED BY sources.md_frederick_point.gid;


CREATE TABLE sources.md_keedysville (
    gid integer NOT NULL,
    area numeric,
    perimeter numeric,
    kshc_geo_ numeric(10,0),
    kshc_geo_i numeric(10,0),
    unit_label character varying(10),
    anno_label character varying(10),
    unit_name character varying(75),
    lith_abbre character varying(254),
    coa_id double precision,
    geomap_id numeric,
    geom public.geometry(MultiPolygon,4326),
    age text,
    description text,
    strat_name text,
    hierarchy text,
    early_id integer,
    late_id integer,
    comments text
);


CREATE SEQUENCE sources.md_keedysville_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.md_keedysville_gid_seq OWNED BY sources.md_keedysville.gid;


CREATE TABLE sources.md_keedysville_line (
    gid integer NOT NULL,
    str_typ_id double precision,
    struc_crt character varying(15),
    type character varying(25),
    modifier character varying(50),
    desc_struc character varying(150),
    geomap_id numeric,
    map_sym character varying(50),
    struc_name character varying(30),
    fgdcrefno character varying(16),
    geom public.geometry(MultiLineString,4326),
    new_type text,
    descrip text
);


CREATE TABLE sources.md_keedysville_q (
    gid integer,
    area numeric,
    perimeter numeric,
    kshc_geo_ numeric(10,0),
    kshc_geo_i numeric(10,0),
    unit_label character varying(10),
    anno_label character varying(10),
    unit_name character varying(75),
    lith_abbre character varying(254),
    coa_id double precision,
    geomap_id numeric,
    geom public.geometry(MultiPolygon,4326),
    age text,
    description text,
    strat_name text,
    hierarchy text,
    early_id integer,
    late_id integer,
    comments text
);


CREATE TABLE sources.md_myerssmith (
    gid integer NOT NULL,
    area numeric,
    perimeter numeric,
    mysm_geo_ numeric(10,0),
    mysm_geo_i numeric(10,0),
    unit_label character varying(10),
    anno_label character varying(10),
    unit_name character varying(75),
    lith_abbre character varying(254),
    coa_id double precision,
    geomap_id numeric,
    geom public.geometry(MultiPolygon,4326),
    age text,
    description text,
    strat_name text,
    hierarchy text,
    comments text,
    early_id integer,
    late_id integer
);


CREATE SEQUENCE sources.md_myerssmith_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.md_myerssmith_gid_seq OWNED BY sources.md_myerssmith.gid;


CREATE TABLE sources.md_myerssmith_lines (
    gid integer NOT NULL,
    str_typ_id double precision,
    struct_crt character varying(15),
    type character varying(25),
    modifier character varying(50),
    desc_struc character varying(150),
    geomap_id numeric,
    map_sym character varying(50),
    struc_name character varying(30),
    fgdcrefno character varying(16),
    geom public.geometry(MultiLineString,4326),
    new_type text
);


CREATE SEQUENCE sources.md_myerssmith_lines_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.md_myerssmith_lines_gid_seq OWNED BY sources.md_myerssmith_lines.gid;


CREATE TABLE sources.md_myerssmith_q (
    gid integer,
    area numeric,
    perimeter numeric,
    mysm_geo_ numeric(10,0),
    mysm_geo_i numeric(10,0),
    unit_label character varying(10),
    anno_label character varying(10),
    unit_name character varying(75),
    lith_abbre character varying(254),
    coa_id double precision,
    geomap_id numeric,
    geom public.geometry(MultiPolygon,4326),
    age text,
    description text,
    strat_name text,
    hierarchy text,
    comments text,
    early_id integer,
    late_id integer
);


CREATE TABLE sources.md_newwindsor (
    gid integer NOT NULL,
    area numeric,
    perimeter numeric,
    newwi_geo_ numeric(10,0),
    newwi_geo1 numeric(10,0),
    unit_label character varying(10),
    anno_label character varying(10),
    unit_name character varying(75),
    lith_abbre character varying(254),
    coa_id double precision,
    geomap_id double precision,
    quadname character varying(25),
    fisher_197 character varying(10),
    geom public.geometry(MultiPolygon,4326),
    age text,
    description text,
    strat_name text,
    hierarchy text,
    comments text,
    early_id integer,
    late_id integer
);


CREATE SEQUENCE sources.md_newwindsor_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.md_newwindsor_gid_seq OWNED BY sources.md_newwindsor.gid;


CREATE TABLE sources.md_newwindsor_lines (
    gid integer NOT NULL,
    fnode_ numeric(10,0),
    tnode_ numeric(10,0),
    lpoly_ numeric(10,0),
    rpoly_ numeric(10,0),
    length numeric,
    newwi_strl numeric(10,0),
    newwi_st_1 numeric(10,0),
    struct_typ double precision,
    struct_ctr character varying(11),
    type character varying(20),
    modifier character varying(50),
    desc_struc character varying(90),
    struct_nam character varying(27),
    fold_gen character varying(5),
    geomap_id double precision,
    quadname character varying(25),
    geom public.geometry(MultiLineString,4326),
    new_type text
);


CREATE SEQUENCE sources.md_newwindsor_lines_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.md_newwindsor_lines_gid_seq OWNED BY sources.md_newwindsor_lines.gid;


CREATE TABLE sources.md_newwindsor_points (
    gid integer NOT NULL,
    area numeric,
    perimeter numeric,
    newwi_strp numeric(10,0),
    newwi_st_1 numeric(10,0),
    strikequad character varying(2),
    strikedegr numeric(10,0),
    dipdirecti character varying(2),
    dipamount numeric(10,0),
    azimuth numeric(10,0),
    struct_typ double precision,
    sym numeric(10,0),
    type character varying(25),
    modifier character varying(50),
    desc_struc character varying(90),
    geomap_id double precision,
    quadname character varying(25),
    north_sp83 numeric,
    east_sp83m numeric,
    f_polygoni numeric(10,0),
    f_scale numeric,
    f_angle numeric,
    geom public.geometry(Point,4326),
    point_type text,
    dip_dir integer,
    strike integer,
    dip integer
);


CREATE SEQUENCE sources.md_newwindsor_points_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.md_newwindsor_points_gid_seq OWNED BY sources.md_newwindsor_points.gid;


CREATE TABLE sources.md_western (
    gid integer NOT NULL,
    objectid integer,
    mapunitabb character varying(16),
    mapunit character varying(254),
    label character varying(254),
    geologicag character varying(50),
    ruleid integer,
    label_1 character varying(254),
    map_unit character varying(254),
    mapunitd_1 character varying(254),
    geologic_1 character varying(254),
    descriptio character varying(254),
    geom public.geometry(MultiPolygon,4326),
    strat_name text,
    early_id integer,
    late_id integer,
    descrip_long text
);


CREATE SEQUENCE sources.md_western_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.md_western_gid_seq OWNED BY sources.md_western.gid;


CREATE TABLE sources.md_western_lines (
    gid integer NOT NULL,
    objectid integer,
    imp_ftype character varying(254),
    label character varying(254),
    locationco double precision,
    exconf smallint,
    idconf smallint,
    locationme character varying(254),
    datasource integer,
    notes character varying(254),
    ruleid integer,
    fgdcrefno character varying(254),
    fgdcdesc character varying(254),
    fc_id integer,
    shape_leng numeric,
    geom public.geometry(MultiLineString,4326),
    new_type text
);


CREATE SEQUENCE sources.md_western_lines_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.md_western_lines_gid_seq OWNED BY sources.md_western_lines.gid;


CREATE TABLE sources.mexico (
    gid integer NOT NULL,
    objectid numeric(10,0),
    area numeric,
    perimeter numeric,
    cnal_pg_ numeric,
    cnal_pg_id numeric,
    clave character varying(15),
    fc numeric(10,0),
    entidad character varying(33),
    clase character varying(20),
    tipo character varying(38),
    era character varying(11),
    sub_era character varying(20),
    sistema character varying(13),
    union_sist character varying(17),
    serie character varying(20),
    union_ser character varying(40),
    shape_area numeric,
    shape_len numeric,
    geom public.geometry(MultiPolygon,4326),
    class text,
    age text,
    type text,
    early_id integer,
    late_id integer
);


CREATE TABLE sources.mexico_lines (
    gid integer NOT NULL,
    objectid numeric(10,0),
    fnode_ double precision,
    tnode_ double precision,
    lpoly_ double precision,
    rpoly_ double precision,
    length double precision,
    cnal_lg_ double precision,
    cnal_lg_id double precision,
    fc numeric(10,0),
    shape_len numeric,
    type character varying(254),
    entity character varying(254),
    direction character varying(254),
    ofblocks character varying(254),
    faultmovem character varying(254),
    inclination character varying(254),
    accuracy character varying(254),
    geom public.geometry(MultiLineString,4326),
    new_type text,
    new_direction text
);


CREATE SEQUENCE sources.mexicogeology_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.mexicogeology_gid_seq OWNED BY sources.mexico.gid;


CREATE SEQUENCE sources.mexicolines_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.mexicolines_gid_seq OWNED BY sources.mexico_lines.gid;


CREATE TABLE sources.mn_houston_co (
    gid integer NOT NULL,
    objectid integer,
    id integer,
    map_label character varying(5),
    shape_leng numeric,
    shape_area numeric,
    descriptn character varying(90),
    major_lith character varying(90),
    litho_modi character varying(90),
    minor_lith character varying(90),
    age character varying(90),
    matrx_comp character varying(90),
    era character varying(50),
    geom public.geometry(MultiPolygon,4326),
    descrip_long text,
    strat_name text,
    early_id integer,
    late_id integer,
    primary_lith text,
    secondary_lith text
);


CREATE TABLE sources.mn_houston_co_lines (
    gid integer NOT NULL,
    type character varying(2),
    gcm_code character varying(3),
    geoc_src character varying(5),
    geoc_date integer,
    descriptn character varying(30),
    shape_leng numeric,
    geom public.geometry(MultiLineString,4326)
);


CREATE SEQUENCE sources.mn_houston_co_faults_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.mn_houston_co_faults_gid_seq OWNED BY sources.mn_houston_co_lines.gid;


CREATE SEQUENCE sources.mn_houston_co_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.mn_houston_co_gid_seq OWNED BY sources.mn_houston_co.gid;


CREATE TABLE sources.mn_redwood_co (
    gid integer NOT NULL,
    area numeric,
    perimeter numeric,
    bgln3_ numeric(10,0),
    bgln3_id numeric(10,0),
    label character varying(4),
    unit_desc character varying(50),
    maplabel character varying(254),
    descriptn character varying(254),
    major_lith character varying(254),
    minor_lith character varying(254),
    era character varying(254),
    terrane_ag character varying(254),
    subdivisio character varying(254),
    unit_name character varying(254),
    f9 character varying(254),
    f10 character varying(254),
    geom public.geometry(MultiPolygon,4326),
    descrip_long text,
    strat_name text,
    early_id integer,
    late_id integer,
    primary_lith text,
    secondary_lith text
);


CREATE TABLE sources.mn_redwood_co_lines (
    gid integer NOT NULL,
    fnode_ numeric(10,0),
    tnode_ numeric(10,0),
    lpoly_ numeric(10,0),
    rpoly_ numeric(10,0),
    length numeric,
    bgln3_ numeric(10,0),
    bgln3_id numeric(10,0),
    id numeric(10,0),
    line_type character varying(16),
    x_coord numeric,
    y_coord numeric,
    geom public.geometry(MultiLineString,4326),
    description text
);


CREATE SEQUENCE sources.mn_redwood_co_faults_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.mn_redwood_co_faults_gid_seq OWNED BY sources.mn_redwood_co_lines.gid;


CREATE SEQUENCE sources.mn_redwood_co_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.mn_redwood_co_gid_seq OWNED BY sources.mn_redwood_co.gid;


CREATE TABLE sources.mn_washington_co (
    gid integer NOT NULL,
    area numeric,
    perimeter numeric,
    map_label character varying(254),
    descript character varying(254),
    major_lith character varying(254),
    litho_mod character varying(254),
    minor_lith character varying(254),
    age character varying(254),
    matrx_comp character varying(254),
    era character varying(254),
    maplabel character varying(16),
    geom public.geometry(MultiPolygon,4326),
    early_id integer,
    late_id integer,
    main_lith text,
    second_lith text,
    descrip_long text
);


CREATE TABLE sources.mn_washington_co_lines (
    gid integer NOT NULL,
    length numeric,
    type character varying(2),
    gcm_code character varying(3),
    geoc_src character varying(5),
    geoc_date numeric(10,0),
    descriptn character varying(90),
    geom public.geometry(MultiLineString,4326)
);


CREATE SEQUENCE sources.mn_washington_co_faults_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.mn_washington_co_faults_gid_seq OWNED BY sources.mn_washington_co_lines.gid;


CREATE SEQUENCE sources.mn_washington_co_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.mn_washington_co_gid_seq OWNED BY sources.mn_washington_co.gid;


CREATE TABLE sources.mn_winona_co (
    gid integer NOT NULL,
    id integer,
    map_label character varying(5),
    shape_leng numeric,
    shape_area numeric,
    descriptn character varying(90),
    major_lith character varying(90),
    litho_modi character varying(90),
    minor_lith character varying(90),
    age character varying(90),
    matrx_comp character varying(90),
    era character varying(50),
    geom public.geometry(MultiPolygon,4326),
    strat_name text,
    descrip_long text,
    early_id integer,
    late_id integer,
    primary_lith text,
    secondary_lith text
);


CREATE TABLE sources.mn_winona_co_lines (
    gid integer NOT NULL,
    id integer,
    name character varying(20),
    geom public.geometry(MultiLineString,4326)
);


CREATE SEQUENCE sources.mn_winona_co_fold_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.mn_winona_co_fold_gid_seq OWNED BY sources.mn_winona_co_lines.gid;


CREATE SEQUENCE sources.mn_winona_co_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.mn_winona_co_gid_seq OWNED BY sources.mn_winona_co.gid;


CREATE SEQUENCE sources.mohaveazgeology_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.mohaveazgeology_gid_seq OWNED BY sources.az_mohave.gid;


CREATE SEQUENCE sources.mohavecoconino_faults_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.mohavecoconino_faults_gid_seq OWNED BY sources.az_peachsprings_lines.gid;


CREATE SEQUENCE sources.mohavecoconinoazgeology_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.mohavecoconinoazgeology_gid_seq OWNED BY sources.az_peachsprings.gid;


CREATE SEQUENCE sources.mohavefault_lines_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.mohavefault_lines_gid_seq OWNED BY sources.az_mohave_lines.gid;


CREATE TABLE sources.mt_trumbull (
    gid integer NOT NULL,
    objectid numeric(10,0),
    ptype100k character varying(12),
    geofnt100k character varying(12),
    shape_leng numeric,
    shape_area numeric,
    objectid_1 integer,
    ptype100_1 character varying(11),
    geofnt10_1 character varying(13),
    unit100k character varying(80),
    age character varying(254),
    glg_age_no numeric,
    geom public.geometry(MultiPolygon,4326),
    descrip text,
    early_id integer,
    late_id integer,
    strat_name character varying(80)
);


CREATE SEQUENCE sources.mt_trumbull_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.mt_trumbull_gid_seq OWNED BY sources.mt_trumbull.gid;


CREATE TABLE sources.mt_trumbull_lines (
    gid integer NOT NULL,
    ltype100k character varying(35),
    flt_nm character varying(50),
    pttype character varying(35),
    shape_leng numeric,
    geom public.geometry(MultiLineString,4326),
    line_type character varying(35)
);


CREATE SEQUENCE sources.mt_trumbull_lines_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.mt_trumbull_lines_gid_seq OWNED BY sources.mt_trumbull_lines.gid;


CREATE TABLE sources.ut_nephi_lines (
    gid integer NOT NULL,
    fnode_ integer,
    tnode_ integer,
    lpoly_ integer,
    rpoly_ integer,
    length numeric,
    geology_ integer,
    geology_id integer,
    type character varying(25),
    subtype character varying(50),
    modifier character varying(25),
    notes character varying(100),
    geom public.geometry(MultiLineString,4326),
    new_type text,
    new_direction text
);


CREATE SEQUENCE sources.nephi_faults_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.nephi_faults_gid_seq OWNED BY sources.ut_nephi_lines.gid;


CREATE TABLE sources.ut_nephi (
    gid integer NOT NULL,
    area numeric,
    perimeter numeric,
    geounit_ integer,
    geounit_id integer,
    unitsymbol character varying(10),
    unitname character varying(80),
    age character varying(50),
    notes character varying(100),
    geom public.geometry(MultiPolygon,4326),
    description text,
    early_id integer,
    late_id integer
);


CREATE SEQUENCE sources.nephiutahgeology_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.nephiutahgeology_gid_seq OWNED BY sources.ut_nephi.gid;


CREATE SEQUENCE sources.nesffaults_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.nesffaults_gid_seq OWNED BY sources.ca_northeastsanfran_lines.gid;


CREATE TABLE sources.new_river_gorge (
    gid integer NOT NULL,
    objectid numeric(10,0),
    fuid numeric(10,0),
    glg_sym character varying(40),
    src_sym character varying(40),
    sort_no numeric,
    notes character varying(254),
    lbl character varying(60),
    gmap_id numeric(10,0),
    shape_leng numeric,
    shape_area numeric,
    geom public.geometry(MultiPolygon,4326),
    name text,
    age text,
    description text,
    comments text,
    early_id integer,
    late_id integer
);


CREATE TABLE sources.new_river_gorge_lines (
    gid integer NOT NULL,
    objectid numeric(10,0),
    fuid numeric(10,0),
    fsubtype integer,
    pos integer,
    glg_sym character varying(40),
    src_sym character varying(40),
    sort_no numeric,
    notes character varying(254),
    lbl character varying(60),
    sym character varying(60),
    gmap_id numeric(10,0),
    shape_leng numeric,
    geom public.geometry(MultiLineString,4326),
    new_type text,
    new_direction text
);


CREATE SEQUENCE sources.new_river_gorge_lines_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.new_river_gorge_lines_gid_seq OWNED BY sources.new_river_gorge_lines.gid;


CREATE SEQUENCE sources.newrivergorge_geo_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.newrivergorge_geo_gid_seq OWNED BY sources.new_river_gorge.gid;


CREATE TABLE sources.newzealand (
    gid integer NOT NULL,
    mapsymbol character varying(20),
    plotsymbol character varying(8),
    name character varying(150),
    descr character varying(254),
    simplename character varying(250),
    typename character varying(50),
    type_uri character varying(150),
    geolhist character varying(150),
    repage_uri character varying(150),
    yngage_uri character varying(150),
    oldage_uri character varying(150),
    stratage character varying(50),
    absmin_ma numeric,
    absmax_ma numeric,
    stratrank character varying(50),
    grpequiv character varying(100),
    sgrpequiv character varying(100),
    terrequiv character varying(100),
    lithology character varying(150),
    replith_ur character varying(150),
    obsmethod character varying(50),
    confidence character varying(150),
    posacc_m integer,
    source character varying(150),
    metadata character varying(150),
    resscale integer,
    captdate date,
    moddate date,
    plotrank integer,
    featureid character varying(150),
    spec_uri character varying(150),
    symbol character varying(12),
    shape_leng numeric,
    shape_area numeric,
    geom public.geometry(MultiPolygon,4326),
    early_id integer,
    late_id integer,
    strat_name character varying(200)
);


CREATE TABLE sources.newzealand_faults (
    gid integer NOT NULL,
    accuracy character varying(20),
    name character varying(150),
    descr character varying(254),
    exposure character varying(50),
    activity character varying(20),
    typename character varying(50),
    type_uri character varying(150),
    defrmstyle character varying(50),
    defrm_uri character varying(254),
    mvttype character varying(50),
    mvttyp_uri character varying(254),
    displcmnt character varying(50),
    totslip_km character varying(10),
    downquad character varying(10),
    dip_deg smallint,
    dipdir_deg smallint,
    geolhist character varying(254),
    repage_uri character varying(254),
    yngage_uri character varying(254),
    oldage_uri character varying(254),
    age character varying(50),
    fltsys character varying(254),
    obsmethod character varying(50),
    confidence character varying(150),
    posacc_m integer,
    source character varying(150),
    metadata character varying(150),
    resscale integer,
    captscale integer,
    captdate date,
    moddate date,
    plotrank integer,
    featureid character varying(150),
    spec_uri character varying(150),
    symbol character varying(12),
    shape_leng numeric,
    geom public.geometry(MultiLineString,4326)
);


CREATE SEQUENCE sources.newzealand_faults_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.newzealand_faults_gid_seq OWNED BY sources.newzealand_faults.gid;


CREATE SEQUENCE sources.newzealand_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.newzealand_gid_seq OWNED BY sources.newzealand.gid;


CREATE TABLE sources.newzealandq (
    gid integer NOT NULL,
    identifier character varying(30),
    code character varying(20),
    main_rock character varying(50),
    sub_rocks character varying(150),
    stratlex character varying(100),
    terr_eqiv character varying(100),
    spgrp_eqiv character varying(100),
    grp_eqiv character varying(150),
    sbgrp_eqiv character varying(100),
    fmn_eqiv character varying(254),
    mbr_eqiv character varying(100),
    protolith character varying(100),
    tzone character varying(10),
    strat_age character varying(50),
    abs_min double precision,
    abs_max double precision,
    confidence character varying(100),
    descr character varying(250),
    rock_group character varying(50),
    rock_class character varying(50),
    text_code character varying(10),
    sim_name character varying(100),
    key_name character varying(254),
    keygp_name character varying(100),
    qmap_name character varying(20),
    qmap_numb integer,
    basecolour character varying(20),
    shape_leng numeric,
    shape_area numeric,
    geom public.geometry(MultiPolygon,4326),
    early_id integer,
    late_id integer,
    old_age double precision,
    young_age double precision,
    lith text,
    age_name text,
    strat_name text,
    comments text,
    new_strat_name text
);


CREATE TABLE sources.newzealandq_dikes (
    gid integer NOT NULL,
    identifier character varying(30),
    accuracy character varying(20),
    code character varying(20),
    plot_rank integer,
    stratlex character varying(100),
    terr_eqiv character varying(100),
    spgrp_eqiv character varying(100),
    grp_eqiv character varying(150),
    sbgrp_eqiv character varying(100),
    fmn_eqiv character varying(254),
    mbr_eqiv character varying(100),
    rock_type character varying(50),
    dip_dir smallint,
    dip smallint,
    age character varying(50),
    abs_min double precision,
    abs_max double precision,
    confidence character varying(100),
    text_code character varying(10),
    sim_name character varying(100),
    key_name character varying(254),
    keygp_name character varying(100),
    qmap_name character varying(16),
    qmap_numb integer,
    shape_leng numeric,
    geom public.geometry(MultiLineString,4326),
    dip_dir_txt character varying(5),
    dip_txt character varying(5)
);


CREATE SEQUENCE sources.newzealandq_dikes_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.newzealandq_dikes_gid_seq OWNED BY sources.newzealandq_dikes.gid;


CREATE TABLE sources.newzealandq_faults (
    gid integer NOT NULL,
    identifier character varying(30),
    accuracy character varying(20),
    dom_sense character varying(20),
    sub_sense character varying(20),
    activity character varying(10),
    plot_rank integer,
    name character varying(50),
    zone character varying(50),
    type character varying(20),
    rdom_sense character varying(20),
    rsub_sense character varying(20),
    rtype character varying(20),
    dip_dir smallint,
    dip smallint,
    age character varying(50),
    total_slip character varying(10),
    down_quad character varying(10),
    qmap_name character varying(20),
    qmap_numb integer,
    shape_leng numeric,
    geom public.geometry(MultiLineString,4326)
);


CREATE SEQUENCE sources.newzealandq_faults_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.newzealandq_faults_gid_seq OWNED BY sources.newzealandq_faults.gid;


CREATE SEQUENCE sources.newzealandq_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.newzealandq_gid_seq OWNED BY sources.newzealandq.gid;


CREATE TABLE sources.nh_lisbon (
    gid integer NOT NULL,
    objectid numeric,
    shape_leng numeric,
    shape_area numeric,
    mapunit character varying(10),
    geom public.geometry(MultiPolygon,4326),
    unitname text,
    age text,
    descrip2 text,
    early_id integer,
    late_id integer,
    strat_name text
);


CREATE SEQUENCE sources.nh_lisbon_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.nh_lisbon_gid_seq OWNED BY sources.nh_lisbon.gid;


CREATE TABLE sources.nh_lisbon_lines (
    gid integer NOT NULL,
    objectid numeric,
    shape_leng numeric,
    type character varying(254),
    isconceale character varying(1),
    symbol character varying(254),
    label character varying(50),
    ruleid bigint,
    override character varying(254),
    geom public.geometry(MultiLineString,4326),
    new_type text
);


CREATE SEQUENCE sources.nh_lisbon_lines_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.nh_lisbon_lines_gid_seq OWNED BY sources.nh_lisbon_lines.gid;


CREATE TABLE sources.nh_lisbon_points (
    gid integer NOT NULL,
    objectid numeric,
    type character varying(254),
    symbol character varying(254),
    azimuth numeric,
    inclinatio numeric,
    notes character varying(254),
    ruleid bigint,
    override character varying(254),
    symbolrota numeric,
    geom public.geometry(Point,4326),
    point_type text,
    dip_dir integer,
    descrip text
);


CREATE SEQUENCE sources.nh_lisbon_points_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.nh_lisbon_points_gid_seq OWNED BY sources.nh_lisbon_points.gid;


CREATE TABLE sources.nl_baieverte (
    gid integer NOT NULL,
    label character varying(25),
    symbol smallint,
    shape_leng numeric,
    shape_area numeric,
    geom public.geometry(MultiPolygon,4326),
    map_unit text,
    max_age text,
    min_age text,
    early_id integer,
    late_id integer,
    use_age text,
    strat_name text,
    hierarchy text,
    descrip text
);


CREATE SEQUENCE sources.nl_baieverte_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.nl_baieverte_gid_seq OWNED BY sources.nl_baieverte.gid;


CREATE TABLE sources.nl_baieverte_lines (
    gid integer NOT NULL,
    code character varying(50),
    contact character varying(50),
    sens character varying(50),
    generation character varying(50),
    name character varying(50),
    qualif character varying(50),
    symbol character varying(10),
    shape_leng numeric,
    geom public.geometry(MultiLineString,4326),
    new_type text,
    descrip text
);


CREATE SEQUENCE sources.nl_baieverte_lines_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.nl_baieverte_lines_gid_seq OWNED BY sources.nl_baieverte_lines.gid;


CREATE TABLE sources.nl_baieverte_points (
    gid integer NOT NULL,
    reveal character varying(1),
    detail_rev character varying(80),
    easting numeric,
    northing numeric,
    detail character varying(80),
    stationid character varying(25),
    azimuth smallint,
    dipplunge smallint,
    source character varying(50),
    strucid character varying(25),
    notes character varying(254),
    intensity character varying(25),
    flattening character varying(25),
    type character varying(6),
    pnt_sym smallint,
    symbol character varying(20),
    geom public.geometry(Point,4326),
    point_type text,
    dip_dir integer,
    comments text
);


CREATE SEQUENCE sources.nl_baieverte_points_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.nl_baieverte_points_gid_seq OWNED BY sources.nl_baieverte_points.gid;


CREATE TABLE sources.nl_king (
    gid integer NOT NULL,
    label character varying(25),
    symbol smallint,
    shape_leng numeric,
    shape_area numeric,
    geom public.geometry(MultiPolygon,4326),
    max_age text,
    min_age text,
    early_id integer,
    late_id integer,
    use_age text,
    strat_name text,
    descrip text,
    map_unit text
);


CREATE SEQUENCE sources.nl_king_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.nl_king_gid_seq OWNED BY sources.nl_king.gid;


CREATE TABLE sources.nl_king_lines (
    gid integer NOT NULL,
    code character varying(50),
    contact character varying(50),
    sens character varying(50),
    generation character varying(50),
    name character varying(50),
    qualif character varying(50),
    symbol character varying(10),
    shape_leng numeric,
    geom public.geometry(MultiLineString,4326),
    new_type text,
    descrip text
);


CREATE SEQUENCE sources.nl_king_lines_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.nl_king_lines_gid_seq OWNED BY sources.nl_king_lines.gid;


CREATE TABLE sources.nl_king_points (
    gid integer NOT NULL,
    reveal character varying(1),
    detail_rev character varying(80),
    easting numeric,
    northing numeric,
    detail character varying(80),
    stationid character varying(25),
    azimuth smallint,
    dipplunge smallint,
    source character varying(50),
    strucid character varying(25),
    notes character varying(254),
    intensity character varying(25),
    flattening character varying(25),
    type character varying(6),
    pnt_sym smallint,
    symbol character varying(20),
    geom public.geometry(Point,4326),
    dip_dir integer,
    point_type text,
    comments text
);


CREATE SEQUENCE sources.nl_king_points_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.nl_king_points_gid_seq OWNED BY sources.nl_king_points.gid;


CREATE TABLE sources.nl_nippers (
    gid integer NOT NULL,
    label character varying(25),
    symbol smallint,
    shape_leng numeric,
    shape_area numeric,
    geom public.geometry(MultiPolygon,4326),
    max_age text,
    min_age text,
    early_id integer,
    late_id integer,
    use_age text,
    strat_name text,
    descrip text,
    map_unit text
);


CREATE SEQUENCE sources.nl_nippers_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.nl_nippers_gid_seq OWNED BY sources.nl_nippers.gid;


CREATE TABLE sources.nl_nippers_lines (
    gid integer NOT NULL,
    code character varying(50),
    contact character varying(50),
    sens character varying(50),
    generation character varying(50),
    name character varying(50),
    qualif character varying(50),
    symbol character varying(10),
    shape_leng numeric,
    geom public.geometry(MultiLineString,4326),
    new_type text,
    descrip text
);


CREATE SEQUENCE sources.nl_nippers_lines_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.nl_nippers_lines_gid_seq OWNED BY sources.nl_nippers_lines.gid;


CREATE TABLE sources.nl_nippers_points (
    gid integer NOT NULL,
    reveal character varying(1),
    detail_rev character varying(80),
    easting numeric,
    northing numeric,
    detail character varying(80),
    stationid character varying(25),
    azimuth smallint,
    dipplunge smallint,
    source character varying(50),
    strucid character varying(25),
    notes character varying(254),
    intensity character varying(25),
    flattening character varying(25),
    type character varying(6),
    pnt_sym smallint,
    symbol character varying(20),
    geom public.geometry(Point,4326),
    dip_dir integer,
    point_type text,
    comments text
);


CREATE SEQUENCE sources.nl_nippers_points_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.nl_nippers_points_gid_seq OWNED BY sources.nl_nippers_points.gid;


CREATE TABLE sources.nm_albuquerque (
    gid integer NOT NULL,
    area numeric,
    perimeter numeric,
    alb_geo_ integer,
    alb_geo_id integer,
    fname character varying(150),
    fcode character varying(25),
    symbol integer,
    geom public.geometry(MultiPolygon,4326),
    age text,
    strat_name text,
    descrip text,
    late_id integer,
    early_id integer,
    name text
);


CREATE SEQUENCE sources.nm_albuquerque_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.nm_albuquerque_gid_seq OWNED BY sources.nm_albuquerque.gid;


CREATE TABLE sources.nm_albuquerque_lines (
    gid integer NOT NULL,
    fnode_ integer,
    tnode_ integer,
    lpoly_ integer,
    rpoly_ integer,
    length numeric,
    alb_lin_ integer,
    alb_lin_id integer,
    fdescr character varying(249),
    fcode character varying(25),
    facc character varying(50),
    geom public.geometry(MultiLineString,4326),
    new_type text,
    new_direction text
);


CREATE SEQUENCE sources.nm_albuquerque_lines_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.nm_albuquerque_lines_gid_seq OWNED BY sources.nm_albuquerque_lines.gid;


CREATE TABLE sources.nm_albuquerque_points (
    gid integer NOT NULL,
    area numeric,
    perimeter numeric,
    alb_pnt_ integer,
    alb_pnt_id integer,
    fdescr character varying(249),
    azimuth smallint,
    attitude smallint,
    direction smallint,
    polygonid integer,
    scale numeric,
    angle numeric,
    geom public.geometry(Point,4326),
    point_type text,
    dip_dir integer
);


CREATE SEQUENCE sources.nm_albuquerque_points_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.nm_albuquerque_points_gid_seq OWNED BY sources.nm_albuquerque_points.gid;


CREATE TABLE sources.nm_espanola (
    gid integer NOT NULL,
    objectid numeric,
    fgdc_code character varying(16),
    geoid character varying(16),
    modified character varying(24),
    label character varying(16),
    confidence character varying(16),
    lthidbasis character varying(50),
    general_id character varying(16),
    sourceid character varying(128),
    descriptn character varying(254),
    shape_leng numeric,
    shape_area numeric,
    geom public.geometry(MultiPolygon,4326),
    name text,
    descrip text,
    age text,
    strat_name text,
    early_id integer,
    late_id integer
);


CREATE SEQUENCE sources.nm_espanola_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.nm_espanola_gid_seq OWNED BY sources.nm_espanola.gid;


CREATE TABLE sources.nm_espanola_lines (
    gid integer NOT NULL,
    objectid numeric,
    fgdc_code character varying(16),
    lineclass character varying(50),
    idmethod character varying(80),
    confidence character varying(16),
    exposure character varying(16),
    showmarker character varying(254),
    faulttype character varying(16),
    slipsense character varying(16),
    subslipsns character varying(16),
    slipbasis character varying(128),
    sliprate numeric,
    slipunits character varying(20),
    name character varying(50),
    dipseparat numeric,
    strikesep numeric,
    sepunits character varying(16),
    fltdipdir character varying(25),
    dipdirbsis character varying(128),
    ancestry character varying(128),
    lastactive character varying(128),
    dsplyscale bigint,
    sourceid character varying(128),
    comments character varying(254),
    shape_leng numeric,
    geom public.geometry(MultiLineString,4326),
    new_type text,
    new_direction text
);


CREATE SEQUENCE sources.nm_espanola_lines_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.nm_espanola_lines_gid_seq OWNED BY sources.nm_espanola_lines.gid;


CREATE TABLE sources.nm_espanola_points (
    gid integer NOT NULL,
    objectid numeric,
    fgdc_plane character varying(16),
    stationid character varying(50),
    rocktype character varying(16),
    planetype character varying(25),
    plnsubtype character varying(25),
    inclnation character varying(16),
    surface character varying(50),
    planeasymm character varying(16),
    strike bigint,
    dipdir bigint,
    dip bigint,
    younging character varying(16),
    youngcrit character varying(16),
    fgdc_line character varying(16),
    linetype character varying(25),
    lnsubtype character varying(25),
    trend bigint,
    plunge bigint,
    rake bigint,
    magnitude numeric,
    lineasymm character varying(16),
    sublnasym character varying(16),
    asymmcrit character varying(50),
    measmethod character varying(50),
    locacctype character varying(50),
    locaccmeas character varying(16),
    locaccval numeric,
    dsplyscale bigint,
    sourceid character varying(128),
    comments character varying(254),
    geom public.geometry(Point,4326),
    point_type text
);


CREATE SEQUENCE sources.nm_espanola_points_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.nm_espanola_points_gid_seq OWNED BY sources.nm_espanola_points.gid;


CREATE TABLE sources.nm_latir (
    gid integer NOT NULL,
    area numeric,
    perimeter numeric,
    latgeo_ integer,
    latgeo_id integer,
    source smallint,
    label character varying(10),
    desc_ character varying(250),
    symbol smallint,
    pattern smallint,
    geom public.geometry(MultiPolygon,4326),
    descrip text,
    age text,
    early_id integer,
    late_id integer,
    strat_name text
);


CREATE SEQUENCE sources.nm_latir_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.nm_latir_gid_seq OWNED BY sources.nm_latir.gid;


CREATE TABLE sources.nm_latir_lines (
    gid integer NOT NULL,
    fnode_ integer,
    tnode_ integer,
    lpoly_ integer,
    rpoly_ integer,
    length numeric,
    latgeo_ integer,
    latgeo_id integer,
    linecode smallint,
    name character varying(150),
    source smallint,
    symbol smallint,
    shape_leng numeric,
    geom public.geometry(MultiLineString,4326),
    new_type text,
    new_direction text
);


CREATE SEQUENCE sources.nm_latir_lines_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.nm_latir_lines_gid_seq OWNED BY sources.nm_latir_lines.gid;


CREATE TABLE sources.nm_latir_points (
    gid integer NOT NULL,
    area numeric,
    perimeter numeric,
    latpts_ integer,
    latpts_id integer,
    pttype character varying(100),
    symbol smallint,
    strike smallint,
    dip smallint,
    source smallint,
    polygonid integer,
    scale numeric,
    angle numeric,
    geom public.geometry(Point,4326),
    point_type text,
    dip_dir integer
);


CREATE SEQUENCE sources.nm_latir_points_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.nm_latir_points_gid_seq OWNED BY sources.nm_latir_points.gid;


CREATE TABLE sources.nm_petroglyps (
    gid integer NOT NULL,
    mapunit character varying(50) NOT NULL,
    name character varying(100) NOT NULL,
    fullname character varying(250) NOT NULL,
    age character varying(100),
    identityconfidence character varying(50) NOT NULL,
    label character varying(50),
    symbol character varying(50),
    datasourceid character varying(25) DEFAULT 'This Report'::character varying NOT NULL,
    notes character varying(50),
    mapunitpolys_id character varying(25) NOT NULL,
    shape_length double precision,
    shape_area double precision,
    ruleid integer,
    override bytea,
    shape public.geometry(MultiPolygon,26913),
    descrip text,
    early_id integer,
    late_id integer,
    strat_name text,
    lith text,
    geom public.geometry
);


CREATE TABLE sources.nm_petroglyps_lines (
    gid integer NOT NULL,
    type character varying(100) NOT NULL,
    isconcealed character varying(5) NOT NULL,
    locationconfidencemeters real DEFAULT '-9999'::integer NOT NULL,
    existenceconfidence character varying(50) NOT NULL,
    identityconfidence character varying(50) NOT NULL,
    label character varying(255),
    symbol character varying(25),
    datasourceid character varying(25) DEFAULT 'DAS1'::character varying NOT NULL,
    notes character varying(50),
    contactandfaults_id character varying(25) NOT NULL,
    shape_length double precision,
    ruleid integer,
    override bytea,
    shape public.geometry(MultiLineString,26913),
    new_type text,
    geom public.geometry
);


CREATE SEQUENCE sources.nm_petroglyps_lines_objectid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.nm_petroglyps_lines_objectid_seq OWNED BY sources.nm_petroglyps_lines.gid;


CREATE SEQUENCE sources.nm_petroglyps_objectid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.nm_petroglyps_objectid_seq OWNED BY sources.nm_petroglyps.gid;


CREATE TABLE sources.nm_tularosa (
    gid integer NOT NULL,
    area numeric,
    perimeter numeric,
    tulgeop_ double precision,
    tulgeop_id double precision,
    type character varying(12),
    unit character varying(8),
    colorsym smallint,
    geom public.geometry(MultiPolygon,4326),
    name text,
    age text,
    description text,
    early_id integer,
    late_id integer
);


CREATE TABLE sources.nm_tularosa_lines (
    gid integer NOT NULL,
    tulflt_ double precision,
    tulflt_id double precision,
    type character varying(16),
    faulttype character varying(10),
    accuracy character varying(11),
    dipvalue smallint,
    dipdirecti character varying(2),
    geom public.geometry(MultiLineString,4326),
    name text,
    description text,
    new_type text
);


CREATE TABLE sources.nm_vermejo (
    gid integer NOT NULL,
    area numeric,
    perimeter numeric,
    vermgeo_ integer,
    vermgeo_id integer,
    source smallint,
    label character varying(10),
    mlabel character varying(10),
    desc_ character varying(150),
    symbol smallint,
    pattern smallint,
    geom public.geometry(MultiPolygon,4326),
    age text,
    descrip text,
    strat_name text,
    early_id integer,
    late_id integer,
    use_name text
);


CREATE SEQUENCE sources.nm_vermejo_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.nm_vermejo_gid_seq OWNED BY sources.nm_vermejo.gid;


CREATE TABLE sources.nm_vermejo_lines (
    gid integer NOT NULL,
    fnode_ integer,
    tnode_ integer,
    lpoly_ integer,
    rpoly_ integer,
    length numeric,
    vermgeo_ integer,
    vermgeo_id integer,
    linecode smallint,
    name character varying(150),
    source smallint,
    symbol smallint,
    geom public.geometry(MultiLineString,4326),
    new_type text,
    new_direction text
);


CREATE SEQUENCE sources.nm_vermejo_lines_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.nm_vermejo_lines_gid_seq OWNED BY sources.nm_vermejo_lines.gid;


CREATE TABLE sources.nm_vermejo_points (
    gid integer NOT NULL,
    area numeric,
    perimeter numeric,
    vermpnt_ integer,
    vermpnt_id integer,
    pttype character varying(100),
    symbol smallint,
    strike smallint,
    dip smallint,
    source smallint,
    polygonid integer,
    scale numeric,
    angle numeric,
    geom public.geometry(Point,4326),
    point_type text,
    dip_dir integer
);


CREATE SEQUENCE sources.nm_vermejo_points_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.nm_vermejo_points_gid_seq OWNED BY sources.nm_vermejo_points.gid;


CREATE SEQUENCE sources.northbay_lines_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.northbay_lines_gid_seq OWNED BY sources.ca_marin_lines.gid;


CREATE SEQUENCE sources.northofsanfrangeology_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.northofsanfrangeology_gid_seq OWNED BY sources.ca_northofsanfran.gid;


CREATE SEQUENCE sources.northofsanfranlines_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.northofsanfranlines_gid_seq OWNED BY sources.ca_northofsanfran_lines.gid;


CREATE TABLE sources.nova_scotia (
    gid integer NOT NULL,
    dataset_id character varying(8),
    theme_id character varying(8),
    gcode character varying(32),
    gcode_desc character varying(96),
    geo_id integer,
    geo_num character varying(32),
    legend_id integer,
    unit_name character varying(96),
    unit_rank character varying(32),
    parent character varying(48),
    age_min character varying(48),
    age_max character varying(48),
    age_desc character varying(48),
    txt_label character varying(12),
    anno_label character varying(12),
    legend_lab character varying(96),
    av_legend character varying(105),
    hotlink character varying(128),
    unit_desc character varying(254),
    av_hue smallint,
    av_sat smallint,
    av_val smallint,
    am_hue smallint,
    am_sat smallint,
    am_val smallint,
    "order" integer,
    "group" character varying(48),
    formation character varying(160),
    gsco_cd integer,
    g9_cd integer,
    terrane_cd character varying(3),
    lu_cd smallint,
    hwy_cd integer,
    geom public.geometry(MultiPolygon,4326),
    strat_name text,
    hierarchy text,
    name text,
    description text,
    comments text,
    early_id integer,
    late_id integer
);


CREATE TABLE sources.nova_scotia_lines (
    gid integer NOT NULL,
    dataset_id character varying(8),
    theme_id character varying(8),
    source_id integer,
    gcode character varying(32),
    gcode_desc character varying(96),
    geo_id integer,
    geo_num character varying(32),
    name character varying(64),
    av_legend character varying(96),
    hotlink character varying(128),
    comments character varying(254),
    notes character varying(254),
    entrd_by character varying(32),
    entrd_date character varying(32),
    terrane_cd character varying(3),
    geom public.geometry(MultiLineString,4326),
    new_type text
);


CREATE SEQUENCE sources.nova_scotia_faults_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.nova_scotia_faults_gid_seq OWNED BY sources.nova_scotia_lines.gid;


CREATE SEQUENCE sources.nova_scotia_geo_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.nova_scotia_geo_gid_seq OWNED BY sources.nova_scotia.gid;


CREATE SEQUENCE sources.nsantabarbgeology_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.nsantabarbgeology_gid_seq OWNED BY sources.ca_north_santabarb.gid;


CREATE SEQUENCE sources.nsbarblines2_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.nsbarblines2_gid_seq OWNED BY sources.ca_north_santabarb_lines.gid;


CREATE TABLE sources.nsw_bathurst (
    gid integer NOT NULL,
    area numeric,
    perimeter numeric,
    geol_ double precision,
    geol_id double precision,
    map_symbol character varying(12),
    plot_symbo character varying(4),
    "group" character varying(64),
    unitname character varying(64),
    member character varying(64),
    lith_desc character varying(254),
    plotrank double precision,
    split character varying(1),
    geom public.geometry(MultiPolygon,4326),
    strat_name text,
    map_unit text,
    age text,
    early_id integer,
    late_id integer
);


CREATE SEQUENCE sources.nsw_bathurst_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.nsw_bathurst_gid_seq OWNED BY sources.nsw_bathurst.gid;


CREATE TABLE sources.nsw_bathurst_lines (
    gid integer NOT NULL,
    fnode_ double precision,
    tnode_ double precision,
    lpoly_ double precision,
    rpoly_ double precision,
    length numeric,
    geol_ double precision,
    geol_id double precision,
    agso_code double precision,
    "desc" character varying(100),
    class double precision,
    name character varying(64),
    polybdy character varying(1),
    unitbdy character varying(1),
    width double precision,
    plotrank double precision,
    split character varying(1),
    cartocode character varying(50),
    geom public.geometry(MultiLineString,4326),
    new_type text
);


CREATE SEQUENCE sources.nsw_bathurst_lines_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.nsw_bathurst_lines_gid_seq OWNED BY sources.nsw_bathurst_lines.gid;


CREATE TABLE sources.nsw_bogangate (
    gid integer NOT NULL,
    area numeric,
    perimeter numeric,
    geol_ integer,
    geol_id integer,
    feature character varying(12),
    ufi integer,
    map_symb character varying(20),
    plot_symb character varying(8),
    stratno integer,
    unitname character varying(200),
    supergroup character varying(64),
    group_ character varying(64),
    subgroup character varying(64),
    formation character varying(64),
    member character varying(64),
    era character varying(100),
    period character varying(100),
    rocktype character varying(24),
    lith_desc character varying(254),
    plotrank smallint,
    shape_leng numeric,
    shape_area numeric,
    geom public.geometry(MultiPolygon,4326),
    age text,
    early_id integer,
    late_id integer,
    strat_name text
);


CREATE SEQUENCE sources.nsw_bogangate_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.nsw_bogangate_gid_seq OWNED BY sources.nsw_bogangate.gid;


CREATE TABLE sources.nsw_bogangate_lines (
    gid integer NOT NULL,
    fnode_ integer,
    tnode_ integer,
    lpoly_ integer,
    rpoly_ integer,
    length numeric,
    strline_ integer,
    strline_id integer,
    feature character varying(12),
    ufi integer,
    agso_code integer,
    class smallint,
    type character varying(64),
    desc_ character varying(100),
    name character varying(64),
    flt_system character varying(64),
    azimuth smallint,
    defn character varying(64),
    polybdy character varying(1),
    unitbdy character varying(1),
    width integer,
    plotrank smallint,
    shape_leng numeric,
    geom public.geometry(MultiLineString,4326),
    new_type text
);


CREATE SEQUENCE sources.nsw_bogangate_lines_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.nsw_bogangate_lines_gid_seq OWNED BY sources.nsw_bogangate_lines.gid;


CREATE TABLE sources.nsw_boorowa (
    gid integer NOT NULL,
    area numeric,
    perimeter numeric,
    goul_pro_g integer,
    goul_pro_1 integer,
    map_symbol character varying(16),
    plot_symbo character varying(16),
    supersuite character varying(50),
    maingroup character varying(50),
    subgroup character varying(50),
    unitname character varying(50),
    unitname2 character varying(50),
    size smallint,
    rank integer,
    desc1 character varying(180),
    desc2 character varying(180),
    desc3 character varying(180),
    era character varying(20),
    era2 character varying(20),
    system character varying(30),
    system2 character varying(30),
    age smallint,
    dom_lith character varying(20),
    lith_class character varying(20),
    dep_env character varying(20),
    gou4_pat smallint,
    gou4 smallint,
    overprint smallint,
    pat_no smallint,
    order_ smallint,
    solid_geol character varying(9),
    pre_pal character varying(9),
    crookwell character varying(4),
    gunning character varying(4),
    boorowa character varying(4),
    taralga character varying(4),
    yass character varying(4),
    goulburn character varying(4),
    yass_basin character varying(4),
    col_ot numeric,
    simp_ot character varying(9),
    geom public.geometry(MultiPolygon,4326),
    age_ text,
    early_id integer,
    late_id integer,
    strat_name text,
    descrip text
);


CREATE SEQUENCE sources.nsw_boorowa_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.nsw_boorowa_gid_seq OWNED BY sources.nsw_boorowa.gid;


CREATE TABLE sources.nsw_boorowa_lines (
    gid integer NOT NULL,
    objectid integer,
    createdate date,
    moddate date,
    capmethod character varying(40),
    obsmethod character varying(60),
    capscale character varying(15),
    publscale character varying(15),
    dmrcode character varying(15),
    codedescpt character varying(180),
    lettsymb character varying(15),
    surface1 character varying(80),
    surface2 character varying(80),
    surface3 character varying(80),
    strucname character varying(50),
    descrptn character varying(250),
    deform character varying(15),
    mapname character varying(120),
    mapnumber character varying(25),
    src_data character varying(254),
    shape_leng numeric,
    geom public.geometry(MultiLineString,4326),
    new_type text
);


CREATE SEQUENCE sources.nsw_boorowa_lines_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.nsw_boorowa_lines_gid_seq OWNED BY sources.nsw_boorowa_lines.gid;


CREATE TABLE sources.nsw_boorowa_points (
    gid integer NOT NULL,
    objectid integer,
    createdate date,
    moddate date,
    capmethod character varying(40),
    obsmethod character varying(60),
    capscale character varying(15),
    publscale character varying(15),
    dmrcode character varying(15),
    codedescpt character varying(180),
    azimuth smallint,
    dip smallint,
    surface character varying(80),
    deform character varying(15),
    rotangle smallint,
    comments character varying(250),
    mapname character varying(120),
    mapnumber character varying(25),
    src_data character varying(254),
    geom public.geometry(Point,4326),
    point_type text,
    descrip text,
    strike integer
);


CREATE SEQUENCE sources.nsw_boorowa_points_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.nsw_boorowa_points_gid_seq OWNED BY sources.nsw_boorowa_points.gid;


CREATE TABLE sources.nsw_bunda (
    gid integer NOT NULL,
    objectid integer,
    lettsymb_m character varying(50),
    polycolor character varying(10),
    pattern character varying(10),
    p_color character varying(10),
    lettsymb character varying(30),
    surface1 character varying(80),
    surface2 character varying(80),
    nsw_code character varying(20),
    orig_fid integer,
    shape_leng numeric,
    shape_area numeric,
    geom public.geometry(MultiPolygon,4326),
    max_age text,
    early_id integer,
    late_id integer,
    strat_name text,
    mapunit text,
    descrip text,
    min_age text,
    use_age text
);


CREATE SEQUENCE sources.nsw_bunda_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.nsw_bunda_gid_seq OWNED BY sources.nsw_bunda.gid;


CREATE TABLE sources.nsw_bunda_lines (
    gid integer NOT NULL,
    objectid integer,
    createdate date,
    createdby character varying(20),
    lasteddate date,
    lasteditor character varying(20),
    capmethod character varying(40),
    obsmethod character varying(60),
    capscale character varying(15),
    publscale character varying(15),
    dmrcode character varying(15),
    codedescpt character varying(180),
    lettsymb character varying(15),
    surface1 character varying(80),
    surface2 character varying(80),
    surface3 character varying(80),
    strucname character varying(50),
    descrptn character varying(250),
    deform character varying(15),
    mapname character varying(120),
    mapnumber character varying(25),
    src_data character varying(254),
    shape_leng numeric,
    geom public.geometry(MultiLineString,4326),
    new_type text
);


CREATE SEQUENCE sources.nsw_bunda_lines_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.nsw_bunda_lines_gid_seq OWNED BY sources.nsw_bunda_lines.gid;


CREATE TABLE sources.nsw_bunda_points (
    gid integer NOT NULL,
    objectid integer,
    createdate date,
    createdby character varying(20),
    lasteddate date,
    lasteditor character varying(20),
    capmethod character varying(40),
    obsmethod character varying(60),
    capscale character varying(15),
    publscale character varying(15),
    dmrcode character varying(15),
    codedescpt character varying(180),
    azimuth smallint,
    dip smallint,
    surface character varying(80),
    deform character varying(15),
    rotangle smallint,
    comments character varying(250),
    mapname character varying(120),
    mapnumber character varying(25),
    src_data character varying(254),
    geom public.geometry(Point,4326),
    point_type text,
    strike integer
);


CREATE SEQUENCE sources.nsw_bunda_points_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.nsw_bunda_points_gid_seq OWNED BY sources.nsw_bunda_points.gid;


CREATE TABLE sources.nsw_cobar (
    gid integer NOT NULL,
    area double precision,
    perimeter double precision,
    cobarpoly1 double precision,
    cobarpoly2 double precision,
    symnum double precision,
    mapnum character varying(11),
    number character varying(11),
    polycolor double precision,
    lett_symb character varying(11),
    age character varying(38),
    formation text,
    descriptio character varying(237),
    geom public.geometry(MultiPolygon,4326),
    early_id integer,
    late_id integer,
    strat_name text
);


CREATE SEQUENCE sources.nsw_cobar_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.nsw_cobar_gid_seq OWNED BY sources.nsw_cobar.gid;


CREATE TABLE sources.nsw_cobar_lines (
    gid integer NOT NULL,
    length double precision,
    symbol smallint,
    thinunit smallint,
    descriptio character varying(100),
    geom public.geometry(MultiLineString,4326),
    new_type text
);


CREATE SEQUENCE sources.nsw_cobar_lines_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.nsw_cobar_lines_gid_seq OWNED BY sources.nsw_cobar_lines.gid;


CREATE TABLE sources.nsw_cobbora (
    gid integer NOT NULL,
    area double precision,
    perimeter double precision,
    z00kgeol_ double precision,
    z00kgeol_i double precision,
    map_symbol character varying(8),
    plot_symbo character varying(13),
    maingroup character varying(50),
    subgroup character varying(50),
    unitname character varying(50),
    unitname2 character varying(50),
    size smallint,
    rank double precision,
    desc1 character varying(100),
    desc2 character varying(100),
    desc3 character varying(100),
    era character varying(20),
    era2 character varying(20),
    system character varying(20),
    system2 character varying(20),
    age integer,
    dubcmyk1 integer,
    dubcmyk integer,
    colour integer,
    order_ integer,
    link character varying(26),
    hlpscrpt character varying(18),
    geom public.geometry(MultiPolygon,4326),
    early_id integer,
    late_id integer,
    strat_name text,
    descrip text,
    age_ text
);


CREATE SEQUENCE sources.nsw_cobbora_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.nsw_cobbora_gid_seq OWNED BY sources.nsw_cobbora.gid;


CREATE TABLE sources.nsw_cobbora_lines (
    gid integer NOT NULL,
    length double precision,
    cartoline integer,
    feat_name character varying(50),
    descriptio character varying(50),
    geom public.geometry(MultiLineString,4326),
    new_type text
);


CREATE SEQUENCE sources.nsw_cobbora_lines_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.nsw_cobbora_lines_gid_seq OWNED BY sources.nsw_cobbora_lines.gid;


CREATE TABLE sources.nsw_cobbora_points (
    gid integer NOT NULL,
    area numeric,
    perimeter numeric,
    "100kfold_" integer,
    "100kfold_i" integer,
    symbol integer,
    descriptio character varying(50),
    display smallint,
    polygonid integer,
    scale numeric,
    angle numeric,
    geom public.geometry(Point,4326),
    point_type text
);


CREATE SEQUENCE sources.nsw_cobbora_points_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.nsw_cobbora_points_gid_seq OWNED BY sources.nsw_cobbora_points.gid;


CREATE TABLE sources.nsw_cobham (
    gid integer NOT NULL,
    objectid integer,
    lettsymb_m character varying(50),
    polycolor character varying(10),
    pattern character varying(10),
    p_color character varying(10),
    p_type character varying(10),
    shape_leng numeric,
    shape_area numeric,
    lettsymb character varying(50),
    objectid_1 integer,
    id numeric,
    sorting numeric,
    age character varying(254),
    old_code character varying(254),
    stratcode character varying(254),
    groupsuite character varying(254),
    formationp character varying(254),
    memberphas character varying(254),
    display character varying(254),
    stratdes text,
    edited_str character varying(254),
    cymk character varying(254),
    pantone character varying(254),
    pattern_1 character varying(254),
    old_notes character varying(254),
    old_lithv1 character varying(254),
    old_lithv2 character varying(254),
    geom public.geometry(MultiPolygon,4326),
    early_id integer,
    late_id integer,
    strat_name text
);


CREATE SEQUENCE sources.nsw_cobham_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.nsw_cobham_gid_seq OWNED BY sources.nsw_cobham.gid;


CREATE TABLE sources.nsw_cobham_lines (
    gid integer NOT NULL,
    objectid integer,
    createdate date,
    moddate date,
    capmethod character varying(40),
    obsmethod character varying(60),
    capscale character varying(15),
    publscale character varying(15),
    dmrcode character varying(15),
    codedescpt character varying(180),
    lettsymb character varying(15),
    surface character varying(80),
    strucname character varying(50),
    descrptn character varying(250),
    deform character varying(15),
    mapname character varying(120),
    mapnumber character varying(25),
    src_data character varying(254),
    shape_leng numeric,
    geom public.geometry(MultiLineString,4326),
    new_type text
);


CREATE SEQUENCE sources.nsw_cobham_lines_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.nsw_cobham_lines_gid_seq OWNED BY sources.nsw_cobham_lines.gid;


CREATE TABLE sources.nsw_cobham_points (
    gid integer NOT NULL,
    objectid integer,
    createdate date,
    moddate date,
    capmethod character varying(40),
    obsmethod character varying(60),
    capscale character varying(15),
    publscale character varying(15),
    dmrcode character varying(15),
    codedescpt character varying(180),
    azimuth smallint,
    dip smallint,
    surface character varying(80),
    deform character varying(15),
    rotangle smallint,
    comments character varying(250),
    mapname character varying(120),
    mapnumber character varying(25),
    src_data character varying(254),
    geom public.geometry(Point,4326),
    point_type text,
    strike integer
);


CREATE SEQUENCE sources.nsw_cobham_points_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.nsw_cobham_points_gid_seq OWNED BY sources.nsw_cobham_points.gid;


CREATE TABLE sources.nsw_cool (
    gid integer NOT NULL,
    objectid bigint,
    lettsymb_m character varying(50),
    polycolor character varying(10),
    pattern character varying(10),
    p_color character varying(10),
    lettsymb character varying(30),
    surface1 character varying(80),
    surface2 character varying(80),
    nsw_code character varying(20),
    shape_leng numeric,
    shape_area numeric,
    unitname character varying(254),
    descriptio character varying(254),
    geom public.geometry(MultiPolygon,4326),
    age text,
    early_id integer,
    late_id integer,
    strat_name text
);


CREATE SEQUENCE sources.nsw_cool_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.nsw_cool_gid_seq OWNED BY sources.nsw_cool.gid;


CREATE TABLE sources.nsw_cool_lines (
    gid integer NOT NULL,
    objectid bigint,
    createdate date,
    createdby character varying(20),
    lasteddate date,
    lasteditor character varying(20),
    capmethod character varying(40),
    obsmethod character varying(60),
    capscale character varying(15),
    publscale character varying(15),
    dmrcode character varying(15),
    codedescpt character varying(180),
    lettsymb character varying(15),
    surface1 character varying(80),
    surface2 character varying(80),
    surface3 character varying(80),
    strucname character varying(50),
    descrptn character varying(250),
    deform character varying(15),
    mapname character varying(120),
    mapnumber character varying(25),
    src_data character varying(254),
    shape_leng numeric,
    geom public.geometry(MultiLineString,4326),
    new_type text,
    descrip text
);


CREATE SEQUENCE sources.nsw_cool_lines_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.nsw_cool_lines_gid_seq OWNED BY sources.nsw_cool_lines.gid;


CREATE TABLE sources.nsw_cool_points (
    gid integer NOT NULL,
    objectid bigint,
    createdate date,
    createdby character varying(20),
    lasteddate date,
    lasteditor character varying(20),
    capmethod character varying(40),
    obsmethod character varying(60),
    capscale character varying(15),
    publscale character varying(15),
    dmrcode character varying(15),
    codedescpt character varying(180),
    azimuth integer,
    dip integer,
    surface character varying(80),
    deform character varying(15),
    rotangle integer,
    comments character varying(250),
    mapname character varying(120),
    mapnumber character varying(25),
    src_data character varying(254),
    geom public.geometry(Point,4326),
    point_type text
);


CREATE SEQUENCE sources.nsw_cool_points_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.nsw_cool_points_gid_seq OWNED BY sources.nsw_cool_points.gid;


CREATE TABLE sources.nsw_gosford (
    gid integer NOT NULL,
    objectid integer,
    lettsymb character varying(30),
    nsw_code character varying(254),
    unit_nam character varying(254),
    descriptio character varying(254),
    supergrp character varying(254),
    grpsuite character varying(254),
    subgroup character varying(254),
    frmpltn character varying(254),
    member character varying(254),
    allstrat character varying(254),
    province character varying(254),
    sub_provin character varying(254),
    strat_ga numeric,
    old_lett_s character varying(254),
    dom_lith character varying(254),
    ig_type character varying(254),
    redox_stat character varying(254),
    fracn_stat character varying(254),
    frac_num character varying(254),
    age_range character varying(254),
    age_range_ character varying(254),
    top_age_na character varying(254),
    top_allage character varying(254),
    top_endage numeric,
    base_age_n character varying(254),
    base_allag character varying(254),
    base_start numeric,
    dep_env character varying(254),
    col_rgb character varying(20),
    col_hex character varying(20),
    map_scale character varying(50),
    map_name character varying(50),
    map_ref character varying(250),
    shape_leng numeric,
    shape_area numeric,
    geom public.geometry(MultiPolygon,4326),
    strat_name text,
    early_id integer,
    late_id integer
);


CREATE SEQUENCE sources.nsw_gosford_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.nsw_gosford_gid_seq OWNED BY sources.nsw_gosford.gid;


CREATE TABLE sources.nsw_gosford_lines (
    gid integer NOT NULL,
    objectid integer,
    createdate date,
    moddate date,
    capmethod character varying(40),
    obsmethod character varying(60),
    capscale character varying(15),
    publscale character varying(15),
    dmrcode character varying(15),
    codedescpt character varying(180),
    lettsymb character varying(15),
    surface1 character varying(80),
    surface2 character varying(80),
    surface3 character varying(80),
    strucname character varying(50),
    descrptn character varying(250),
    deform character varying(15),
    mapname character varying(120),
    mapnumber character varying(25),
    src_data character varying(254),
    shape_leng numeric,
    geom public.geometry(MultiLineString,4326),
    new_type text,
    descrip text
);


CREATE SEQUENCE sources.nsw_gosford_lines_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.nsw_gosford_lines_gid_seq OWNED BY sources.nsw_gosford_lines.gid;


CREATE TABLE sources.nsw_gosford_points (
    gid integer NOT NULL,
    objectid integer,
    createdate date,
    moddate date,
    capmethod character varying(40),
    obsmethod character varying(60),
    capscale character varying(15),
    publscale character varying(15),
    dmrcode character varying(15),
    codedescpt character varying(180),
    azimuth smallint,
    dip smallint,
    surface character varying(80),
    deform character varying(15),
    rotangle smallint,
    comments character varying(250),
    mapname character varying(120),
    mapnumber character varying(25),
    src_data character varying(254),
    geom public.geometry(Point,4326),
    point_type text,
    strike integer
);


CREATE SEQUENCE sources.nsw_gosford_points_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.nsw_gosford_points_gid_seq OWNED BY sources.nsw_gosford_points.gid;


CREATE TABLE sources.nsw_goul (
    gid integer NOT NULL,
    area numeric,
    perimeter numeric,
    gou_pro_25 integer,
    gou_pro_26 integer,
    map_symbol character varying(16),
    plot_symbo character varying(16),
    supersuite character varying(50),
    maingroup character varying(50),
    subgroup character varying(50),
    unitname character varying(50),
    unitname2 character varying(50),
    size smallint,
    rank integer,
    desc1 character varying(180),
    desc2 character varying(180),
    desc3 character varying(180),
    era character varying(30),
    era2 character varying(30),
    system character varying(30),
    system2 character varying(30),
    age smallint,
    dom_lith character varying(20),
    lith_class character varying(20),
    dep_env character varying(20),
    gou4_pat smallint,
    gou4 smallint,
    overprint smallint,
    pat_no smallint,
    order_ smallint,
    solid_geol character varying(9),
    pre_pal character varying(9),
    crookwell character varying(4),
    gunning character varying(4),
    boorowa character varying(4),
    taralga character varying(4),
    yass character varying(4),
    goulburn character varying(4),
    yass_basin character varying(4),
    col_ot numeric,
    simp_ot character varying(9),
    n35 character varying(9),
    desc_check character varying(18),
    desc_chk character varying(2),
    d_mh character varying(2),
    polygonid integer,
    scale numeric,
    angle numeric,
    orig_fid integer,
    shape_leng numeric,
    shape_area numeric,
    geom public.geometry(MultiPolygon,4326),
    early_id integer,
    late_id integer,
    strat_name text,
    max_age text,
    min_age text,
    map_unit text,
    descrip text
);


CREATE SEQUENCE sources.nsw_goul_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.nsw_goul_gid_seq OWNED BY sources.nsw_goul.gid;


CREATE TABLE sources.nsw_goul_lines (
    gid integer NOT NULL,
    objectid integer,
    createdate date,
    moddate date,
    capmethod character varying(40),
    obsmethod character varying(60),
    capscale character varying(15),
    publscale character varying(15),
    dmrcode character varying(15),
    codedescpt character varying(180),
    lettsymb character varying(15),
    surface character varying(80),
    strucname character varying(50),
    descrptn character varying(250),
    deform character varying(15),
    mapname character varying(120),
    mapnumber character varying(25),
    src_data character varying(254),
    shape_leng numeric,
    geom public.geometry(MultiLineString,4326),
    new_type text,
    descrip text
);


CREATE SEQUENCE sources.nsw_goul_lines_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.nsw_goul_lines_gid_seq OWNED BY sources.nsw_goul_lines.gid;


CREATE TABLE sources.nsw_goul_points (
    gid integer NOT NULL,
    objectid integer,
    createdate date,
    moddate date,
    capmethod character varying(40),
    obsmethod character varying(60),
    capscale character varying(15),
    publscale character varying(15),
    dmrcode character varying(15),
    codedescpt character varying(180),
    azimuth smallint,
    dip smallint,
    surface character varying(80),
    deform character varying(15),
    rotangle smallint,
    comments character varying(250),
    mapname character varying(120),
    mapnumber character varying(25),
    src_data character varying(254),
    geom public.geometry(Point,4326),
    point_type text,
    dip_dir integer
);


CREATE SEQUENCE sources.nsw_goul_points_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.nsw_goul_points_gid_seq OWNED BY sources.nsw_goul_points.gid;


CREATE TABLE sources.nsw_sussex (
    gid integer NOT NULL,
    lettsymb character varying(50),
    nsw_code character varying(254),
    strat_ga double precision,
    descriptio text,
    supergrp character varying(254),
    grpsuite character varying(254),
    frmpluton character varying(254),
    member character varying(254),
    era character varying(254),
    period character varying(254),
    max_age character varying(254),
    min_age character varying(254),
    mapname character varying(254),
    mapscale character varying(254),
    mapnumber character varying(254),
    src_data character varying(254),
    geom public.geometry(MultiPolygon,4326),
    use_age text,
    early_id integer,
    late_id integer,
    unit_name text,
    strat_name text
);


CREATE SEQUENCE sources.nsw_sussex_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.nsw_sussex_gid_seq OWNED BY sources.nsw_sussex.gid;


CREATE TABLE sources.nsw_sussex_lines (
    gid integer NOT NULL,
    objectid integer,
    createdate date,
    moddate date,
    capmethod character varying(40),
    obsmethod character varying(60),
    capscale character varying(15),
    publscale character varying(15),
    dmrcode character varying(15),
    codedescpt character varying(180),
    lettsymb character varying(15),
    surface1 character varying(80),
    surface2 character varying(80),
    surface3 character varying(80),
    strucname character varying(50),
    descrptn character varying(250),
    deform character varying(15),
    mapname character varying(120),
    mapnumber character varying(25),
    src_data character varying(254),
    shape_leng numeric,
    geom public.geometry(MultiLineString,4326),
    new_type text
);


CREATE SEQUENCE sources.nsw_sussex_lines_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.nsw_sussex_lines_gid_seq OWNED BY sources.nsw_sussex_lines.gid;


CREATE TABLE sources.nsw_sussex_points (
    gid integer NOT NULL,
    objectid integer,
    createdate date,
    moddate date,
    capmethod character varying(40),
    obsmethod character varying(60),
    capscale character varying(15),
    publscale character varying(15),
    dmrcode character varying(15),
    codedescpt character varying(180),
    dip_dir smallint,
    dip smallint,
    surface character varying(80),
    deform character varying(15),
    rotangle smallint,
    comments character varying(250),
    mapname character varying(120),
    mapnumber character varying(25),
    src_data character varying(254),
    geom public.geometry(Point,4326),
    point_type text,
    strike integer
);


CREATE SEQUENCE sources.nsw_sussex_points_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.nsw_sussex_points_gid_seq OWNED BY sources.nsw_sussex_points.gid;


CREATE TABLE sources.nsw_wonnaminta (
    gid integer NOT NULL,
    objectid integer,
    lettsymb_m character varying(50),
    polycolor character varying(10),
    pattern character varying(10),
    p_color character varying(10),
    lettsymb character varying(30),
    surface1 character varying(80),
    surface2 character varying(80),
    nsw_code character varying(20),
    orig_fid integer,
    shape_leng numeric,
    shape_area numeric,
    unitname character varying(254),
    descriptio character varying(254),
    geom public.geometry(MultiPolygon,4326),
    age text,
    early_id integer,
    late_id integer,
    strat_name text
);


CREATE SEQUENCE sources.nsw_wonnaminta_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.nsw_wonnaminta_gid_seq OWNED BY sources.nsw_wonnaminta.gid;


CREATE TABLE sources.nsw_wonnaminta_lines (
    gid integer NOT NULL,
    objectid integer,
    createdate date,
    createdby character varying(20),
    lasteddate date,
    lasteditor character varying(20),
    capmethod character varying(40),
    obsmethod character varying(60),
    capscale character varying(15),
    publscale character varying(15),
    dmrcode character varying(15),
    codedescpt character varying(180),
    lettsymb character varying(15),
    surface1 character varying(80),
    surface2 character varying(80),
    surface3 character varying(80),
    strucname character varying(50),
    descrptn character varying(250),
    mapname character varying(120),
    mapnumber character varying(25),
    src_data character varying(254),
    shape_leng numeric,
    geom public.geometry(MultiLineString,4326),
    new_type text,
    descrip text
);


CREATE SEQUENCE sources.nsw_wonnaminta_lines_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.nsw_wonnaminta_lines_gid_seq OWNED BY sources.nsw_wonnaminta_lines.gid;


CREATE TABLE sources.nsw_wonnaminta_points (
    gid integer NOT NULL,
    objectid integer,
    createdate date,
    createdby character varying(20),
    lasteddate date,
    lasteditor character varying(20),
    capmethod character varying(40),
    obsmethod character varying(60),
    capscale character varying(15),
    publscale character varying(15),
    dmrcode character varying(15),
    codedescpt character varying(180),
    azimuth smallint,
    dip smallint,
    surface character varying(80),
    deform character varying(15),
    rotangle smallint,
    comments character varying(250),
    mapname character varying(120),
    mapnumber character varying(25),
    src_data character varying(254),
    geom public.geometry(Point,4326),
    point_type text,
    strike integer
);


CREATE SEQUENCE sources.nsw_wonnaminta_points_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.nsw_wonnaminta_points_gid_seq OWNED BY sources.nsw_wonnaminta_points.gid;


CREATE TABLE sources.nu_chidliak_n (
    gid integer NOT NULL,
    labelid character varying(10),
    sourceid character varying(15),
    remarks character varying(254),
    creatorid character varying(25),
    createdate date,
    editorid character varying(25),
    editdate date,
    shape_leng numeric,
    shape_area numeric,
    d_labelid character varying(254),
    d_sourceid character varying(254),
    geom public.geometry(MultiPolygon,4326),
    age text,
    early_id integer,
    late_id integer,
    map_unit text,
    strat_name text,
    descrip text
);


CREATE SEQUENCE sources.nu_chidliak_n_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.nu_chidliak_n_gid_seq OWNED BY sources.nu_chidliak_n.gid;


CREATE TABLE sources.nu_chidliak_s (
    gid integer NOT NULL,
    labelid character varying(10),
    sourceid character varying(15),
    remarks character varying(254),
    creatorid character varying(25),
    createdate date,
    editorid character varying(25),
    editdate date,
    shape_leng numeric,
    shape_area numeric,
    d_labelid character varying(254),
    d_sourceid character varying(254),
    geom public.geometry(MultiPolygon,4326),
    age text,
    early_id integer,
    late_id integer,
    map_unit text,
    strat_name text,
    descrip text
);


CREATE SEQUENCE sources.nu_chidliak_s_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.nu_chidliak_s_gid_seq OWNED BY sources.nu_chidliak_s.gid;


CREATE TABLE sources.nu_chidliak_s_lines (
    gid integer NOT NULL,
    geolinetyp integer,
    qualifier character varying(4),
    confidence character varying(2),
    attitude character varying(2),
    generation character varying(2),
    name character varying(254),
    remarks character varying(254),
    movement character varying(2),
    hwalldir character varying(2),
    foldtrend character varying(2),
    foldplunge character varying(25),
    arrowdir character varying(2),
    minage character varying(50),
    maxage character varying(50),
    creatorid character varying(25),
    editorid character varying(25),
    feat integer,
    createdate date,
    editdate date,
    fgdc_symbo character varying(12),
    geolineid character varying(12),
    sourceid character varying(15),
    isboundary character varying(2),
    shape_leng numeric,
    d_geolinet character varying(254),
    d_qualifie character varying(254),
    d_confiden character varying(254),
    d_attitude character varying(254),
    d_generati character varying(254),
    d_movement character varying(254),
    d_hwalldir character varying(254),
    d_foldtren character varying(254),
    d_arrowdir character varying(254),
    d_creatori character varying(254),
    d_editorid character varying(254),
    d_sourceid character varying(254),
    d_isbounda character varying(254),
    geom public.geometry(MultiLineString,4326),
    new_type text,
    descrip text
);


CREATE SEQUENCE sources.nu_chidliak_s_lines_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.nu_chidliak_s_lines_gid_seq OWNED BY sources.nu_chidliak_s_lines.gid;


CREATE TABLE sources.nu_circle (
    gid integer NOT NULL,
    area double precision,
    perimeter double precision,
    geo_cgm000 integer,
    geo_cgm0_1 integer,
    poly_ integer,
    subclass character varying(13),
    subclass_ integer,
    rings_ok integer,
    rings_nok integer,
    code character varying(16),
    geo_sym character varying(50),
    geo_misc character varying(16),
    geo_surf character varying(16),
    geo_link numeric,
    geo_pat character varying(16),
    descriptio character varying(254),
    shape_leng numeric,
    gsc_bedroc character varying(11),
    shape_le_1 numeric,
    shape_area numeric,
    geom public.geometry(MultiPolygon,4326),
    max_age text,
    min_age text,
    early_id integer,
    late_id integer,
    use_age text,
    map_unit text,
    strat_name text,
    descrip text
);


CREATE SEQUENCE sources.nu_circle_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.nu_circle_gid_seq OWNED BY sources.nu_circle.gid;


CREATE TABLE sources.nu_circle_lines (
    gid integer NOT NULL,
    symbol character varying(15),
    notes character varying(254),
    linetype character varying(25),
    code character varying(50),
    geo_sym character varying(30),
    confidence character varying(15),
    shape_leng numeric,
    geom public.geometry(MultiLineString,4326),
    new_type text,
    descrip text
);


CREATE SEQUENCE sources.nu_circle_lines_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.nu_circle_lines_gid_seq OWNED BY sources.nu_circle_lines.gid;


CREATE TABLE sources.nu_circle_points (
    gid integer NOT NULL,
    objectid integer,
    id integer,
    stationid character varying(25),
    earthmatid character varying(25),
    strucid character varying(25),
    strucno smallint,
    class character varying(25),
    struc_type character varying(50),
    detail character varying(80),
    method character varying(50),
    azimuth smallint,
    dipplunge smallint,
    symang smallint,
    icefeature character varying(100),
    relage smallint,
    numindic character varying(50),
    relation character varying(50),
    definition character varying(50),
    notes character varying(254),
    symbol smallint,
    intensity character varying(25),
    flattening character varying(25),
    geom public.geometry(Point,4326),
    point_type text,
    comments text,
    dip_dir integer
);


CREATE SEQUENCE sources.nu_circle_points_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.nu_circle_points_gid_seq OWNED BY sources.nu_circle_points.gid;


CREATE TABLE sources.nu_ellef_s (
    gid integer NOT NULL,
    map_theme character varying(50),
    feature character varying(50),
    map_unit character varying(100),
    parents character varying(254),
    max_age character varying(50),
    min_age character varying(50),
    lith_list character varying(100),
    descriptio character varying(254),
    genesis character varying(100),
    remarks character varying(254),
    label character varying(30),
    reference character varying(254),
    source_ref character varying(254),
    map_id character varying(254),
    pub_scale numeric,
    include_hc character varying(5),
    symbol character varying(100),
    shape_leng numeric,
    shape_area numeric,
    geom public.geometry(MultiPolygon,4326),
    name text,
    strat_name text,
    early_id integer,
    late_id integer,
    new_descrip text,
    use_age text
);


CREATE SEQUENCE sources.nu_ellef_s_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.nu_ellef_s_gid_seq OWNED BY sources.nu_ellef_s.gid;


CREATE TABLE sources.nu_ellef_s_lines (
    gid integer NOT NULL,
    map_theme character varying(50),
    feature character varying(50),
    subfeature character varying(50),
    attitude character varying(50),
    confidence character varying(15),
    generation character varying(25),
    max_age character varying(50),
    min_age character varying(50),
    foldtrend character varying(20),
    foldplunge character varying(20),
    name character varying(254),
    properties character varying(254),
    remarks character varying(254),
    reference character varying(254),
    source_ref character varying(254),
    map_id character varying(254),
    pub_scale numeric,
    include_hc character varying(5),
    arrow_dir character varying(20),
    symbol character varying(100),
    shape_leng numeric,
    geom public.geometry(MultiLineString,4326),
    new_type text,
    descrip text
);


CREATE SEQUENCE sources.nu_ellef_s_lines_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.nu_ellef_s_lines_gid_seq OWNED BY sources.nu_ellef_s_lines.gid;


CREATE TABLE sources.nu_ellef_s_points (
    gid integer NOT NULL,
    map_theme character varying(50),
    feature character varying(50),
    planar_id character varying(50),
    subfeature character varying(50),
    fab_elem character varying(254),
    attitude character varying(50),
    young_evid character varying(50),
    generation character varying(50),
    method character varying(50),
    dip_dir integer,
    strike integer,
    dip integer,
    strain character varying(50),
    flattening character varying(50),
    lith_id character varying(50),
    station_id character varying(50),
    related_id character varying(100),
    linear_id character varying(100),
    planar_id2 character varying(100),
    remarks character varying(254),
    reference character varying(254),
    source_ref character varying(254),
    map_id character varying(254),
    release character varying(30),
    authority character varying(100),
    include_hc character varying(5),
    symbol character varying(100),
    geom public.geometry(Point,4326),
    trend integer,
    plunge text,
    point_type text,
    comments text
);


CREATE SEQUENCE sources.nu_ellef_s_points_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.nu_ellef_s_points_gid_seq OWNED BY sources.nu_ellef_s_points.gid;


CREATE TABLE sources.nu_grinnell (
    gid integer NOT NULL,
    remarks character varying(254),
    fgdc_symbo character varying(15),
    shape_leng numeric,
    shape_area numeric,
    sourceid character varying(150),
    geo_descri character varying(254),
    labelid character varying(254),
    geom public.geometry(MultiPolygonZM,4326),
    name text,
    strat_name text,
    age text,
    early_id integer,
    late_id integer
);


CREATE SEQUENCE sources.nu_grinnell_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.nu_grinnell_gid_seq OWNED BY sources.nu_grinnell.gid;


CREATE TABLE sources.nu_grinnell_lines (
    gid integer NOT NULL,
    name character varying(254),
    remarks character varying(254),
    foldplunge character varying(25),
    minage character varying(50),
    maxage character varying(50),
    feat integer,
    fgdc_symbo character varying(12),
    geolineid character varying(12),
    sourceid character varying(150),
    shape_leng numeric,
    geolinetyp character varying(254),
    qualifier character varying(254),
    confidence character varying(254),
    attitude character varying(254),
    generation character varying(254),
    movement character varying(254),
    hwalldir character varying(254),
    foldtrend character varying(254),
    arrowdir character varying(254),
    isboundary character varying(254),
    geom public.geometry(MultiLineStringZM,4326),
    new_type text,
    descrip text
);


CREATE SEQUENCE sources.nu_grinnell_lines_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.nu_grinnell_lines_gid_seq OWNED BY sources.nu_grinnell_lines.gid;


CREATE TABLE sources.nu_grinnell_points (
    gid integer NOT NULL,
    azimuth smallint,
    dipplunge smallint,
    fgdc_symbo character varying(15),
    dipdesc character varying(30),
    geopointid character varying(13),
    stationid character varying(25),
    prime_stru character varying(3),
    sourceid character varying(150),
    geopointty character varying(254),
    geopointsu character varying(254),
    strucattit character varying(254),
    strucgener character varying(254),
    strucyoung character varying(254),
    strucmetho character varying(254),
    display_fr character varying(254),
    display_to character varying(254),
    sense_evid character varying(254),
    ruleid character varying(254),
    geom public.geometry(PointZM,4326),
    point_type text,
    comments text,
    dip_dir integer
);


CREATE SEQUENCE sources.nu_grinnell_points_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.nu_grinnell_points_gid_seq OWNED BY sources.nu_grinnell_points.gid;


CREATE TABLE sources.nu_irvine_s (
    gid integer NOT NULL,
    labelid character varying(10),
    sourceid character varying(15),
    shape_leng numeric,
    shape_area numeric,
    d_labelid character varying(254),
    d_sourceid character varying(254),
    gsc_symbol character varying(15),
    descrip character varying(254),
    geom public.geometry(MultiPolygon,4326),
    max_age text,
    min_age text,
    early_id integer,
    late_id integer,
    use_age text,
    strat_name text,
    hierarchy text,
    map_unit text
);


CREATE SEQUENCE sources.nu_irvine_s_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.nu_irvine_s_gid_seq OWNED BY sources.nu_irvine_s.gid;


CREATE TABLE sources.nu_irvine_s_lines (
    gid integer NOT NULL,
    geolineid character varying(12),
    geolinetyp integer,
    qualifier character varying(4),
    confidence character varying(2),
    attitude character varying(2),
    generation character varying(2),
    name character varying(254),
    movement character varying(2),
    hwalldir character varying(2),
    foldtrend character varying(2),
    foldplunge character varying(25),
    arrowdir character varying(2),
    minage character varying(50),
    maxage character varying(50),
    gsc_symbol character varying(12),
    sourceid character varying(15),
    isboundary character varying(2),
    origcode character varying(50),
    displaypub smallint,
    shape_leng numeric,
    d_geolinet character varying(254),
    d_qualifie character varying(254),
    d_confiden character varying(254),
    d_attitude character varying(254),
    d_generati character varying(254),
    d_movement character varying(254),
    d_hwalldir character varying(254),
    d_foldtren character varying(254),
    d_arrowdir character varying(254),
    d_sourceid character varying(254),
    d_isbounda character varying(254),
    d_displayp character varying(254),
    geom public.geometry(MultiLineStringZM,4326),
    new_type text,
    descrip text
);


CREATE SEQUENCE sources.nu_irvine_s_lines_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.nu_irvine_s_lines_gid_seq OWNED BY sources.nu_irvine_s_lines.gid;


CREATE TABLE sources.nu_irvine_s_points (
    gid integer NOT NULL,
    objectid integer,
    geopointid character varying(13),
    geopointty integer,
    geopointsu character varying(4),
    strucattit character varying(2),
    strucgener character varying(2),
    strucyoung character varying(2),
    strucmetho character varying(2),
    relatedstr character varying(15),
    azimuth smallint,
    dipplunge smallint,
    dipdesc character varying(30),
    sense_evid character varying(50),
    strain character varying(2),
    flattening character varying(2),
    gsc_symbol character varying(15),
    f_strucid character varying(25),
    sourceid character varying(15),
    origcode character varying(50),
    display_fr character varying(20),
    display_to character varying(20),
    displaypub smallint,
    editremark character varying(254),
    geom public.geometry(PointZM,4326),
    feature text,
    point_type text,
    dip_dir integer,
    subfeature text
);


CREATE SEQUENCE sources.nu_irvine_s_points_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.nu_irvine_s_points_gid_seq OWNED BY sources.nu_irvine_s_points.gid;


CREATE TABLE sources.nu_mumiksaa (
    gid integer NOT NULL,
    labelid character varying(10),
    sourceid character varying(15),
    shape_leng numeric,
    shape_area numeric,
    d_labelid character varying(254),
    d_sourceid character varying(254),
    geom public.geometry(MultiPolygon,4326),
    max_age text,
    min_age text,
    early_id integer,
    late_id integer,
    use_age text,
    map_unit text,
    strat_name text,
    descrip text
);


CREATE SEQUENCE sources.nu_mumiksaa_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.nu_mumiksaa_gid_seq OWNED BY sources.nu_mumiksaa.gid;


CREATE TABLE sources.nu_mumiksaa_lines (
    gid integer NOT NULL,
    geolineid character varying(12),
    geolinetyp integer,
    qualifier character varying(4),
    confidence character varying(2),
    attitude character varying(2),
    generation character varying(2),
    name character varying(254),
    movement character varying(2),
    hwalldir character varying(2),
    foldtrend character varying(2),
    foldplunge character varying(25),
    arrowdir character varying(2),
    isboundary character varying(2),
    gsc_symbol character varying(12),
    sourceid character varying(15),
    geoevent_i integer,
    origcode character varying(50),
    displaypub smallint,
    label character varying(50),
    shape_leng numeric,
    d_geolinet character varying(254),
    d_qualifie character varying(254),
    d_confiden character varying(254),
    d_attitude character varying(254),
    d_generati character varying(254),
    d_movement character varying(254),
    d_hwalldir character varying(254),
    d_foldtren character varying(254),
    d_arrowdir character varying(254),
    d_isbounda character varying(254),
    d_sourceid character varying(254),
    d_displayp character varying(254),
    geom public.geometry(MultiLineStringZM,4326),
    new_type text,
    descrip text
);


CREATE SEQUENCE sources.nu_mumiksaa_lines_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.nu_mumiksaa_lines_gid_seq OWNED BY sources.nu_mumiksaa_lines.gid;


CREATE TABLE sources.nu_mumiksaa_points (
    gid integer NOT NULL,
    geopointid character varying(13),
    geopointty integer,
    geopointsu character varying(4),
    strucattit character varying(2),
    strucgener character varying(2),
    strucyoung character varying(2),
    strucmetho character varying(2),
    relatedstr character varying(15),
    azimuth smallint,
    dipplunge smallint,
    dipdesc character varying(30),
    sense_evid character varying(50),
    strain character varying(2),
    flattening character varying(2),
    f_strucid character varying(25),
    gsc_symbol character varying(15),
    sourceid character varying(15),
    origcode character varying(50),
    display_fr character varying(20),
    display_to character varying(20),
    displaypub smallint,
    d_geopoint character varying(254),
    d_geopoi_1 character varying(254),
    d_strucatt character varying(254),
    d_strucgen character varying(254),
    d_strucyou character varying(254),
    d_strucmet character varying(254),
    d_dipdesc character varying(254),
    d_sense_ev character varying(254),
    d_strain character varying(254),
    d_flatteni character varying(254),
    d_sourceid character varying(254),
    d_display_ character varying(254),
    d_display1 character varying(254),
    d_displayp character varying(254),
    geom public.geometry(PointZM,4326),
    dip_dir integer,
    point_type text,
    comments text
);


CREATE SEQUENCE sources.nu_mumiksaa_points_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.nu_mumiksaa_points_gid_seq OWNED BY sources.nu_mumiksaa_points.gid;


CREATE TABLE sources.nu_paquet (
    gid integer NOT NULL,
    labelid character varying(10),
    sourceid character varying(15),
    shape_leng numeric,
    shape_area numeric,
    d_labelid character varying(254),
    d_sourceid character varying(254),
    geom public.geometry(MultiPolygon,4326),
    max_age text,
    min_age text,
    early_id integer,
    late_id integer,
    use_age text,
    strat_name text,
    hierarchy text,
    descrip text,
    map_unit text
);


CREATE SEQUENCE sources.nu_paquet_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.nu_paquet_gid_seq OWNED BY sources.nu_paquet.gid;


CREATE TABLE sources.nu_paquet_lines (
    gid integer NOT NULL,
    geolineid character varying(12),
    geolinetyp integer,
    qualifier character varying(4),
    confidence character varying(2),
    attitude character varying(2),
    generation character varying(2),
    name character varying(254),
    movement character varying(2),
    hwalldir character varying(2),
    foldtrend character varying(2),
    foldplunge character varying(25),
    arrowdir character varying(2),
    isboundary character varying(2),
    gsc_symbol character varying(12),
    sourceid character varying(15),
    geoevent_i integer,
    origcode character varying(50),
    displaypub smallint,
    label character varying(50),
    shape_leng numeric,
    d_geolinet character varying(254),
    d_qualifie character varying(254),
    d_confiden character varying(254),
    d_attitude character varying(254),
    d_generati character varying(254),
    d_movement character varying(254),
    d_hwalldir character varying(254),
    d_foldtren character varying(254),
    d_arrowdir character varying(254),
    d_isbounda character varying(254),
    d_sourceid character varying(254),
    d_displayp character varying(254),
    geom public.geometry(MultiLineStringZM,4326),
    new_type text,
    descrip text
);


CREATE SEQUENCE sources.nu_paquet_lines_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.nu_paquet_lines_gid_seq OWNED BY sources.nu_paquet_lines.gid;


CREATE TABLE sources.nu_paquet_points (
    gid integer NOT NULL,
    geopointid character varying(13),
    geopointty integer,
    geopointsu character varying(4),
    strucattit character varying(2),
    strucgener character varying(2),
    strucyoung character varying(2),
    strucmetho character varying(2),
    relatedstr character varying(15),
    azimuth smallint,
    dipplunge smallint,
    dipdesc character varying(30),
    sense_evid character varying(50),
    strain character varying(2),
    flattening character varying(2),
    f_strucid character varying(25),
    gsc_symbol character varying(15),
    sourceid character varying(15),
    origcode character varying(50),
    display_fr character varying(20),
    display_to character varying(20),
    displaypub smallint,
    d_geopoint character varying(254),
    d_geopoi_1 character varying(254),
    d_strucatt character varying(254),
    d_strucgen character varying(254),
    d_strucyou character varying(254),
    d_strucmet character varying(254),
    d_dipdesc character varying(254),
    d_sense_ev character varying(254),
    d_strain character varying(254),
    d_flatteni character varying(254),
    d_sourceid character varying(254),
    d_display_ character varying(254),
    d_display1 character varying(254),
    d_displayp character varying(254),
    geom public.geometry(PointZM,4326),
    point_type text,
    dip_dir integer
);


CREATE SEQUENCE sources.nu_paquet_points_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.nu_paquet_points_gid_seq OWNED BY sources.nu_paquet_points.gid;


CREATE TABLE sources.nu_pritzler (
    gid integer NOT NULL,
    remarks character varying(254),
    fgdc_symbo character varying(15),
    shape_leng numeric,
    shape_area numeric,
    sourceid character varying(150),
    descrip character varying(254),
    labelid character varying(254),
    geom public.geometry(MultiPolygonZM,4326),
    age text,
    early_id integer,
    late_id integer,
    map_unit text,
    strat_name text
);


CREATE SEQUENCE sources.nu_pritzler_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.nu_pritzler_gid_seq OWNED BY sources.nu_pritzler.gid;


CREATE TABLE sources.nu_pritzler_lines (
    gid integer NOT NULL,
    name character varying(254),
    remarks character varying(254),
    foldplunge character varying(25),
    minage character varying(50),
    maxage character varying(50),
    feat integer,
    fgdc_symbo character varying(12),
    geolineid character varying(12),
    sourceid character varying(150),
    shape_leng numeric,
    geolinetyp character varying(254),
    qualifier character varying(254),
    confidence character varying(254),
    attitude character varying(254),
    generation character varying(254),
    movement character varying(254),
    hwalldir character varying(254),
    foldtrend character varying(254),
    arrowdir character varying(254),
    isboundary character varying(254),
    geom public.geometry(MultiLineStringZM,4326),
    new_type text,
    descrip text
);


CREATE SEQUENCE sources.nu_pritzler_lines_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.nu_pritzler_lines_gid_seq OWNED BY sources.nu_pritzler_lines.gid;


CREATE TABLE sources.nu_pritzler_points (
    gid integer NOT NULL,
    azimuth smallint,
    dipplunge smallint,
    fgdc_symbo character varying(15),
    dipdesc character varying(30),
    geopointid character varying(13),
    stationid character varying(25),
    prime_stru character varying(3),
    sourceid character varying(150),
    geopointty character varying(254),
    geopointsu character varying(254),
    strucattit character varying(254),
    strucgener character varying(254),
    strucyoung character varying(254),
    strucmetho character varying(254),
    display_fr character varying(254),
    display_to character varying(254),
    sense_evid character varying(254),
    ruleid character varying(254),
    geom public.geometry(PointZM,4326),
    dip_dir integer,
    point_type text,
    comments text
);


CREATE SEQUENCE sources.nu_pritzler_points_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.nu_pritzler_points_gid_seq OWNED BY sources.nu_pritzler_points.gid;


CREATE TABLE sources.nu_rae (
    gid integer NOT NULL,
    geo_sym smallint,
    code character varying(16),
    map_source character varying(100),
    reference character varying(254),
    symbol character varying(100),
    age character varying(50),
    group_ character varying(50),
    subgroup character varying(50),
    type character varying(50),
    shape_leng numeric,
    shape_area numeric,
    geom public.geometry(MultiPolygon,4326),
    use_age text,
    early_id integer,
    late_id integer,
    strat_name text,
    descrip text,
    hierarchy text,
    max_age text,
    min_age text,
    use_name text
);


CREATE SEQUENCE sources.nu_rae_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.nu_rae_gid_seq OWNED BY sources.nu_rae.gid;


CREATE TABLE sources.nu_rae_lines (
    gid integer NOT NULL,
    lin_type character varying(3),
    lin_sym smallint,
    lin_misc character varying(25),
    code character varying(16),
    map_source character varying(40),
    shape_leng numeric,
    geom public.geometry(MultiLineString,4326),
    new_type text,
    descrip text
);


CREATE SEQUENCE sources.nu_rae_lines_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.nu_rae_lines_gid_seq OWNED BY sources.nu_rae_lines.gid;


CREATE TABLE sources.nu_sunneshine (
    gid integer NOT NULL,
    code character varying(16),
    geo_sym character varying(50),
    geo_misc character varying(16),
    geo_surf character varying(16),
    geo_link numeric,
    geo_pat character varying(16),
    descriptio character varying(254),
    shape_leng numeric,
    shape_area numeric,
    geom public.geometry(MultiPolygon,4326),
    max_age text,
    min_age text,
    early_id integer,
    late_id integer,
    use_age text,
    strat_name text,
    descrip text,
    map_unit text,
    geom_mod public.geometry
);


CREATE SEQUENCE sources.nu_sunneshine_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.nu_sunneshine_gid_seq OWNED BY sources.nu_sunneshine.gid;


CREATE TABLE sources.nu_sunneshine_lines (
    gid integer NOT NULL,
    symbol character varying(15),
    notes character varying(254),
    linetype character varying(25),
    code character varying(50),
    geo_sym character varying(30),
    confidence character varying(15),
    shape_leng numeric,
    geom public.geometry(MultiLineString,4326),
    new_type text,
    descrip text
);


CREATE SEQUENCE sources.nu_sunneshine_lines_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.nu_sunneshine_lines_gid_seq OWNED BY sources.nu_sunneshine_lines.gid;


CREATE TABLE sources.nu_sunneshine_points (
    gid integer NOT NULL,
    objectid integer,
    id integer,
    stationid character varying(25),
    earthmatid character varying(25),
    strucid character varying(25),
    strucno smallint,
    class character varying(25),
    struc_type character varying(50),
    detail character varying(80),
    method character varying(50),
    azimuth smallint,
    dipplunge smallint,
    symang smallint,
    icefeature character varying(100),
    relage smallint,
    numindic character varying(50),
    relation character varying(50),
    definition character varying(50),
    notes character varying(254),
    symbol smallint,
    intensity character varying(25),
    flattening character varying(25),
    geom public.geometry(Point,4326),
    dip_dir integer,
    point_type text,
    comments text
);


CREATE SEQUENCE sources.nu_sunneshine_points_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.nu_sunneshine_points_gid_seq OWNED BY sources.nu_sunneshine_points.gid;


CREATE TABLE sources.nu_sylvia_s (
    gid integer NOT NULL,
    labelid character varying(10),
    sourceid character varying(15),
    shape_leng numeric,
    shape_area numeric,
    d_labelid character varying(254),
    d_sourceid character varying(254),
    geo_desc character varying(254),
    fgdc_symbo character varying(15),
    geom public.geometry(MultiPolygon,4326),
    name text,
    strat_name text,
    age text,
    early_id integer,
    late_id integer
);


CREATE SEQUENCE sources.nu_sylvia_s_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.nu_sylvia_s_gid_seq OWNED BY sources.nu_sylvia_s.gid;


CREATE TABLE sources.nu_sylvia_s_lines (
    gid integer NOT NULL,
    geolineid character varying(12),
    geolinetyp integer,
    qualifier character varying(4),
    confidence character varying(2),
    attitude character varying(2),
    generation character varying(2),
    name character varying(254),
    movement character varying(2),
    hwalldir character varying(2),
    foldtrend character varying(2),
    foldplunge character varying(25),
    arrowdir character varying(2),
    minage character varying(50),
    maxage character varying(50),
    gsc_symbol character varying(12),
    sourceid character varying(15),
    isboundary character varying(2),
    origcode character varying(50),
    displaypub smallint,
    shape_leng numeric,
    d_geolinet character varying(254),
    d_qualifie character varying(254),
    d_confiden character varying(254),
    d_attitude character varying(254),
    d_generati character varying(254),
    d_movement character varying(254),
    d_hwalldir character varying(254),
    d_foldtren character varying(254),
    d_arrowdir character varying(254),
    d_sourceid character varying(254),
    d_isbounda character varying(254),
    d_displayp character varying(254),
    geom public.geometry(MultiLineStringZM,4326),
    new_type text,
    descrip text
);


CREATE SEQUENCE sources.nu_sylvia_s_lines_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.nu_sylvia_s_lines_gid_seq OWNED BY sources.nu_sylvia_s_lines.gid;


CREATE TABLE sources.nu_sylvia_s_points (
    gid integer NOT NULL,
    geopointid character varying(13),
    geopointty integer,
    geopointsu character varying(4),
    strucattit character varying(2),
    strucgener character varying(2),
    strucyoung character varying(2),
    strucmetho character varying(2),
    relatedstr character varying(15),
    azimuth smallint,
    dipplunge smallint,
    dipdesc character varying(30),
    sense_evid character varying(50),
    strain character varying(2),
    flattening character varying(2),
    gsc_symbol character varying(15),
    f_strucid character varying(25),
    sourceid character varying(15),
    origcode character varying(50),
    display_fr character varying(20),
    display_to character varying(20),
    displaypub smallint,
    d_geopoint character varying(254),
    d_geopoi_1 character varying(254),
    d_strucatt character varying(254),
    d_strucgen character varying(254),
    d_strucyou character varying(254),
    d_strucmet character varying(254),
    d_dipdesc character varying(254),
    d_sense_ev character varying(254),
    d_strain character varying(254),
    d_flatteni character varying(254),
    d_sourceid character varying(254),
    d_display_ character varying(254),
    d_display1 character varying(254),
    d_displayp character varying(254),
    geom public.geometry(PointZM,4326),
    column38 text,
    point_type text,
    comments text,
    dip_dir integer
);


CREATE SEQUENCE sources.nu_sylvia_s_points_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.nu_sylvia_s_points_gid_seq OWNED BY sources.nu_sylvia_s_points.gid;


CREATE TABLE sources.nu_tebesjuak (
    gid integer NOT NULL,
    map_theme character varying(50),
    feature character varying(50),
    map_unit character varying(100),
    parents character varying(254),
    max_age character varying(50),
    min_age character varying(50),
    lith_list character varying(100),
    genesis character varying(100),
    remarks character varying(254),
    label character varying(30),
    reference character varying(254),
    source_ref character varying(254),
    map_id character varying(254),
    include_hc character varying(5),
    symbol character varying(100),
    shape_leng numeric,
    shape_area numeric,
    geom public.geometry(MultiPolygon,4326),
    early_id integer,
    late_id integer,
    strat_name text,
    descrip text,
    use_age text
);


CREATE SEQUENCE sources.nu_tebesjuak_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.nu_tebesjuak_gid_seq OWNED BY sources.nu_tebesjuak.gid;


CREATE TABLE sources.nu_tebesjuak_lines (
    gid integer NOT NULL,
    map_theme character varying(50),
    feature character varying(50),
    subfeature character varying(50),
    attitude character varying(50),
    confidence character varying(15),
    generation character varying(25),
    max_age character varying(50),
    min_age character varying(50),
    name character varying(254),
    properties character varying(254),
    movement character varying(254),
    hwall_dir character varying(254),
    remarks character varying(254),
    reference character varying(254),
    source_ref character varying(254),
    map_id character varying(254),
    include_hc character varying(5),
    symbol character varying(100),
    shape_leng numeric,
    geom public.geometry(MultiLineString,4326),
    new_type text,
    descrip text
);


CREATE SEQUENCE sources.nu_tebesjuak_lines_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.nu_tebesjuak_lines_gid_seq OWNED BY sources.nu_tebesjuak_lines.gid;


CREATE TABLE sources.nu_tebesjuak_points (
    gid integer NOT NULL,
    map_theme character varying(50),
    feature character varying(50),
    planar_id character varying(50),
    subfeature character varying(50),
    fab_elem character varying(254),
    attitude character varying(50),
    young_evid character varying(50),
    generation character varying(50),
    method character varying(50),
    dip_dir integer,
    strike integer,
    dip integer,
    strain character varying(50),
    flattening character varying(50),
    lith_id character varying(50),
    station_id character varying(50),
    linear_id character varying(100),
    planar_id2 character varying(100),
    remarks character varying(254),
    reference character varying(254),
    source_ref character varying(254),
    map_id character varying(254),
    include_hc character varying(5),
    symbol character varying(100),
    geom public.geometry(Point,4326),
    point_type text,
    comments text
);


CREATE SEQUENCE sources.nu_tebesjuak_points_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.nu_tebesjuak_points_gid_seq OWNED BY sources.nu_tebesjuak_points.gid;


CREATE TABLE sources.nu_terra (
    gid integer NOT NULL,
    remarks character varying(254),
    fgdc_symbo character varying(15),
    shape_leng numeric,
    shape_area numeric,
    sourceid character varying(150),
    descrip character varying(254),
    labelid character varying(254),
    geom public.geometry(MultiPolygonZM,4326),
    map_unit text,
    age text,
    early_id integer,
    late_id integer,
    strat_name text
);


CREATE SEQUENCE sources.nu_terra_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.nu_terra_gid_seq OWNED BY sources.nu_terra.gid;


CREATE TABLE sources.nu_terra_lines (
    gid integer NOT NULL,
    name character varying(254),
    remarks character varying(254),
    foldplunge character varying(25),
    minage character varying(50),
    maxage character varying(50),
    feat integer,
    fgdc_symbo character varying(12),
    geolineid character varying(12),
    sourceid character varying(150),
    shape_leng numeric,
    geolinetyp character varying(254),
    qualifier character varying(254),
    confidence character varying(254),
    attitude character varying(254),
    generation character varying(254),
    movement character varying(254),
    hwalldir character varying(254),
    foldtrend character varying(254),
    arrowdir character varying(254),
    isboundary character varying(254),
    geom public.geometry(MultiLineStringZM,4326),
    new_type text,
    descrip text
);


CREATE SEQUENCE sources.nu_terra_lines_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.nu_terra_lines_gid_seq OWNED BY sources.nu_terra_lines.gid;


CREATE TABLE sources.nu_terra_points (
    gid integer NOT NULL,
    azimuth smallint,
    dipplunge smallint,
    fgdc_symbo character varying(15),
    dipdesc character varying(30),
    geopointid character varying(13),
    stationid character varying(25),
    prime_stru character varying(3),
    sourceid character varying(150),
    geopointty character varying(254),
    geopointsu character varying(254),
    strucattit character varying(254),
    strucgener character varying(254),
    strucyoung character varying(254),
    strucmetho character varying(254),
    display_fr character varying(254),
    display_to character varying(254),
    sense_evid character varying(254),
    ruleid character varying(254),
    geom public.geometry(PointZM,4326),
    point_type text,
    comments text,
    dip_dir integer
);


CREATE SEQUENCE sources.nu_terra_points_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.nu_terra_points_gid_seq OWNED BY sources.nu_terra_points.gid;


CREATE TABLE sources.nv_beatty (
    gid integer NOT NULL,
    area double precision,
    perimeter double precision,
    bty_geo0_ numeric(10,0),
    bty_geo0_i numeric(10,0),
    ptype character varying(35),
    sel smallint,
    symb smallint,
    geom public.geometry(MultiPolygon,4326),
    name text,
    age text,
    description text,
    strat_name text,
    hierarchy text,
    early_id integer,
    late_id integer
);


CREATE SEQUENCE sources.nv_beatty_geo_poly_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.nv_beatty_geo_poly_gid_seq OWNED BY sources.nv_beatty.gid;


CREATE TABLE sources.nv_beatty_lines (
    gid integer NOT NULL,
    fnode_ numeric(10,0),
    tnode_ numeric(10,0),
    lpoly_ numeric(10,0),
    rpoly_ numeric(10,0),
    length double precision,
    bty_anno0_ numeric(10,0),
    bty_anno01 numeric(10,0),
    ltype character varying(65),
    sel smallint,
    symb smallint,
    geom public.geometry(MultiLineString,4326),
    new_type text,
    description text
);


CREATE SEQUENCE sources.nv_beatty_line_annotation_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.nv_beatty_line_annotation_gid_seq OWNED BY sources.nv_beatty_lines.gid;


CREATE TABLE sources.nv_las_vegas (
    gid integer,
    lv_geol_ double precision,
    lv_geol_id double precision,
    unit_ integer,
    unit character varying(5),
    descriptio character varying(100),
    geom public.geometry(MultiPolygon,4326),
    name text,
    strat_name text,
    age text,
    age_top text,
    age_bottom text,
    descrip text,
    late_id integer,
    early_id integer
);


CREATE TABLE sources.nv_las_vegas_lines (
    gid integer NOT NULL,
    fnode_ double precision,
    tnode_ double precision,
    lpoly_ double precision,
    rpoly_ double precision,
    lv_flt_ double precision,
    lv_flt_id double precision,
    descriptio character varying(100),
    geom public.geometry(MultiLineString,4326),
    new_type character varying(65),
    new_direction character varying(65)
);


CREATE SEQUENCE sources.nv_las_vegas_lines_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.nv_las_vegas_lines_gid_seq OWNED BY sources.nv_las_vegas_lines.gid;


CREATE TABLE sources.nv_las_vegas_units (
    gid integer NOT NULL,
    lv_geol_ double precision,
    lv_geol_id double precision,
    unit_ integer,
    unit character varying(5),
    descriptio character varying(100),
    symbol smallint,
    geom public.geometry(MultiPolygon,4326)
);


CREATE SEQUENCE sources.nv_las_vegas_units_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.nv_las_vegas_units_gid_seq OWNED BY sources.nv_las_vegas_units.gid;


CREATE TABLE sources.nw_lacmaunoir (
    gid integer NOT NULL,
    map_theme character varying(50),
    feature character varying(50),
    map_unit character varying(100),
    parents character varying(254),
    max_age character varying(50),
    min_age character varying(50),
    lith_list character varying(100),
    genesis character varying(100),
    remarks character varying(254),
    label character varying(30),
    reference character varying(254),
    map_id character varying(254),
    pub_scale numeric,
    symbol character varying(50),
    anno character varying(60),
    shape_leng numeric,
    shape_area numeric,
    geom public.geometry(MultiPolygon,4326),
    descrip text,
    strat_name text,
    use_age text,
    early_id integer,
    late_id integer
);


CREATE TABLE sources.nw_lacmaunoir_drift (
    gid integer NOT NULL,
    map_theme character varying(50),
    feature character varying(50),
    map_unit character varying(100),
    parents character varying(254),
    max_age character varying(50),
    min_age character varying(50),
    lith_list character varying(100),
    genesis character varying(100),
    remarks character varying(254),
    label character varying(30),
    reference character varying(254),
    map_id character varying(254),
    pub_scale numeric,
    symbol character varying(50),
    anno character varying(60),
    shape_leng numeric,
    shape_area numeric,
    geom public.geometry(MultiPolygon,4326),
    descrip text,
    early_id integer,
    late_id integer
);


CREATE SEQUENCE sources.nw_lacmaunoir_drift_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.nw_lacmaunoir_drift_gid_seq OWNED BY sources.nw_lacmaunoir_drift.gid;


CREATE TABLE sources.nw_lacmaunoir_folds (
    gid integer NOT NULL,
    map_theme character varying(50),
    feature character varying(50),
    subfeature character varying(50),
    attitude character varying(50),
    confidence character varying(15),
    evid_from character varying(50),
    max_age character varying(50),
    min_age character varying(50),
    foldtrend character varying(20),
    foldplunge character varying(20),
    name character varying(254),
    properties character varying(254),
    remarks character varying(254),
    reference character varying(254),
    source_ref character varying(254),
    map_id character varying(254),
    pub_scale numeric,
    arrow_dir character varying(20),
    symbol character varying(50),
    shape_leng numeric,
    geom public.geometry(MultiLineString,4326),
    new_type text
);


CREATE SEQUENCE sources.nw_lacmaunoir_folds_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.nw_lacmaunoir_folds_gid_seq OWNED BY sources.nw_lacmaunoir_folds.gid;


CREATE SEQUENCE sources.nw_lacmaunoir_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.nw_lacmaunoir_gid_seq OWNED BY sources.nw_lacmaunoir.gid;


CREATE TABLE sources.nw_lacmaunoir_points (
    gid integer NOT NULL,
    map_theme character varying(50),
    feature character varying(50),
    planar_id character varying(50),
    subfeature character varying(50),
    attitude character varying(50),
    young_evid character varying(50),
    generation character varying(25),
    method character varying(50),
    dip_dir smallint,
    strike smallint,
    dip smallint,
    sense character varying(254),
    sense_evid character varying(50),
    lith_id character varying(50),
    station_id character varying(50),
    linear_id character varying(100),
    planar_id2 character varying(100),
    remarks character varying(254),
    reference character varying(254),
    source_ref character varying(254),
    map_id character varying(254),
    symbol character varying(50),
    geom public.geometry(Point,4326)
);


CREATE SEQUENCE sources.nw_lacmaunoir_points_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.nw_lacmaunoir_points_gid_seq OWNED BY sources.nw_lacmaunoir_points.gid;


CREATE TABLE sources.nw_slave_lines (
    gid integer NOT NULL,
    type character varying(30),
    subtype character varying(100),
    modifier character varying(30),
    attitude character varying(30),
    confidence character varying(30),
    dip_fp character varying(10),
    dip_dir_fp character varying(30),
    movement character varying(30),
    name character varying(30),
    remarks character varying(250),
    struc_lv character varying(50),
    reference character varying(250),
    imw_map character varying(12),
    shape_leng numeric,
    geom public.geometry(MultiLineString,4326),
    new_type text
);


CREATE SEQUENCE sources.nw_slave_lines_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.nw_slave_lines_gid_seq OWNED BY sources.nw_slave_lines.gid;


CREATE TABLE sources.nw_slave_rv (
    gid integer NOT NULL,
    gr_ste character varying(254),
    fm_ld character varying(254),
    member character varying(30),
    i_map_unit character varying(100),
    max_age character varying(50),
    min_age character varying(50),
    major_lith character varying(250),
    minor_lith character varying(250),
    remarks character varying(250),
    label character varying(18),
    rgb_colour character varying(12),
    legend_ord character varying(18),
    struc_lv character varying(50),
    reference character varying(250),
    imw_map character varying(12),
    shape_leng numeric,
    shape_area numeric,
    geom public.geometry(MultiPolygon,4326),
    use_age text,
    strat_name text,
    early_id integer,
    late_id integer,
    use_name text
);


CREATE SEQUENCE sources.nw_slave_rv_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.nw_slave_rv_gid_seq OWNED BY sources.nw_slave_rv.gid;


CREATE TABLE sources.nwt_calder (
    gid integer NOT NULL,
    areakm2 numeric,
    annotation character varying(50),
    annotati_1 character varying(50),
    eon character varying(50),
    era character varying(50),
    period character varying(50),
    assemblage character varying(50),
    assembla_1 character varying(50),
    supergroup character varying(50),
    group_ character varying(50),
    formation character varying(50),
    member character varying(100),
    intrusion_ character varying(150),
    lithology character varying(254),
    shape_leng numeric,
    shape_area numeric,
    geom public.geometry(MultiPolygon,4326),
    strat_name text,
    early_id integer,
    late_id integer,
    age text,
    map_unit text,
    descrip text
);


CREATE SEQUENCE sources.nwt_calder_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.nwt_calder_gid_seq OWNED BY sources.nwt_calder.gid;


CREATE TABLE sources.nwt_calder_lines (
    gid integer NOT NULL,
    fault_type character varying(50),
    shape_leng numeric,
    descriptio character varying(254),
    symbol character varying(20),
    geom public.geometry(MultiLineString,4326),
    new_type text
);


CREATE SEQUENCE sources.nwt_calder_lines_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.nwt_calder_lines_gid_seq OWNED BY sources.nwt_calder_lines.gid;


CREATE TABLE sources.nwt_calder_points (
    gid integer NOT NULL,
    struc_type character varying(50),
    azimuth smallint,
    dipplunge smallint,
    visible smallint,
    geom public.geometry(Point,4326),
    dip_dir integer,
    point_type text
);


CREATE SEQUENCE sources.nwt_calder_points_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.nwt_calder_points_gid_seq OWNED BY sources.nwt_calder_points.gid;


CREATE TABLE sources.nwt_campbell (
    gid integer NOT NULL,
    map_theme character varying(50),
    feature character varying(50),
    map_unit character varying(100),
    parents character varying(254),
    max_age character varying(50),
    min_age character varying(50),
    lith_list character varying(100),
    descrip text,
    genesis character varying(100),
    remarks character varying(254),
    label character varying(30),
    reference character varying(254),
    source_ref character varying(254),
    map_id character varying(254),
    pub_scale numeric,
    include_hc character varying(5),
    symbol character varying(100),
    shape_leng numeric,
    shape_area numeric,
    geom public.geometry(MultiPolygonZM,4326),
    early_id integer,
    late_id integer,
    use_age text,
    strat_name text
);


CREATE SEQUENCE sources.nwt_campbell_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.nwt_campbell_gid_seq OWNED BY sources.nwt_campbell.gid;


CREATE TABLE sources.nwt_campbell_lines (
    gid integer NOT NULL,
    map_theme character varying(50),
    feature character varying(50),
    subfeature character varying(50),
    attitude character varying(50),
    confidence character varying(15),
    generation character varying(25),
    max_age character varying(50),
    min_age character varying(50),
    name character varying(254),
    properties character varying(254),
    movement character varying(254),
    hwall_dir character varying(254),
    remarks character varying(254),
    reference character varying(254),
    source_ref character varying(254),
    map_id character varying(254),
    pub_scale numeric,
    include_hc character varying(5),
    symbol character varying(100),
    shape_leng numeric,
    geom public.geometry(MultiLineString,4326),
    new_type text,
    descrip text
);


CREATE SEQUENCE sources.nwt_campbell_lines_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.nwt_campbell_lines_gid_seq OWNED BY sources.nwt_campbell_lines.gid;


CREATE TABLE sources.nwt_campbell_points (
    gid integer NOT NULL,
    map_theme character varying(50),
    feature character varying(50),
    planar_id character varying(50),
    subfeature character varying(50),
    fab_elem character varying(254),
    attitude character varying(50),
    young_evid character varying(50),
    generation character varying(50),
    method character varying(50),
    dip_dir integer,
    strike integer,
    dip integer,
    strain character varying(50),
    flattening character varying(50),
    lith_id character varying(50),
    station_id character varying(50),
    related_id character varying(100),
    linear_id character varying(100),
    planar_id2 character varying(100),
    remarks character varying(254),
    reference character varying(254),
    source_ref character varying(254),
    map_id character varying(254),
    release character varying(30),
    authority character varying(100),
    include_hc character varying(5),
    symbol character varying(100),
    geom public.geometry(Point,4326),
    point_type text
);


CREATE SEQUENCE sources.nwt_campbell_points_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.nwt_campbell_points_gid_seq OWNED BY sources.nwt_campbell_points.gid;


CREATE TABLE sources.nwt_carcajou (
    gid integer NOT NULL,
    map_theme character varying(50),
    feature character varying(50),
    map_unit character varying(100),
    parents character varying(254),
    max_age character varying(50),
    min_age character varying(50),
    lith_list character varying(100),
    genesis character varying(100),
    remarks character varying(254),
    label character varying(30),
    reference character varying(254),
    source_ref character varying(254),
    map_id character varying(254),
    symbol character varying(100),
    shape_area numeric,
    shape_len numeric,
    geom public.geometry(MultiPolygon,4326),
    early_id integer,
    late_id integer,
    descrip text,
    strat_name text,
    use_age text,
    hierarchy text
);


CREATE SEQUENCE sources.nwt_carcajou_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.nwt_carcajou_gid_seq OWNED BY sources.nwt_carcajou.gid;


CREATE TABLE sources.nwt_carcajou_lines (
    gid integer NOT NULL,
    map_theme character varying(50),
    feature character varying(50),
    subfeature character varying(50),
    attitude character varying(50),
    confidence character varying(15),
    generation character varying(25),
    max_age character varying(50),
    min_age character varying(50),
    name character varying(254),
    properties character varying(254),
    movement character varying(254),
    hwall_dir character varying(254),
    remarks character varying(254),
    reference character varying(254),
    source_ref character varying(254),
    map_id character varying(254),
    symbol character varying(100),
    shape_len numeric,
    geom public.geometry(MultiLineString,4326),
    new_type text
);


CREATE SEQUENCE sources.nwt_carcajou_lines_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.nwt_carcajou_lines_gid_seq OWNED BY sources.nwt_carcajou_lines.gid;


CREATE TABLE sources.nwt_carcajou_ne (
    gid integer NOT NULL,
    map_theme character varying(50),
    feature character varying(50),
    map_unit character varying(100),
    parents character varying(254),
    max_age character varying(50),
    min_age character varying(50),
    lith_list character varying(100),
    genesis character varying(100),
    remarks character varying(254),
    label character varying(30),
    reference character varying(254),
    source_ref character varying(254),
    map_id character varying(254),
    symbol character varying(100),
    shape_area numeric,
    shape_len numeric,
    geom public.geometry(MultiPolygon,4326),
    early_id integer,
    late_id integer,
    use_age text,
    strat_name text,
    descrip text,
    hierarchy text
);


CREATE SEQUENCE sources.nwt_carcajou_ne_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.nwt_carcajou_ne_gid_seq OWNED BY sources.nwt_carcajou_ne.gid;


CREATE TABLE sources.nwt_carcajou_ne_lines (
    gid integer NOT NULL,
    map_theme character varying(50),
    feature character varying(50),
    subfeature character varying(50),
    attitude character varying(50),
    confidence character varying(15),
    generation character varying(25),
    max_age character varying(50),
    min_age character varying(50),
    foldtrend character varying(20),
    foldplunge character varying(20),
    name character varying(254),
    properties character varying(254),
    remarks character varying(254),
    reference character varying(254),
    source_ref character varying(254),
    map_id character varying(254),
    arrow_dir character varying(20),
    symbol character varying(100),
    shape_len numeric,
    geom public.geometry(MultiLineString,4326),
    new_type text
);


CREATE SEQUENCE sources.nwt_carcajou_ne_lines_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.nwt_carcajou_ne_lines_gid_seq OWNED BY sources.nwt_carcajou_ne_lines.gid;


CREATE TABLE sources.nwt_carcajou_ne_points (
    gid integer NOT NULL,
    map_theme character varying(50),
    feature character varying(50),
    planar_id character varying(50),
    subfeature character varying(60),
    attitude character varying(50),
    young_evid character varying(50),
    generation character varying(50),
    method character varying(50),
    dip_dir bigint,
    strike bigint,
    dip bigint,
    lith_id character varying(50),
    station_id character varying(50),
    linear_id character varying(100),
    planar_id2 character varying(100),
    remarks character varying(254),
    reference character varying(254),
    source_ref character varying(254),
    map_id character varying(254),
    symbol character varying(100),
    geom public.geometry(Point,4326),
    point_type text
);


CREATE SEQUENCE sources.nwt_carcajou_ne_points_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.nwt_carcajou_ne_points_gid_seq OWNED BY sources.nwt_carcajou_ne_points.gid;


CREATE TABLE sources.nwt_carcajou_points (
    gid integer NOT NULL,
    map_theme character varying(50),
    feature character varying(50),
    planar_id character varying(50),
    subfeature character varying(50),
    fab_elem character varying(254),
    attitude character varying(50),
    young_evid character varying(50),
    generation character varying(50),
    method character varying(50),
    dip_dir bigint,
    strike bigint,
    dip bigint,
    strain character varying(50),
    flattening character varying(50),
    lith_id character varying(50),
    station_id character varying(50),
    linear_id character varying(100),
    planar_id2 character varying(100),
    remarks character varying(254),
    reference character varying(254),
    source_ref character varying(254),
    map_id character varying(254),
    symbol character varying(100),
    geom public.geometry(Point,4326),
    point_type text
);


CREATE SEQUENCE sources.nwt_carcajou_points_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.nwt_carcajou_points_gid_seq OWNED BY sources.nwt_carcajou_points.gid;


CREATE TABLE sources.nwt_carcajou_se (
    gid integer NOT NULL,
    map_theme character varying(50),
    feature character varying(50),
    map_unit character varying(100),
    parents character varying(254),
    max_age character varying(50),
    min_age character varying(50),
    lith_list character varying(100),
    genesis character varying(100),
    remarks character varying(254),
    label character varying(30),
    reference character varying(254),
    source_ref character varying(254),
    map_id character varying(254),
    symbol character varying(100),
    shape_area numeric,
    shape_len numeric,
    geom public.geometry(MultiPolygon,4326),
    early_id integer,
    late_id integer,
    use_age text,
    strat_name text,
    descrip text,
    hierarchy text
);


CREATE SEQUENCE sources.nwt_carcajou_se_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.nwt_carcajou_se_gid_seq OWNED BY sources.nwt_carcajou_se.gid;


CREATE TABLE sources.nwt_carcajou_se_lines (
    gid integer NOT NULL,
    map_theme character varying(50),
    feature character varying(50),
    subfeature character varying(50),
    attitude character varying(50),
    confidence character varying(15),
    generation character varying(25),
    max_age character varying(50),
    min_age character varying(50),
    name character varying(254),
    properties character varying(254),
    movement character varying(254),
    hwall_dir character varying(254),
    remarks character varying(254),
    reference character varying(254),
    source_ref character varying(254),
    map_id character varying(254),
    symbol character varying(100),
    shape_len numeric,
    geom public.geometry(MultiLineString,4326),
    new_type text
);


CREATE SEQUENCE sources.nwt_carcajou_se_lines_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.nwt_carcajou_se_lines_gid_seq OWNED BY sources.nwt_carcajou_se_lines.gid;


CREATE TABLE sources.nwt_carcajou_se_points (
    gid integer NOT NULL,
    map_theme character varying(50),
    feature character varying(50),
    planar_id character varying(50),
    subfeature character varying(50),
    fab_elem character varying(254),
    attitude character varying(50),
    young_evid character varying(50),
    generation character varying(50),
    method character varying(50),
    dip_dir bigint,
    strike bigint,
    dip bigint,
    strain character varying(50),
    flattening character varying(50),
    lith_id character varying(50),
    station_id character varying(50),
    linear_id character varying(100),
    planar_id2 character varying(100),
    remarks character varying(254),
    reference character varying(254),
    source_ref character varying(254),
    map_id character varying(254),
    symbol character varying(100),
    geom public.geometry(Point,4326),
    point_type text
);


CREATE SEQUENCE sources.nwt_carcajou_se_points_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.nwt_carcajou_se_points_gid_seq OWNED BY sources.nwt_carcajou_se_points.gid;


CREATE TABLE sources.nwt_carcajou_sw (
    gid integer NOT NULL,
    map_theme character varying(50),
    feature character varying(50),
    map_unit character varying(100),
    parents character varying(254),
    max_age character varying(50),
    min_age character varying(50),
    lith_list character varying(100),
    genesis character varying(100),
    remarks character varying(254),
    label character varying(30),
    reference character varying(254),
    source_ref character varying(254),
    map_id character varying(254),
    symbol character varying(100),
    shape_area numeric,
    shape_len numeric,
    geom public.geometry(MultiPolygon,4326),
    early_id integer,
    late_id integer,
    use_age text,
    strat_name text,
    descrip text,
    hierarchy text
);


CREATE SEQUENCE sources.nwt_carcajou_sw_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.nwt_carcajou_sw_gid_seq OWNED BY sources.nwt_carcajou_sw.gid;


CREATE TABLE sources.nwt_carcajou_sw_lines (
    gid integer NOT NULL,
    map_theme character varying(50),
    feature character varying(50),
    subfeature character varying(50),
    attitude character varying(50),
    confidence character varying(15),
    generation character varying(25),
    max_age character varying(50),
    min_age character varying(50),
    name character varying(254),
    properties character varying(254),
    movement character varying(254),
    hwall_dir character varying(254),
    remarks character varying(254),
    reference character varying(254),
    source_ref character varying(254),
    map_id character varying(254),
    symbol character varying(100),
    shape_len numeric,
    geom public.geometry(MultiLineString,4326),
    new_type text
);


CREATE SEQUENCE sources.nwt_carcajou_sw_lines_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.nwt_carcajou_sw_lines_gid_seq OWNED BY sources.nwt_carcajou_sw_lines.gid;


CREATE TABLE sources.nwt_carcajou_sw_points (
    gid integer NOT NULL,
    map_theme character varying(50),
    feature character varying(50),
    planar_id character varying(50),
    subfeature character varying(50),
    fab_elem character varying(254),
    attitude character varying(50),
    young_evid character varying(50),
    generation character varying(50),
    method character varying(50),
    dip_dir bigint,
    strike bigint,
    dip bigint,
    strain character varying(50),
    flattening character varying(50),
    lith_id character varying(50),
    station_id character varying(50),
    linear_id character varying(100),
    planar_id2 character varying(100),
    remarks character varying(254),
    reference character varying(254),
    source_ref character varying(254),
    map_id character varying(254),
    symbol character varying(100),
    geom public.geometry(Point,4326),
    point_type text
);


CREATE SEQUENCE sources.nwt_carcajou_sw_points_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.nwt_carcajou_sw_points_gid_seq OWNED BY sources.nwt_carcajou_sw_points.gid;


CREATE TABLE sources.nwt_mahony_sw (
    gid integer NOT NULL,
    map_theme character varying(50),
    feature character varying(50),
    map_unit character varying(100),
    parents character varying(254),
    max_age character varying(50),
    min_age character varying(50),
    lith_list character varying(100),
    genesis character varying(100),
    remarks character varying(254),
    label character varying(30),
    reference character varying(254),
    source_ref character varying(254),
    map_id character varying(254),
    symbol character varying(100),
    shape_leng numeric,
    shape_area numeric,
    geom public.geometry(MultiPolygon,4326),
    early_id integer,
    late_id integer,
    use_age text,
    strat_name text,
    descrip text,
    hierarchy text
);


CREATE SEQUENCE sources.nwt_mahony_sw_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.nwt_mahony_sw_gid_seq OWNED BY sources.nwt_mahony_sw.gid;


CREATE TABLE sources.nwt_mahony_sw_lines (
    gid integer NOT NULL,
    map_theme character varying(50),
    feature character varying(50),
    subfeature character varying(50),
    attitude character varying(50),
    confidence character varying(15),
    generation character varying(25),
    max_age character varying(50),
    min_age character varying(50),
    foldtrend character varying(20),
    foldplunge character varying(20),
    name character varying(254),
    properties character varying(254),
    remarks character varying(254),
    reference character varying(254),
    source_ref character varying(254),
    map_id character varying(254),
    arrow_dir character varying(20),
    symbol character varying(100),
    shape_len numeric,
    geom public.geometry(MultiLineString,4326),
    new_type text
);


CREATE SEQUENCE sources.nwt_mahony_sw_lines_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.nwt_mahony_sw_lines_gid_seq OWNED BY sources.nwt_mahony_sw_lines.gid;


CREATE TABLE sources.nwt_mahony_sw_points (
    gid integer NOT NULL,
    map_theme character varying(50),
    feature character varying(50),
    planar_id character varying(50),
    subfeature character varying(50),
    attitude character varying(50),
    young_evid character varying(50),
    generation character varying(50),
    method character varying(50),
    dip_dir bigint,
    strike bigint,
    dip bigint,
    lith_id character varying(50),
    station_id character varying(50),
    linear_id character varying(100),
    planar_id2 character varying(100),
    remarks character varying(254),
    reference character varying(254),
    source_ref character varying(254),
    map_id character varying(254),
    symbol character varying(100),
    geom public.geometry(Point,4326),
    point_type text
);


CREATE SEQUENCE sources.nwt_mahony_sw_points_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.nwt_mahony_sw_points_gid_seq OWNED BY sources.nwt_mahony_sw_points.gid;


CREATE TABLE sources.nwt_norman_nw (
    gid integer NOT NULL,
    map_theme character varying(50),
    feature character varying(50),
    map_unit character varying(100),
    parents character varying(254),
    max_age character varying(50),
    min_age character varying(50),
    lith_list character varying(100),
    descriptio character varying(254),
    genesis character varying(100),
    remarks character varying(254),
    label character varying(30),
    reference character varying(254),
    source_ref character varying(254),
    map_id character varying(254),
    symbol character varying(100),
    shape_area numeric,
    shape_len numeric,
    geom public.geometry(MultiPolygon,4326),
    early_id integer,
    late_id integer,
    use_age text,
    strat_name text,
    descrip text,
    hierarchy text
);


CREATE SEQUENCE sources.nwt_norman_nw_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.nwt_norman_nw_gid_seq OWNED BY sources.nwt_norman_nw.gid;


CREATE TABLE sources.nwt_norman_nw_lines (
    gid integer NOT NULL,
    map_theme character varying(50),
    feature character varying(50),
    subfeature character varying(50),
    attitude character varying(50),
    confidence character varying(15),
    generation character varying(25),
    max_age character varying(50),
    min_age character varying(50),
    foldtrend character varying(20),
    foldplunge character varying(20),
    name character varying(254),
    properties character varying(254),
    remarks character varying(254),
    reference character varying(254),
    source_ref character varying(254),
    map_id character varying(254),
    arrow_dir character varying(20),
    symbol character varying(100),
    shape_len numeric,
    geom public.geometry(MultiLineString,4326),
    new_type text
);


CREATE SEQUENCE sources.nwt_norman_nw_lines_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.nwt_norman_nw_lines_gid_seq OWNED BY sources.nwt_norman_nw_lines.gid;


CREATE TABLE sources.nwt_norman_nw_points (
    gid integer NOT NULL,
    map_theme character varying(50),
    feature character varying(50),
    planar_id character varying(50),
    subfeature character varying(50),
    attitude character varying(50),
    young_evid character varying(50),
    generation character varying(50),
    method character varying(50),
    dip_dir bigint,
    strike bigint,
    dip bigint,
    lith_id character varying(50),
    station_id character varying(50),
    linear_id character varying(100),
    planar_id2 character varying(100),
    remarks character varying(254),
    reference character varying(254),
    source_ref character varying(254),
    map_id character varying(254),
    symbol character varying(100),
    geom public.geometry(Point,4326),
    point_type text
);


CREATE SEQUENCE sources.nwt_norman_nw_points_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.nwt_norman_nw_points_gid_seq OWNED BY sources.nwt_norman_nw_points.gid;


CREATE TABLE sources.nwt_norman_se (
    gid integer NOT NULL,
    map_theme character varying(50),
    feature character varying(50),
    map_unit character varying(100),
    parents character varying(254),
    max_age character varying(50),
    min_age character varying(50),
    lith_list character varying(100),
    genesis character varying(100),
    remarks character varying(254),
    label character varying(30),
    reference character varying(254),
    source_ref character varying(254),
    map_id character varying(254),
    symbol character varying(100),
    shape_area numeric,
    shape_len numeric,
    geom public.geometry(MultiPolygon,4326),
    early_id integer,
    late_id integer,
    use_age text,
    strat_name text,
    descrip text,
    hierarchy text
);


CREATE SEQUENCE sources.nwt_norman_se_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.nwt_norman_se_gid_seq OWNED BY sources.nwt_norman_se.gid;


CREATE TABLE sources.nwt_norman_se_lines (
    gid integer NOT NULL,
    map_theme character varying(50),
    feature character varying(50),
    subfeature character varying(50),
    attitude character varying(50),
    confidence character varying(15),
    generation character varying(25),
    max_age character varying(50),
    min_age character varying(50),
    name character varying(254),
    properties character varying(254),
    movement character varying(254),
    hwall_dir character varying(254),
    remarks character varying(254),
    reference character varying(254),
    source_ref character varying(254),
    map_id character varying(254),
    symbol character varying(100),
    shape_len numeric,
    geom public.geometry(MultiLineString,4326),
    new_type text
);


CREATE SEQUENCE sources.nwt_norman_se_lines_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.nwt_norman_se_lines_gid_seq OWNED BY sources.nwt_norman_se_lines.gid;


CREATE TABLE sources.nwt_norman_se_points (
    gid integer NOT NULL,
    map_theme character varying(50),
    feature character varying(50),
    planar_id character varying(50),
    subfeature character varying(75),
    attitude character varying(50),
    young_evid character varying(50),
    generation character varying(50),
    method character varying(50),
    dip_dir bigint,
    strike bigint,
    dip bigint,
    lith_id character varying(50),
    station_id character varying(50),
    linear_id character varying(100),
    planar_id2 character varying(100),
    remarks character varying(254),
    reference character varying(254),
    source_ref character varying(254),
    map_id character varying(254),
    symbol character varying(100),
    geom public.geometry(Point,4326),
    point_type text
);


CREATE SEQUENCE sources.nwt_norman_se_points_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.nwt_norman_se_points_gid_seq OWNED BY sources.nwt_norman_se_points.gid;


CREATE TABLE sources.nwt_taki (
    gid integer NOT NULL,
    label_1 character varying(60),
    nb_label smallint,
    editing_re character varying(50),
    shape_leng numeric,
    shape_area numeric,
    symbol character varying(50),
    code character varying(50),
    geom public.geometry(MultiPolygon,4326),
    name text,
    age text,
    early_id integer,
    late_id integer,
    strat_name text,
    descrip text,
    hierarchy text
);


CREATE SEQUENCE sources.nwt_taki_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.nwt_taki_gid_seq OWNED BY sources.nwt_taki.gid;


CREATE TABLE sources.nwt_taki_lines (
    gid integer NOT NULL,
    feature integer,
    subfeature character varying(50),
    confidence character varying(15),
    movement character varying(20),
    attitude character varying(50),
    generation character varying(10),
    remarks character varying(254),
    symbol character varying(20),
    shape_leng numeric,
    geom public.geometry(MultiLineString,4326),
    subfeature2 text,
    new_type text,
    confidence2 text,
    descrip text
);


CREATE SEQUENCE sources.nwt_taki_lines_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.nwt_taki_lines_gid_seq OWNED BY sources.nwt_taki_lines.gid;


CREATE TABLE sources.nwt_taki_points (
    gid integer NOT NULL,
    stationid character varying(25),
    earthmatid character varying(25),
    strucid character varying(25),
    strucno smallint,
    strucclass character varying(10),
    structype character varying(30),
    detail character varying(50),
    method character varying(50),
    format character varying(25),
    attitude character varying(50),
    younging character varying(50),
    generation character varying(50),
    strain character varying(50),
    flattening character varying(50),
    related character varying(50),
    fabric character varying(254),
    sense character varying(254),
    azimuth smallint,
    dipplunge smallint,
    symang smallint,
    notes character varying(254),
    keep4map character varying(3),
    shown smallint,
    symbology character varying(12),
    scale50ks smallint,
    scale100ks smallint,
    geom public.geometry(Point,4326),
    point_type text,
    dip_dir integer,
    comments text
);


CREATE SEQUENCE sources.nwt_taki_points_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.nwt_taki_points_gid_seq OWNED BY sources.nwt_taki_points.gid;


CREATE SEQUENCE sources.oceanside_ca_lines_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.oceanside_ca_lines_gid_seq OWNED BY sources.ca_oceanside_lines.gid;


CREATE SEQUENCE sources.oceanside_pointorn_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.oceanside_pointorn_gid_seq OWNED BY sources.ca_oceanside_points.gid;


CREATE TABLE sources.ontario (
    gid integer NOT NULL,
    area numeric,
    perimeter numeric,
    geology_ integer,
    geology_id integer,
    feature character varying(50),
    type_all character varying(50),
    type_p character varying(50),
    type_s character varying(50),
    type_t character varying(50),
    unitname_p character varying(200),
    rocktype_p character varying(254),
    strat_p character varying(200),
    supereon_p character varying(50),
    eon_p character varying(50),
    era_p character varying(75),
    period_p character varying(50),
    epoch_p character varying(50),
    province_p character varying(50),
    tectzone_p character varying(50),
    orogen_p character varying(100),
    sut_gab_p character varying(100),
    geom public.geometry(MultiPolygon,4326),
    age character varying(75),
    early_id integer,
    late_id integer,
    name text,
    strat_name text
);


CREATE TABLE sources.ontario_dikes (
    gid integer NOT NULL,
    feature character varying(50),
    type character varying(50),
    age character varying(80),
    dike_type character varying(150),
    dike_code character varying(10),
    map_source character varying(50),
    label character varying(50),
    geom public.geometry(MultiLineString,4326)
);


CREATE SEQUENCE sources.ontario_dikes_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.ontario_dikes_gid_seq OWNED BY sources.ontario_dikes.gid;


CREATE SEQUENCE sources.ontario_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.ontario_gid_seq OWNED BY sources.ontario.gid;


CREATE TABLE sources.ontario_pz (
    gid integer NOT NULL,
    area double precision,
    perimeter double precision,
    paleo_poly_ integer,
    paleo_poly_id integer,
    orig_unit character varying(10),
    orig_formation character varying(50),
    orig_lithology character varying(320),
    age character varying(25),
    source_map character varying(10),
    legend_key character varying(15),
    unit_number character varying(2),
    subunit character varying(4),
    unit_name character varying(50),
    group_ character varying(30),
    formation text,
    member character varying(100),
    primary_litho character varying(50),
    descript_full character varying(320),
    descript_brief character varying(120),
    shape_length double precision,
    shape_area double precision,
    strat_name text,
    early_id integer,
    late_id integer,
    omit_poly character varying(1),
    geom public.geometry
);


CREATE TABLE sources.ontario_pz_lines (
    gid integer NOT NULL,
    fnode_ integer,
    tnode_ integer,
    lpoly_ integer,
    rpoly_ integer,
    length double precision,
    paleo_fault_ integer,
    paleo_fault_id integer,
    feature_code character varying(15),
    description character varying(50),
    source_map character varying(10),
    comments character varying(50),
    shape_length double precision,
    new_type text,
    geom public.geometry
);


CREATE TABLE sources.ontario_pz_mod (
    unit_name character varying(50),
    strat_name text,
    age character varying(25),
    orig_lithology character varying(320),
    descript_full character varying(320),
    late_id integer,
    early_id integer,
    geom public.geometry,
    gid integer NOT NULL
);


CREATE SEQUENCE sources.ontario_pz_mod_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.ontario_pz_mod_gid_seq OWNED BY sources.ontario_pz_mod.gid;


CREATE TABLE sources.ontario_pz_points (
    gid integer NOT NULL,
    area double precision,
    perimeter double precision,
    paleo_point_ integer,
    paleo_point_id integer,
    feature_code character varying(15),
    description character varying(25),
    source_map character varying(10),
    comments character varying(50),
    f_polygonid integer,
    f_scale double precision,
    f_angle double precision,
    geom public.geometry(Point,4269)
);


CREATE TABLE sources.oregon (
    gid integer NOT NULL,
    ref_id_cod character varying(254),
    map_unit_l character varying(254),
    map_unit_n character varying(254),
    g_mrg_u_l character varying(254),
    geo_genl_u character varying(254),
    age_name character varying(254),
    terrane_gr character varying(254),
    formation character varying(254),
    member character varying(254),
    unit character varying(254),
    g_rock_typ character varying(254),
    lith_m_u_l character varying(254),
    lith_gen_u character varying(254),
    lth_rk_typ character varying(254),
    layering character varying(254),
    cr_grn_siz character varying(254),
    getec_prop character varying(254),
    gn_lith_ty character varying(254),
    arcjoinkey character varying(254),
    mapunitpk numeric,
    shape_leng numeric,
    shape_area numeric,
    datasource numeric(10,0),
    idconf numeric(10,0),
    geom public.geometry(MultiPolygon,4326),
    thickness character varying(55),
    lith_mods text,
    early_id integer,
    late_id integer,
    strat_name text
);


CREATE TABLE sources.oregon_faults (
    gid integer NOT NULL,
    imp_ftype character varying(254),
    label character varying(254),
    datasource numeric(10,0),
    notes character varying(254),
    fgdcrefno character varying(254),
    fc_id numeric(10,0),
    fltpl_dir character varying(254),
    fltpl_deg character varying(254),
    idconf numeric(10,0),
    locconf numeric(10,0),
    locconfmet numeric,
    shape_leng numeric,
    geom public.geometry(MultiLineString,4326),
    dir character varying(254),
    use_label character varying(254)
);


CREATE SEQUENCE sources.oregon_faults_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.oregon_faults_gid_seq OWNED BY sources.oregon_faults.gid;


CREATE SEQUENCE sources.oregon_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.oregon_gid_seq OWNED BY sources.oregon.gid;


CREATE TABLE sources.pakistan_westcentral (
    gid integer NOT NULL,
    objectid numeric(10,0),
    unit character varying(20),
    name character varying(254),
    age character varying(254),
    shape_leng numeric,
    shape_area numeric,
    geom public.geometry(MultiPolygon,4326),
    description text,
    early_id integer,
    late_id integer
);


CREATE TABLE sources.pakistan_westcentral_lines (
    gid integer NOT NULL,
    objectid numeric(10,0),
    type character varying(100),
    shape_leng numeric,
    geom public.geometry(MultiLineString,4326),
    descriptio text,
    new_type text,
    new_direction text
);


CREATE SEQUENCE sources.paleo_fault_arc_objectid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.paleo_fault_arc_objectid_seq OWNED BY sources.ontario_pz_lines.gid;


CREATE SEQUENCE sources.paleo_point_point_objectid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.paleo_point_point_objectid_seq OWNED BY sources.ontario_pz_points.gid;


CREATE SEQUENCE sources.paleo_poly_polygon_objectid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.paleo_poly_polygon_objectid_seq OWNED BY sources.ontario_pz.gid;


CREATE TABLE sources.va_middletown_points (
    gid integer NOT NULL,
    dip numeric(4,0),
    strike numeric(9,0),
    type character varying(12),
    geom public.geometry,
    point_type text,
    dip_dir integer,
    descrip text
);


CREATE SEQUENCE sources.points_ogc_fid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.points_ogc_fid_seq OWNED BY sources.va_middletown_points.gid;


CREATE SEQUENCE sources.poncafaults_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.poncafaults_gid_seq OWNED BY sources.ar_ponca_lines.gid;


CREATE SEQUENCE sources.poncageo_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.poncageo_gid_seq OWNED BY sources.ar_ponca.gid;


CREATE SEQUENCE sources.prescottgeology_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.prescottgeology_gid_seq OWNED BY sources.az_prescott.gid;


CREATE SEQUENCE sources.prescottlines_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.prescottlines_gid_seq OWNED BY sources.az_prescott_lines.gid;


CREATE TABLE sources.ut_price (
    gid integer NOT NULL,
    area numeric,
    perimeter numeric,
    geology_ integer,
    geology_id integer,
    unitsymbol character varying(15),
    unitname character varying(80),
    age character varying(50),
    notes character varying(50),
    geom public.geometry(MultiPolygon,4326),
    lithology text,
    late_id integer,
    early_id integer
);


CREATE SEQUENCE sources.price_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.price_gid_seq OWNED BY sources.ut_price.gid;


CREATE TABLE sources.ut_provo_lines (
    gid integer NOT NULL,
    geologicli smallint,
    layer character varying(15),
    feature character varying(100),
    type character varying(30),
    subtype character varying(50),
    modifier character varying(50),
    shape_leng numeric,
    ruleid integer,
    layerint smallint,
    layer_2 character varying(10),
    shape_le_2 numeric,
    ruleid_2 integer,
    geom public.geometry(MultiLineString,4326),
    new_type text,
    new_direction text
);


CREATE SEQUENCE sources.provo_lines_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.provo_lines_gid_seq OWNED BY sources.ut_provo_lines.gid;


CREATE TABLE sources.ut_provo (
    gid integer NOT NULL,
    shape_leng numeric,
    shape_area numeric,
    ruleid integer,
    unitrank smallint,
    unitsymbol character varying(15),
    unitname character varying(125),
    geom public.geometry(MultiPolygon,4326),
    description text,
    age text,
    early_id integer,
    late_id integer
);


CREATE SEQUENCE sources.provoutahgeology_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.provoutahgeology_gid_seq OWNED BY sources.ut_provo.gid;


CREATE TABLE sources.puerto_rico (
    gid integer NOT NULL,
    area double precision,
    perimeter double precision,
    pr_geology integer,
    pr_geolo_1 integer,
    fmatn character varying(5),
    colr double precision,
    colr2 double precision,
    shade double precision,
    prov double precision,
    geom public.geometry(MultiPolygon,4326),
    name character varying(255),
    age character varying(255),
    descrip text,
    early_id integer,
    late_id integer
);


CREATE SEQUENCE sources.puerto_rico_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.puerto_rico_gid_seq OWNED BY sources.puerto_rico.gid;


CREATE TABLE sources.puerto_rico_lines (
    gid integer NOT NULL,
    length double precision,
    lntype smallint,
    geom public.geometry(MultiLineString,4326),
    type text,
    new_type text,
    new_direction text
);


CREATE SEQUENCE sources.puertorico_nfaults_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.puertorico_nfaults_gid_seq OWNED BY sources.puerto_rico_lines.gid;


CREATE TABLE sources.ut_richfield_lines (
    gid integer NOT NULL,
    fnode_ integer,
    tnode_ integer,
    lpoly_ integer,
    rpoly_ integer,
    length numeric,
    geology_ integer,
    geology_id integer,
    type character varying(25),
    subtype character varying(25),
    modifier character varying(30),
    notes character varying(30),
    geom public.geometry(MultiLineString,4326),
    new_type text,
    new_direction text
);


CREATE SEQUENCE sources.richfield_faults_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.richfield_faults_gid_seq OWNED BY sources.ut_richfield_lines.gid;


CREATE TABLE sources.ut_richfield (
    gid integer NOT NULL,
    area numeric,
    perimeter numeric,
    geology_ integer,
    geology_id integer,
    unitsymbol character varying(15),
    unitname character varying(120),
    age character varying(50),
    notes character varying(50),
    geom public.geometry(MultiPolygon,4326),
    description text,
    early_id integer,
    late_id integer,
    comments text
);


CREATE SEQUENCE sources.richfieldutgeology_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.richfieldutgeology_gid_seq OWNED BY sources.ut_richfield.gid;


CREATE TABLE sources.wy_rock_springs (
    gid integer NOT NULL,
    objectid integer,
    unit character varying(8),
    g_sym character varying(8),
    g_nam character varying(125),
    shape_leng numeric,
    shape_area numeric,
    geom public.geometry(MultiPolygon,4326),
    name text,
    age text,
    description text,
    comments text,
    early_id integer,
    late_id integer
);


CREATE SEQUENCE sources.rock_springs_geo_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.rock_springs_geo_gid_seq OWNED BY sources.wy_rock_springs.gid;


CREATE TABLE sources.wy_rock_springs_lines (
    gid integer NOT NULL,
    objectid integer,
    name character varying(50),
    type character varying(30),
    shape_leng numeric,
    geom public.geometry(MultiLineString,4326),
    new_type text,
    new_direction text
);


CREATE SEQUENCE sources.rock_springs_lines_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.rock_springs_lines_gid_seq OWNED BY sources.wy_rock_springs_lines.gid;


CREATE TABLE sources.wy_rock_springs_points (
    gid integer NOT NULL,
    objectid integer,
    type character varying(50),
    dip integer,
    strike integer,
    geom public.geometry(Point,4326),
    point_type text,
    certainty text,
    comments text,
    new_strike integer
);


CREATE SEQUENCE sources.rock_springs_points_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.rock_springs_points_gid_seq OWNED BY sources.wy_rock_springs_points.gid;


CREATE TABLE sources.rockies (
    gid integer NOT NULL,
    area numeric,
    perimeter numeric,
    nr_geo_ numeric(10,0),
    nr_geo_id numeric(10,0),
    poly_id numeric(10,0),
    mu_id numeric,
    igmu_id numeric,
    map_tile character varying(50),
    ig_code smallint,
    source_pds smallint,
    rowid_ integer,
    source numeric(10,0),
    originator character varying(250),
    date character varying(30),
    title character varying(250),
    title_cont character varying(200),
    pub character varying(150),
    unpub_hist character varying(90),
    scale_base numeric,
    scale_pub numeric,
    url character varying(170),
    rowid1 integer,
    mu_id_1 numeric,
    name_majr1 character varying(254),
    name_majr2 character varying(254),
    name_minor character varying(254),
    name_other character varying(140),
    lname_dom character varying(70),
    lname_1 character varying(60),
    lname_2 character varying(70),
    lname_3 character varying(55),
    lname_4 character varying(40),
    lname_5 character varying(20),
    rowid1_1 integer,
    mu_id_12 numeric,
    lab_asc character varying(15),
    lab_gaf character varying(15),
    name character varying(250),
    strat_age character varying(45),
    age character varying(40),
    unit_type character varying(2),
    source_1 smallint,
    lab_asc_or character varying(10),
    lab_gaf_or character varying(10),
    name_or character varying(250),
    minage_or character varying(25),
    maxage_or character varying(25),
    age_or character varying(40),
    source_or smallint,
    rowid1_12 integer,
    mu_id_1_13 numeric,
    name_major character varying(240),
    name_min_1 character varying(55),
    name_oth_1 character varying(90),
    uname_dom character varying(75),
    uname_1 character varying(25),
    uname_2 character varying(40),
    uname_3 character varying(40),
    uname_4 character varying(75),
    rowid1__13 integer,
    igmu_id_1 numeric,
    ig_label character varying(10),
    ig_name character varying(125),
    ig_style character varying(35),
    ig_lith character varying(175),
    ig_feature character varying(200),
    ig_minage character varying(20),
    ig_maxage character varying(20),
    ig_age character varying(35),
    geom public.geometry(MultiPolygon,4326),
    early_id integer,
    late_id integer,
    lith_name text
);


CREATE SEQUENCE sources.rockies_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.rockies_gid_seq OWNED BY sources.rockies.gid;


CREATE TABLE sources.rockies_lines (
    gid integer NOT NULL,
    fnode_ numeric(10,0),
    tnode_ numeric(10,0),
    lpoly_ numeric(10,0),
    rpoly_ numeric(10,0),
    length numeric,
    nr_geo_ numeric(10,0),
    nr_geo_id numeric(10,0),
    arc_id numeric(10,0),
    linecode integer,
    mu_id numeric,
    str_name character varying(30),
    igmu_id numeric,
    map_tile character varying(50),
    ig_code smallint,
    source_arc smallint,
    source_lds smallint,
    rowid_ integer,
    linecode_1 integer,
    line_type1 character varying(30),
    line_type2 character varying(50),
    line_type3 character varying(90),
    geom public.geometry(MultiLineString,4326),
    new_type character varying(50),
    new_direction character varying(50)
);


CREATE SEQUENCE sources.rockies_lines_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.rockies_lines_gid_seq OWNED BY sources.rockies_lines.gid;


CREATE SEQUENCE sources.rockport_l2_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.rockport_l2_gid_seq OWNED BY sources.ma_glouster_lines.gid;


CREATE TABLE sources.rockymountainnationalparkgeology (
    gid integer NOT NULL,
    objectid numeric(10,0),
    fuid numeric(10,0),
    glg_sym character varying(12),
    src_sym character varying(12),
    sort_no numeric,
    notes character varying(254),
    lbl character varying(60),
    gmap_id numeric(10,0),
    shape_leng numeric,
    shape_area numeric,
    objectid_1 integer,
    glg_sym_1 character varying(12),
    glg_name character varying(100),
    age character varying(100),
    mj_lith character varying(254),
    geom public.geometry(MultiPolygon,4326),
    description text,
    early_id integer,
    late_id integer
);


CREATE SEQUENCE sources.rockymountainnationalparkgeology_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.rockymountainnationalparkgeology_gid_seq OWNED BY sources.rockymountainnationalparkgeology.gid;


CREATE TABLE sources.rockymtn_np_lines (
    gid integer NOT NULL,
    objectid numeric(10,0),
    fuid numeric(10,0),
    name character varying(60),
    label character varying(60),
    shape_leng numeric,
    type character varying(254),
    positionalaccuracy character varying(254),
    subtype character varying(254),
    plunge text,
    age text,
    majorlith text,
    new_type text,
    new_direction text,
    geom public.geometry(MultiLineString)
);


CREATE SEQUENCE sources.rockymtn_faults_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.rockymtn_faults_gid_seq OWNED BY sources.rockymtn_np_lines.gid;


CREATE SEQUENCE sources.rondinia_dikes_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.rondinia_dikes_gid_seq OWNED BY sources.brazil_lines.gid;


CREATE TABLE sources.saipan_lines (
    gid integer NOT NULL,
    objectid numeric(10,0),
    name character varying(60),
    notes character varying(254),
    label character varying(60),
    gmap_id numeric(10,0),
    shape_leng numeric,
    positionalaccuracy character varying(254),
    subtype character varying(254),
    type character varying(254),
    geom public.geometry(MultiLineString,4326),
    new_type text,
    new_direction text
);


CREATE SEQUENCE sources.saipan_lines_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.saipan_lines_gid_seq OWNED BY sources.saipan_lines.gid;


CREATE SEQUENCE sources.san_diego_ca_lines_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.san_diego_ca_lines_gid_seq OWNED BY sources.ca_san_diego_lines.gid;


CREATE SEQUENCE sources.san_diego_ca_points_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.san_diego_ca_points_gid_seq OWNED BY sources.ca_san_diego_points.gid;


CREATE TABLE sources.san_salvador (
    gid integer NOT NULL,
    id numeric(10,0),
    geo_id character varying(6),
    unit text,
    area numeric,
    perimeter numeric,
    acres numeric,
    text character varying(25),
    age_ybp character varying(254),
    geom public.geometry(MultiPolygon,4326),
    description text,
    age text,
    comments text,
    early_id integer,
    late_id integer,
    strat_name text
);


CREATE SEQUENCE sources.san_salvador_geo_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.san_salvador_geo_gid_seq OWNED BY sources.san_salvador.gid;


CREATE SEQUENCE sources.sanberno_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.sanberno_gid_seq OWNED BY sources.ca_sanberno.gid;


CREATE SEQUENCE sources.sanberno_lines_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.sanberno_lines_gid_seq OWNED BY sources.ca_sanberno_lines.gid;


CREATE SEQUENCE sources.sanjosegeology_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.sanjosegeology_gid_seq OWNED BY sources.ca_sanjose.gid;


CREATE SEQUENCE sources.sanjoselines_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.sanjoselines_gid_seq OWNED BY sources.ca_sanjose_lines.gid;


CREATE TABLE sources.wa_sanjuan_island_lines (
    gid integer NOT NULL,
    fname character varying(60),
    notes character varying(254),
    gmap_id integer,
    help_id character varying(12),
    geom public.geometry(MultiLineString,4326),
    type text,
    subtype text,
    accuracy text,
    plunge text,
    new_type text,
    new_direction text
);


CREATE SEQUENCE sources.sanjuanfaults_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.sanjuanfaults_gid_seq OWNED BY sources.wa_sanjuan_island_lines.gid;


CREATE TABLE sources.wa_sanjuan_island (
    gid integer NOT NULL,
    fuid integer,
    glg_sym character varying(12),
    src_sym character varying(12),
    sort_no double precision,
    notes character varying(254),
    gmap_id integer,
    help_id character varying(12),
    shape_leng numeric,
    shape_area numeric,
    geom public.geometry(MultiPolygon,4326),
    name text,
    age text,
    description text,
    early_id integer,
    late_id integer,
    strat_name text
);


CREATE SEQUENCE sources.sanjuanislandgeology_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.sanjuanislandgeology_gid_seq OWNED BY sources.wa_sanjuan_island.gid;


CREATE SEQUENCE sources.sanmateofaults_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.sanmateofaults_gid_seq OWNED BY sources.ca_sanmateo_lines.gid;


CREATE SEQUENCE sources.sanmateogeology_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.sanmateogeology_gid_seq OWNED BY sources.ca_sanmateo.gid;


CREATE SEQUENCE sources.santacruz_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.santacruz_gid_seq OWNED BY sources.ca_santacruz.gid;


CREATE TABLE sources.saskatchewan (
    gid integer NOT NULL,
    rock_code character varying(14),
    eon character varying(21),
    era character varying(25),
    period character varying(12),
    group_ character varying(25),
    formation character varying(65),
    member character varying(25),
    rock_type character varying(150),
    area numeric,
    len numeric,
    geom public.geometry(MultiPolygon,4326),
    early_id integer,
    late_id integer,
    lithostrat character varying(150),
    name text,
    age text
);


CREATE TABLE sources.saskatchewan_dikes (
    gid integer NOT NULL,
    id numeric,
    rock_code character varying(6),
    rocktype character varying(22),
    code character varying(5),
    area numeric,
    len numeric,
    geom public.geometry(MultiLineString,4326)
);


CREATE SEQUENCE sources.saskatchewan_dikes_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.saskatchewan_dikes_gid_seq OWNED BY sources.saskatchewan_dikes.gid;


CREATE SEQUENCE sources.saskatchewan_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.saskatchewan_gid_seq OWNED BY sources.saskatchewan.gid;


CREATE TABLE sources.wi_sauk_lines (
    gid integer NOT NULL,
    sk_geolsym numeric(10,0),
    sk_geols_1 numeric(10,0),
    symbol character varying(35),
    geom public.geometry(MultiLineString,4326),
    new_type character varying(35),
    new_direction character varying(35)
);


CREATE SEQUENCE sources.sauk_lines_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.sauk_lines_gid_seq OWNED BY sources.wi_sauk_lines.gid;


CREATE TABLE sources.scale_groups_tiny (
    source_id integer,
    group_id bigint
);


CREATE SEQUENCE sources.scruz_lines_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.scruz_lines_gid_seq OWNED BY sources.ca_santacruz_lines.gid;


CREATE TABLE sources.wi_southeast (
    gid integer NOT NULL,
    area numeric,
    perimeter numeric,
    se_br_geol numeric(10,0),
    se_br_ge_1 numeric(10,0),
    uname22 character varying(254),
    shape_leng numeric,
    shape_area numeric,
    geom public.geometry(MultiPolygon,4326),
    name text,
    age text,
    description text,
    early_id integer,
    late_id integer
);


CREATE SEQUENCE sources.se_wisconsin_geo_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.se_wisconsin_geo_gid_seq OWNED BY sources.wi_southeast.gid;


CREATE TABLE sources.wi_southeast_lines (
    gid integer NOT NULL,
    fnode_ numeric(10,0),
    tnode_ numeric(10,0),
    lpoly_ numeric(10,0),
    rpoly_ numeric(10,0),
    length numeric,
    se_br_geol numeric(10,0),
    se_br_ge_1 numeric(10,0),
    uname character varying(254),
    edit_note character varying(254),
    shape_leng numeric,
    geom public.geometry(MultiLineString,4326),
    new_type text,
    new_direction text
);


CREATE SEQUENCE sources.se_wisconsin_lines_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.se_wisconsin_lines_gid_seq OWNED BY sources.wi_southeast_lines.gid;


CREATE TABLE sources.ut_seepridge_lines (
    gid integer NOT NULL,
    shape_leng numeric,
    feature character varying(75),
    type character varying(50),
    subtype character varying(50),
    modifier character varying(50),
    name character varying(75),
    notes character varying(50),
    geom public.geometry(MultiLineString,4326),
    new_type text,
    new_direction text
);


CREATE SEQUENCE sources.seepridge_lines_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.seepridge_lines_gid_seq OWNED BY sources.ut_seepridge_lines.gid;


CREATE TABLE sources.wi_sheboygan (
    gid integer NOT NULL,
    shape_leng numeric,
    shape_area numeric,
    unitcode character varying(25),
    unitid character varying(25),
    name character varying(254),
    desc_ character varying(254),
    agedisplay character varying(128),
    geom public.geometry(MultiPolygon,4326),
    early_id integer,
    late_id integer
);


CREATE SEQUENCE sources.sheboygan_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.sheboygan_gid_seq OWNED BY sources.wi_sheboygan.gid;


CREATE TABLE sources.wy_sheridan (
    gid integer NOT NULL,
    objectid integer,
    area double precision,
    perimeter double precision,
    sheridan_b integer,
    sheridan_1 integer,
    sher4_ integer,
    sher4_id integer,
    unit character varying(7),
    shape_leng numeric,
    shape_area numeric,
    geom public.geometry(MultiPolygon,4326),
    age text,
    name text,
    strat_name text,
    hierarchy text,
    description text,
    early_id integer,
    late_id integer
);


CREATE SEQUENCE sources.sheridan_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.sheridan_gid_seq OWNED BY sources.wy_sheridan.gid;


CREATE TABLE sources.wy_sheridan_lines (
    gid integer NOT NULL,
    objectid integer,
    fnode_ numeric,
    tnode_ numeric,
    lpoly_ numeric,
    rpoly_ numeric,
    length numeric,
    sfaultdd2_ numeric,
    sfaultdd21 numeric,
    faults character varying(10),
    shape_leng numeric,
    geom public.geometry(MultiLineString,4326),
    new_type text
);


CREATE SEQUENCE sources.sheridan_lines_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.sheridan_lines_gid_seq OWNED BY sources.wy_sheridan_lines.gid;


CREATE TABLE sources.ut_smokymtns_lines (
    gid integer NOT NULL,
    length numeric,
    type character varying(25),
    subtype character varying(25),
    modifier character varying(30),
    name character varying(100),
    geom public.geometry(MultiLineString,4326),
    new_type text,
    new_direction text
);


CREATE SEQUENCE sources.smkymtns_faults_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.smkymtns_faults_gid_seq OWNED BY sources.ut_smokymtns_lines.gid;


CREATE TABLE sources.smokies (
    gid integer NOT NULL,
    objectid integer,
    area double precision,
    perimeter double precision,
    bedrk_27u_ integer,
    bedrk_27u1 integer,
    shape_leng numeric,
    shape_area numeric,
    map_unit character varying(10),
    geom public.geometry(MultiPolygon,4326),
    descrip text,
    name character varying(100),
    age character varying(100),
    early_id integer,
    late_id integer,
    strat_name text,
    hierarchy text
);


CREATE SEQUENCE sources.smokies_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.smokies_gid_seq OWNED BY sources.smokies.gid;


CREATE TABLE sources.smokies_lines (
    gid integer NOT NULL,
    length double precision,
    type character varying(50),
    shape_leng numeric,
    geom public.geometry(MultiLineString,4326),
    new_type text,
    new_direction text
);


CREATE SEQUENCE sources.smokymountainsnationalpark_lines_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.smokymountainsnationalpark_lines_gid_seq OWNED BY sources.smokies_lines.gid;


CREATE TABLE sources.ut_smokymtns (
    gid integer NOT NULL,
    area numeric,
    perimeter numeric,
    unitsymbol character varying(15),
    unitname text,
    age text,
    notes character varying(50),
    geom public.geometry(MultiPolygon,4326),
    description text,
    early_id integer,
    late_id integer
);


CREATE SEQUENCE sources.smokymtnsutgeology_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.smokymtnsutgeology_gid_seq OWNED BY sources.ut_smokymtns.gid;


CREATE TABLE sources.so_africa (
    gid integer NOT NULL,
    uq_geol numeric(10,0),
    uq_sacs_no integer,
    lithstrat character varying(50),
    lithrank character varying(12),
    parent1 character varying(50),
    rank1 character varying(12),
    parent2 character varying(50),
    rank2 character varying(12),
    parent3 character varying(50),
    rank3 character varying(12),
    chronstrat character varying(50),
    chronrank character varying(5),
    litho_grp smallint,
    descriptio character varying(254),
    color_code character varying(4),
    hatch smallint,
    hatcht character varying(4),
    text_label character varying(9),
    shape_area numeric,
    shape_len numeric,
    geom public.geometry(MultiPolygon,4326),
    new_age character varying(100),
    early_id integer,
    late_id integer,
    new_age2 character varying(100),
    combined_name character varying(120),
    age character varying(100),
    strat_name character varying(120)
);


CREATE SEQUENCE sources.so_africa_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.so_africa_gid_seq OWNED BY sources.so_africa.gid;


CREATE TABLE sources.so_africa_lines (
    gid integer NOT NULL,
    lntype numeric(10,0),
    lntypet character varying(5),
    shape_len numeric,
    descriptio character varying(254),
    geom public.geometry(MultiLineString,4326),
    name character varying(50)
);


CREATE SEQUENCE sources.so_africa_lines_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.so_africa_lines_gid_seq OWNED BY sources.so_africa_lines.gid;


CREATE SEQUENCE sources."sources.md_keedysville_line_gid_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources."sources.md_keedysville_line_gid_seq" OWNED BY sources.md_keedysville_line.gid;


CREATE SEQUENCE sources.southsanfrangeology_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.southsanfrangeology_gid_seq OWNED BY sources.ca_southsanfran.gid;


CREATE SEQUENCE sources.southsanfranlines_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.southsanfranlines_gid_seq OWNED BY sources.ca_southsanfran_lines.gid;


CREATE TABLE sources.spain (
    gid integer NOT NULL,
    area double precision,
    perimeter double precision,
    geopb_ double precision,
    geopb_id double precision,
    id integer,
    codigofaci smallint,
    id_unidadc integer,
    siglas character varying(6),
    dominio character varying(50),
    litogen_cl smallint,
    dlo character varying(200),
    litologia character varying(254),
    simb_lito character varying(4),
    eon_era_spanish character varying(50),
    subera_spanish character varying(50),
    sistema character varying(50),
    serie character varying(50),
    piso character varying(50),
    litofacies character varying(30),
    trama_c character varying(4),
    color integer,
    geom public.geometry(MultiPolygon,4326),
    domain text,
    subera text,
    description text,
    lithology text,
    eon_era text,
    period text,
    epoch text,
    stage text,
    lithofacies text,
    early_id integer,
    late_id integer,
    age text
);


CREATE TABLE sources.spain_lines (
    gid integer NOT NULL,
    fnode_ double precision,
    tnode_ double precision,
    lpoly_ double precision,
    rpoly_ double precision,
    length double precision,
    geopb_ double precision,
    geopb_id double precision,
    id integer,
    tipo character varying(100),
    simbolo character varying(8),
    geom public.geometry(MultiLineString,4326),
    type text,
    new_type text,
    new_direction text
);


CREATE SEQUENCE sources.spainlines1_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.spainlines1_gid_seq OWNED BY sources.spain_lines.gid;


CREATE SEQUENCE sources.spainpbgeology_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.spainpbgeology_gid_seq OWNED BY sources.spain.gid;


CREATE TABLE sources.texas_mexico_lines (
    gid integer NOT NULL,
    fnode_ integer,
    tnode_ integer,
    lpoly_ integer,
    rpoly_ integer,
    length double precision,
    mextexflt_ integer,
    mextexflt1 integer,
    type character varying(100),
    geom public.geometry(MultiLineString,4326),
    new_type text,
    new_direction text
);


CREATE SEQUENCE sources.stexasmexico_geolines_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.stexasmexico_geolines_gid_seq OWNED BY sources.texas_mexico_lines.gid;


CREATE TABLE sources.texas_mexico (
    gid integer NOT NULL,
    area double precision,
    perimeter double precision,
    mextexgeo_ integer,
    mextexgeo1 integer,
    symbol character varying(20),
    source character varying(30),
    name text,
    age character varying(50),
    geom public.geometry(MultiPolygon,4326),
    description text,
    early_id integer,
    late_id integer
);


CREATE SEQUENCE sources.stexasmexicogeology_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.stexasmexicogeology_gid_seq OWNED BY sources.texas_mexico.gid;


CREATE TABLE sources.sweden (
    gid integer NOT NULL,
    brg integer,
    litologi character varying(254),
    lithology character varying(254),
    tekt integer,
    tekt_enhet character varying(254),
    tect_unit character varying(254),
    tekt_under integer,
    underenhet character varying(254),
    subunit character varying(254),
    symbol character varying(10),
    legend character varying(254),
    legend_en character varying(254),
    c smallint,
    m smallint,
    y smallint,
    k smallint,
    etikett smallint,
    objectid integer,
    shape_leng numeric,
    shape_area numeric,
    geom public.geometry(MultiPolygon,4326),
    age text,
    early_id integer,
    late_id integer
);


CREATE TABLE sources.sweden_lines (
    gid integer NOT NULL,
    defz integer,
    def_zon character varying(254),
    def_zone character varying(254),
    symbol character varying(10),
    legend character varying(254),
    legend_en character varying(254),
    objectid integer,
    shape_leng numeric,
    geom public.geometry(MultiLineString,4326),
    litologi text,
    lithology text,
    brg integer,
    tekt integer,
    tekt_enhet text,
    tect_unit text,
    tekt_under integer,
    underenhet text,
    subunit text,
    c smallint,
    m smallint,
    y smallint,
    k smallint,
    etikett smallint,
    new_type text,
    new_direction text
);


CREATE SEQUENCE sources.sweden_faults_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.sweden_faults_gid_seq OWNED BY sources.sweden_lines.gid;


CREATE SEQUENCE sources.swedengeology2_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.swedengeology2_gid_seq OWNED BY sources.sweden.gid;


CREATE TABLE sources.switzerland (
    gid integer NOT NULL,
    area numeric,
    perimeter numeric,
    fl_id numeric,
    l_id smallint,
    c_id smallint,
    t1_id smallint,
    t2_id smallint,
    h1_id smallint,
    h2_id smallint,
    h3_id smallint,
    geol_f character varying(5),
    leg_geol character varying(254),
    litho character varying(254),
    periode character varying(254),
    epoche character varying(254),
    stufe character varying(254),
    tecto_f character varying(5),
    leg_tek_1 character varying(254),
    leg_tek_2 character varying(254),
    leg_tek_3 character varying(254),
    aquifer character varying(254),
    hydrogeol character varying(254),
    produktiv character varying(254),
    id_lith numeric,
    lith_pet character varying(254),
    id_genese numeric,
    genese character varying(254),
    id_gestein numeric,
    gesteinkl character varying(254),
    deckschich character varying(150),
    periods_en character varying(254),
    litho_engl character varying(254),
    epochs_eng character varying(254),
    rocktype_e character varying(254),
    geom public.geometry(MultiPolygonZM,4326),
    early_id integer,
    late_id integer,
    use_age character varying(254)
);


CREATE TABLE sources.switzerland_lines (
    gid integer NOT NULL,
    length numeric,
    hydro numeric,
    type character varying(254),
    id smallint,
    english_type character varying(254),
    geom public.geometry(MultiLineString,4326),
    new_type text,
    new_direction text
);


CREATE SEQUENCE sources.switzerland_faults_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.switzerland_faults_gid_seq OWNED BY sources.switzerland_lines.gid;


CREATE SEQUENCE sources.switzerland_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.switzerland_gid_seq OWNED BY sources.switzerland.gid;


CREATE SEQUENCE sources.table_name_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.table_name_gid_seq OWNED BY sources.ca_oceanside.gid;


CREATE TABLE sources.tanzania_oldonyo (
    gid integer NOT NULL,
    id double precision,
    strat_code double precision,
    unit_symbo character varying(12),
    unit_name text,
    lithology text,
    age character varying(30),
    source character varying(30),
    geom public.geometry(MultiPolygonZM,4326),
    strat_name text,
    hierarchy text,
    description text,
    early_id integer,
    late_id integer
);


CREATE SEQUENCE sources.tanzania_geo2_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.tanzania_geo2_gid_seq OWNED BY sources.tanzania_oldonyo.gid;


CREATE TABLE sources.tanzania_oldonyo_lines (
    gid integer NOT NULL,
    id double precision,
    line_code double precision,
    descriptio text,
    age text,
    side_down text,
    data_sourc text,
    note text,
    geom public.geometry(MultiLineStringZM,4326),
    unit_symbo text,
    new_type text
);


CREATE SEQUENCE sources.tanzania_structures_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.tanzania_structures_gid_seq OWNED BY sources.tanzania_oldonyo_lines.gid;


CREATE TABLE sources.world_lines (
    gid integer NOT NULL,
    faultno integer,
    id2 integer,
    fclass character varying(2),
    fdisp character varying(2),
    wrongpolar character varying(1),
    agera character varying(3),
    agequ character varying(1),
    use character varying(1),
    name character varying(40),
    signif character varying(30),
    fault_id numeric(10,0),
    faultno_id double precision,
    symbol numeric(10,0),
    feature_id integer,
    id2_1 integer,
    ftclass character varying(2),
    ftdisp character varying(2),
    wrongpol_1 character varying(1),
    agera_1 character varying(3),
    agequ_1 character varying(1),
    use_1 character varying(1),
    name_1 character varying(40),
    signif_1 character varying(30),
    fltantaz_i numeric(10,0),
    fltant_id numeric(10,0),
    ftclass_1 character varying(2),
    longdesc character varying(30),
    geom public.geometry(MultiLineString,4326),
    new_direction character varying(40),
    new_type character varying(40)
);


CREATE SEQUENCE sources.tiny_lines_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.tiny_lines_gid_seq OWNED BY sources.world_lines.gid;


CREATE SEQUENCE sources.tularosafaults_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.tularosafaults_gid_seq OWNED BY sources.nm_tularosa_lines.gid;


CREATE SEQUENCE sources.tularosageo_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.tularosageo_gid_seq OWNED BY sources.nm_tularosa.gid;


CREATE TABLE sources.ut_tulevalley_lines (
    gid integer NOT NULL,
    fnode_ integer,
    tnode_ integer,
    lpoly_ integer,
    rpoly_ integer,
    length numeric,
    geology_ integer,
    geology_id integer,
    type character varying(25),
    subtype character varying(25),
    modifier character varying(30),
    geom public.geometry(MultiLineString,4326),
    new_type text,
    new_direction text
);


CREATE SEQUENCE sources.tulevalley_faults_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.tulevalley_faults_gid_seq OWNED BY sources.ut_tulevalley_lines.gid;


CREATE TABLE sources.ut_tulevalley (
    gid integer NOT NULL,
    area numeric,
    perimeter numeric,
    geology_ integer,
    geology_id integer,
    unitsymbol character varying(15),
    unitname character varying(100),
    age character varying(50),
    notes character varying(50),
    geom public.geometry(MultiPolygon,4326),
    description text,
    early_id integer,
    late_id integer
);


CREATE SEQUENCE sources.tulevalleyutgeology_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.tulevalleyutgeology_gid_seq OWNED BY sources.ut_tulevalley.gid;


CREATE TABLE sources.twincitiesmn_lines (
    gid integer NOT NULL,
    fnode_ integer,
    tnode_ integer,
    lpoly_ integer,
    rpoly_ integer,
    length numeric,
    tenco_pg_ integer,
    tenco_pg_i integer,
    type_code character varying(2),
    gcm_code character varying(3),
    geoc_src character varying(5),
    geoc_date integer,
    mgscode integer,
    type character varying(90),
    geom public.geometry(MultiLineString,4326),
    description text,
    polarity text,
    new_type text,
    new_direction text
);


CREATE SEQUENCE sources.twincities_faults_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.twincities_faults_gid_seq OWNED BY sources.twincitiesmn_lines.gid;


CREATE TABLE sources.twincitiesmngeology (
    gid integer NOT NULL,
    area numeric,
    perimeter numeric,
    type character varying(2),
    gcm_code character varying(3),
    geoc_src character varying(5),
    geoc_date integer,
    maplabel character varying(6),
    unitname text,
    terrane character varying(90),
    era character varying(50),
    subdivisio character varying(50),
    geom public.geometry(MultiPolygon,4326),
    age text,
    description text,
    early_id integer,
    late_id integer
);


CREATE SEQUENCE sources.twincitiesmngeology_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.twincitiesmngeology_gid_seq OWNED BY sources.twincitiesmngeology.gid;


CREATE TABLE sources.tx_bexar (
    gid integer NOT NULL,
    unit_order bigint,
    geo_unit_1 character varying(25),
    geo_unit_2 character varying(50),
    groupnm character varying(50),
    formation character varying(75),
    member character varying(254),
    lithology character varying(254),
    hydro_unit character varying(100),
    hydrostrat character varying(100),
    thickness character varying(20),
    hydro_func character varying(100),
    porosity character varying(75),
    fieldid character varying(254),
    shape_leng numeric,
    shape_area numeric,
    geom public.geometry(MultiPolygon,4326),
    early_id integer,
    late_id integer,
    age text,
    strat_name text,
    use_name text
);


CREATE SEQUENCE sources.tx_bexar_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.tx_bexar_gid_seq OWNED BY sources.tx_bexar.gid;


CREATE TABLE sources.tx_bexar_lines (
    gid integer NOT NULL,
    type character varying(25),
    shape_leng numeric,
    geom public.geometry(MultiLineString,4326),
    new_type text
);


CREATE SEQUENCE sources.tx_bexar_lines_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.tx_bexar_lines_gid_seq OWNED BY sources.tx_bexar_lines.gid;


CREATE TABLE sources.tx_blanco (
    gid integer NOT NULL,
    objectid integer,
    geo_unit_l character varying(25),
    geo_unit_d character varying(50),
    shape_leng numeric,
    shape_area numeric,
    geom public.geometry(MultiPolygon,4326),
    name text,
    strat_name text,
    descrip text,
    age text,
    early_id integer,
    late_id integer,
    hierarchy text,
    comments text,
    lith text
);


CREATE SEQUENCE sources.tx_blanco_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.tx_blanco_gid_seq OWNED BY sources.tx_blanco.gid;


CREATE TABLE sources.tx_blanco_lines (
    gid integer NOT NULL,
    type character varying(25),
    shape_leng numeric,
    geom public.geometry(MultiLineString,4326),
    new_type text
);


CREATE SEQUENCE sources.tx_blanco_lines_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.tx_blanco_lines_gid_seq OWNED BY sources.tx_blanco_lines.gid;


CREATE TABLE sources.tx_chisos (
    gid integer NOT NULL,
    age_order numeric,
    era character varying(21),
    period character varying(24),
    epoch character varying(29),
    radiometic character varying(40),
    shape_leng numeric,
    shape_area numeric,
    unit character varying(20),
    descriptio character varying(100),
    descript_1 character varying(100),
    age character varying(50),
    geom public.geometry(MultiPolygon,4326),
    strat_name text,
    descrip_long text,
    early_id integer,
    late_id integer,
    use_name text
);


CREATE SEQUENCE sources.tx_chisos_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.tx_chisos_gid_seq OWNED BY sources.tx_chisos.gid;


CREATE TABLE sources.tx_chisos_lines (
    gid integer NOT NULL,
    shape_leng numeric,
    descriptio character varying(100),
    geom public.geometry(MultiLineString,4326),
    new_type text
);


CREATE SEQUENCE sources.tx_chisos_lines_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.tx_chisos_lines_gid_seq OWNED BY sources.tx_chisos_lines.gid;


CREATE TABLE sources.tx_chisos_points (
    gid integer NOT NULL,
    rotation numeric,
    azimuth numeric,
    dip character varying(10),
    descriptio character varying(100),
    geom public.geometry(Point,4326),
    point_type text,
    dip_dir integer
);


CREATE SEQUENCE sources.tx_chisos_points_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.tx_chisos_points_gid_seq OWNED BY sources.tx_chisos_points.gid;


CREATE TABLE sources.tx_hays (
    gid integer NOT NULL,
    unit_order bigint,
    geo_unit_1 character varying(25),
    geo_unit_2 character varying(50),
    groupnm character varying(50),
    formation character varying(75),
    member character varying(254),
    hydro_unit character varying(100),
    hydrostrat character varying(100),
    thickness character varying(20),
    hydro_func character varying(100),
    porosity character varying(75),
    shape_leng numeric,
    shape_area numeric,
    geom public.geometry(MultiPolygon,4326),
    descrip text,
    age text,
    lith text,
    early_id integer,
    late_id integer,
    use_name text,
    strat_name text
);


CREATE SEQUENCE sources.tx_hays_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.tx_hays_gid_seq OWNED BY sources.tx_hays.gid;


CREATE TABLE sources.tx_hays_lines (
    gid integer NOT NULL,
    type character varying(25),
    shape_leng numeric,
    geom public.geometry(MultiLineString,4326),
    new_type text
);


CREATE SEQUENCE sources.tx_hays_lines_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.tx_hays_lines_gid_seq OWNED BY sources.tx_hays_lines.gid;


CREATE TABLE sources.tx_laredo (
    gid integer NOT NULL,
    label character varying(20),
    descriptio character varying(150),
    shape_leng numeric,
    shape_area numeric,
    geom public.geometry(MultiPolygon,4326),
    name text,
    age text,
    descrip text,
    early_id integer,
    late_id integer,
    strat_name text
);


CREATE SEQUENCE sources.tx_laredo_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.tx_laredo_gid_seq OWNED BY sources.tx_laredo.gid;


CREATE TABLE sources.tx_laredo_lines (
    gid integer NOT NULL,
    descriptio character varying(100),
    shape_leng numeric,
    geom public.geometry(MultiLineString,4326),
    new_type text,
    new_direction text
);


CREATE SEQUENCE sources.tx_laredo_lines_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.tx_laredo_lines_gid_seq OWNED BY sources.tx_laredo_lines.gid;


CREATE TABLE sources.tx_laredo_points (
    gid integer NOT NULL,
    id integer,
    type character varying(50),
    descript character varying(50),
    azimuth smallint,
    dip smallint,
    geom public.geometry(Point,4326),
    point_type text,
    dip_dir integer
);


CREATE SEQUENCE sources.tx_laredo_points_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.tx_laredo_points_gid_seq OWNED BY sources.tx_laredo_points.gid;


CREATE TABLE sources.uk (
    gid integer NOT NULL,
    lex character varying(5),
    lex_d character varying(200),
    lex_rcs character varying(12),
    rcs character varying(6),
    rcs_x character varying(50),
    rcs_d character varying(200),
    rank character varying(16),
    bed_eq character varying(5),
    bed_eq_d character varying(200),
    mb_eq character varying(5),
    mb_eq_d character varying(200),
    fm_eq character varying(5),
    fm_eq_d character varying(200),
    subgp_eq character varying(5),
    subgp_eq_d character varying(200),
    gp_eq character varying(5),
    gp_eq_d character varying(200),
    supgp_eq character varying(5),
    supgp_eq_d character varying(200),
    max_time_d character varying(32),
    min_time_d character varying(32),
    max_time_y double precision,
    min_time_y numeric(10,0),
    max_index numeric(10,0),
    min_index numeric(10,0),
    max_age character varying(32),
    min_age character varying(32),
    max_epoch character varying(32),
    min_epoch character varying(32),
    max_subper character varying(32),
    min_subper character varying(32),
    max_period character varying(32),
    min_period character varying(32),
    max_era character varying(32),
    min_era character varying(32),
    max_eon character varying(32),
    min_eon character varying(32),
    prev_name character varying(250),
    bgstype character varying(32),
    lex_rcs_i character varying(20),
    lex_rcs_d character varying(100),
    map_code character varying(10),
    age_onegl character varying(32),
    bgsref numeric(10,0),
    bgsref_lex numeric(10,0),
    bgsref_fm numeric(10,0),
    bgsref_gp numeric(10,0),
    bgsref_rk numeric(10,0),
    sheet character varying(60),
    version character varying(10),
    released character varying(10),
    nom_scale character varying(10),
    nom_os_yr character varying(10),
    nom_bgs_yr character varying(10),
    mslink numeric(10,0),
    geom public.geometry(MultiPolygon,4326),
    early_id integer,
    late_id integer,
    age_name character varying(70),
    hierarchy character varying(155),
    strat_name text,
    strat_name_id integer
);


CREATE SEQUENCE sources.uk_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.uk_gid_seq OWNED BY sources.uk.gid;


CREATE TABLE sources.uk_lines (
    gid integer NOT NULL,
    category character varying(32),
    feature character varying(60),
    feature_d character varying(100),
    fltname_c character varying(6),
    fltname_d character varying(100),
    sheet character varying(60),
    version character varying(10),
    released character varying(10),
    nom_scale character varying(10),
    nom_os_yr character varying(10),
    nom_bgs_yr character varying(10),
    mslink numeric(10,0),
    geom public.geometry(MultiLineString,4326)
);


CREATE SEQUENCE sources.uk_lines_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.uk_lines_gid_seq OWNED BY sources.uk_lines.gid;


CREATE TABLE sources.usgs_world (
    gid integer NOT NULL,
    area double precision,
    perimeter double precision,
    roxsam0_ numeric(10,0),
    roxsam0_id numeric(10,0),
    polyno integer,
    id2 integer,
    agera character varying(3),
    agequ character varying(1),
    rxtp character varying(3),
    use character varying(1),
    name character varying(30),
    signif character varying(30),
    ageclass_i numeric(10,0),
    polyno_id2 double precision,
    roxnam0_ numeric(10,0),
    roxnam0_id numeric(10,0),
    roxeur0_ numeric(10,0),
    roxeur0_id numeric(10,0),
    roxaus0_ numeric(10,0),
    roxaus0_id numeric(10,0),
    roxasi0_ numeric(10,0),
    roxasi0_id numeric(10,0),
    roxantaz0_ numeric(10,0),
    roxantaz01 numeric(10,0),
    roxant_id numeric(10,0),
    roxafr0_ numeric(10,0),
    roxafr0_id numeric(10,0),
    geom public.geometry(MultiPolygon,4326),
    lith text,
    comments text,
    early_id integer,
    late_id integer,
    "interval" text
);


CREATE SEQUENCE sources.usgs_world_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.usgs_world_gid_seq OWNED BY sources.usgs_world.gid;


CREATE TABLE sources.usgs_world_lines (
    gid integer NOT NULL,
    fnode_ numeric(10,0),
    tnode_ numeric(10,0),
    lpoly_ numeric(10,0),
    rpoly_ numeric(10,0),
    length double precision,
    fltafr0_ numeric(10,0),
    fltafr0_id numeric(10,0),
    faultno integer,
    id2 integer,
    fclass character varying(2),
    fdisp character varying(2),
    wrongpolar character varying(1),
    agera character varying(3),
    agequ character varying(1),
    use character varying(1),
    name character varying(40),
    signif character varying(30),
    fault_id numeric(10,0),
    faultno_id double precision,
    symbol numeric(10,0),
    fltantaz0_ numeric(10,0),
    fltantaz01 numeric(10,0),
    fltant_id numeric(10,0),
    fltasi0_ numeric(10,0),
    fltasi0_id numeric(10,0),
    fltaus0_ numeric(10,0),
    fltaus0_id numeric(10,0),
    flteur0_ numeric(10,0),
    flteur0_id numeric(10,0),
    fltsam0_ numeric(10,0),
    fltsam0_id numeric(10,0),
    fltnam0_ numeric(10,0),
    fltnam0_id numeric(10,0),
    geom public.geometry(MultiLineString,4326)
);


CREATE SEQUENCE sources.usgs_world_lines_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.usgs_world_lines_gid_seq OWNED BY sources.usgs_world_lines.gid;


CREATE TABLE sources.ut_beaver (
    gid integer NOT NULL,
    unitrank integer,
    unitsymbol character varying(20),
    unitlabel character varying(20),
    unitname character varying(120),
    "grouping" character varying(75),
    age_strat character varying(75),
    composition character varying(250),
    genesis character varying(150),
    description character varying(1600),
    source character varying(150),
    notes character varying(250),
    shape_length double precision,
    shape_area double precision,
    ruleid integer,
    override bytea,
    early_id integer,
    late_id integer,
    strat_name text,
    geom public.geometry
);


CREATE TABLE sources.ut_beaver_lines (
    gid integer NOT NULL,
    layerint smallint,
    layer character varying(10),
    feature character varying(100),
    type character varying(50),
    subtype character varying(50),
    modifier character varying(50),
    featurename character varying(100),
    source character varying(150),
    notes character varying(250),
    ruleid integer,
    override bytea,
    shape_length double precision,
    new_type text,
    direction text,
    geom public.geometry
);


CREATE SEQUENCE sources.ut_beaver_lines_objectid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.ut_beaver_lines_objectid_seq OWNED BY sources.ut_beaver_lines.gid;


CREATE SEQUENCE sources.ut_beaver_objectid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.ut_beaver_objectid_seq OWNED BY sources.ut_beaver.gid;


CREATE TABLE sources.ut_dugway (
    gid integer NOT NULL,
    objectid numeric(10,0),
    unitrank integer,
    unitsymbol character varying(20),
    unitlabel character varying(20),
    unitname character varying(100),
    "grouping" character varying(75),
    age_strat character varying(75),
    compositio character varying(150),
    genesis character varying(150),
    source character varying(150),
    notes character varying(250),
    shape_leng numeric,
    shape_area numeric,
    ruleid numeric(10,0),
    geom public.geometry(MultiPolygon,4326),
    description text,
    strat_name text,
    hierarchy text,
    early_id integer,
    late_id integer
);


CREATE TABLE sources.ut_dugway_lines (
    gid integer NOT NULL,
    objectid numeric(10,0),
    layerint integer,
    layer character varying(10),
    feature character varying(100),
    type character varying(50),
    subtype character varying(50),
    modifier character varying(50),
    featurenam character varying(100),
    source character varying(150),
    notes character varying(250),
    orig_fid numeric(10,0),
    ruleid numeric(10,0),
    shape_leng numeric,
    geom public.geometry(MultiLineString,4326),
    elevation integer,
    new_type text,
    descrip text,
    new_direction text
);


CREATE TABLE sources.ut_dugway_points (
    gid integer NOT NULL,
    objectid numeric(10,0),
    layerint integer,
    layer character varying(25),
    feature character varying(100),
    type character varying(50),
    subtype character varying(50),
    modifier character varying(50),
    rotation numeric,
    strike numeric,
    dipdirecti numeric,
    dipangle numeric,
    cad_angle numeric,
    feature_id character varying(15),
    source character varying(50),
    notes character varying(254),
    geom public.geometry(Point,4326),
    point_type text
);


CREATE SEQUENCE sources.ut_dugwayprovinggrounds_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.ut_dugwayprovinggrounds_gid_seq OWNED BY sources.ut_dugway.gid;


CREATE SEQUENCE sources.ut_dugwayprovinggrounds_lines_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.ut_dugwayprovinggrounds_lines_gid_seq OWNED BY sources.ut_dugway_lines.gid;


CREATE SEQUENCE sources.ut_dugwayprovinggrounds_points_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.ut_dugwayprovinggrounds_points_gid_seq OWNED BY sources.ut_dugway_points.gid;


CREATE TABLE sources.ut_escalante (
    gid integer NOT NULL,
    area numeric,
    perimeter numeric,
    unitsymbol character varying(15),
    unitname character varying(80),
    age character varying(50),
    notes character varying(50),
    geom public.geometry(MultiPolygon,4326),
    description text,
    hierarchy text,
    early_id integer,
    late_id integer,
    strat_name text
);


CREATE SEQUENCE sources.ut_escalante_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.ut_escalante_gid_seq OWNED BY sources.ut_escalante.gid;


CREATE TABLE sources.ut_escalante_lines (
    gid integer NOT NULL,
    length numeric,
    type character varying(25),
    subtype character varying(25),
    modifier character varying(30),
    notes character varying(30),
    geom public.geometry(MultiLineString),
    new_type text,
    descrip text
);


CREATE SEQUENCE sources.ut_escalante_lines_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.ut_escalante_lines_gid_seq OWNED BY sources.ut_escalante_lines.gid;


CREATE TABLE sources.ut_kanab (
    gid integer NOT NULL,
    objectid integer,
    unitsymbol character varying(15),
    unitname character varying(100),
    age character varying(50),
    notes character varying(50),
    shape_leng numeric,
    shape_area numeric,
    geom public.geometry(MultiPolygon,4326),
    descrip text,
    early_id integer,
    late_id integer,
    strat_name text,
    hierarchy text
);


CREATE SEQUENCE sources.ut_kanab_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.ut_kanab_gid_seq OWNED BY sources.ut_kanab.gid;


CREATE TABLE sources.ut_kanab_lines (
    gid integer NOT NULL,
    type character varying(25),
    subtype character varying(25),
    modifier character varying(30),
    notes character varying(30),
    shape_leng numeric,
    geom public.geometry(MultiLineString,4326),
    use_name character varying(60)
);


CREATE SEQUENCE sources.ut_kanab_lines_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.ut_kanab_lines_gid_seq OWNED BY sources.ut_kanab_lines.gid;


CREATE TABLE sources.ut_lasal (
    gid integer NOT NULL,
    area numeric,
    perimeter numeric,
    geology_ integer,
    geology_id integer,
    unitsymbol character varying(15),
    unitname character varying(80),
    age character varying(50),
    notes character varying(50),
    geom public.geometry(MultiPolygon,4326),
    descrip text,
    early_id integer,
    late_id integer,
    strat_name text,
    hierarchy text
);


CREATE SEQUENCE sources.ut_lasal_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.ut_lasal_gid_seq OWNED BY sources.ut_lasal.gid;


CREATE TABLE sources.ut_lasal_lines (
    gid integer NOT NULL,
    length double precision,
    faults_ integer,
    faults_id integer,
    type character varying(25),
    subtype character varying(25),
    modifier character varying(30),
    notes character varying(50),
    geom public.geometry(MultiLineString,4326),
    use_name character varying(75)
);


CREATE SEQUENCE sources.ut_lasal_lines_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.ut_lasal_lines_gid_seq OWNED BY sources.ut_lasal_lines.gid;


CREATE TABLE sources.ut_logan (
    gid integer NOT NULL,
    area numeric,
    perimeter numeric,
    geology_ integer,
    geology_id integer,
    unitsymbol character varying(15),
    unitname character varying(80),
    age character varying(50),
    notes character varying(50),
    loganlitho character varying(254),
    geom public.geometry(MultiPolygon,4326),
    early_id integer,
    late_id integer
);


CREATE SEQUENCE sources.ut_logan_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.ut_logan_gid_seq OWNED BY sources.ut_logan.gid;


CREATE TABLE sources.ut_lynndyl (
    gid integer NOT NULL,
    area numeric,
    perimeter numeric,
    geology_ integer,
    geology_id integer,
    g_unit character varying(15),
    unitname character varying(80),
    age character varying(50),
    notes character varying(50),
    geom public.geometry(MultiPolygon,4326),
    name text,
    description text,
    strat_name text,
    hierarchy text,
    comments text,
    early_id integer,
    late_id integer
);


CREATE SEQUENCE sources.ut_lynndyl_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.ut_lynndyl_gid_seq OWNED BY sources.ut_lynndyl.gid;


CREATE TABLE sources.ut_lynndyl_lines (
    gid integer NOT NULL,
    fnode_ integer,
    tnode_ integer,
    lpoly_ integer,
    rpoly_ integer,
    length numeric,
    geology_ integer,
    geology_id integer,
    type character varying(25),
    subtype character varying(25),
    modifier character varying(30),
    notes character varying(30),
    geom public.geometry(MultiLineString,4326),
    new_type text,
    description text
);


CREATE SEQUENCE sources.ut_lynndyl_lines_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.ut_lynndyl_lines_gid_seq OWNED BY sources.ut_lynndyl_lines.gid;


CREATE TABLE sources.ut_moab (
    gid integer NOT NULL,
    area double precision,
    perimeter double precision,
    contacts_ double precision,
    contacts_i double precision,
    unitsymbol character varying(25),
    unitname character varying(80),
    age character varying(50),
    notes character varying(50),
    colorname integer,
    geom public.geometry(MultiPolygon,4326),
    descrip text,
    early_id integer,
    late_id integer,
    strat_name text,
    hierarchy text
);


CREATE SEQUENCE sources.ut_moab_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.ut_moab_gid_seq OWNED BY sources.ut_moab.gid;


CREATE TABLE sources.ut_moab_lines (
    gid integer NOT NULL,
    type character varying(35),
    sub_type character varying(35),
    modifier character varying(35),
    notes character varying(35),
    geom public.geometry(MultiLineString,4326),
    use_type character varying(75),
    use_name character varying(75)
);


CREATE SEQUENCE sources.ut_moab_lines_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.ut_moab_lines_gid_seq OWNED BY sources.ut_moab_lines.gid;


CREATE TABLE sources.ut_ogden (
    gid integer NOT NULL,
    objectid bigint,
    unitrank integer,
    unitsymbol character varying(20),
    unitlabel character varying(20),
    unitname character varying(150),
    "grouping" character varying(100),
    age_strat character varying(75),
    compositio text,
    genesis character varying(150),
    source character varying(150),
    notes character varying(250),
    shape_leng numeric,
    shape_area numeric,
    geom public.geometry(MultiPolygon,4326),
    max_age text,
    min_age text,
    early_id integer,
    late_id integer,
    strat_name text,
    descrip text
);


CREATE SEQUENCE sources.ut_ogden_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.ut_ogden_gid_seq OWNED BY sources.ut_ogden.gid;


CREATE TABLE sources.ut_ogden_lines (
    gid integer NOT NULL,
    objectid bigint,
    layerint integer,
    layer character varying(10),
    feature character varying(100),
    type character varying(50),
    subtype character varying(50),
    modifier character varying(50),
    featurenam character varying(100),
    source character varying(150),
    notes character varying(250),
    shape_leng numeric,
    geom public.geometry(MultiLineString,4326),
    new_type text
);


CREATE SEQUENCE sources.ut_ogden_lines_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.ut_ogden_lines_gid_seq OWNED BY sources.ut_ogden_lines.gid;


CREATE TABLE sources.ut_ogden_points (
    gid integer NOT NULL,
    objectid bigint,
    layerint integer,
    layer character varying(25),
    feature character varying(100),
    type character varying(50),
    subtype character varying(50),
    modifier character varying(50),
    rotation numeric,
    strike numeric,
    dipdirecti numeric,
    dipangle numeric,
    cad_angle numeric,
    feature_id character varying(15),
    source character varying(50),
    notes character varying(254),
    geom public.geometry(Point,4326),
    point_type text
);


CREATE SEQUENCE sources.ut_ogden_points_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.ut_ogden_points_gid_seq OWNED BY sources.ut_ogden_points.gid;


CREATE TABLE sources.ut_panguitch (
    gid integer NOT NULL,
    unitrank integer,
    unitsymbol character varying(30),
    unitlabel character varying(50),
    unitname character varying(254),
    "grouping" character varying(150),
    age_strat character varying(100),
    compositio character varying(150),
    genesis character varying(150),
    source character varying(150),
    notes character varying(250),
    shape_leng numeric,
    shape_area numeric,
    ruleid numeric(10,0),
    geom public.geometry(MultiPolygon,4326),
    early_id integer,
    late_id integer,
    descrip text
);


CREATE SEQUENCE sources.ut_panguitch_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.ut_panguitch_gid_seq OWNED BY sources.ut_panguitch.gid;


CREATE TABLE sources.ut_panguitch_lines (
    gid integer NOT NULL,
    layerint integer,
    layer character varying(10),
    feature character varying(100),
    type character varying(50),
    subtype character varying(50),
    modifier character varying(50),
    featurenam character varying(100),
    source character varying(150),
    notes character varying(250),
    shape_leng numeric,
    geom public.geometry(MultiLineString,4326),
    new_type character varying(50),
    new_direction character varying(50)
);


CREATE SEQUENCE sources.ut_panguitch_lines_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.ut_panguitch_lines_gid_seq OWNED BY sources.ut_panguitch_lines.gid;


CREATE TABLE sources.ut_price_lines (
    gid integer NOT NULL,
    fnode_ integer,
    tnode_ integer,
    lpoly_ integer,
    rpoly_ integer,
    length numeric,
    geology_ integer,
    geology_id integer,
    type character varying(25),
    subtype character varying(25),
    modifier character varying(30),
    notes character varying(30),
    geom public.geometry(MultiLineString,4326),
    new_type text
);


CREATE SEQUENCE sources.ut_price_lines_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.ut_price_lines_gid_seq OWNED BY sources.ut_price_lines.gid;


CREATE TABLE sources.ut_prommontorymtns (
    gid integer NOT NULL,
    unitrank integer,
    unitsymbol character varying(20),
    unitlabel character varying(20),
    unitname character varying(100),
    "grouping" character varying(75),
    age_strat character varying(75),
    composition character varying(250),
    genesis character varying(150),
    description character varying(1200),
    source character varying(150),
    notes character varying(250),
    orig_fid integer,
    shape_length double precision,
    shape_area double precision,
    ruleid integer,
    override bytea,
    wkb_geometry public.geometry(MultiPolygon,26712),
    geom public.geometry,
    early_id integer,
    late_id integer,
    strat_name text
);


CREATE TABLE sources.ut_prommontorymtns_folds (
    gid integer NOT NULL,
    layerint smallint,
    layer character varying(25),
    feature character varying(150),
    type character varying(50),
    subtype character varying(50),
    modifier character varying(50),
    featurename character varying(100),
    elevation smallint,
    datum character varying(100),
    notes character varying(255),
    shape_length double precision,
    ruleid integer,
    override bytea,
    wkb_geometry public.geometry(MultiLineString,26712),
    geom public.geometry,
    new_type text,
    new_direction text
);


CREATE SEQUENCE sources.ut_prommontorymtns_folds_objectid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.ut_prommontorymtns_folds_objectid_seq OWNED BY sources.ut_prommontorymtns_folds.gid;


CREATE SEQUENCE sources.ut_prommontorymtns_objectid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.ut_prommontorymtns_objectid_seq OWNED BY sources.ut_prommontorymtns.gid;


CREATE TABLE sources.ut_prommontorymtns_points (
    gid integer NOT NULL,
    layerint smallint,
    layer character varying(25),
    feature character varying(100),
    type character varying(50),
    subtype character varying(50),
    modifier character varying(50),
    rotation double precision,
    strike double precision,
    dipdirection double precision,
    dipangle double precision,
    feature_id character varying(15),
    gps_id character varying(25),
    source character varying(250),
    notes character varying(254),
    ruleid integer,
    override bytea,
    wkb_geometry public.geometry(MultiPoint,26712),
    geom public.geometry
);


CREATE SEQUENCE sources.ut_prommontorymtns_points_objectid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.ut_prommontorymtns_points_objectid_seq OWNED BY sources.ut_prommontorymtns_points.gid;


CREATE TABLE sources.ut_salina (
    gid integer NOT NULL,
    objectid numeric(10,0),
    unitrank integer,
    unitsymbol character varying(20),
    unitlabel character varying(20),
    unitname character varying(100),
    "grouping" character varying(75),
    age_strat character varying(75),
    compositio character varying(250),
    genesis character varying(150),
    source character varying(150),
    notes character varying(250),
    shape_leng numeric,
    shape_area numeric,
    ruleid numeric(10,0),
    geom public.geometry(MultiPolygon,4326),
    description text,
    strat_name text,
    hierarchy text,
    early_id integer,
    late_id integer
);


CREATE SEQUENCE sources.ut_salina_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.ut_salina_gid_seq OWNED BY sources.ut_salina.gid;


CREATE TABLE sources.ut_salina_lines (
    gid integer NOT NULL,
    objectid numeric(10,0),
    layerint integer,
    layer character varying(10),
    feature character varying(100),
    type character varying(50),
    subtype character varying(50),
    modifier character varying(50),
    featurenam character varying(100),
    source character varying(150),
    notes character varying(250),
    shape_leng numeric,
    ruleid numeric(10,0),
    geom public.geometry(MultiLineString,4326),
    new_type text
);


CREATE SEQUENCE sources.ut_salina_lines_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.ut_salina_lines_gid_seq OWNED BY sources.ut_salina_lines.gid;


CREATE TABLE sources.ut_salina_points (
    gid integer NOT NULL,
    objectid numeric(10,0),
    layerint integer,
    layer character varying(25),
    feature character varying(100),
    type character varying(50),
    subtype character varying(50),
    modifier character varying(50),
    rotation numeric,
    strike numeric,
    dipdirecti numeric,
    dipangle numeric,
    cad_angle numeric,
    feature_id character varying(15),
    source character varying(50),
    notes character varying(254),
    geom public.geometry(Point,4326),
    point_type text
);


CREATE SEQUENCE sources.ut_salina_points_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.ut_salina_points_gid_seq OWNED BY sources.ut_salina_points.gid;


CREATE TABLE sources.ut_saltlake (
    gid integer NOT NULL,
    area numeric,
    perimeter numeric,
    geology_ integer,
    geology_id integer,
    unitsymbol character varying(15),
    unitname character varying(100),
    age character varying(50),
    notes character varying(50),
    geom public.geometry(MultiPolygon,4326),
    strat_name text,
    descrip text,
    early_id integer,
    late_id integer,
    age_temp text
);


CREATE SEQUENCE sources.ut_saltlake_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.ut_saltlake_gid_seq OWNED BY sources.ut_saltlake.gid;


CREATE TABLE sources.ut_saltlake_lines (
    gid integer NOT NULL,
    fnode_ integer,
    tnode_ integer,
    lpoly_ integer,
    rpoly_ integer,
    length numeric,
    geology_ integer,
    geology_id integer,
    type character varying(25),
    subtype character varying(25),
    modifier character varying(30),
    notes character varying(30),
    geom public.geometry(MultiLineString,4326),
    new_type text
);


CREATE SEQUENCE sources.ut_saltlake_lines_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.ut_saltlake_lines_gid_seq OWNED BY sources.ut_saltlake_lines.gid;


CREATE TABLE sources.ut_seepridge (
    gid integer NOT NULL,
    rank smallint,
    unitsymbol character varying(10),
    unitname character varying(75),
    "grouping" character varying(75),
    age character varying(75),
    compositio character varying(125),
    color character varying(75),
    morphology character varying(75),
    thickness character varying(50),
    genesis character varying(50),
    notes character varying(254),
    orig_fid integer,
    shape_leng numeric,
    shape_area numeric,
    geom public.geometry(MultiPolygon,4326),
    early_id integer,
    late_id integer
);


CREATE SEQUENCE sources.ut_seepridge_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.ut_seepridge_gid_seq OWNED BY sources.ut_seepridge.gid;


CREATE TABLE sources.ut_stgeorge (
    gid integer NOT NULL,
    unitrank integer,
    unitsymbol character varying(15),
    unitname character varying(80),
    "grouping" character varying(80),
    age character varying(80),
    compositio character varying(80),
    genesis character varying(80),
    notes text,
    shape_leng numeric,
    shape_area numeric,
    ruleid integer,
    geom public.geometry(MultiPolygon,4326),
    early_id integer,
    late_id integer,
    strat_name text,
    hierarchy text
);


CREATE SEQUENCE sources.ut_stgeorge_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.ut_stgeorge_gid_seq OWNED BY sources.ut_stgeorge.gid;


CREATE TABLE sources.ut_stgeorge_lines (
    gid integer NOT NULL,
    layerint smallint,
    layer character varying(10),
    feature character varying(100),
    type character varying(50),
    subtype character varying(50),
    modifier character varying(50),
    age character varying(100),
    featurenam character varying(100),
    notes character varying(254),
    shape_leng numeric,
    ruleid integer,
    geom public.geometry(MultiLineString,4326),
    use_name character varying(100),
    use_type character varying(100)
);


CREATE SEQUENCE sources.ut_stgeorge_lines_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.ut_stgeorge_lines_gid_seq OWNED BY sources.ut_stgeorge_lines.gid;


CREATE TABLE sources.ut_tooele (
    gid integer NOT NULL,
    objectid bigint,
    unitrank integer,
    unitsymbol character varying(20),
    unitlabel character varying(20),
    unitname character varying(150),
    "grouping" character varying(100),
    age_strat character varying(75),
    compositio character varying(254),
    genesis character varying(150),
    source character varying(150),
    notes character varying(250),
    shape_leng numeric,
    shape_area numeric,
    geom public.geometry(MultiPolygon,4326),
    max_age text,
    min_age text,
    early_id integer,
    late_id integer,
    strat_name text,
    descrip text
);


CREATE SEQUENCE sources.ut_tooele_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.ut_tooele_gid_seq OWNED BY sources.ut_tooele.gid;


CREATE TABLE sources.ut_tooele_lines (
    gid integer NOT NULL,
    objectid bigint,
    layerint integer,
    layer character varying(10),
    feature character varying(100),
    type character varying(50),
    subtype character varying(50),
    modifier character varying(50),
    featurenam character varying(100),
    source character varying(150),
    notes character varying(250),
    shape_leng numeric,
    geom public.geometry(MultiLineString,4326),
    new_type text
);


CREATE SEQUENCE sources.ut_tooele_lines_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.ut_tooele_lines_gid_seq OWNED BY sources.ut_tooele_lines.gid;


CREATE TABLE sources.ut_tooele_points (
    gid integer NOT NULL,
    objectid bigint,
    layerint integer,
    layer character varying(25),
    feature character varying(100),
    type character varying(50),
    subtype character varying(50),
    modifier character varying(50),
    rotation numeric,
    strike numeric,
    dipdirecti numeric,
    dipangle numeric,
    cad_angle numeric,
    feature_id character varying(15),
    gps_id character varying(25),
    source character varying(250),
    notes character varying(254),
    geom public.geometry(Point,4326),
    point_type text,
    comments text
);


CREATE SEQUENCE sources.ut_tooele_points_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.ut_tooele_points_gid_seq OWNED BY sources.ut_tooele_points.gid;


CREATE TABLE sources.ut_vernal (
    gid integer NOT NULL,
    area numeric,
    perimeter numeric,
    geology_ integer,
    geology_id integer,
    unitsymbol character varying(15),
    unitname character varying(80),
    age character varying(50),
    geom public.geometry(MultiPolygon,4326),
    description text,
    early_id integer,
    late_id integer
);


CREATE TABLE sources.ut_vernal_lines (
    gid integer NOT NULL,
    fnode_ integer,
    tnode_ integer,
    lpoly_ integer,
    rpoly_ integer,
    length numeric,
    geology_ integer,
    geology_id integer,
    type character varying(25),
    subtype character varying(25),
    modifier character varying(30),
    name character varying(30),
    geom public.geometry(MultiLineString,4326),
    source text,
    new_type text,
    new_direction text
);


CREATE TABLE sources.ut_wahwahmtns (
    gid integer NOT NULL,
    area double precision,
    perimeter double precision,
    geology_ integer,
    geology_id integer,
    unitsymbol character varying(15),
    unitname character varying(150),
    age character varying(50),
    notes character varying(50),
    geom public.geometry(MultiPolygon,4326),
    description text,
    early_id integer,
    late_id integer
);


CREATE TABLE sources.ut_wahwahmtns_lines (
    gid integer NOT NULL,
    fnode_ integer,
    tnode_ integer,
    lpoly_ integer,
    rpoly_ integer,
    length double precision,
    geology_ integer,
    geology_id integer,
    type character varying(25),
    subtype character varying(25),
    modifier character varying(30),
    notes character varying(30),
    geom public.geometry(MultiLineString,4326),
    new_type text,
    new_direction text
);


CREATE TABLE sources.ut_westwater (
    gid integer NOT NULL,
    area numeric,
    perimeter numeric,
    geology_ integer,
    geology_id integer,
    unitsymbol character varying(15),
    unitname character varying(80),
    age character varying(50),
    notes character varying(50),
    geom public.geometry(MultiPolygon,4326),
    lithology text,
    late_id integer,
    early_id integer
);


CREATE TABLE sources.ut_westwater_lines (
    gid integer NOT NULL,
    fnode_ integer,
    tnode_ integer,
    lpoly_ integer,
    rpoly_ integer,
    length numeric,
    geology_ integer,
    geology_id integer,
    type character varying(25),
    subtype character varying(25),
    modifier character varying(30),
    notes character varying(30),
    geom public.geometry(MultiLineString,4326),
    new_type character varying(30)
);


CREATE SEQUENCE sources.ut_westwater_lines_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.ut_westwater_lines_gid_seq OWNED BY sources.ut_westwater_lines.gid;


CREATE TABLE sources.utquad_cedarcity (
    gid integer NOT NULL,
    shape_leng numeric,
    shape_area numeric,
    rank smallint,
    unitsymbol character varying(15),
    unitname character varying(100),
    age character varying(50),
    changes character varying(50),
    notes character varying(50),
    geom public.geometry(MultiPolygon,4326),
    descrip text,
    early_id integer,
    late_id integer
);


CREATE SEQUENCE sources.utquad_cedarcity_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.utquad_cedarcity_gid_seq OWNED BY sources.utquad_cedarcity.gid;


CREATE TABLE sources.utquad_cedarcity_ln (
    gid integer NOT NULL,
    layer smallint,
    feature character varying(50),
    type character varying(25),
    subtype character varying(25),
    modifier character varying(35),
    shape_leng numeric,
    geom public.geometry(MultiLineString,4326)
);


CREATE SEQUENCE sources.utquad_cedarcity_ln_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.utquad_cedarcity_ln_gid_seq OWNED BY sources.utquad_cedarcity_ln.gid;


CREATE TABLE sources.utquad_eastslc (
    gid integer NOT NULL,
    shape_leng numeric,
    shape_area numeric,
    rank smallint,
    unitsymbol character varying(10),
    unitname character varying(100),
    "grouping" character varying(50),
    age character varying(50),
    compositio character varying(200),
    genesis character varying(100),
    notes character varying(50),
    ruleid integer,
    geom public.geometry(MultiPolygon,4326),
    descrip text,
    early_id integer,
    late_id integer,
    age_text character varying(50),
    strat_name text,
    hierarchy text
);


CREATE SEQUENCE sources.utquad_eastslc_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.utquad_eastslc_gid_seq OWNED BY sources.utquad_eastslc.gid;


CREATE TABLE sources.utquad_eastslc_ln (
    gid integer NOT NULL,
    shape_leng numeric,
    layer smallint,
    feature character varying(75),
    type character varying(25),
    subtype character varying(25),
    modifier character varying(25),
    age character varying(50),
    featurenam character varying(50),
    notes character varying(100),
    ruleid integer,
    geom public.geometry(MultiLineString,4326)
);


CREATE SEQUENCE sources.utquad_eastslc_ln_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.utquad_eastslc_ln_gid_seq OWNED BY sources.utquad_eastslc_ln.gid;


CREATE TABLE sources.va_middletown (
    gid integer NOT NULL,
    area double precision,
    perimeter double precision,
    map_unit character varying(10),
    surf_bed character varying(11),
    surftype character varying(15),
    lithpri character varying(25),
    lithsec character varying(25),
    lithter character varying(25),
    form character varying(55),
    member character varying(35),
    group_ character varying(35),
    supergroup character varying(35),
    rockclass character varying(35),
    age character varying(35),
    geochr character varying(35),
    geochrtech character varying(35),
    geochrref character varying(35),
    fossil character varying(3),
    fossiltype character varying(35),
    fossilref character varying(35),
    correlextr character varying(35),
    origin character varying(50),
    res character varying(35),
    resref character varying(35),
    color character varying(35),
    minpri character varying(35),
    minsec character varying(35),
    minoth character varying(35),
    clastpri character varying(35),
    clastsec character varying(35),
    cement character varying(35),
    thickapprx character varying(35),
    thickrange character varying(35),
    bedthin character varying(9),
    bedmedium character varying(12),
    bedthick character varying(10),
    contup character varying(20),
    contlow character varying(20),
    folpri character varying(35),
    folsec character varying(35),
    folter character varying(35),
    cmpm character varying(35),
    rmpm character varying(35),
    rmrm character varying(35),
    deformage character varying(35),
    deformtech character varying(50),
    deformref character varying(35),
    comments character varying(254),
    shape_leng numeric,
    shape_area numeric,
    geom public.geometry(MultiPolygon,4326),
    early_id integer,
    late_id integer,
    strat_name text,
    lith text,
    use_comments text,
    descrip_long text
);


CREATE SEQUENCE sources.va_middletown_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.va_middletown_gid_seq OWNED BY sources.va_middletown.gid;


CREATE TABLE sources.va_middletown_lines (
    gid integer NOT NULL,
    strux_type character varying(50),
    strux_name character varying(50),
    shape_leng numeric,
    geom public.geometry(MultiLineString,4326),
    new_type text
);


CREATE SEQUENCE sources.va_middletown_lines_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.va_middletown_lines_gid_seq OWNED BY sources.va_middletown_lines.gid;


CREATE TABLE sources.va_stephcity (
    gid integer NOT NULL,
    objectid integer,
    area numeric,
    perimeter numeric,
    map_unit character varying(8),
    shape_leng numeric,
    oid_ integer,
    map_unit_1 character varying(10),
    surf_bed character varying(11),
    surftype character varying(15),
    lithpri character varying(25),
    lithsec character varying(25),
    lithter character varying(25),
    form character varying(95),
    member character varying(35),
    group_ character varying(35),
    supergroup character varying(35),
    rockclass character varying(35),
    age character varying(35),
    geochr character varying(35),
    geochrtech character varying(35),
    geochrref character varying(35),
    fossil character varying(3),
    fossiltype character varying(35),
    fossilref character varying(35),
    correlextr character varying(35),
    origin character varying(50),
    res character varying(35),
    resref character varying(35),
    color character varying(35),
    minpri character varying(35),
    minsec character varying(35),
    minoth character varying(35),
    clastpri character varying(35),
    clastsec character varying(35),
    cement character varying(35),
    thickapprx character varying(35),
    thickrange character varying(35),
    bedthin character varying(9),
    bedmedium character varying(12),
    bedthick character varying(10),
    contup character varying(20),
    contlow character varying(20),
    folpri character varying(35),
    folsec character varying(35),
    folter character varying(35),
    cmpm character varying(35),
    rmpm character varying(35),
    rmrm character varying(35),
    deformage character varying(35),
    deformtech character varying(50),
    deformref character varying(35),
    comments character varying(254),
    shape_le_1 numeric,
    shape_area numeric,
    geom public.geometry(MultiPolygon,4326),
    use_comments text,
    descrip_long text,
    early_id integer,
    late_id integer,
    strat_name text,
    lith text
);


CREATE SEQUENCE sources.va_stephcity_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.va_stephcity_gid_seq OWNED BY sources.va_stephcity.gid;


CREATE TABLE sources.va_stephcity_lines (
    gid integer NOT NULL,
    fnode_ integer,
    tnode_ integer,
    lpoly_ integer,
    rpoly_ integer,
    length numeric,
    win_linstr integer,
    win_lins_1 integer,
    strux_type character varying(25),
    strux_nm character varying(25),
    shape_leng numeric,
    geom public.geometry(MultiLineString,4326),
    new_type text,
    comments text
);


CREATE SEQUENCE sources.va_stephcity_lines_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.va_stephcity_lines_gid_seq OWNED BY sources.va_stephcity_lines.gid;


CREATE TABLE sources.va_stephcity_points (
    gid integer NOT NULL,
    station character varying(10),
    unit character varying(30),
    strike_rr_ integer,
    dip integer,
    jt1_az_rr_ integer,
    jt1_dip integer,
    jt1_sp character varying(8),
    jt2_az_rr_ integer,
    jt2_dip integer,
    jt2_sp character varying(8),
    jt3_az_rr_ integer,
    jt3_dip integer,
    jt3_sp character varying(8),
    jt4_az_rr_ integer,
    jt4_dip integer,
    jt4_sp character varying(8),
    bed_type character varying(12),
    clv_strike integer,
    clv_dip integer,
    cleavage character varying(35),
    geom public.geometry(Point,4326),
    point_type text,
    dip_dir integer
);


CREATE SEQUENCE sources.va_stephcity_points_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.va_stephcity_points_gid_seq OWNED BY sources.va_stephcity_points.gid;


CREATE TABLE sources.venezuela_lines (
    gid integer NOT NULL,
    objectid numeric(10,0),
    shape_leng numeric,
    line_type integer,
    geom public.geometry(MultiLineString,4326),
    type text,
    new_type text,
    new_direction text
);


CREATE SEQUENCE sources.venez_lines_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.venez_lines_gid_seq OWNED BY sources.venezuela_lines.gid;


CREATE TABLE sources.venezuela (
    gid integer NOT NULL,
    objectid numeric(10,0),
    unit_abbre character varying(8),
    lith character varying(100),
    age character varying(35),
    shape_leng numeric,
    shape_area numeric,
    unit_name character varying(254),
    geom public.geometry(MultiPolygon,4326),
    name text,
    lithology text,
    strat_name text,
    hierarchy text,
    early_id integer,
    late_id integer
);


CREATE SEQUENCE sources.venezuela_geo_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.venezuela_geo_gid_seq OWNED BY sources.venezuela.gid;


CREATE SEQUENCE sources.vernal_faults_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.vernal_faults_gid_seq OWNED BY sources.ut_vernal_lines.gid;


CREATE SEQUENCE sources.vernalutahgeology_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.vernalutahgeology_gid_seq OWNED BY sources.ut_vernal.gid;


CREATE TABLE sources.wa100k (
    gid integer NOT NULL,
    geologic_u numeric(10,0),
    geologic_1 character varying(254),
    geologic_a character varying(254),
    lithology character varying(254),
    named_unit character varying(254),
    shape_leng numeric,
    shape_area numeric,
    geom public.geometry(MultiPolygon,4326),
    early_id integer,
    late_id integer
);


CREATE SEQUENCE sources.wa100k_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.wa100k_gid_seq OWNED BY sources.wa100k.gid;


CREATE TABLE sources.wa100k_line (
    gid integer NOT NULL,
    orig_id integer,
    name character varying(255),
    type character varying(100),
    direction character varying(20),
    descrip text,
    geom public.geometry(Geometry,4326)
);


CREATE SEQUENCE sources.wa100k_line_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.wa100k_line_gid_seq OWNED BY sources.wa100k_line.gid;


CREATE SEQUENCE sources.wahwahmountainutgeology_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.wahwahmountainutgeology_gid_seq OWNED BY sources.ut_wahwahmtns.gid;


CREATE SEQUENCE sources.wahwahmtn_geolines_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.wahwahmtn_geolines_gid_seq OWNED BY sources.ut_wahwahmtns_lines.gid;


CREATE SEQUENCE sources.westcentralpakistangeology_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.westcentralpakistangeology_gid_seq OWNED BY sources.pakistan_westcentral.gid;


CREATE SEQUENCE sources.westwater_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.westwater_gid_seq OWNED BY sources.ut_westwater.gid;


CREATE TABLE sources.wi_ashland (
    gid integer NOT NULL,
    area double precision,
    perimeter double precision,
    bedrock_ double precision,
    bedrock_id double precision,
    plot_code smallint,
    symbol character varying(4),
    era character varying(12),
    period character varying(22),
    subperiod character varying(28),
    supergroup character varying(15),
    grp character varying(80),
    unit_name character varying(90),
    sunit_name character varying(20),
    age character varying(9),
    rk_type character varying(11),
    major_subt character varying(15),
    major_lith character varying(21),
    minor1_rkt character varying(12),
    minor1_sub character varying(15),
    minor1_lit character varying(25),
    minor2_rkt character varying(12),
    minor2_sub character varying(15),
    minor2_lit character varying(20),
    prov_orign character varying(48),
    subprov_or character varying(40),
    prov_age character varying(18),
    rewrk_prov character varying(8),
    rewrk_subp character varying(20),
    rewrk_age character varying(18),
    env_formtn character varying(26),
    tect_setng character varying(24),
    lith_assem character varying(52),
    geom public.geometry(MultiPolygon,4326),
    descrip text,
    early_id integer,
    late_id integer,
    strat_name text,
    lith text
);


CREATE SEQUENCE sources.wi_ashland_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.wi_ashland_gid_seq OWNED BY sources.wi_ashland.gid;


CREATE TABLE sources.wi_ashland_lines (
    gid integer NOT NULL,
    length double precision,
    ashl_fault double precision,
    fault_code smallint,
    type character varying(42),
    geom public.geometry(MultiLineString,4326),
    new_type text
);


CREATE SEQUENCE sources.wi_ashland_lines_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.wi_ashland_lines_gid_seq OWNED BY sources.wi_ashland_lines.gid;


CREATE TABLE sources.wi_ashland_points (
    gid integer NOT NULL,
    ashl_dips_ double precision,
    symbol character varying(4),
    azimuth character varying(9),
    incline character varying(5),
    rotation integer,
    geom public.geometry(Point,4326),
    point_type text,
    dip_dir integer
);


CREATE SEQUENCE sources.wi_ashland_points_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.wi_ashland_points_gid_seq OWNED BY sources.wi_ashland_points.gid;


CREATE TABLE sources.wi_brown (
    gid integer NOT NULL,
    objectid numeric(10,0),
    unitcode character varying(25),
    shape_leng numeric,
    shape_area numeric,
    geom public.geometry(MultiPolygon,4326),
    name text,
    age text,
    description text,
    strat_name text,
    hierarchy text,
    early_id integer,
    late_id integer
);


CREATE SEQUENCE sources.wi_brown_geology_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.wi_brown_geology_gid_seq OWNED BY sources.wi_brown.gid;


CREATE TABLE sources.wi_brown_lines (
    gid integer NOT NULL,
    type numeric(10,0),
    feature numeric(10,0),
    conf numeric(10,0),
    d_type character varying(254),
    d_feature character varying(254),
    d_conf character varying(254),
    geom public.geometry(MultiLineString,4326),
    name text,
    description text,
    new_type text
);


CREATE SEQUENCE sources.wi_brown_lines_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.wi_brown_lines_gid_seq OWNED BY sources.wi_brown_lines.gid;


CREATE TABLE sources.wi_brown_points (
    gid integer NOT NULL,
    wuwn character varying(25),
    imagenum character varying(25),
    sitetype numeric(10,0),
    d_sitetype character varying(254),
    geom public.geometry(Point,4326),
    point_type text
);


CREATE SEQUENCE sources.wi_brown_point_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.wi_brown_point_gid_seq OWNED BY sources.wi_brown_points.gid;


CREATE TABLE sources.wi_fond_du (
    gid integer NOT NULL,
    mupid character varying(50),
    mapunit character varying(10),
    muname character varying(128),
    mudescr text,
    muagedis character varying(128),
    mulith bigint,
    identcon character varying(50),
    label character varying(50),
    notes character varying(254),
    dasid character varying(50),
    publishr character varying(254),
    shape_leng numeric,
    shape_area numeric,
    shorttxt character varying(254),
    geom public.geometry(MultiPolygon,4326),
    early_id integer,
    late_id integer,
    strat_name text
);


CREATE SEQUENCE sources.wi_fond_du_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.wi_fond_du_gid_seq OWNED BY sources.wi_fond_du.gid;


CREATE TABLE sources.wi_fond_du_lines (
    gid integer NOT NULL,
    gelid character varying(50),
    type character varying(254),
    conceald character varying(1),
    existcon character varying(50),
    identcon character varying(50),
    dasid character varying(50),
    notes character varying(254),
    shape_leng numeric,
    maptext character varying(254),
    geom public.geometry(MultiLineString,4326),
    new_type text
);


CREATE SEQUENCE sources.wi_fond_du_lines_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.wi_fond_du_lines_gid_seq OWNED BY sources.wi_fond_du_lines.gid;


CREATE TABLE sources.wi_juneaucounty (
    gid integer NOT NULL,
    unitcode character varying(25),
    geom public.geometry(MultiPolygon,4326),
    name text,
    age text,
    description text,
    strat_name text,
    hierarchy text,
    early_id integer,
    late_id integer
);


CREATE TABLE sources.wi_juneaucounty_lines (
    gid integer NOT NULL,
    type integer,
    feature integer,
    conf integer,
    maptext character varying(250),
    geom public.geometry(MultiLineString,4326),
    new_type text,
    description text
);


CREATE SEQUENCE sources.wi_juneaucounty_lines_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.wi_juneaucounty_lines_gid_seq OWNED BY sources.wi_juneaucounty_lines.gid;


CREATE SEQUENCE sources.wi_juneaucounty_polygon_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.wi_juneaucounty_polygon_gid_seq OWNED BY sources.wi_juneaucounty.gid;


CREATE TABLE sources.wi_marathon (
    gid integer NOT NULL,
    mucode character varying(25),
    geom public.geometry(MultiPolygon,4326),
    name text,
    descrip text,
    age text,
    early_id integer,
    late_id integer,
    strat_name text
);


CREATE SEQUENCE sources.wi_marathon_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.wi_marathon_gid_seq OWNED BY sources.wi_marathon.gid;


CREATE TABLE sources.wi_marathon_lines (
    gid integer NOT NULL,
    type integer,
    feature integer,
    conf integer,
    maptext character varying(250),
    geom public.geometry(MultiLineString,4326),
    new_type text
);


CREATE SEQUENCE sources.wi_marathon_lines_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.wi_marathon_lines_gid_seq OWNED BY sources.wi_marathon_lines.gid;


CREATE TABLE sources.wi_marathon_points (
    gid integer NOT NULL,
    feature integer,
    orien numeric,
    incdirec integer,
    incvalue numeric,
    maptext character varying(250),
    geom public.geometry(Point,4326),
    point_type text,
    strike integer,
    dip integer,
    dip_dir integer
);


CREATE SEQUENCE sources.wi_marathon_points_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.wi_marathon_points_gid_seq OWNED BY sources.wi_marathon_points.gid;


CREATE TABLE sources.wi_piercestcroix (
    gid integer NOT NULL,
    objectid numeric(10,0),
    mapunit character varying(25),
    geom public.geometry(MultiPolygon,4326),
    name text,
    age text,
    description text,
    strat_name text,
    hierarchy text,
    early_id integer,
    late_id integer
);


CREATE SEQUENCE sources.wi_piercestcroix_geology_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.wi_piercestcroix_geology_gid_seq OWNED BY sources.wi_piercestcroix.gid;


CREATE TABLE sources.wi_piercestcroix_lines (
    gid integer NOT NULL,
    feattype numeric(10,0),
    featcat numeric(10,0),
    featacc numeric(10,0),
    detail numeric(10,0),
    d_feattype character varying(254),
    d_featcat character varying(254),
    d_featacc character varying(254),
    d_detail character varying(254),
    geom public.geometry(MultiLineString,4326),
    name text,
    new_type text,
    description text
);


CREATE SEQUENCE sources.wi_piercestcroix_line_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.wi_piercestcroix_line_gid_seq OWNED BY sources.wi_piercestcroix_lines.gid;


CREATE TABLE sources.wy_rattlesnakehills (
    gid integer NOT NULL,
    objectid numeric(10,0),
    ptype character varying(10),
    shape_leng numeric,
    shape_area numeric,
    descriptio character varying(6),
    geom public.geometry(MultiPolygon,4326),
    name text,
    age text,
    description text,
    strat_name text,
    hierarchy text,
    early_id integer,
    late_id integer,
    comments text
);


CREATE SEQUENCE sources.wi_rattlesnakehills_polygon_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.wi_rattlesnakehills_polygon_gid_seq OWNED BY sources.wy_rattlesnakehills.gid;


CREATE TABLE sources.wi_sauk (
    gid integer,
    symbol text,
    age text,
    strat_name text,
    name text,
    descrip text,
    geom public.geometry(MultiPolygon,4326),
    early_id integer,
    late_id integer,
    use_name text,
    use_strat_name text
);


CREATE TABLE sources.wi_wood (
    gid integer NOT NULL,
    unitcode character varying(25),
    geom public.geometry(MultiPolygon,4326),
    name text,
    strat_name text,
    descrip text,
    age text,
    early_id integer,
    late_id integer
);


CREATE SEQUENCE sources.wi_wood_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.wi_wood_gid_seq OWNED BY sources.wi_wood.gid;


CREATE TABLE sources.wi_wood_lines (
    gid integer NOT NULL,
    type integer,
    feature integer,
    conf integer,
    maptext character varying(250),
    geom public.geometry(MultiLineString,4326),
    new_type text
);


CREATE SEQUENCE sources.wi_wood_lines_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.wi_wood_lines_gid_seq OWNED BY sources.wi_wood_lines.gid;


CREATE TABLE sources.wi_wood_points (
    gid integer NOT NULL,
    feature integer,
    orien numeric,
    incdirec integer,
    incvalue numeric,
    maptext character varying(250),
    geom public.geometry(Point,4326),
    point_type text,
    strike integer,
    dip integer,
    dip_dir integer
);


CREATE SEQUENCE sources.wi_wood_points_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.wi_wood_points_gid_seq OWNED BY sources.wi_wood_points.gid;


CREATE TABLE sources.world_basins (
    gid integer NOT NULL,
    id integer,
    symbol character varying(100),
    basin_name character varying(50),
    region_tel character varying(100),
    tellus_bas character varying(25),
    sub_regime character varying(100),
    subreg_grp character varying(100),
    basin_id character varying(20),
    region_tl_ character varying(11),
    hotlink double precision,
    available smallint,
    gf_basins smallint,
    srceweb character varying(37),
    url character varying(100),
    geom public.geometry(MultiPolygon,4326),
    hex_color character varying(7)
);


CREATE SEQUENCE sources.world_basins_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.world_basins_gid_seq OWNED BY sources.world_basins.gid;


CREATE SEQUENCE sources.wpakistan_faults_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.wpakistan_faults_gid_seq OWNED BY sources.pakistan_westcentral_lines.gid;


CREATE TABLE sources.wy_baggs (
    gid integer NOT NULL,
    g_unit character varying(8),
    g_sym character varying(8),
    g_nam character varying(125),
    shape_leng numeric,
    shape_area numeric,
    geom public.geometry(MultiPolygon,4326),
    name text,
    age text,
    description text,
    strat_name text,
    hierarchy text,
    comments text,
    early_id integer,
    late_id integer
);


CREATE SEQUENCE sources.wy_baggs_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.wy_baggs_gid_seq OWNED BY sources.wy_baggs.gid;


CREATE TABLE sources.wy_baggs_lines (
    gid integer NOT NULL,
    type character varying(50),
    shape_leng numeric,
    source character varying(50),
    name character varying(50),
    geom public.geometry(MultiLineString,4326),
    new_type text,
    descrip text
);


CREATE SEQUENCE sources.wy_baggs_lines_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.wy_baggs_lines_gid_seq OWNED BY sources.wy_baggs_lines.gid;


CREATE TABLE sources.wy_baggs_points (
    gid integer NOT NULL,
    type character varying(20),
    rotation numeric,
    dip smallint,
    name character varying(50),
    geom public.geometry(Point,4326),
    point_type text,
    strike integer
);


CREATE SEQUENCE sources.wy_baggs_points_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.wy_baggs_points_gid_seq OWNED BY sources.wy_baggs_points.gid;


CREATE TABLE sources.wy_bairoil (
    gid integer NOT NULL,
    objectid integer,
    g_sym character varying(15),
    orig_fid integer,
    shape_leng numeric,
    shape_area numeric,
    geom public.geometry(MultiPolygon,4326),
    name text,
    age text,
    description text,
    strat_name text,
    hierarchy text,
    comments text,
    early_id integer,
    late_id integer
);


CREATE SEQUENCE sources.wy_bairoil_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.wy_bairoil_gid_seq OWNED BY sources.wy_bairoil.gid;


CREATE TABLE sources.wy_bairoil_lines (
    gid integer NOT NULL,
    objectid integer,
    name character varying(50),
    type character varying(30),
    shape_leng numeric,
    geom public.geometry(MultiLineString,4326),
    new_type text
);


CREATE SEQUENCE sources.wy_bairoil_lines_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.wy_bairoil_lines_gid_seq OWNED BY sources.wy_bairoil_lines.gid;


CREATE TABLE sources.wy_bill (
    gid integer NOT NULL,
    g_id integer,
    g_unit character varying(8),
    g_sym character varying(8),
    g_nam character varying(125),
    p_acc integer,
    a_id smallint,
    m_id character varying(25),
    w_id integer,
    shape_leng numeric,
    shape_area numeric,
    geom public.geometry(MultiPolygon,4326),
    name text,
    age text,
    description text,
    strat_name text,
    hierarchy text,
    comments text,
    early_id integer,
    late_id integer
);


CREATE SEQUENCE sources.wy_bill_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.wy_bill_gid_seq OWNED BY sources.wy_bill.gid;


CREATE TABLE sources.wy_bill_lines (
    gid integer NOT NULL,
    flt_id integer,
    flt_type integer,
    p_acc integer,
    flt_sym character varying(8),
    flt_name character varying(125),
    dir character varying(1),
    a_id smallint,
    m_id character varying(25),
    w_id integer,
    shape_leng numeric,
    geom public.geometry(MultiLineString,4326),
    new_type text,
    description text
);


CREATE SEQUENCE sources.wy_bill_lines_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.wy_bill_lines_gid_seq OWNED BY sources.wy_bill_lines.gid;


CREATE TABLE sources.wy_buffalo (
    gid integer NOT NULL,
    g_id integer,
    g_unit character varying(8),
    g_sym character varying(8),
    g_nam character varying(125),
    p_acc character varying(30),
    geom public.geometry(MultiPolygon,4326),
    name text,
    age text,
    description text,
    strat_name text,
    hierarchy text,
    comments text,
    early_id integer,
    late_id integer
);


CREATE SEQUENCE sources.wy_buffalo_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.wy_buffalo_gid_seq OWNED BY sources.wy_buffalo.gid;


CREATE TABLE sources.wy_buffalo_lines (
    gid integer NOT NULL,
    f_type character varying(60),
    p_acc character varying(30),
    direction character varying(50),
    geom public.geometry(MultiLineString,4326),
    new_type text,
    descrip text
);


CREATE SEQUENCE sources.wy_buffalo_lines_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.wy_buffalo_lines_gid_seq OWNED BY sources.wy_buffalo_lines.gid;


CREATE TABLE sources.wy_casper_lines (
    gid integer NOT NULL,
    f_type character varying(60),
    f_name character varying(125),
    p_acc character varying(30),
    geom public.geometry(MultiLineString,4326),
    new_type text,
    description text
);


CREATE SEQUENCE sources.wy_caspar_lines_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.wy_caspar_lines_gid_seq OWNED BY sources.wy_casper_lines.gid;


CREATE TABLE sources.wy_casper (
    gid integer NOT NULL,
    g_id integer,
    g_unit character varying(8),
    g_sym character varying(8),
    g_nam character varying(125),
    p_acc character varying(30),
    geom public.geometry(MultiPolygon,4326),
    name text,
    age text,
    description text,
    strat_name text,
    hierarchy text,
    early_id integer,
    late_id integer
);


CREATE SEQUENCE sources.wy_caspar_polygon_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.wy_caspar_polygon_gid_seq OWNED BY sources.wy_casper.gid;


CREATE TABLE sources.wy_cheyenne (
    gid integer NOT NULL,
    objectid integer,
    g_id integer,
    g_unit character varying(8),
    g_sym character varying(8),
    g_nam character varying(125),
    p_acc character varying(30),
    shape_leng numeric,
    shape_area numeric,
    geom public.geometry(MultiPolygon,4326),
    name text,
    age text,
    description text,
    strat_name text,
    hierarchy text,
    early_id integer,
    late_id integer
);


CREATE SEQUENCE sources.wy_cheyenne_polygon_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.wy_cheyenne_polygon_gid_seq OWNED BY sources.wy_cheyenne.gid;


CREATE TABLE sources.wy_douglas (
    gid integer NOT NULL,
    objectid numeric(10,0),
    g_unit character varying(8),
    g_sym character varying(8),
    g_nam character varying(125),
    shape_leng numeric,
    shape_area numeric,
    geom public.geometry(MultiPolygon,4326),
    name text,
    age text,
    description text,
    strat_name text,
    hierarchy text,
    early_id integer,
    late_id integer,
    comments text
);


CREATE SEQUENCE sources.wy_douglas_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.wy_douglas_gid_seq OWNED BY sources.wy_douglas.gid;


CREATE TABLE sources.wy_douglas_lines (
    gid integer NOT NULL,
    objectid numeric(10,0),
    flt_id numeric(10,0),
    flt_type numeric(10,0),
    p_acc numeric(10,0),
    flt_sym character varying(8),
    flt_name character varying(125),
    dir character varying(1),
    a_id integer,
    m_id character varying(25),
    w_id numeric(10,0),
    shape_leng numeric,
    geom public.geometry(MultiLineString,4326),
    new_type text
);


CREATE SEQUENCE sources.wy_douglas_lines_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.wy_douglas_lines_gid_seq OWNED BY sources.wy_douglas_lines.gid;


CREATE TABLE sources.wy_evanston (
    gid integer NOT NULL,
    g_unit character varying(8),
    g_sym character varying(8),
    g_nam character varying(125),
    p_acc character varying(30),
    geom public.geometry(MultiPolygon,4326),
    shape_leng integer,
    shape_area integer,
    name text,
    description text,
    age text,
    strat_name text,
    hierarchy text,
    early_id integer,
    late_id integer,
    comments text
);


CREATE TABLE sources.wy_evanston_lines (
    gid integer NOT NULL,
    objectid integer,
    g_name character varying(125),
    p_acc character varying(30),
    shape_leng numeric,
    geom public.geometry(MultiLineString,4326),
    new_type text
);


CREATE SEQUENCE sources.wy_evanston_lines_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.wy_evanston_lines_gid_seq OWNED BY sources.wy_evanston_lines.gid;


CREATE SEQUENCE sources.wy_evanston_polygon_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.wy_evanston_polygon_gid_seq OWNED BY sources.wy_evanston.gid;


CREATE TABLE sources.wy_farson (
    gid integer NOT NULL,
    g_unit character varying(10),
    source character varying(50),
    shape_leng numeric,
    shape_area numeric,
    geom public.geometry(MultiPolygon,4326),
    name text,
    age text,
    strat_name text,
    descrip text,
    early_id integer,
    late_id integer,
    comments text
);


CREATE SEQUENCE sources.wy_farson_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.wy_farson_gid_seq OWNED BY sources.wy_farson.gid;


CREATE TABLE sources.wy_farson_lines (
    gid integer NOT NULL,
    type character varying(15),
    source character varying(50),
    name character varying(50),
    shape_leng numeric,
    geom public.geometry(MultiLineString,4326),
    new_type text,
    new_direction text
);


CREATE SEQUENCE sources.wy_farson_lines_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.wy_farson_lines_gid_seq OWNED BY sources.wy_farson_lines.gid;


CREATE TABLE sources.wy_gillette (
    gid integer NOT NULL,
    area double precision,
    perimeter double precision,
    gilldd_ double precision,
    gilldd_id double precision,
    name text,
    class integer,
    deposits character varying(9),
    geom public.geometry(MultiPolygon,4326),
    age text,
    description text,
    strat_name text,
    hierarchy text,
    comments text,
    early_id integer,
    late_id integer
);


CREATE SEQUENCE sources.wy_gillette_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.wy_gillette_gid_seq OWNED BY sources.wy_gillette.gid;


CREATE TABLE sources.wy_kaycee (
    gid integer NOT NULL,
    g_unit character varying(8),
    g_sym character varying(8),
    g_nam character varying(125),
    p_acc character varying(30),
    geom public.geometry(MultiPolygon,4326),
    name text,
    age text,
    description text,
    strat_name text,
    hierarchy text,
    comments text,
    early_id integer,
    late_id integer
);


CREATE SEQUENCE sources.wy_kaycee_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.wy_kaycee_gid_seq OWNED BY sources.wy_kaycee.gid;


CREATE TABLE sources.wy_kaycee_lines (
    gid integer NOT NULL,
    f_type character varying(60),
    p_acc character varying(30),
    geom public.geometry(MultiLineString,4326),
    new_type text,
    descrip text
);


CREATE SEQUENCE sources.wy_kaycee_lines_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.wy_kaycee_lines_gid_seq OWNED BY sources.wy_kaycee_lines.gid;


CREATE TABLE sources.wy_kemmerer (
    gid integer NOT NULL,
    g_id integer,
    g_unit character varying(8),
    g_sym character varying(8),
    g_nam character varying(125),
    p_acc character varying(30),
    shape_leng numeric,
    shape_area numeric,
    geom public.geometry(MultiPolygon,4326),
    name text,
    age text,
    description text,
    strat_name text,
    hierarchy text,
    early_id integer,
    late_id integer
);


CREATE TABLE sources.wy_kemmerer_lines (
    gid integer NOT NULL,
    ltype character varying(125),
    p_acc character varying(30),
    shape_leng numeric,
    geom public.geometry(MultiLineString,4326),
    new_type text
);


CREATE SEQUENCE sources.wy_kemmerer_lines_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.wy_kemmerer_lines_gid_seq OWNED BY sources.wy_kemmerer_lines.gid;


CREATE SEQUENCE sources.wy_kemmerer_polygon_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.wy_kemmerer_polygon_gid_seq OWNED BY sources.wy_kemmerer.gid;


CREATE TABLE sources.wy_kinneyrim (
    gid integer NOT NULL,
    g_id integer,
    g_unit character varying(8),
    g_sym character varying(8),
    g_nam character varying(125),
    p_acc character varying(30),
    shape_leng numeric,
    shape_area numeric,
    geom public.geometry(MultiPolygon,4326),
    name text,
    age text,
    description text,
    strat_name text,
    hierarchy text,
    comments text,
    early_id integer,
    late_id integer
);


CREATE SEQUENCE sources.wy_kinneyrim_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.wy_kinneyrim_gid_seq OWNED BY sources.wy_kinneyrim.gid;


CREATE TABLE sources.wy_kinneyrim_lines (
    gid integer NOT NULL,
    f_type character varying(125),
    p_acc character varying(30),
    shape_leng numeric,
    geom public.geometry(MultiLineString,4326),
    type text,
    new_type text,
    descrip text
);


CREATE SEQUENCE sources.wy_kinneyrim_lines_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.wy_kinneyrim_lines_gid_seq OWNED BY sources.wy_kinneyrim_lines.gid;


CREATE TABLE sources.wy_lancecreek (
    gid integer NOT NULL,
    objectid integer,
    g_id integer,
    g_unit character varying(8),
    g_sym character varying(8),
    g_nam character varying(125),
    shape_leng numeric,
    shape_area numeric,
    geo_descri character varying(254),
    geom public.geometry(MultiPolygon,4326),
    name text,
    age text,
    description text,
    strat_name text,
    hierarchy text,
    comments text,
    early_id integer,
    late_id integer
);


CREATE TABLE sources.wy_lancecreek_lines (
    gid integer NOT NULL,
    objectid integer,
    shape_leng numeric,
    name character varying(50),
    type character varying(30),
    shape_le_1 numeric,
    geom public.geometry(MultiLineString,4326),
    new_type text,
    descrip text
);


CREATE TABLE sources.wy_lander (
    gid integer NOT NULL,
    objectid integer,
    g_unit character varying(5),
    g_sym character varying(5),
    descriptio character varying(50),
    g_age character varying(20),
    shape_leng numeric,
    shape_le_1 numeric,
    shape_area numeric,
    geom public.geometry(MultiPolygon,4326),
    name text,
    age text,
    description text,
    strat_name text,
    hierarchy text,
    early_id integer,
    late_id integer,
    comments text
);


CREATE TABLE sources.wy_lander_lines (
    gid integer NOT NULL,
    objectid integer,
    name character varying(50),
    type character varying(30),
    shape_leng numeric,
    geom public.geometry(MultiLineString,4326),
    new_type text,
    description text
);


CREATE SEQUENCE sources.wy_lanecreek_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.wy_lanecreek_gid_seq OWNED BY sources.wy_lancecreek.gid;


CREATE SEQUENCE sources.wy_lanecreek_lines_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.wy_lanecreek_lines_gid_seq OWNED BY sources.wy_lancecreek_lines.gid;


CREATE TABLE sources.wy_midwest (
    gid integer NOT NULL,
    objectid integer,
    g_id integer,
    g_unit character varying(8),
    g_sym character varying(8),
    g_nam character varying(125),
    p_acc integer,
    a_id smallint,
    m_id character varying(25),
    w_id integer,
    shape_leng numeric,
    shape_area numeric,
    geom public.geometry(MultiPolygon,4326),
    name text,
    age text,
    description text,
    strat_name text,
    hierarchy text,
    comments text,
    early_id integer,
    late_id integer
);


CREATE SEQUENCE sources.wy_midwest_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.wy_midwest_gid_seq OWNED BY sources.wy_midwest.gid;


CREATE TABLE sources.wy_midwest_lines (
    gid integer NOT NULL,
    objectid integer,
    flt_id integer,
    flt_type integer,
    p_acc integer,
    flt_sym character varying(8),
    flt_name character varying(125),
    dir character varying(1),
    a_id smallint,
    m_id character varying(25),
    w_id integer,
    shape_leng numeric,
    geom public.geometry(MultiLineString,4326),
    descrip text,
    new_type text
);


CREATE SEQUENCE sources.wy_midwest_lines_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.wy_midwest_lines_gid_seq OWNED BY sources.wy_midwest_lines.gid;


CREATE TABLE sources.wy_newcastle (
    gid integer NOT NULL,
    objectid integer,
    g_unit character varying(5),
    g_sym character varying(5),
    descriptio character varying(254),
    g_name character varying(100),
    shape_leng numeric,
    shape_le_1 numeric,
    shape_area numeric,
    geom public.geometry(MultiPolygon,4326),
    name text,
    age text,
    description text,
    strat_name text,
    hierarchy text,
    comments text,
    early_id integer,
    late_id integer
);


CREATE SEQUENCE sources.wy_newcastle_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.wy_newcastle_gid_seq OWNED BY sources.wy_newcastle.gid;


CREATE TABLE sources.wy_newcastle_lines (
    gid integer NOT NULL,
    objectid integer,
    id integer,
    shape_leng numeric,
    type character varying(20),
    geom public.geometry(MultiLineString,4326),
    new_type text,
    description text,
    name text
);


CREATE SEQUENCE sources.wy_newcastle_lines_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.wy_newcastle_lines_gid_seq OWNED BY sources.wy_newcastle_lines.gid;


CREATE TABLE sources.wy_nowater (
    gid integer NOT NULL,
    g_id integer,
    g_unit character varying(8),
    g_sym character varying(8),
    g_nam character varying(125),
    p_acc character varying(30),
    shape_leng numeric,
    shape_area numeric,
    geom public.geometry(MultiPolygon,4326),
    strat_name text,
    age text,
    descrip text,
    early_id integer,
    late_id integer
);


CREATE SEQUENCE sources.wy_nowater_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.wy_nowater_gid_seq OWNED BY sources.wy_nowater.gid;


CREATE TABLE sources.wy_nowater_lines (
    gid integer NOT NULL,
    f_type character varying(60),
    p_acc character varying(30),
    shape_leng numeric,
    dir smallint,
    direction character varying(10),
    geom public.geometry(MultiLineString,4326),
    name text
);


CREATE SEQUENCE sources.wy_nowater_lines_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.wy_nowater_lines_gid_seq OWNED BY sources.wy_nowater_lines.gid;


CREATE TABLE sources.wy_rattlesnakehills_lines (
    gid integer NOT NULL,
    objectid integer,
    fault_cont character varying(5),
    shape_leng numeric,
    geom public.geometry(MultiLineString,4326),
    new_type text
);


CREATE SEQUENCE sources.wy_rattlesnakehills_arcs_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.wy_rattlesnakehills_arcs_gid_seq OWNED BY sources.wy_rattlesnakehills_lines.gid;


CREATE TABLE sources.wy_rawlins (
    gid integer NOT NULL,
    objectid integer,
    g_unit character varying(50),
    g_symbol character varying(50),
    descriptio character varying(250),
    g_age character varying(50),
    shape_leng numeric,
    shape_area numeric,
    geom public.geometry(MultiPolygon,4326),
    name text,
    age text,
    description text,
    strat_name text,
    hierarchy text,
    early_id integer,
    late_id integer,
    comments text
);


CREATE SEQUENCE sources.wy_rawlins_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.wy_rawlins_gid_seq OWNED BY sources.wy_rawlins.gid;


CREATE TABLE sources.wy_rawlins_lines (
    gid integer NOT NULL,
    objectid integer,
    name character varying(50),
    type character varying(30),
    shape_leng numeric,
    geom public.geometry(MultiLineString,4326),
    descrip text,
    new_type text
);


CREATE SEQUENCE sources.wy_rawlins_lines_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.wy_rawlins_lines_gid_seq OWNED BY sources.wy_rawlins_lines.gid;


CREATE TABLE sources.wy_recluse (
    gid integer NOT NULL,
    g_id integer,
    g_unit character varying(8),
    g_sym character varying(8),
    g_nam character varying(125),
    p_acc character varying(30),
    geom public.geometry(MultiPolygon,4326),
    name text,
    age text,
    description text,
    strat_name text,
    hierarchy text,
    comments text,
    early_id integer,
    late_id integer,
    new_geom public.geometry
);


CREATE SEQUENCE sources.wy_recluse_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.wy_recluse_gid_seq OWNED BY sources.wy_recluse.gid;


CREATE TABLE sources.wy_recluse_lines (
    gid integer NOT NULL,
    f_type character varying(60),
    p_acc character varying(30),
    geom public.geometry(MultiLineString,4326),
    new_type text,
    descrip text
);


CREATE SEQUENCE sources.wy_recluse_lines_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.wy_recluse_lines_gid_seq OWNED BY sources.wy_recluse_lines.gid;


CREATE TABLE sources.wy_renojunction (
    gid integer NOT NULL,
    objectid integer,
    id integer,
    shape_leng numeric,
    shape_area numeric,
    g_unit character varying(10),
    geom public.geometry(MultiPolygon,4326),
    name text,
    age text,
    description text,
    strat_name text,
    hierarchy text,
    comments text,
    early_id integer,
    late_id integer
);


CREATE SEQUENCE sources.wy_renojunction_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.wy_renojunction_gid_seq OWNED BY sources.wy_renojunction.gid;


CREATE TABLE sources.wy_sundance (
    gid integer NOT NULL,
    objectid_1 integer,
    objectid numeric,
    quad_name character varying(32),
    quad_date character varying(2),
    usgs_id character varying(8),
    utm_zone character varying(2),
    shape_leng numeric,
    shape_area numeric,
    geo_name character varying(20),
    geom public.geometry(MultiPolygon,4326),
    name text,
    strat_name text,
    descrip text,
    age text,
    early_id integer,
    late_id integer
);


CREATE SEQUENCE sources.wy_sundance_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.wy_sundance_gid_seq OWNED BY sources.wy_sundance.gid;


CREATE TABLE sources.wy_sundance_lines (
    gid integer NOT NULL,
    objectid integer,
    shape_leng numeric,
    flt_sym character varying(50),
    flt_nam character varying(50),
    geom public.geometry(MultiLineString,4326),
    new_type text,
    new_direction text,
    name text
);


CREATE SEQUENCE sources.wy_sundance_lines_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.wy_sundance_lines_gid_seq OWNED BY sources.wy_sundance_lines.gid;


CREATE TABLE sources.wy_sundance_points (
    gid integer NOT NULL,
    objectid integer,
    str_ang integer,
    dip_ang integer,
    atd_nam character varying(25),
    geom public.geometry(Point,4326),
    point_type text,
    strike integer,
    dip_dir integer
);


CREATE SEQUENCE sources.wy_sundance_points_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.wy_sundance_points_gid_seq OWNED BY sources.wy_sundance_points.gid;


CREATE TABLE sources.wy_torrington (
    gid integer NOT NULL,
    objectid integer,
    g_id integer,
    g_unit character varying(8),
    g_sym character varying(8),
    g_nam character varying(125),
    p_acc integer,
    a_id smallint,
    m_id character varying(25),
    w_id integer,
    shape_leng numeric,
    shape_area numeric,
    geom public.geometry(MultiPolygon,4326),
    name text,
    age text,
    description text,
    strat_name text,
    hierarchy text,
    comments text,
    early_id integer,
    late_id integer
);


CREATE SEQUENCE sources.wy_torrington_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.wy_torrington_gid_seq OWNED BY sources.wy_torrington.gid;


CREATE TABLE sources.wy_torrington_lines (
    gid integer NOT NULL,
    objectid integer,
    fld_id integer,
    fld_type integer,
    p_acc integer,
    fld_sym character varying(8),
    fld_nam character varying(125),
    dir character varying(1),
    a_id smallint,
    m_id character varying(25),
    w_id integer,
    shape_leng numeric,
    geom public.geometry(MultiLineString,4326),
    new_type text,
    descrip text,
    name text
);


CREATE SEQUENCE sources.wy_torrington_lines_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.wy_torrington_lines_gid_seq OWNED BY sources.wy_torrington_lines.gid;


CREATE SEQUENCE sources.wyoming_lander_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.wyoming_lander_gid_seq OWNED BY sources.wy_lander.gid;


CREATE SEQUENCE sources.wyoming_lander_lines_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.wyoming_lander_lines_gid_seq OWNED BY sources.wy_lander_lines.gid;


CREATE TABLE sources.yk_joyal (
    gid integer NOT NULL,
    map_theme character varying(50),
    feature character varying(50),
    map_unit character varying(100),
    parents character varying(254),
    max_age character varying(50),
    min_age character varying(50),
    lith_list character varying(100),
    genesis character varying(100),
    remarks character varying(254),
    label character varying(30),
    reference character varying(254),
    source_ref character varying(254),
    map_id character varying(254),
    symbol character varying(100),
    shape_area numeric,
    shape_len numeric,
    geom public.geometry(MultiPolygon,4326),
    early_id integer,
    late_id integer,
    use_age text,
    strat_name text,
    descrip text
);


CREATE SEQUENCE sources.yk_joyal_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.yk_joyal_gid_seq OWNED BY sources.yk_joyal.gid;


CREATE TABLE sources.yk_joyal_lines (
    gid integer NOT NULL,
    map_theme character varying(50),
    feature character varying(50),
    subfeature character varying(50),
    attitude character varying(50),
    confidence character varying(15),
    generation character varying(25),
    max_age character varying(50),
    min_age character varying(50),
    name character varying(254),
    properties character varying(254),
    movement character varying(254),
    hwall_dir character varying(254),
    remarks character varying(254),
    reference character varying(254),
    source_ref character varying(254),
    map_id character varying(254),
    symbol character varying(100),
    shape_len numeric,
    geom public.geometry(MultiLineString,4326),
    new_type text,
    descrip text
);


CREATE SEQUENCE sources.yk_joyal_lines_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.yk_joyal_lines_gid_seq OWNED BY sources.yk_joyal_lines.gid;


CREATE TABLE sources.yk_joyal_points (
    gid integer NOT NULL,
    map_theme character varying(50),
    feature character varying(50),
    planar_id character varying(50),
    subfeature character varying(50),
    fab_elem character varying(254),
    attitude character varying(50),
    young_evid character varying(50),
    generation character varying(50),
    method character varying(50),
    dip_dir bigint,
    strike bigint,
    dip bigint,
    strain character varying(50),
    flattening character varying(50),
    lith_id character varying(50),
    station_id character varying(50),
    linear_id character varying(100),
    planar_id2 character varying(100),
    remarks character varying(300),
    reference character varying(254),
    source_ref character varying(254),
    map_id character varying(254),
    symbol character varying(100),
    geom public.geometry(Point,4326),
    trend integer,
    plunge integer,
    point_type text
);


CREATE SEQUENCE sources.yk_joyal_points_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.yk_joyal_points_gid_seq OWNED BY sources.yk_joyal_points.gid;


CREATE TABLE sources.yukon (
    gid integer NOT NULL,
    unit_1m character varying(25),
    unit_250k character varying(25),
    unit_orig character varying(25),
    supergroup character varying(50),
    gp_suite character varying(50),
    formation character varying(50),
    member character varying(50),
    name character varying(50),
    terrane character varying(50),
    terr_label character varying(10),
    tect_elem character varying(50),
    era_max character varying(50),
    period_max character varying(50),
    epoch_max character varying(50),
    stage_max character varying(50),
    age_max_ma double precision,
    era_min character varying(50),
    period_min character varying(50),
    epoch_min character varying(50),
    stage_min character varying(50),
    age_min_ma double precision,
    rock_class character varying(50),
    rock_subcl character varying(50),
    short_desc character varying(150),
    rock_major character varying(100),
    rock_minor character varying(100),
    rock_notes character varying(254),
    reference character varying(254),
    label_250k character varying(12),
    label_1m character varying(12),
    comments character varying(250),
    red integer,
    green integer,
    blue integer,
    shape_leng numeric,
    shape_area numeric,
    mi_colour numeric(10,0),
    geom public.geometry(MultiPolygon,4326),
    early_id integer,
    late_id integer,
    strat_name character varying(100),
    lith character varying(200),
    unit_name character varying(150),
    age_name character varying(50)
);


CREATE TABLE sources.yukon_folds (
    gid integer NOT NULL,
    fold_id numeric(10,0),
    fold_type character varying(80),
    fold_name character varying(30),
    length_met numeric,
    geometry_l numeric,
    geom public.geometry(MultiLineString,4326),
    type_name character varying(80),
    print_name character varying(80)
);


CREATE SEQUENCE sources.yukon_folds_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.yukon_folds_gid_seq OWNED BY sources.yukon_folds.gid;


CREATE SEQUENCE sources.yukon_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.yukon_gid_seq OWNED BY sources.yukon.gid;


CREATE TABLE sources.yukon_lines (
    gid integer NOT NULL,
    feature character varying(25),
    type character varying(30),
    subtype character varying(30),
    confidence character varying(25),
    name character varying(50),
    reference character varying(254),
    scale integer,
    symbol_dir character varying(10),
    comments character varying(250),
    shape_leng numeric,
    geom public.geometry(MultiLineString,4326),
    show_name character varying(100),
    show_type character varying(100),
    show_direction character varying(50)
);


CREATE SEQUENCE sources.yukon_lines_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.yukon_lines_gid_seq OWNED BY sources.yukon_lines.gid;


CREATE TABLE sources.yukon_mtmartin (
    gid integer NOT NULL,
    area numeric,
    perimeter numeric,
    una2087_ integer,
    una2087_id integer,
    gp character varying(100),
    formation character varying(100),
    member character varying(100),
    i_map_unit character varying(100),
    max_age character varying(50),
    min_age character varying(50),
    major_lith character varying(250),
    minor_lith character varying(250),
    remarks character varying(250),
    label character varying(18),
    rgb_colour character varying(12),
    legend_ord character varying(18),
    reference character varying(250),
    nts_map character varying(12),
    geom public.geometry(MultiPolygon,4326),
    strat_name text,
    early_id integer,
    late_id integer,
    use_name text,
    use_age text
);


CREATE TABLE sources.yukon_mtmartin_folds (
    gid integer NOT NULL,
    fnode_ integer,
    tnode_ integer,
    lpoly_ integer,
    rpoly_ integer,
    length numeric,
    fol2087_ integer,
    fol2087_id integer,
    type character varying(30),
    subtype character varying(100),
    attitude character varying(30),
    confidence character varying(30),
    dip_ap character varying(10),
    dip_dir_ap character varying(30),
    foldtrend character varying(8),
    foldplunge character varying(8),
    name character varying(30),
    reference character varying(250),
    nts_map character varying(12),
    geom public.geometry(MultiLineString,4326),
    new_type text,
    new_direction text
);


CREATE SEQUENCE sources.yukon_mtmartin_folds_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.yukon_mtmartin_folds_gid_seq OWNED BY sources.yukon_mtmartin_folds.gid;


CREATE SEQUENCE sources.yukon_mtmartin_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.yukon_mtmartin_gid_seq OWNED BY sources.yukon_mtmartin.gid;


CREATE TABLE sources.yukon_mtmartin_points (
    gid integer NOT NULL,
    area double precision,
    perimeter double precision,
    plp2087_ integer,
    plp2087_id integer,
    planar_id character varying(30),
    type character varying(50),
    modifier character varying(50),
    dip numeric,
    dip_dir numeric,
    location character varying(100),
    remarks character varying(250),
    linear_id character varying(30),
    unit character varying(50),
    station_id character varying(30),
    reference character varying(250),
    nts_map character varying(12),
    polygonid integer,
    scale double precision,
    angle double precision,
    geom public.geometry(Point,4326),
    strike numeric
);


CREATE SEQUENCE sources.yukon_mtmartin_points_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.yukon_mtmartin_points_gid_seq OWNED BY sources.yukon_mtmartin_points.gid;


CREATE TABLE sources.yukon_mtmerril (
    gid integer NOT NULL,
    area double precision,
    perimeter double precision,
    una2091_ double precision,
    una2091_id double precision,
    poly_ double precision,
    gp character varying(100),
    formation character varying(100),
    member character varying(100),
    i_map_unit character varying(100),
    max_age character varying(50),
    min_age character varying(50),
    major_lith character varying(250),
    minor_lith character varying(250),
    remarks character varying(250),
    label character varying(18),
    rgb_colour character varying(12),
    legend_ord character varying(18),
    reference character varying(250),
    nts_map character varying(12),
    geom public.geometry(MultiPolygon,4326),
    use_age text,
    strat_name text,
    use_name text,
    early_id integer,
    late_id integer
);


CREATE TABLE sources.yukon_mtmerril_folds (
    gid integer NOT NULL,
    fnode_ double precision,
    tnode_ double precision,
    lpoly_ double precision,
    rpoly_ double precision,
    length numeric,
    fol2091_ double precision,
    fol2091_id double precision,
    type character varying(30),
    subtype character varying(100),
    attitude character varying(30),
    confidence character varying(30),
    dip_ap character varying(10),
    dip_dir_ap character varying(30),
    foldtrend numeric,
    foldplunge numeric,
    name character varying(30),
    reference character varying(250),
    nts_map character varying(12),
    geom public.geometry(MultiLineString,4326),
    new_type text
);


CREATE SEQUENCE sources.yukon_mtmerril_folds_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.yukon_mtmerril_folds_gid_seq OWNED BY sources.yukon_mtmerril_folds.gid;


CREATE SEQUENCE sources.yukon_mtmerril_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.yukon_mtmerril_gid_seq OWNED BY sources.yukon_mtmerril.gid;


CREATE TABLE sources.yukon_mtmerril_points (
    gid integer NOT NULL,
    area double precision,
    perimeter double precision,
    plp2091_ double precision,
    plp2091_id double precision,
    planar_id character varying(30),
    type character varying(50),
    modifier character varying(50),
    dip double precision,
    dip_dir double precision,
    location character varying(100),
    remarks character varying(250),
    linear_id character varying(30),
    unit character varying(254),
    station_id character varying(30),
    reference character varying(100),
    nts_map character varying(12),
    geom public.geometry(Point,4326),
    strike integer
);


CREATE SEQUENCE sources.yukon_mtmerril_points_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE sources.yukon_mtmerril_points_gid_seq OWNED BY sources.yukon_mtmerril_points.gid;


ALTER TABLE ONLY detrital_zircon.located_query_bounds ALTER COLUMN id SET DEFAULT nextval('detrital_zircon.located_query_bounds_id_seq'::regclass);


ALTER TABLE ONLY geologic_boundaries.boundaries ALTER COLUMN boundary_id SET DEFAULT nextval('geologic_boundaries.boundaries_boundary_id_seq'::regclass);


ALTER TABLE ONLY hexgrids.r10 ALTER COLUMN hex_id SET DEFAULT nextval('hexgrids.r10_ogc_fid_seq'::regclass);


ALTER TABLE ONLY hexgrids.r11 ALTER COLUMN hex_id SET DEFAULT nextval('hexgrids.r11_ogc_fid_seq'::regclass);


ALTER TABLE ONLY hexgrids.r12 ALTER COLUMN hex_id SET DEFAULT nextval('hexgrids.r12_ogc_fid_seq'::regclass);


ALTER TABLE ONLY hexgrids.r5 ALTER COLUMN hex_id SET DEFAULT nextval('hexgrids.r5_ogc_fid_seq'::regclass);


ALTER TABLE ONLY hexgrids.r6 ALTER COLUMN hex_id SET DEFAULT nextval('hexgrids.r6_ogc_fid_seq'::regclass);


ALTER TABLE ONLY hexgrids.r7 ALTER COLUMN hex_id SET DEFAULT nextval('hexgrids.r7_ogc_fid_seq'::regclass);


ALTER TABLE ONLY hexgrids.r8 ALTER COLUMN hex_id SET DEFAULT nextval('hexgrids.r8_ogc_fid_seq'::regclass);


ALTER TABLE ONLY hexgrids.r9 ALTER COLUMN hex_id SET DEFAULT nextval('hexgrids.r9_ogc_fid_seq'::regclass);


ALTER TABLE ONLY macrostrat.intervals ALTER COLUMN id SET DEFAULT nextval('macrostrat.intervals_new_id_seq1'::regclass);


ALTER TABLE ONLY macrostrat.measurements ALTER COLUMN id SET DEFAULT nextval('macrostrat.measurements_new_id_seq'::regclass);


ALTER TABLE ONLY macrostrat.measuremeta ALTER COLUMN id SET DEFAULT nextval('macrostrat.measuremeta_new_id_seq1'::regclass);


ALTER TABLE ONLY macrostrat.measures ALTER COLUMN id SET DEFAULT nextval('macrostrat.measures_new_id_seq1'::regclass);


ALTER TABLE ONLY macrostrat.strat_names ALTER COLUMN id SET DEFAULT nextval('macrostrat.strat_names_new_id_seq'::regclass);


ALTER TABLE ONLY macrostrat.unit_measures ALTER COLUMN id SET DEFAULT nextval('macrostrat.unit_measures_new_id_seq'::regclass);


ALTER TABLE ONLY macrostrat.unit_strat_names ALTER COLUMN id SET DEFAULT nextval('macrostrat.unit_strat_names_new_id_seq1'::regclass);


ALTER TABLE ONLY macrostrat.units_sections ALTER COLUMN id SET DEFAULT nextval('macrostrat.units_sections_new_id_seq'::regclass);


ALTER TABLE ONLY maps.legend ALTER COLUMN legend_id SET DEFAULT nextval('maps.legend_legend_id_seq'::regclass);


ALTER TABLE ONLY maps.manual_matches ALTER COLUMN match_id SET DEFAULT nextval('maps.manual_matches_match_id_seq'::regclass);


ALTER TABLE ONLY maps.sources ALTER COLUMN source_id SET DEFAULT nextval('maps.sources_source_id_seq'::regclass);


ALTER TABLE ONLY points.points ALTER COLUMN point_id SET DEFAULT nextval('points.points_point_id_seq'::regclass);


ALTER TABLE ONLY public.impervious ALTER COLUMN rid SET DEFAULT nextval('public.impervious_rid_seq'::regclass);


ALTER TABLE ONLY public.land ALTER COLUMN gid SET DEFAULT nextval('public.land_gid_seq'::regclass);


ALTER TABLE ONLY public.macrostrat_union ALTER COLUMN id SET DEFAULT nextval('public.macrostrat_union_id_seq'::regclass);


ALTER TABLE ONLY public.test_rgeom ALTER COLUMN gid SET DEFAULT nextval('public.test_rgeom_gid_seq'::regclass);


ALTER TABLE ONLY sources.ab_spray ALTER COLUMN gid SET DEFAULT nextval('sources.ab_spray_gid_seq'::regclass);


ALTER TABLE ONLY sources.ab_spray_lines ALTER COLUMN gid SET DEFAULT nextval('sources.ab_spray_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.ab_spray_points ALTER COLUMN gid SET DEFAULT nextval('sources.ab_spray_points_gid_seq'::regclass);


ALTER TABLE ONLY sources.ab_stimson ALTER COLUMN gid SET DEFAULT nextval('sources.ab_stimson_gid_seq'::regclass);


ALTER TABLE ONLY sources.ab_stimson_lines ALTER COLUMN gid SET DEFAULT nextval('sources.ab_stimson_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.ab_stimson_points ALTER COLUMN gid SET DEFAULT nextval('sources.ab_stimson_points_gid_seq'::regclass);


ALTER TABLE ONLY sources.afghan ALTER COLUMN gid SET DEFAULT nextval('sources.afghan_gid_seq'::regclass);


ALTER TABLE ONLY sources.afghan_lines ALTER COLUMN gid SET DEFAULT nextval('sources.afghan_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.africa ALTER COLUMN gid SET DEFAULT nextval('sources.africa_gid_seq'::regclass);


ALTER TABLE ONLY sources.africa_lines ALTER COLUMN gid SET DEFAULT nextval('sources.lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.ak ALTER COLUMN gid SET DEFAULT nextval('sources.ak_gid_seq'::regclass);


ALTER TABLE ONLY sources.ak_lines ALTER COLUMN gid SET DEFAULT nextval('sources.ak_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.al_greenwood ALTER COLUMN gid SET DEFAULT nextval('sources.greenwoodalgeology_gid_seq'::regclass);


ALTER TABLE ONLY sources.al_greenwood_lines ALTER COLUMN gid SET DEFAULT nextval('sources.greenwood_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.al_greenwood_points ALTER COLUMN gid SET DEFAULT nextval('sources.greenwood_points_gid_seq'::regclass);


ALTER TABLE ONLY sources.alberta ALTER COLUMN gid SET DEFAULT nextval('sources.alberta_gid_seq'::regclass);


ALTER TABLE ONLY sources.alberta_faults ALTER COLUMN gid SET DEFAULT nextval('sources.alberta_faults_gid_seq'::regclass);


ALTER TABLE ONLY sources.ar_buffalo_nriver ALTER COLUMN gid SET DEFAULT nextval('sources.ar_buffalo_nriver_gid_seq'::regclass);


ALTER TABLE ONLY sources.ar_buffalo_nriver_lines ALTER COLUMN gid SET DEFAULT nextval('sources.ar_buffalo_nriver_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.ar_hasty ALTER COLUMN gid SET DEFAULT nextval('sources.hasty_geo_gid_seq'::regclass);


ALTER TABLE ONLY sources.ar_hasty_lines ALTER COLUMN gid SET DEFAULT nextval('sources.hastylines2_gid_seq'::regclass);


ALTER TABLE ONLY sources.ar_hasty_points ALTER COLUMN gid SET DEFAULT nextval('sources.hasty_points_gid_seq'::regclass);


ALTER TABLE ONLY sources.ar_hotsprings_np ALTER COLUMN gid SET DEFAULT nextval('sources.hotspringsnationalparkgeology_gid_seq'::regclass);


ALTER TABLE ONLY sources.ar_hotsprings_np_lines ALTER COLUMN gid SET DEFAULT nextval('sources.hot_springs_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.ar_hotsprings_np_points ALTER COLUMN gid SET DEFAULT nextval('sources.hot_springs_points_gid_seq'::regclass);


ALTER TABLE ONLY sources.ar_jasper ALTER COLUMN gid SET DEFAULT nextval('sources.jaspergeo_gid_seq'::regclass);


ALTER TABLE ONLY sources.ar_jasper_lines ALTER COLUMN gid SET DEFAULT nextval('sources.jasperlines_gid_seq'::regclass);


ALTER TABLE ONLY sources.ar_ponca ALTER COLUMN gid SET DEFAULT nextval('sources.poncageo_gid_seq'::regclass);


ALTER TABLE ONLY sources.ar_ponca_lines ALTER COLUMN gid SET DEFAULT nextval('sources.poncafaults_gid_seq'::regclass);


ALTER TABLE ONLY sources.arctic ALTER COLUMN gid SET DEFAULT nextval('sources.arctic_newgeom_gid_seq'::regclass);


ALTER TABLE ONLY sources.arctic_lines ALTER COLUMN gid SET DEFAULT nextval('sources.arcticrus_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.arctic_orig ALTER COLUMN gid SET DEFAULT nextval('sources.arctic_gid_seq'::regclass);


ALTER TABLE ONLY sources.australia ALTER COLUMN gid SET DEFAULT nextval('sources.australia_gid_seq'::regclass);


ALTER TABLE ONLY sources.australia2 ALTER COLUMN gid SET DEFAULT nextval('sources.australia2_gid_seq'::regclass);


ALTER TABLE ONLY sources.australia2_faults ALTER COLUMN gid SET DEFAULT nextval('sources.australia2_faults_gid_seq'::regclass);


ALTER TABLE ONLY sources.australia_faults ALTER COLUMN gid SET DEFAULT nextval('sources.australia_faults_gid_seq'::regclass);


ALTER TABLE ONLY sources.az_fredonia ALTER COLUMN gid SET DEFAULT nextval('sources.az_fredonia_polygon_one_gid_seq'::regclass);


ALTER TABLE ONLY sources.az_fredonia_lines ALTER COLUMN gid SET DEFAULT nextval('sources.az_fredonia_lines_one_gid_seq'::regclass);


ALTER TABLE ONLY sources.az_fredonia_points ALTER COLUMN gid SET DEFAULT nextval('sources.az_fredonia_point_two_gid_seq'::regclass);


ALTER TABLE ONLY sources.az_mohave ALTER COLUMN gid SET DEFAULT nextval('sources.mohaveazgeology_gid_seq'::regclass);


ALTER TABLE ONLY sources.az_mohave_lines ALTER COLUMN gid SET DEFAULT nextval('sources.mohavefault_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.az_peachsprings ALTER COLUMN gid SET DEFAULT nextval('sources.mohavecoconinoazgeology_gid_seq'::regclass);


ALTER TABLE ONLY sources.az_peachsprings_lines ALTER COLUMN gid SET DEFAULT nextval('sources.mohavecoconino_faults_gid_seq'::regclass);


ALTER TABLE ONLY sources.az_prescott ALTER COLUMN gid SET DEFAULT nextval('sources.prescottgeology_gid_seq'::regclass);


ALTER TABLE ONLY sources.az_prescott_lines ALTER COLUMN gid SET DEFAULT nextval('sources.prescottlines_gid_seq'::regclass);


ALTER TABLE ONLY sources.az_whitehills ALTER COLUMN gid SET DEFAULT nextval('sources.az_whitehills_gid_seq'::regclass);


ALTER TABLE ONLY sources.az_whitehills_lines ALTER COLUMN gid SET DEFAULT nextval('sources.az_whitehills_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.az_whitehills_points ALTER COLUMN gid SET DEFAULT nextval('sources.az_whitehills_points_gid_seq'::regclass);


ALTER TABLE ONLY sources.az_winslow ALTER COLUMN gid SET DEFAULT nextval('sources.az_winslow_gid_seq'::regclass);


ALTER TABLE ONLY sources.az_winslow_lines ALTER COLUMN gid SET DEFAULT nextval('sources.az_winslow_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.az_winslow_points ALTER COLUMN gid SET DEFAULT nextval('sources.az_winslow_points_gid_seq'::regclass);


ALTER TABLE ONLY sources.bc ALTER COLUMN gid SET DEFAULT nextval('sources.bc_gid_seq'::regclass);


ALTER TABLE ONLY sources.bc_2017 ALTER COLUMN gid SET DEFAULT nextval('sources.bc_2017_gid_seq'::regclass);


ALTER TABLE ONLY sources.bc_2017_lines ALTER COLUMN gid SET DEFAULT nextval('sources.bc_2017_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.bc_2017_quat ALTER COLUMN gid SET DEFAULT nextval('sources.bc_2017_quat_gid_seq'::regclass);


ALTER TABLE ONLY sources.bc_abruzzi ALTER COLUMN gid SET DEFAULT nextval('sources.bc_abruzzi_gid_seq'::regclass);


ALTER TABLE ONLY sources.bc_abruzzi_lines ALTER COLUMN gid SET DEFAULT nextval('sources.bc_abruzzi_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.bc_abruzzi_points ALTER COLUMN gid SET DEFAULT nextval('sources.bc_abruzzi_points_gid_seq'::regclass);


ALTER TABLE ONLY sources.bc_assini ALTER COLUMN gid SET DEFAULT nextval('sources.bc_assini_gid_seq'::regclass);


ALTER TABLE ONLY sources.bc_assini_lines ALTER COLUMN gid SET DEFAULT nextval('sources.bc_assini_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.bc_assini_points ALTER COLUMN gid SET DEFAULT nextval('sources.bc_assini_points_gid_seq'::regclass);


ALTER TABLE ONLY sources.bc_chinook ALTER COLUMN gid SET DEFAULT nextval('sources.bc_chinook_gid_seq'::regclass);


ALTER TABLE ONLY sources.bc_chinook_lines ALTER COLUMN gid SET DEFAULT nextval('sources.bc_chinook_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.bc_chinook_points ALTER COLUMN gid SET DEFAULT nextval('sources.bc_chinook_points_gid_seq'::regclass);


ALTER TABLE ONLY sources.bc_eight ALTER COLUMN gid SET DEFAULT nextval('sources.bc_eight_gid_seq'::regclass);


ALTER TABLE ONLY sources.bc_eight_lines ALTER COLUMN gid SET DEFAULT nextval('sources.bc_eight_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.bc_eight_points ALTER COLUMN gid SET DEFAULT nextval('sources.bc_eight_points_gid_seq'::regclass);


ALTER TABLE ONLY sources.bc_faults ALTER COLUMN gid SET DEFAULT nextval('sources.bc_faults_gid_seq'::regclass);


ALTER TABLE ONLY sources.bc_fernie ALTER COLUMN gid SET DEFAULT nextval('sources.bc_fernie_gid_seq'::regclass);


ALTER TABLE ONLY sources.bc_fernie_lines ALTER COLUMN gid SET DEFAULT nextval('sources.bc_fernie_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.bc_fernie_points ALTER COLUMN gid SET DEFAULT nextval('sources.bc_fernie_points_gid_seq'::regclass);


ALTER TABLE ONLY sources.bc_grayling ALTER COLUMN gid SET DEFAULT nextval('sources.bc_grayling_gid_seq'::regclass);


ALTER TABLE ONLY sources.bc_grayling_lines ALTER COLUMN gid SET DEFAULT nextval('sources.bc_grayling_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.bc_grayling_points ALTER COLUMN gid SET DEFAULT nextval('sources.bc_grayling_points_gid_seq'::regclass);


ALTER TABLE ONLY sources.bc_kananaskis ALTER COLUMN gid SET DEFAULT nextval('sources.bc_kananaskis_gid_seq'::regclass);


ALTER TABLE ONLY sources.bc_kananaskis_lines ALTER COLUMN gid SET DEFAULT nextval('sources.bc_kananaskis_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.bc_kananaskis_points ALTER COLUMN gid SET DEFAULT nextval('sources.bc_kananaskis_points_gid_seq'::regclass);


ALTER TABLE ONLY sources.bc_prudence ALTER COLUMN gid SET DEFAULT nextval('sources.bc_prudence_gid_seq'::regclass);


ALTER TABLE ONLY sources.bc_prudence_lines ALTER COLUMN gid SET DEFAULT nextval('sources.bc_prudence_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.bc_prudence_points ALTER COLUMN gid SET DEFAULT nextval('sources.bc_prudence_points_gid_seq'::regclass);


ALTER TABLE ONLY sources.bc_redfern ALTER COLUMN gid SET DEFAULT nextval('sources.bc_redfern_gid_seq'::regclass);


ALTER TABLE ONLY sources.bc_redfern_lines ALTER COLUMN gid SET DEFAULT nextval('sources.bc_redfern_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.bc_redfern_points ALTER COLUMN gid SET DEFAULT nextval('sources.bc_redfern_points_gid_seq'::regclass);


ALTER TABLE ONLY sources.bc_tangle ALTER COLUMN gid SET DEFAULT nextval('sources.bc_tangle_gid_seq'::regclass);


ALTER TABLE ONLY sources.bc_tangle_lines ALTER COLUMN gid SET DEFAULT nextval('sources.bc_tangle_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.bc_tangle_points ALTER COLUMN gid SET DEFAULT nextval('sources.bc_tangle_points_gid_seq'::regclass);


ALTER TABLE ONLY sources.bc_toad ALTER COLUMN gid SET DEFAULT nextval('sources.bc_toad_gid_seq'::regclass);


ALTER TABLE ONLY sources.bc_toad_lines ALTER COLUMN gid SET DEFAULT nextval('sources.bc_toad_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.bc_toad_ne ALTER COLUMN gid SET DEFAULT nextval('sources.bc_toad_ne_gid_seq'::regclass);


ALTER TABLE ONLY sources.bc_toad_ne_lines ALTER COLUMN gid SET DEFAULT nextval('sources.bc_toad_ne_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.bc_toad_ne_points ALTER COLUMN gid SET DEFAULT nextval('sources.bc_toad_ne_points_gid_seq'::regclass);


ALTER TABLE ONLY sources.bc_toad_points ALTER COLUMN gid SET DEFAULT nextval('sources.bc_toad_points_gid_seq'::regclass);


ALTER TABLE ONLY sources.bc_ware ALTER COLUMN gid SET DEFAULT nextval('sources.bc_ware_gid_seq'::regclass);


ALTER TABLE ONLY sources.bc_ware_lines ALTER COLUMN gid SET DEFAULT nextval('sources.bc_ware_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.bigbend ALTER COLUMN gid SET DEFAULT nextval('sources.bigbend_gid_seq'::regclass);


ALTER TABLE ONLY sources.bigbend_lines ALTER COLUMN gid SET DEFAULT nextval('sources.bigbend_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.blackhills ALTER COLUMN gid SET DEFAULT nextval('sources.blackhillsgeology_gid_seq'::regclass);


ALTER TABLE ONLY sources.blackhills_lines ALTER COLUMN gid SET DEFAULT nextval('sources.blackhills_foldsfaults_gid_seq'::regclass);


ALTER TABLE ONLY sources.boulder ALTER COLUMN gid SET DEFAULT nextval('sources.boulder_gid_seq'::regclass);


ALTER TABLE ONLY sources.boulder_lines ALTER COLUMN gid SET DEFAULT nextval('sources.boulder_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.brazil ALTER COLUMN gid SET DEFAULT nextval('sources.brazil_gid_seq'::regclass);


ALTER TABLE ONLY sources.brazil_lines ALTER COLUMN gid SET DEFAULT nextval('sources.rondinia_dikes_gid_seq'::regclass);


ALTER TABLE ONLY sources.brazil_sp ALTER COLUMN gid SET DEFAULT nextval('sources.brazil_sp_gid_seq'::regclass);


ALTER TABLE ONLY sources.brycecanyon_lines ALTER COLUMN gid SET DEFAULT nextval('sources.brycecanyon_faults_gid_seq'::regclass);


ALTER TABLE ONLY sources.brycecanyonnationalparkgeology ALTER COLUMN gid SET DEFAULT nextval('sources.brycecanyonnationalparkgeology_gid_seq'::regclass);


ALTER TABLE ONLY sources.ca_alameda ALTER COLUMN gid SET DEFAULT nextval('sources.alamedageology2_gid_seq'::regclass);


ALTER TABLE ONLY sources.ca_alameda_lines ALTER COLUMN gid SET DEFAULT nextval('sources.alam_fault_gid_seq'::regclass);


ALTER TABLE ONLY sources.ca_cambria ALTER COLUMN gid SET DEFAULT nextval('sources.cambriacageology_gid_seq'::regclass);


ALTER TABLE ONLY sources.ca_cambria_lines ALTER COLUMN gid SET DEFAULT nextval('sources.cambria_faults_gid_seq'::regclass);


ALTER TABLE ONLY sources.ca_carizoplain ALTER COLUMN gid SET DEFAULT nextval('sources.ca_carizonplains_geo_polygon_gid_seq'::regclass);


ALTER TABLE ONLY sources.ca_carizoplain_lines ALTER COLUMN gid SET DEFAULT nextval('sources.ca_carizonplains_geo_arc_gid_seq'::regclass);


ALTER TABLE ONLY sources.ca_carizoplain_points ALTER COLUMN gid SET DEFAULT nextval('sources.ca_carizonplains_point_gid_seq'::regclass);


ALTER TABLE ONLY sources.ca_contracosta ALTER COLUMN gid SET DEFAULT nextval('sources.contracostageology_gid_seq'::regclass);


ALTER TABLE ONLY sources.ca_contracosta_lines ALTER COLUMN gid SET DEFAULT nextval('sources.contracostafaults_gid_seq'::regclass);


ALTER TABLE ONLY sources.ca_elcajon ALTER COLUMN gid SET DEFAULT nextval('sources.ca_elcajon_geo_polygon_gid_seq'::regclass);


ALTER TABLE ONLY sources.ca_elcajon_lines ALTER COLUMN gid SET DEFAULT nextval('sources.ca_elcajon_geo_arc_gid_seq'::regclass);


ALTER TABLE ONLY sources.ca_funeralmtns ALTER COLUMN gid SET DEFAULT nextval('sources.ca_funeralmtns_gid_seq'::regclass);


ALTER TABLE ONLY sources.ca_funeralmtns_lines ALTER COLUMN gid SET DEFAULT nextval('sources.ca_funeralmtns_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.ca_funeralmtns_points ALTER COLUMN gid SET DEFAULT nextval('sources.ca_funeralmtns_points_gid_seq'::regclass);


ALTER TABLE ONLY sources.ca_long_beach ALTER COLUMN gid SET DEFAULT nextval('sources.long_beach_ca_geo_gid_seq'::regclass);


ALTER TABLE ONLY sources.ca_long_beach_lines ALTER COLUMN gid SET DEFAULT nextval('sources.long_beach_ca_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.ca_long_beach_points ALTER COLUMN gid SET DEFAULT nextval('sources.long_beach_ca_points_gid_seq'::regclass);


ALTER TABLE ONLY sources.ca_los_angeles ALTER COLUMN gid SET DEFAULT nextval('sources.los_angeles_geo_gid_seq'::regclass);


ALTER TABLE ONLY sources.ca_los_angeles_lines ALTER COLUMN gid SET DEFAULT nextval('sources.los_angeles_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.ca_marin ALTER COLUMN gid SET DEFAULT nextval('sources.marin_co_gid_seq'::regclass);


ALTER TABLE ONLY sources.ca_marin_lines ALTER COLUMN gid SET DEFAULT nextval('sources.northbay_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.ca_marin_lines_nad27 ALTER COLUMN gid SET DEFAULT nextval('sources.ca_marin_lines_nad27_gid_seq'::regclass);


ALTER TABLE ONLY sources.ca_marin_nad27 ALTER COLUMN gid SET DEFAULT nextval('sources.ca_marin_nad27_gid_seq'::regclass);


ALTER TABLE ONLY sources.ca_monterey ALTER COLUMN gid SET DEFAULT nextval('sources.ca_monterrey_gid_seq'::regclass);


ALTER TABLE ONLY sources.ca_monterey_lines ALTER COLUMN gid SET DEFAULT nextval('sources.ca_monterey_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.ca_napa ALTER COLUMN gid SET DEFAULT nextval('sources.ca_napa_gid_seq'::regclass);


ALTER TABLE ONLY sources.ca_napa_lines ALTER COLUMN gid SET DEFAULT nextval('sources.ca_napa_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.ca_napa_points ALTER COLUMN gid SET DEFAULT nextval('sources.ca_napa_points_gid_seq'::regclass);


ALTER TABLE ONLY sources.ca_north_santabarb ALTER COLUMN gid SET DEFAULT nextval('sources.nsantabarbgeology_gid_seq'::regclass);


ALTER TABLE ONLY sources.ca_north_santabarb_lines ALTER COLUMN gid SET DEFAULT nextval('sources.nsbarblines2_gid_seq'::regclass);


ALTER TABLE ONLY sources.ca_northeastsanfran ALTER COLUMN gid SET DEFAULT nextval('sources.ca_northeastsanfran_union_gid_new_seq'::regclass);


ALTER TABLE ONLY sources.ca_northeastsanfran_lines ALTER COLUMN gid SET DEFAULT nextval('sources.nesffaults_gid_seq'::regclass);


ALTER TABLE ONLY sources.ca_northofsanfran ALTER COLUMN gid SET DEFAULT nextval('sources.northofsanfrangeology_gid_seq'::regclass);


ALTER TABLE ONLY sources.ca_northofsanfran_lines ALTER COLUMN gid SET DEFAULT nextval('sources.northofsanfranlines_gid_seq'::regclass);


ALTER TABLE ONLY sources.ca_oakland_unioned ALTER COLUMN gid SET DEFAULT nextval('sources.ca_oakland_unioned_gid_seq'::regclass);


ALTER TABLE ONLY sources.ca_oceanside ALTER COLUMN gid SET DEFAULT nextval('sources.table_name_gid_seq'::regclass);


ALTER TABLE ONLY sources.ca_oceanside_lines ALTER COLUMN gid SET DEFAULT nextval('sources.oceanside_ca_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.ca_oceanside_points ALTER COLUMN gid SET DEFAULT nextval('sources.oceanside_pointorn_gid_seq'::regclass);


ALTER TABLE ONLY sources.ca_point_reyes ALTER COLUMN gid SET DEFAULT nextval('sources.ca_point_reyes_gid_seq'::regclass);


ALTER TABLE ONLY sources.ca_providence_mtns ALTER COLUMN gid SET DEFAULT nextval('sources.ca_providence_mtns_gid_seq'::regclass);


ALTER TABLE ONLY sources.ca_providence_mtns_lines ALTER COLUMN gid SET DEFAULT nextval('sources.ca_providence_mtns_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.ca_providence_mtns_points ALTER COLUMN gid SET DEFAULT nextval('sources.ca_providence_mtns_points_gid_seq'::regclass);


ALTER TABLE ONLY sources.ca_providencemountains ALTER COLUMN gid SET DEFAULT nextval('sources.ca_providencemountains_polygon_gid_seq'::regclass);


ALTER TABLE ONLY sources.ca_providencemountains_lines ALTER COLUMN gid SET DEFAULT nextval('sources.ca_providencemountains_arc_gid_seq'::regclass);


ALTER TABLE ONLY sources.ca_san_diego_lines ALTER COLUMN gid SET DEFAULT nextval('sources.san_diego_ca_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.ca_san_diego_points ALTER COLUMN gid SET DEFAULT nextval('sources.san_diego_ca_points_gid_seq'::regclass);


ALTER TABLE ONLY sources.ca_sanberno ALTER COLUMN gid SET DEFAULT nextval('sources.sanberno_gid_seq'::regclass);


ALTER TABLE ONLY sources.ca_sanberno_lines ALTER COLUMN gid SET DEFAULT nextval('sources.sanberno_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.ca_sanjose ALTER COLUMN gid SET DEFAULT nextval('sources.sanjosegeology_gid_seq'::regclass);


ALTER TABLE ONLY sources.ca_sanjose_lines ALTER COLUMN gid SET DEFAULT nextval('sources.sanjoselines_gid_seq'::regclass);


ALTER TABLE ONLY sources.ca_sanmateo ALTER COLUMN gid SET DEFAULT nextval('sources.sanmateogeology_gid_seq'::regclass);


ALTER TABLE ONLY sources.ca_sanmateo_lines ALTER COLUMN gid SET DEFAULT nextval('sources.sanmateofaults_gid_seq'::regclass);


ALTER TABLE ONLY sources.ca_santabarbara ALTER COLUMN gid SET DEFAULT nextval('sources.ca_santabarbara_geol_polygon_gid_seq'::regclass);


ALTER TABLE ONLY sources.ca_santabarbara_lines ALTER COLUMN gid SET DEFAULT nextval('sources.ca_santabarbara_geol_arc_gid_seq'::regclass);


ALTER TABLE ONLY sources.ca_santabarbara_points ALTER COLUMN gid SET DEFAULT nextval('sources.ca_santabarbara_structure_point_gid_seq'::regclass);


ALTER TABLE ONLY sources.ca_santacruz ALTER COLUMN gid SET DEFAULT nextval('sources.santacruz_gid_seq'::regclass);


ALTER TABLE ONLY sources.ca_santacruz_lines ALTER COLUMN gid SET DEFAULT nextval('sources.scruz_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.ca_southsanfran ALTER COLUMN gid SET DEFAULT nextval('sources.southsanfrangeology_gid_seq'::regclass);


ALTER TABLE ONLY sources.ca_southsanfran_lines ALTER COLUMN gid SET DEFAULT nextval('sources.southsanfranlines_gid_seq'::regclass);


ALTER TABLE ONLY sources.ca_yosemite_lines ALTER COLUMN gid SET DEFAULT nextval('sources.ca_yosemite_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.ca_yosemite_units ALTER COLUMN gid SET DEFAULT nextval('sources.ca_yosemite_units_gid_seq'::regclass);


ALTER TABLE ONLY sources.catalunya50k ALTER COLUMN gid SET DEFAULT nextval('sources.catalunya50k_redo_gid_seq'::regclass);


ALTER TABLE ONLY sources.catalunya50k_lines ALTER COLUMN gid SET DEFAULT nextval('sources.catalunya50k_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.co_arkansa_riv ALTER COLUMN gid SET DEFAULT nextval('sources.co_arkansa_riv_gid_seq'::regclass);


ALTER TABLE ONLY sources.co_arkansa_riv_lines ALTER COLUMN gid SET DEFAULT nextval('sources.co_arkansa_riv_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.co_arkansa_riv_points ALTER COLUMN gid SET DEFAULT nextval('sources.co_arkansa_riv_points_gid_seq'::regclass);


ALTER TABLE ONLY sources.co_denver ALTER COLUMN gid SET DEFAULT nextval('sources.denvergeology_gid_seq'::regclass);


ALTER TABLE ONLY sources.co_ftcollins ALTER COLUMN gid SET DEFAULT nextval('sources.co_ftcollins_gid_seq'::regclass);


ALTER TABLE ONLY sources.co_ftcollins_lines ALTER COLUMN gid SET DEFAULT nextval('sources.co_ftcollins_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.co_ftcollins_points ALTER COLUMN gid SET DEFAULT nextval('sources.co_ftcollins_points_gid_seq'::regclass);


ALTER TABLE ONLY sources.co_grandjunction ALTER COLUMN gid SET DEFAULT nextval('sources.grand_junction_geo_gid_seq'::regclass);


ALTER TABLE ONLY sources.co_grandjunction_lines ALTER COLUMN gid SET DEFAULT nextval('sources.grand_junction_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.co_greatsanddunes ALTER COLUMN gid SET DEFAULT nextval('sources.gsd_co_geology_gid_seq'::regclass);


ALTER TABLE ONLY sources.co_greatsanddunes_lines ALTER COLUMN gid SET DEFAULT nextval('sources.co_greatsanddunes_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.co_homestake ALTER COLUMN gid SET DEFAULT nextval('sources.co_homestake_objectid_seq'::regclass);


ALTER TABLE ONLY sources.co_homestake_lines ALTER COLUMN gid SET DEFAULT nextval('sources.co_homestake_lines_objectid_seq'::regclass);


ALTER TABLE ONLY sources.co_homestake_points ALTER COLUMN gid SET DEFAULT nextval('sources.co_homestake_points_objectid_seq'::regclass);


ALTER TABLE ONLY sources.colombia ALTER COLUMN gid SET DEFAULT nextval('sources.colombia_geo_gid_seq'::regclass);


ALTER TABLE ONLY sources.colombia_lines ALTER COLUMN gid SET DEFAULT nextval('sources.colombia_faults_gid_seq'::regclass);


ALTER TABLE ONLY sources.congareenationalpark_lines ALTER COLUMN gid SET DEFAULT nextval('sources.congaree_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.congareenationalparkgeology ALTER COLUMN gid SET DEFAULT nextval('sources.congareenationalparkgeology_gid_seq'::regclass);


ALTER TABLE ONLY sources.dane_co ALTER COLUMN gid SET DEFAULT nextval('sources.dane_co_gid_seq'::regclass);


ALTER TABLE ONLY sources.dane_faults ALTER COLUMN gid SET DEFAULT nextval('sources.dane_faults_gid_seq'::regclass);


ALTER TABLE ONLY sources.dc_lines ALTER COLUMN gid SET DEFAULT nextval('sources.dc_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.denver ALTER COLUMN gid SET DEFAULT nextval('sources.denver_gid_seq'::regclass);


ALTER TABLE ONLY sources.denver_lines ALTER COLUMN gid SET DEFAULT nextval('sources.denver_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.devils_tower ALTER COLUMN gid SET DEFAULT nextval('sources.devils_tower_geo_gid_seq'::regclass);


ALTER TABLE ONLY sources.devils_tower_lines ALTER COLUMN gid SET DEFAULT nextval('sources.devils_tower_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.endikai ALTER COLUMN gid SET DEFAULT nextval('sources.endikai_gid_seq'::regclass);


ALTER TABLE ONLY sources.endikai_lines ALTER COLUMN gid SET DEFAULT nextval('sources.albanel_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.europe_5m ALTER COLUMN gid SET DEFAULT nextval('sources.europe_5m_gid_seq'::regclass);


ALTER TABLE ONLY sources.europe_5m_lines ALTER COLUMN gid SET DEFAULT nextval('sources.europe_5m_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.florissant ALTER COLUMN gid SET DEFAULT nextval('sources.florissant_gid_seq'::regclass);


ALTER TABLE ONLY sources.florissant_lines ALTER COLUMN gid SET DEFAULT nextval('sources."florissant-lines_gid_seq"'::regclass);


ALTER TABLE ONLY sources.france ALTER COLUMN gid SET DEFAULT nextval('sources.france_gid_seq'::regclass);


ALTER TABLE ONLY sources.france_lines ALTER COLUMN gid SET DEFAULT nextval('sources.france_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.geo_lgm ALTER COLUMN gid SET DEFAULT nextval('sources.geo_ice_gid_seq'::regclass);


ALTER TABLE ONLY sources.geo_regions ALTER COLUMN gid SET DEFAULT nextval('sources.geo_regions_gid_seq'::regclass);


ALTER TABLE ONLY sources.geo_regions_canada ALTER COLUMN gid SET DEFAULT nextval('sources.geo_regions_canada_gid_seq'::regclass);


ALTER TABLE ONLY sources.geo_regions_europe ALTER COLUMN gid SET DEFAULT nextval('sources.geo_regions_europe_gid_seq'::regclass);


ALTER TABLE ONLY sources.geo_regions_us ALTER COLUMN gid SET DEFAULT nextval('sources.geo_regions_us_gid_seq'::regclass);


ALTER TABLE ONLY sources.german_nuremburg ALTER COLUMN gid SET DEFAULT nextval('sources.german_nurenburg_gid_seq'::regclass);


ALTER TABLE ONLY sources.german_nuremburg_lines ALTER COLUMN gid SET DEFAULT nextval('sources.german_nuremburg_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.germany ALTER COLUMN gid SET DEFAULT nextval('sources.germanygeology_gid_seq'::regclass);


ALTER TABLE ONLY sources.germany_lines ALTER COLUMN gid SET DEFAULT nextval('sources.glines_gid_seq'::regclass);


ALTER TABLE ONLY sources.glacier_np_lines ALTER COLUMN gid SET DEFAULT nextval('sources.glacier_dikes_gid_seq'::regclass);


ALTER TABLE ONLY sources.glaciernationalparkgeology ALTER COLUMN gid SET DEFAULT nextval('sources.glaciernationalparkgeology_gid_seq'::regclass);


ALTER TABLE ONLY sources.global2 ALTER COLUMN gid SET DEFAULT nextval('sources.global2_gid_seq'::regclass);


ALTER TABLE ONLY sources.global2_lines ALTER COLUMN gid SET DEFAULT nextval('sources.global2_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.global_ecoregions ALTER COLUMN gid SET DEFAULT nextval('sources.global_ecoregions_gid_seq'::regclass);


ALTER TABLE ONLY sources.gmna_faults ALTER COLUMN gid SET DEFAULT nextval('sources.faults_gid_seq'::regclass);


ALTER TABLE ONLY sources.gmus2 ALTER COLUMN gid SET DEFAULT nextval('sources.gmus2_gid_seq'::regclass);


ALTER TABLE ONLY sources.gmus2_lines ALTER COLUMN gid SET DEFAULT nextval('sources.gmus2_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.grandcanyon ALTER COLUMN gid SET DEFAULT nextval('sources.grandcanyon_gid_seq'::regclass);


ALTER TABLE ONLY sources.grandcanyon_lines ALTER COLUMN gid SET DEFAULT nextval('sources.grandcanyon_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.grandcanyon_points ALTER COLUMN gid SET DEFAULT nextval('sources.grandcanyon_points_gid_seq'::regclass);


ALTER TABLE ONLY sources.greatbasinnationalpark_lines ALTER COLUMN gid SET DEFAULT nextval('sources.greatbasin_contacts_faults_gid_seq'::regclass);


ALTER TABLE ONLY sources.greatbasinnationalparkgeology ALTER COLUMN gid SET DEFAULT nextval('sources.greatbasinnationalparkgeology_gid_seq'::regclass);


ALTER TABLE ONLY sources.guam ALTER COLUMN gid SET DEFAULT nextval('sources.guamgeology_gid_seq'::regclass);


ALTER TABLE ONLY sources.gumo ALTER COLUMN gid SET DEFAULT nextval('sources.gumo_gid_seq'::regclass);


ALTER TABLE ONLY sources.gumo_lines ALTER COLUMN gid SET DEFAULT nextval('sources.gumo_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.gumo_points ALTER COLUMN gid SET DEFAULT nextval('sources.gumo_points_gid_seq'::regclass);


ALTER TABLE ONLY sources.hawaii ALTER COLUMN gid SET DEFAULT nextval('sources.hawaii_gid_seq'::regclass);


ALTER TABLE ONLY sources.hawaii_lines ALTER COLUMN gid SET DEFAULT nextval('sources.hawaii_dikes_gid_seq'::regclass);


ALTER TABLE ONLY sources.honduras ALTER COLUMN gid SET DEFAULT nextval('sources.honduras_geo_gid_seq'::regclass);


ALTER TABLE ONLY sources.id_arco ALTER COLUMN gid SET DEFAULT nextval('sources.id_arco_objectid_seq'::regclass);


ALTER TABLE ONLY sources.id_arco_lines ALTER COLUMN gid SET DEFAULT nextval('sources.id_arco_lines_objectid_seq'::regclass);


ALTER TABLE ONLY sources.id_bonners ALTER COLUMN gid SET DEFAULT nextval('sources.id_bonners_objectid_seq'::regclass);


ALTER TABLE ONLY sources.id_bonners_lines ALTER COLUMN gid SET DEFAULT nextval('sources.id_bonners_lines_objectid_seq'::regclass);


ALTER TABLE ONLY sources.id_deadwood ALTER COLUMN gid SET DEFAULT nextval('sources.id_deadwood_gid_seq'::regclass);


ALTER TABLE ONLY sources.id_deadwood_lines ALTER COLUMN gid SET DEFAULT nextval('sources.id_deadwood_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.id_deadwood_points ALTER COLUMN gid SET DEFAULT nextval('sources.id_deadwood_points_gid_seq'::regclass);


ALTER TABLE ONLY sources.id_fairfield ALTER COLUMN gid SET DEFAULT nextval('sources.id_fairfield_objectid_seq'::regclass);


ALTER TABLE ONLY sources.id_fairfield_lines ALTER COLUMN gid SET DEFAULT nextval('sources.id_fairfield_lines_objectid_seq'::regclass);


ALTER TABLE ONLY sources.id_grangeville ALTER COLUMN gid SET DEFAULT nextval('sources.id_grangeville_objectid_seq'::regclass);


ALTER TABLE ONLY sources.id_grangeville_lines ALTER COLUMN gid SET DEFAULT nextval('sources.id_grangeville_lines_objectid_seq'::regclass);


ALTER TABLE ONLY sources.id_idahocity ALTER COLUMN gid SET DEFAULT nextval('sources.id_idahocity_objectid_seq'::regclass);


ALTER TABLE ONLY sources.id_idahocity_lines ALTER COLUMN gid SET DEFAULT nextval('sources.id_idahocity_lines_objectid_seq'::regclass);


ALTER TABLE ONLY sources.id_murphy ALTER COLUMN gid SET DEFAULT nextval('sources.id_murphy_objectid_seq'::regclass);


ALTER TABLE ONLY sources.id_murphy_lines ALTER COLUMN gid SET DEFAULT nextval('sources.id_murphy_lines_objectid_seq'::regclass);


ALTER TABLE ONLY sources.id_salmon ALTER COLUMN objectid SET DEFAULT nextval('sources.id_salmon_objectid_seq'::regclass);


ALTER TABLE ONLY sources.id_salmon ALTER COLUMN gid SET DEFAULT nextval('sources.id_salmon_gid_seq'::regclass);


ALTER TABLE ONLY sources.id_salmon_lines ALTER COLUMN objectid SET DEFAULT nextval('sources.id_salmon_lines_objectid_seq'::regclass);


ALTER TABLE ONLY sources.id_salmon_lines ALTER COLUMN gid SET DEFAULT nextval('sources.id_salmon_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.id_sandpoint ALTER COLUMN gid SET DEFAULT nextval('sources.id_sandpoint_objectid_seq'::regclass);


ALTER TABLE ONLY sources.id_sandpoint_lines ALTER COLUMN gid SET DEFAULT nextval('sources.id_sandpoint_lines_objectid_seq'::regclass);


ALTER TABLE ONLY sources.id_twinfalls ALTER COLUMN gid SET DEFAULT nextval('sources.id_twinfalls_objectid_seq'::regclass);


ALTER TABLE ONLY sources.id_twinfalls_lines ALTER COLUMN gid SET DEFAULT nextval('sources.id_twinfalls_lines_objectid_seq'::regclass);


ALTER TABLE ONLY sources.in_allen ALTER COLUMN gid SET DEFAULT nextval('sources.in_allen_gid_seq'::regclass);


ALTER TABLE ONLY sources.in_lawrence ALTER COLUMN gid SET DEFAULT nextval('sources.in_lawrence_gid_seq'::regclass);


ALTER TABLE ONLY sources.in_lawrence_lines ALTER COLUMN gid SET DEFAULT nextval('sources.in_lawrence_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.in_marion ALTER COLUMN gid SET DEFAULT nextval('sources.in_marion_gid_seq'::regclass);


ALTER TABLE ONLY sources.in_morresville_w ALTER COLUMN gid SET DEFAULT nextval('sources.in_morresville_w_objectid_1_seq'::regclass);


ALTER TABLE ONLY sources.in_swhitleyw ALTER COLUMN gid SET DEFAULT nextval('sources.in_swhitleyw_gid_seq'::regclass);


ALTER TABLE ONLY sources.iowa ALTER COLUMN gid SET DEFAULT nextval('sources.iowa_gid_seq'::regclass);


ALTER TABLE ONLY sources.iowa_co_wi ALTER COLUMN gid SET DEFAULT nextval('sources.iowa_co_wi_gid_seq'::regclass);


ALTER TABLE ONLY sources.iowa_lines ALTER COLUMN gid SET DEFAULT nextval('sources.iowa_lines2_gid_seq'::regclass);


ALTER TABLE ONLY sources.iran ALTER COLUMN gid SET DEFAULT nextval('sources.iran_gid_seq'::regclass);


ALTER TABLE ONLY sources.iran_lines ALTER COLUMN gid SET DEFAULT nextval('sources.iran_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.joshuatree ALTER COLUMN gid SET DEFAULT nextval('sources.joshuatree_gid_seq'::regclass);


ALTER TABLE ONLY sources.joshuatree_faults ALTER COLUMN gid SET DEFAULT nextval('sources.joshuatree_faults_gid_seq'::regclass);


ALTER TABLE ONLY sources.ky24k ALTER COLUMN gid SET DEFAULT nextval('sources.ky24k_gid_seq'::regclass);


ALTER TABLE ONLY sources.ky24k_faults ALTER COLUMN gid SET DEFAULT nextval('sources.ky24k_faults_gid_seq'::regclass);


ALTER TABLE ONLY sources.ky_descrip ALTER COLUMN id SET DEFAULT nextval('sources.ky_descrip_id_seq'::regclass);


ALTER TABLE ONLY sources.lake_mead ALTER COLUMN gid SET DEFAULT nextval('sources.lake_mead_gid_seq'::regclass);


ALTER TABLE ONLY sources.laketahoe ALTER COLUMN gid SET DEFAULT nextval('sources.laketahoe_geology_gid_seq'::regclass);


ALTER TABLE ONLY sources.laketahoe_lines ALTER COLUMN gid SET DEFAULT nextval('sources.laketahoe_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.laketahoe_point ALTER COLUMN gid SET DEFAULT nextval('sources.laketahoe_point_gid_seq'::regclass);


ALTER TABLE ONLY sources.lissadellaustralia ALTER COLUMN gid SET DEFAULT nextval('sources.lissadellaustralia_gid_seq'::regclass);


ALTER TABLE ONLY sources.ma_glouster ALTER COLUMN gid SET DEFAULT nextval('sources.gloucester_rockport_geo2_gid_seq'::regclass);


ALTER TABLE ONLY sources.ma_glouster_lines ALTER COLUMN gid SET DEFAULT nextval('sources.rockport_l2_gid_seq'::regclass);


ALTER TABLE ONLY sources.manitoba ALTER COLUMN gid SET DEFAULT nextval('sources.manitoba_gid_seq'::regclass);


ALTER TABLE ONLY sources.manitoba_faults ALTER COLUMN gid SET DEFAULT nextval('sources.manitoba_faults_gid_seq'::regclass);


ALTER TABLE ONLY sources.md_catocinfurnace ALTER COLUMN gid SET DEFAULT nextval('sources.md_catocinfurnace_gid_seq'::regclass);


ALTER TABLE ONLY sources.md_catocinfurnace_lines ALTER COLUMN gid SET DEFAULT nextval('sources.md_catocinfurnace_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.md_catocinfurnace_points ALTER COLUMN gid SET DEFAULT nextval('sources.md_catocinfurnace_points_gid_seq'::regclass);


ALTER TABLE ONLY sources.md_clearspring ALTER COLUMN gid SET DEFAULT nextval('sources.md_clearspring_gid_seq'::regclass);


ALTER TABLE ONLY sources.md_clearspring_lines ALTER COLUMN gid SET DEFAULT nextval('sources.md_clearspring_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.md_clearspring_points ALTER COLUMN gid SET DEFAULT nextval('sources.md_clearspring_points_gid_seq'::regclass);


ALTER TABLE ONLY sources.md_frederick ALTER COLUMN gid SET DEFAULT nextval('sources.md_frederick_gid_seq'::regclass);


ALTER TABLE ONLY sources.md_frederick_lines ALTER COLUMN gid SET DEFAULT nextval('sources.md_frederick_linestwo_gid_seq'::regclass);


ALTER TABLE ONLY sources.md_frederick_point ALTER COLUMN gid SET DEFAULT nextval('sources.md_frederick_point_gid_seq'::regclass);


ALTER TABLE ONLY sources.md_keedysville ALTER COLUMN gid SET DEFAULT nextval('sources.md_keedysville_gid_seq'::regclass);


ALTER TABLE ONLY sources.md_keedysville_line ALTER COLUMN gid SET DEFAULT nextval('sources."sources.md_keedysville_line_gid_seq"'::regclass);


ALTER TABLE ONLY sources.md_myerssmith ALTER COLUMN gid SET DEFAULT nextval('sources.md_myerssmith_gid_seq'::regclass);


ALTER TABLE ONLY sources.md_myerssmith_lines ALTER COLUMN gid SET DEFAULT nextval('sources.md_myerssmith_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.md_newwindsor ALTER COLUMN gid SET DEFAULT nextval('sources.md_newwindsor_gid_seq'::regclass);


ALTER TABLE ONLY sources.md_newwindsor_lines ALTER COLUMN gid SET DEFAULT nextval('sources.md_newwindsor_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.md_newwindsor_points ALTER COLUMN gid SET DEFAULT nextval('sources.md_newwindsor_points_gid_seq'::regclass);


ALTER TABLE ONLY sources.md_western ALTER COLUMN gid SET DEFAULT nextval('sources.md_western_gid_seq'::regclass);


ALTER TABLE ONLY sources.md_western_lines ALTER COLUMN gid SET DEFAULT nextval('sources.md_western_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.mexico ALTER COLUMN gid SET DEFAULT nextval('sources.mexicogeology_gid_seq'::regclass);


ALTER TABLE ONLY sources.mexico_lines ALTER COLUMN gid SET DEFAULT nextval('sources.mexicolines_gid_seq'::regclass);


ALTER TABLE ONLY sources.mn_houston_co ALTER COLUMN gid SET DEFAULT nextval('sources.mn_houston_co_gid_seq'::regclass);


ALTER TABLE ONLY sources.mn_houston_co_lines ALTER COLUMN gid SET DEFAULT nextval('sources.mn_houston_co_faults_gid_seq'::regclass);


ALTER TABLE ONLY sources.mn_redwood_co ALTER COLUMN gid SET DEFAULT nextval('sources.mn_redwood_co_gid_seq'::regclass);


ALTER TABLE ONLY sources.mn_redwood_co_lines ALTER COLUMN gid SET DEFAULT nextval('sources.mn_redwood_co_faults_gid_seq'::regclass);


ALTER TABLE ONLY sources.mn_washington_co ALTER COLUMN gid SET DEFAULT nextval('sources.mn_washington_co_gid_seq'::regclass);


ALTER TABLE ONLY sources.mn_washington_co_lines ALTER COLUMN gid SET DEFAULT nextval('sources.mn_washington_co_faults_gid_seq'::regclass);


ALTER TABLE ONLY sources.mn_winona_co ALTER COLUMN gid SET DEFAULT nextval('sources.mn_winona_co_gid_seq'::regclass);


ALTER TABLE ONLY sources.mn_winona_co_lines ALTER COLUMN gid SET DEFAULT nextval('sources.mn_winona_co_fold_gid_seq'::regclass);


ALTER TABLE ONLY sources.mt_trumbull ALTER COLUMN gid SET DEFAULT nextval('sources.mt_trumbull_gid_seq'::regclass);


ALTER TABLE ONLY sources.mt_trumbull_lines ALTER COLUMN gid SET DEFAULT nextval('sources.mt_trumbull_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.new_river_gorge ALTER COLUMN gid SET DEFAULT nextval('sources.newrivergorge_geo_gid_seq'::regclass);


ALTER TABLE ONLY sources.new_river_gorge_lines ALTER COLUMN gid SET DEFAULT nextval('sources.new_river_gorge_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.newzealand ALTER COLUMN gid SET DEFAULT nextval('sources.newzealand_gid_seq'::regclass);


ALTER TABLE ONLY sources.newzealand_faults ALTER COLUMN gid SET DEFAULT nextval('sources.newzealand_faults_gid_seq'::regclass);


ALTER TABLE ONLY sources.newzealandq ALTER COLUMN gid SET DEFAULT nextval('sources.newzealandq_gid_seq'::regclass);


ALTER TABLE ONLY sources.newzealandq_dikes ALTER COLUMN gid SET DEFAULT nextval('sources.newzealandq_dikes_gid_seq'::regclass);


ALTER TABLE ONLY sources.newzealandq_faults ALTER COLUMN gid SET DEFAULT nextval('sources.newzealandq_faults_gid_seq'::regclass);


ALTER TABLE ONLY sources.nh_lisbon ALTER COLUMN gid SET DEFAULT nextval('sources.nh_lisbon_gid_seq'::regclass);


ALTER TABLE ONLY sources.nh_lisbon_lines ALTER COLUMN gid SET DEFAULT nextval('sources.nh_lisbon_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.nh_lisbon_points ALTER COLUMN gid SET DEFAULT nextval('sources.nh_lisbon_points_gid_seq'::regclass);


ALTER TABLE ONLY sources.nl_baieverte ALTER COLUMN gid SET DEFAULT nextval('sources.nl_baieverte_gid_seq'::regclass);


ALTER TABLE ONLY sources.nl_baieverte_lines ALTER COLUMN gid SET DEFAULT nextval('sources.nl_baieverte_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.nl_baieverte_points ALTER COLUMN gid SET DEFAULT nextval('sources.nl_baieverte_points_gid_seq'::regclass);


ALTER TABLE ONLY sources.nl_king ALTER COLUMN gid SET DEFAULT nextval('sources.nl_king_gid_seq'::regclass);


ALTER TABLE ONLY sources.nl_king_lines ALTER COLUMN gid SET DEFAULT nextval('sources.nl_king_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.nl_king_points ALTER COLUMN gid SET DEFAULT nextval('sources.nl_king_points_gid_seq'::regclass);


ALTER TABLE ONLY sources.nl_nippers ALTER COLUMN gid SET DEFAULT nextval('sources.nl_nippers_gid_seq'::regclass);


ALTER TABLE ONLY sources.nl_nippers_lines ALTER COLUMN gid SET DEFAULT nextval('sources.nl_nippers_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.nl_nippers_points ALTER COLUMN gid SET DEFAULT nextval('sources.nl_nippers_points_gid_seq'::regclass);


ALTER TABLE ONLY sources.nm_albuquerque ALTER COLUMN gid SET DEFAULT nextval('sources.nm_albuquerque_gid_seq'::regclass);


ALTER TABLE ONLY sources.nm_albuquerque_lines ALTER COLUMN gid SET DEFAULT nextval('sources.nm_albuquerque_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.nm_albuquerque_points ALTER COLUMN gid SET DEFAULT nextval('sources.nm_albuquerque_points_gid_seq'::regclass);


ALTER TABLE ONLY sources.nm_espanola ALTER COLUMN gid SET DEFAULT nextval('sources.nm_espanola_gid_seq'::regclass);


ALTER TABLE ONLY sources.nm_espanola_lines ALTER COLUMN gid SET DEFAULT nextval('sources.nm_espanola_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.nm_espanola_points ALTER COLUMN gid SET DEFAULT nextval('sources.nm_espanola_points_gid_seq'::regclass);


ALTER TABLE ONLY sources.nm_latir ALTER COLUMN gid SET DEFAULT nextval('sources.nm_latir_gid_seq'::regclass);


ALTER TABLE ONLY sources.nm_latir_lines ALTER COLUMN gid SET DEFAULT nextval('sources.nm_latir_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.nm_latir_points ALTER COLUMN gid SET DEFAULT nextval('sources.nm_latir_points_gid_seq'::regclass);


ALTER TABLE ONLY sources.nm_petroglyps ALTER COLUMN gid SET DEFAULT nextval('sources.nm_petroglyps_objectid_seq'::regclass);


ALTER TABLE ONLY sources.nm_petroglyps_lines ALTER COLUMN gid SET DEFAULT nextval('sources.nm_petroglyps_lines_objectid_seq'::regclass);


ALTER TABLE ONLY sources.nm_tularosa ALTER COLUMN gid SET DEFAULT nextval('sources.tularosageo_gid_seq'::regclass);


ALTER TABLE ONLY sources.nm_tularosa_lines ALTER COLUMN gid SET DEFAULT nextval('sources.tularosafaults_gid_seq'::regclass);


ALTER TABLE ONLY sources.nm_vermejo ALTER COLUMN gid SET DEFAULT nextval('sources.nm_vermejo_gid_seq'::regclass);


ALTER TABLE ONLY sources.nm_vermejo_lines ALTER COLUMN gid SET DEFAULT nextval('sources.nm_vermejo_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.nm_vermejo_points ALTER COLUMN gid SET DEFAULT nextval('sources.nm_vermejo_points_gid_seq'::regclass);


ALTER TABLE ONLY sources.nova_scotia ALTER COLUMN gid SET DEFAULT nextval('sources.nova_scotia_geo_gid_seq'::regclass);


ALTER TABLE ONLY sources.nova_scotia_lines ALTER COLUMN gid SET DEFAULT nextval('sources.nova_scotia_faults_gid_seq'::regclass);


ALTER TABLE ONLY sources.nsw_bathurst ALTER COLUMN gid SET DEFAULT nextval('sources.nsw_bathurst_gid_seq'::regclass);


ALTER TABLE ONLY sources.nsw_bathurst_lines ALTER COLUMN gid SET DEFAULT nextval('sources.nsw_bathurst_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.nsw_bogangate ALTER COLUMN gid SET DEFAULT nextval('sources.nsw_bogangate_gid_seq'::regclass);


ALTER TABLE ONLY sources.nsw_bogangate_lines ALTER COLUMN gid SET DEFAULT nextval('sources.nsw_bogangate_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.nsw_boorowa ALTER COLUMN gid SET DEFAULT nextval('sources.nsw_boorowa_gid_seq'::regclass);


ALTER TABLE ONLY sources.nsw_boorowa_lines ALTER COLUMN gid SET DEFAULT nextval('sources.nsw_boorowa_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.nsw_boorowa_points ALTER COLUMN gid SET DEFAULT nextval('sources.nsw_boorowa_points_gid_seq'::regclass);


ALTER TABLE ONLY sources.nsw_bunda ALTER COLUMN gid SET DEFAULT nextval('sources.nsw_bunda_gid_seq'::regclass);


ALTER TABLE ONLY sources.nsw_bunda_lines ALTER COLUMN gid SET DEFAULT nextval('sources.nsw_bunda_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.nsw_bunda_points ALTER COLUMN gid SET DEFAULT nextval('sources.nsw_bunda_points_gid_seq'::regclass);


ALTER TABLE ONLY sources.nsw_cobar ALTER COLUMN gid SET DEFAULT nextval('sources.nsw_cobar_gid_seq'::regclass);


ALTER TABLE ONLY sources.nsw_cobar_lines ALTER COLUMN gid SET DEFAULT nextval('sources.nsw_cobar_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.nsw_cobbora ALTER COLUMN gid SET DEFAULT nextval('sources.nsw_cobbora_gid_seq'::regclass);


ALTER TABLE ONLY sources.nsw_cobbora_lines ALTER COLUMN gid SET DEFAULT nextval('sources.nsw_cobbora_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.nsw_cobbora_points ALTER COLUMN gid SET DEFAULT nextval('sources.nsw_cobbora_points_gid_seq'::regclass);


ALTER TABLE ONLY sources.nsw_cobham ALTER COLUMN gid SET DEFAULT nextval('sources.nsw_cobham_gid_seq'::regclass);


ALTER TABLE ONLY sources.nsw_cobham_lines ALTER COLUMN gid SET DEFAULT nextval('sources.nsw_cobham_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.nsw_cobham_points ALTER COLUMN gid SET DEFAULT nextval('sources.nsw_cobham_points_gid_seq'::regclass);


ALTER TABLE ONLY sources.nsw_cool ALTER COLUMN gid SET DEFAULT nextval('sources.nsw_cool_gid_seq'::regclass);


ALTER TABLE ONLY sources.nsw_cool_lines ALTER COLUMN gid SET DEFAULT nextval('sources.nsw_cool_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.nsw_cool_points ALTER COLUMN gid SET DEFAULT nextval('sources.nsw_cool_points_gid_seq'::regclass);


ALTER TABLE ONLY sources.nsw_gosford ALTER COLUMN gid SET DEFAULT nextval('sources.nsw_gosford_gid_seq'::regclass);


ALTER TABLE ONLY sources.nsw_gosford_lines ALTER COLUMN gid SET DEFAULT nextval('sources.nsw_gosford_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.nsw_gosford_points ALTER COLUMN gid SET DEFAULT nextval('sources.nsw_gosford_points_gid_seq'::regclass);


ALTER TABLE ONLY sources.nsw_goul ALTER COLUMN gid SET DEFAULT nextval('sources.nsw_goul_gid_seq'::regclass);


ALTER TABLE ONLY sources.nsw_goul_lines ALTER COLUMN gid SET DEFAULT nextval('sources.nsw_goul_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.nsw_goul_points ALTER COLUMN gid SET DEFAULT nextval('sources.nsw_goul_points_gid_seq'::regclass);


ALTER TABLE ONLY sources.nsw_sussex ALTER COLUMN gid SET DEFAULT nextval('sources.nsw_sussex_gid_seq'::regclass);


ALTER TABLE ONLY sources.nsw_sussex_lines ALTER COLUMN gid SET DEFAULT nextval('sources.nsw_sussex_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.nsw_sussex_points ALTER COLUMN gid SET DEFAULT nextval('sources.nsw_sussex_points_gid_seq'::regclass);


ALTER TABLE ONLY sources.nsw_wonnaminta ALTER COLUMN gid SET DEFAULT nextval('sources.nsw_wonnaminta_gid_seq'::regclass);


ALTER TABLE ONLY sources.nsw_wonnaminta_lines ALTER COLUMN gid SET DEFAULT nextval('sources.nsw_wonnaminta_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.nsw_wonnaminta_points ALTER COLUMN gid SET DEFAULT nextval('sources.nsw_wonnaminta_points_gid_seq'::regclass);


ALTER TABLE ONLY sources.nu_chidliak_n ALTER COLUMN gid SET DEFAULT nextval('sources.nu_chidliak_n_gid_seq'::regclass);


ALTER TABLE ONLY sources.nu_chidliak_s ALTER COLUMN gid SET DEFAULT nextval('sources.nu_chidliak_s_gid_seq'::regclass);


ALTER TABLE ONLY sources.nu_chidliak_s_lines ALTER COLUMN gid SET DEFAULT nextval('sources.nu_chidliak_s_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.nu_circle ALTER COLUMN gid SET DEFAULT nextval('sources.nu_circle_gid_seq'::regclass);


ALTER TABLE ONLY sources.nu_circle_lines ALTER COLUMN gid SET DEFAULT nextval('sources.nu_circle_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.nu_circle_points ALTER COLUMN gid SET DEFAULT nextval('sources.nu_circle_points_gid_seq'::regclass);


ALTER TABLE ONLY sources.nu_ellef_s ALTER COLUMN gid SET DEFAULT nextval('sources.nu_ellef_s_gid_seq'::regclass);


ALTER TABLE ONLY sources.nu_ellef_s_lines ALTER COLUMN gid SET DEFAULT nextval('sources.nu_ellef_s_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.nu_ellef_s_points ALTER COLUMN gid SET DEFAULT nextval('sources.nu_ellef_s_points_gid_seq'::regclass);


ALTER TABLE ONLY sources.nu_grinnell ALTER COLUMN gid SET DEFAULT nextval('sources.nu_grinnell_gid_seq'::regclass);


ALTER TABLE ONLY sources.nu_grinnell_lines ALTER COLUMN gid SET DEFAULT nextval('sources.nu_grinnell_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.nu_grinnell_points ALTER COLUMN gid SET DEFAULT nextval('sources.nu_grinnell_points_gid_seq'::regclass);


ALTER TABLE ONLY sources.nu_irvine_s ALTER COLUMN gid SET DEFAULT nextval('sources.nu_irvine_s_gid_seq'::regclass);


ALTER TABLE ONLY sources.nu_irvine_s_lines ALTER COLUMN gid SET DEFAULT nextval('sources.nu_irvine_s_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.nu_irvine_s_points ALTER COLUMN gid SET DEFAULT nextval('sources.nu_irvine_s_points_gid_seq'::regclass);


ALTER TABLE ONLY sources.nu_mumiksaa ALTER COLUMN gid SET DEFAULT nextval('sources.nu_mumiksaa_gid_seq'::regclass);


ALTER TABLE ONLY sources.nu_mumiksaa_lines ALTER COLUMN gid SET DEFAULT nextval('sources.nu_mumiksaa_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.nu_mumiksaa_points ALTER COLUMN gid SET DEFAULT nextval('sources.nu_mumiksaa_points_gid_seq'::regclass);


ALTER TABLE ONLY sources.nu_paquet ALTER COLUMN gid SET DEFAULT nextval('sources.nu_paquet_gid_seq'::regclass);


ALTER TABLE ONLY sources.nu_paquet_lines ALTER COLUMN gid SET DEFAULT nextval('sources.nu_paquet_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.nu_paquet_points ALTER COLUMN gid SET DEFAULT nextval('sources.nu_paquet_points_gid_seq'::regclass);


ALTER TABLE ONLY sources.nu_pritzler ALTER COLUMN gid SET DEFAULT nextval('sources.nu_pritzler_gid_seq'::regclass);


ALTER TABLE ONLY sources.nu_pritzler_lines ALTER COLUMN gid SET DEFAULT nextval('sources.nu_pritzler_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.nu_pritzler_points ALTER COLUMN gid SET DEFAULT nextval('sources.nu_pritzler_points_gid_seq'::regclass);


ALTER TABLE ONLY sources.nu_rae ALTER COLUMN gid SET DEFAULT nextval('sources.nu_rae_gid_seq'::regclass);


ALTER TABLE ONLY sources.nu_rae_lines ALTER COLUMN gid SET DEFAULT nextval('sources.nu_rae_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.nu_sunneshine ALTER COLUMN gid SET DEFAULT nextval('sources.nu_sunneshine_gid_seq'::regclass);


ALTER TABLE ONLY sources.nu_sunneshine_lines ALTER COLUMN gid SET DEFAULT nextval('sources.nu_sunneshine_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.nu_sunneshine_points ALTER COLUMN gid SET DEFAULT nextval('sources.nu_sunneshine_points_gid_seq'::regclass);


ALTER TABLE ONLY sources.nu_sylvia_s ALTER COLUMN gid SET DEFAULT nextval('sources.nu_sylvia_s_gid_seq'::regclass);


ALTER TABLE ONLY sources.nu_sylvia_s_lines ALTER COLUMN gid SET DEFAULT nextval('sources.nu_sylvia_s_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.nu_sylvia_s_points ALTER COLUMN gid SET DEFAULT nextval('sources.nu_sylvia_s_points_gid_seq'::regclass);


ALTER TABLE ONLY sources.nu_tebesjuak ALTER COLUMN gid SET DEFAULT nextval('sources.nu_tebesjuak_gid_seq'::regclass);


ALTER TABLE ONLY sources.nu_tebesjuak_lines ALTER COLUMN gid SET DEFAULT nextval('sources.nu_tebesjuak_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.nu_tebesjuak_points ALTER COLUMN gid SET DEFAULT nextval('sources.nu_tebesjuak_points_gid_seq'::regclass);


ALTER TABLE ONLY sources.nu_terra ALTER COLUMN gid SET DEFAULT nextval('sources.nu_terra_gid_seq'::regclass);


ALTER TABLE ONLY sources.nu_terra_lines ALTER COLUMN gid SET DEFAULT nextval('sources.nu_terra_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.nu_terra_points ALTER COLUMN gid SET DEFAULT nextval('sources.nu_terra_points_gid_seq'::regclass);


ALTER TABLE ONLY sources.nv_las_vegas_lines ALTER COLUMN gid SET DEFAULT nextval('sources.nv_las_vegas_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.nv_las_vegas_units ALTER COLUMN gid SET DEFAULT nextval('sources.nv_las_vegas_units_gid_seq'::regclass);


ALTER TABLE ONLY sources.nw_lacmaunoir ALTER COLUMN gid SET DEFAULT nextval('sources.nw_lacmaunoir_gid_seq'::regclass);


ALTER TABLE ONLY sources.nw_lacmaunoir_drift ALTER COLUMN gid SET DEFAULT nextval('sources.nw_lacmaunoir_drift_gid_seq'::regclass);


ALTER TABLE ONLY sources.nw_lacmaunoir_folds ALTER COLUMN gid SET DEFAULT nextval('sources.nw_lacmaunoir_folds_gid_seq'::regclass);


ALTER TABLE ONLY sources.nw_lacmaunoir_points ALTER COLUMN gid SET DEFAULT nextval('sources.nw_lacmaunoir_points_gid_seq'::regclass);


ALTER TABLE ONLY sources.nw_slave_lines ALTER COLUMN gid SET DEFAULT nextval('sources.nw_slave_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.nw_slave_rv ALTER COLUMN gid SET DEFAULT nextval('sources.nw_slave_rv_gid_seq'::regclass);


ALTER TABLE ONLY sources.nwt_calder ALTER COLUMN gid SET DEFAULT nextval('sources.nwt_calder_gid_seq'::regclass);


ALTER TABLE ONLY sources.nwt_calder_lines ALTER COLUMN gid SET DEFAULT nextval('sources.nwt_calder_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.nwt_calder_points ALTER COLUMN gid SET DEFAULT nextval('sources.nwt_calder_points_gid_seq'::regclass);


ALTER TABLE ONLY sources.nwt_campbell ALTER COLUMN gid SET DEFAULT nextval('sources.nwt_campbell_gid_seq'::regclass);


ALTER TABLE ONLY sources.nwt_campbell_lines ALTER COLUMN gid SET DEFAULT nextval('sources.nwt_campbell_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.nwt_campbell_points ALTER COLUMN gid SET DEFAULT nextval('sources.nwt_campbell_points_gid_seq'::regclass);


ALTER TABLE ONLY sources.nwt_carcajou ALTER COLUMN gid SET DEFAULT nextval('sources.nwt_carcajou_gid_seq'::regclass);


ALTER TABLE ONLY sources.nwt_carcajou_lines ALTER COLUMN gid SET DEFAULT nextval('sources.nwt_carcajou_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.nwt_carcajou_ne ALTER COLUMN gid SET DEFAULT nextval('sources.nwt_carcajou_ne_gid_seq'::regclass);


ALTER TABLE ONLY sources.nwt_carcajou_ne_lines ALTER COLUMN gid SET DEFAULT nextval('sources.nwt_carcajou_ne_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.nwt_carcajou_ne_points ALTER COLUMN gid SET DEFAULT nextval('sources.nwt_carcajou_ne_points_gid_seq'::regclass);


ALTER TABLE ONLY sources.nwt_carcajou_points ALTER COLUMN gid SET DEFAULT nextval('sources.nwt_carcajou_points_gid_seq'::regclass);


ALTER TABLE ONLY sources.nwt_carcajou_se ALTER COLUMN gid SET DEFAULT nextval('sources.nwt_carcajou_se_gid_seq'::regclass);


ALTER TABLE ONLY sources.nwt_carcajou_se_lines ALTER COLUMN gid SET DEFAULT nextval('sources.nwt_carcajou_se_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.nwt_carcajou_se_points ALTER COLUMN gid SET DEFAULT nextval('sources.nwt_carcajou_se_points_gid_seq'::regclass);


ALTER TABLE ONLY sources.nwt_carcajou_sw ALTER COLUMN gid SET DEFAULT nextval('sources.nwt_carcajou_sw_gid_seq'::regclass);


ALTER TABLE ONLY sources.nwt_carcajou_sw_lines ALTER COLUMN gid SET DEFAULT nextval('sources.nwt_carcajou_sw_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.nwt_carcajou_sw_points ALTER COLUMN gid SET DEFAULT nextval('sources.nwt_carcajou_sw_points_gid_seq'::regclass);


ALTER TABLE ONLY sources.nwt_mahony_sw ALTER COLUMN gid SET DEFAULT nextval('sources.nwt_mahony_sw_gid_seq'::regclass);


ALTER TABLE ONLY sources.nwt_mahony_sw_lines ALTER COLUMN gid SET DEFAULT nextval('sources.nwt_mahony_sw_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.nwt_mahony_sw_points ALTER COLUMN gid SET DEFAULT nextval('sources.nwt_mahony_sw_points_gid_seq'::regclass);


ALTER TABLE ONLY sources.nwt_norman_nw ALTER COLUMN gid SET DEFAULT nextval('sources.nwt_norman_nw_gid_seq'::regclass);


ALTER TABLE ONLY sources.nwt_norman_nw_lines ALTER COLUMN gid SET DEFAULT nextval('sources.nwt_norman_nw_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.nwt_norman_nw_points ALTER COLUMN gid SET DEFAULT nextval('sources.nwt_norman_nw_points_gid_seq'::regclass);


ALTER TABLE ONLY sources.nwt_norman_se ALTER COLUMN gid SET DEFAULT nextval('sources.nwt_norman_se_gid_seq'::regclass);


ALTER TABLE ONLY sources.nwt_norman_se_lines ALTER COLUMN gid SET DEFAULT nextval('sources.nwt_norman_se_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.nwt_norman_se_points ALTER COLUMN gid SET DEFAULT nextval('sources.nwt_norman_se_points_gid_seq'::regclass);


ALTER TABLE ONLY sources.nwt_taki ALTER COLUMN gid SET DEFAULT nextval('sources.nwt_taki_gid_seq'::regclass);


ALTER TABLE ONLY sources.nwt_taki_lines ALTER COLUMN gid SET DEFAULT nextval('sources.nwt_taki_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.nwt_taki_points ALTER COLUMN gid SET DEFAULT nextval('sources.nwt_taki_points_gid_seq'::regclass);


ALTER TABLE ONLY sources.ontario ALTER COLUMN gid SET DEFAULT nextval('sources.ontario_gid_seq'::regclass);


ALTER TABLE ONLY sources.ontario_dikes ALTER COLUMN gid SET DEFAULT nextval('sources.ontario_dikes_gid_seq'::regclass);


ALTER TABLE ONLY sources.ontario_pz ALTER COLUMN gid SET DEFAULT nextval('sources.paleo_poly_polygon_objectid_seq'::regclass);


ALTER TABLE ONLY sources.ontario_pz_lines ALTER COLUMN gid SET DEFAULT nextval('sources.paleo_fault_arc_objectid_seq'::regclass);


ALTER TABLE ONLY sources.ontario_pz_mod ALTER COLUMN gid SET DEFAULT nextval('sources.ontario_pz_mod_gid_seq'::regclass);


ALTER TABLE ONLY sources.ontario_pz_points ALTER COLUMN gid SET DEFAULT nextval('sources.paleo_point_point_objectid_seq'::regclass);


ALTER TABLE ONLY sources.oregon ALTER COLUMN gid SET DEFAULT nextval('sources.oregon_gid_seq'::regclass);


ALTER TABLE ONLY sources.oregon_faults ALTER COLUMN gid SET DEFAULT nextval('sources.oregon_faults_gid_seq'::regclass);


ALTER TABLE ONLY sources.pakistan_westcentral ALTER COLUMN gid SET DEFAULT nextval('sources.westcentralpakistangeology_gid_seq'::regclass);


ALTER TABLE ONLY sources.pakistan_westcentral_lines ALTER COLUMN gid SET DEFAULT nextval('sources.wpakistan_faults_gid_seq'::regclass);


ALTER TABLE ONLY sources.puerto_rico ALTER COLUMN gid SET DEFAULT nextval('sources.puerto_rico_gid_seq'::regclass);


ALTER TABLE ONLY sources.puerto_rico_lines ALTER COLUMN gid SET DEFAULT nextval('sources.puertorico_nfaults_gid_seq'::regclass);


ALTER TABLE ONLY sources.rockies ALTER COLUMN gid SET DEFAULT nextval('sources.rockies_gid_seq'::regclass);


ALTER TABLE ONLY sources.rockies_lines ALTER COLUMN gid SET DEFAULT nextval('sources.rockies_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.rockymountainnationalparkgeology ALTER COLUMN gid SET DEFAULT nextval('sources.rockymountainnationalparkgeology_gid_seq'::regclass);


ALTER TABLE ONLY sources.rockymtn_np_lines ALTER COLUMN gid SET DEFAULT nextval('sources.rockymtn_faults_gid_seq'::regclass);


ALTER TABLE ONLY sources.saipan ALTER COLUMN gid SET DEFAULT nextval('sources.marianaislandsgeology_gid_seq'::regclass);


ALTER TABLE ONLY sources.saipan_lines ALTER COLUMN gid SET DEFAULT nextval('sources.saipan_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.san_salvador ALTER COLUMN gid SET DEFAULT nextval('sources.san_salvador_geo_gid_seq'::regclass);


ALTER TABLE ONLY sources.saskatchewan ALTER COLUMN gid SET DEFAULT nextval('sources.saskatchewan_gid_seq'::regclass);


ALTER TABLE ONLY sources.saskatchewan_dikes ALTER COLUMN gid SET DEFAULT nextval('sources.saskatchewan_dikes_gid_seq'::regclass);


ALTER TABLE ONLY sources.smokies ALTER COLUMN gid SET DEFAULT nextval('sources.smokies_gid_seq'::regclass);


ALTER TABLE ONLY sources.smokies_lines ALTER COLUMN gid SET DEFAULT nextval('sources.smokymountainsnationalpark_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.so_africa ALTER COLUMN gid SET DEFAULT nextval('sources.so_africa_gid_seq'::regclass);


ALTER TABLE ONLY sources.so_africa_lines ALTER COLUMN gid SET DEFAULT nextval('sources.so_africa_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.spain ALTER COLUMN gid SET DEFAULT nextval('sources.spainpbgeology_gid_seq'::regclass);


ALTER TABLE ONLY sources.spain_lines ALTER COLUMN gid SET DEFAULT nextval('sources.spainlines1_gid_seq'::regclass);


ALTER TABLE ONLY sources.sweden ALTER COLUMN gid SET DEFAULT nextval('sources.swedengeology2_gid_seq'::regclass);


ALTER TABLE ONLY sources.sweden_lines ALTER COLUMN gid SET DEFAULT nextval('sources.sweden_faults_gid_seq'::regclass);


ALTER TABLE ONLY sources.switzerland ALTER COLUMN gid SET DEFAULT nextval('sources.switzerland_gid_seq'::regclass);


ALTER TABLE ONLY sources.switzerland_lines ALTER COLUMN gid SET DEFAULT nextval('sources.switzerland_faults_gid_seq'::regclass);


ALTER TABLE ONLY sources.tanzania_oldonyo ALTER COLUMN gid SET DEFAULT nextval('sources.tanzania_geo2_gid_seq'::regclass);


ALTER TABLE ONLY sources.tanzania_oldonyo_lines ALTER COLUMN gid SET DEFAULT nextval('sources.tanzania_structures_gid_seq'::regclass);


ALTER TABLE ONLY sources.texas_mexico ALTER COLUMN gid SET DEFAULT nextval('sources.stexasmexicogeology_gid_seq'::regclass);


ALTER TABLE ONLY sources.texas_mexico_lines ALTER COLUMN gid SET DEFAULT nextval('sources.stexasmexico_geolines_gid_seq'::regclass);


ALTER TABLE ONLY sources.twincitiesmn_lines ALTER COLUMN gid SET DEFAULT nextval('sources.twincities_faults_gid_seq'::regclass);


ALTER TABLE ONLY sources.twincitiesmngeology ALTER COLUMN gid SET DEFAULT nextval('sources.twincitiesmngeology_gid_seq'::regclass);


ALTER TABLE ONLY sources.tx_bexar ALTER COLUMN gid SET DEFAULT nextval('sources.tx_bexar_gid_seq'::regclass);


ALTER TABLE ONLY sources.tx_bexar_lines ALTER COLUMN gid SET DEFAULT nextval('sources.tx_bexar_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.tx_blanco ALTER COLUMN gid SET DEFAULT nextval('sources.tx_blanco_gid_seq'::regclass);


ALTER TABLE ONLY sources.tx_blanco_lines ALTER COLUMN gid SET DEFAULT nextval('sources.tx_blanco_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.tx_chisos ALTER COLUMN gid SET DEFAULT nextval('sources.tx_chisos_gid_seq'::regclass);


ALTER TABLE ONLY sources.tx_chisos_lines ALTER COLUMN gid SET DEFAULT nextval('sources.tx_chisos_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.tx_chisos_points ALTER COLUMN gid SET DEFAULT nextval('sources.tx_chisos_points_gid_seq'::regclass);


ALTER TABLE ONLY sources.tx_hays ALTER COLUMN gid SET DEFAULT nextval('sources.tx_hays_gid_seq'::regclass);


ALTER TABLE ONLY sources.tx_hays_lines ALTER COLUMN gid SET DEFAULT nextval('sources.tx_hays_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.tx_laredo ALTER COLUMN gid SET DEFAULT nextval('sources.tx_laredo_gid_seq'::regclass);


ALTER TABLE ONLY sources.tx_laredo_lines ALTER COLUMN gid SET DEFAULT nextval('sources.tx_laredo_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.tx_laredo_points ALTER COLUMN gid SET DEFAULT nextval('sources.tx_laredo_points_gid_seq'::regclass);


ALTER TABLE ONLY sources.uk ALTER COLUMN gid SET DEFAULT nextval('sources.uk_gid_seq'::regclass);


ALTER TABLE ONLY sources.uk_lines ALTER COLUMN gid SET DEFAULT nextval('sources.uk_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.usgs_world ALTER COLUMN gid SET DEFAULT nextval('sources.usgs_world_gid_seq'::regclass);


ALTER TABLE ONLY sources.usgs_world_lines ALTER COLUMN gid SET DEFAULT nextval('sources.usgs_world_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.ut_beaver ALTER COLUMN gid SET DEFAULT nextval('sources.ut_beaver_objectid_seq'::regclass);


ALTER TABLE ONLY sources.ut_beaver_lines ALTER COLUMN gid SET DEFAULT nextval('sources.ut_beaver_lines_objectid_seq'::regclass);


ALTER TABLE ONLY sources.ut_delta ALTER COLUMN gid SET DEFAULT nextval('sources.deltautah_gid_seq'::regclass);


ALTER TABLE ONLY sources.ut_delta_lines ALTER COLUMN gid SET DEFAULT nextval('sources.delta_faults_gid_seq'::regclass);


ALTER TABLE ONLY sources.ut_dugway ALTER COLUMN gid SET DEFAULT nextval('sources.ut_dugwayprovinggrounds_gid_seq'::regclass);


ALTER TABLE ONLY sources.ut_dugway_lines ALTER COLUMN gid SET DEFAULT nextval('sources.ut_dugwayprovinggrounds_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.ut_dugway_points ALTER COLUMN gid SET DEFAULT nextval('sources.ut_dugwayprovinggrounds_points_gid_seq'::regclass);


ALTER TABLE ONLY sources.ut_dutchjohn ALTER COLUMN gid SET DEFAULT nextval('sources.dutchjohn_gid_seq'::regclass);


ALTER TABLE ONLY sources.ut_dutchjohn_lines ALTER COLUMN gid SET DEFAULT nextval('sources.dutchjohn_faults_gid_seq'::regclass);


ALTER TABLE ONLY sources.ut_escalante ALTER COLUMN gid SET DEFAULT nextval('sources.ut_escalante_gid_seq'::regclass);


ALTER TABLE ONLY sources.ut_escalante_lines ALTER COLUMN gid SET DEFAULT nextval('sources.ut_escalante_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.ut_huntington ALTER COLUMN gid SET DEFAULT nextval('sources.huntingtonutahgeology_gid_seq'::regclass);


ALTER TABLE ONLY sources.ut_huntington_lines ALTER COLUMN gid SET DEFAULT nextval('sources.huntington_faults_gid_seq'::regclass);


ALTER TABLE ONLY sources.ut_kanab ALTER COLUMN gid SET DEFAULT nextval('sources.ut_kanab_gid_seq'::regclass);


ALTER TABLE ONLY sources.ut_kanab_lines ALTER COLUMN gid SET DEFAULT nextval('sources.ut_kanab_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.ut_lasal ALTER COLUMN gid SET DEFAULT nextval('sources.ut_lasal_gid_seq'::regclass);


ALTER TABLE ONLY sources.ut_lasal_lines ALTER COLUMN gid SET DEFAULT nextval('sources.ut_lasal_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.ut_logan ALTER COLUMN gid SET DEFAULT nextval('sources.ut_logan_gid_seq'::regclass);


ALTER TABLE ONLY sources.ut_logan_lines ALTER COLUMN gid SET DEFAULT nextval('sources.logan_faults_gid_seq'::regclass);


ALTER TABLE ONLY sources.ut_lynndyl ALTER COLUMN gid SET DEFAULT nextval('sources.ut_lynndyl_gid_seq'::regclass);


ALTER TABLE ONLY sources.ut_lynndyl_lines ALTER COLUMN gid SET DEFAULT nextval('sources.ut_lynndyl_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.ut_manti ALTER COLUMN gid SET DEFAULT nextval('sources.mantiutgeology_gid_seq'::regclass);


ALTER TABLE ONLY sources.ut_manti_lines ALTER COLUMN gid SET DEFAULT nextval('sources.manti_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.ut_moab ALTER COLUMN gid SET DEFAULT nextval('sources.ut_moab_gid_seq'::regclass);


ALTER TABLE ONLY sources.ut_moab_lines ALTER COLUMN gid SET DEFAULT nextval('sources.ut_moab_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.ut_nephi ALTER COLUMN gid SET DEFAULT nextval('sources.nephiutahgeology_gid_seq'::regclass);


ALTER TABLE ONLY sources.ut_nephi_lines ALTER COLUMN gid SET DEFAULT nextval('sources.nephi_faults_gid_seq'::regclass);


ALTER TABLE ONLY sources.ut_ogden ALTER COLUMN gid SET DEFAULT nextval('sources.ut_ogden_gid_seq'::regclass);


ALTER TABLE ONLY sources.ut_ogden_lines ALTER COLUMN gid SET DEFAULT nextval('sources.ut_ogden_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.ut_ogden_points ALTER COLUMN gid SET DEFAULT nextval('sources.ut_ogden_points_gid_seq'::regclass);


ALTER TABLE ONLY sources.ut_panguitch ALTER COLUMN gid SET DEFAULT nextval('sources.ut_panguitch_gid_seq'::regclass);


ALTER TABLE ONLY sources.ut_panguitch_lines ALTER COLUMN gid SET DEFAULT nextval('sources.ut_panguitch_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.ut_price ALTER COLUMN gid SET DEFAULT nextval('sources.price_gid_seq'::regclass);


ALTER TABLE ONLY sources.ut_price_lines ALTER COLUMN gid SET DEFAULT nextval('sources.ut_price_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.ut_prommontorymtns ALTER COLUMN gid SET DEFAULT nextval('sources.ut_prommontorymtns_objectid_seq'::regclass);


ALTER TABLE ONLY sources.ut_prommontorymtns_folds ALTER COLUMN gid SET DEFAULT nextval('sources.ut_prommontorymtns_folds_objectid_seq'::regclass);


ALTER TABLE ONLY sources.ut_prommontorymtns_points ALTER COLUMN gid SET DEFAULT nextval('sources.ut_prommontorymtns_points_objectid_seq'::regclass);


ALTER TABLE ONLY sources.ut_provo ALTER COLUMN gid SET DEFAULT nextval('sources.provoutahgeology_gid_seq'::regclass);


ALTER TABLE ONLY sources.ut_provo_lines ALTER COLUMN gid SET DEFAULT nextval('sources.provo_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.ut_richfield ALTER COLUMN gid SET DEFAULT nextval('sources.richfieldutgeology_gid_seq'::regclass);


ALTER TABLE ONLY sources.ut_richfield_lines ALTER COLUMN gid SET DEFAULT nextval('sources.richfield_faults_gid_seq'::regclass);


ALTER TABLE ONLY sources.ut_salina ALTER COLUMN gid SET DEFAULT nextval('sources.ut_salina_gid_seq'::regclass);


ALTER TABLE ONLY sources.ut_salina_lines ALTER COLUMN gid SET DEFAULT nextval('sources.ut_salina_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.ut_salina_points ALTER COLUMN gid SET DEFAULT nextval('sources.ut_salina_points_gid_seq'::regclass);


ALTER TABLE ONLY sources.ut_saltlake ALTER COLUMN gid SET DEFAULT nextval('sources.ut_saltlake_gid_seq'::regclass);


ALTER TABLE ONLY sources.ut_saltlake_lines ALTER COLUMN gid SET DEFAULT nextval('sources.ut_saltlake_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.ut_seepridge ALTER COLUMN gid SET DEFAULT nextval('sources.ut_seepridge_gid_seq'::regclass);


ALTER TABLE ONLY sources.ut_seepridge_lines ALTER COLUMN gid SET DEFAULT nextval('sources.seepridge_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.ut_smokymtns ALTER COLUMN gid SET DEFAULT nextval('sources.smokymtnsutgeology_gid_seq'::regclass);


ALTER TABLE ONLY sources.ut_smokymtns_lines ALTER COLUMN gid SET DEFAULT nextval('sources.smkymtns_faults_gid_seq'::regclass);


ALTER TABLE ONLY sources.ut_stgeorge ALTER COLUMN gid SET DEFAULT nextval('sources.ut_stgeorge_gid_seq'::regclass);


ALTER TABLE ONLY sources.ut_stgeorge_lines ALTER COLUMN gid SET DEFAULT nextval('sources.ut_stgeorge_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.ut_tooele ALTER COLUMN gid SET DEFAULT nextval('sources.ut_tooele_gid_seq'::regclass);


ALTER TABLE ONLY sources.ut_tooele_lines ALTER COLUMN gid SET DEFAULT nextval('sources.ut_tooele_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.ut_tooele_points ALTER COLUMN gid SET DEFAULT nextval('sources.ut_tooele_points_gid_seq'::regclass);


ALTER TABLE ONLY sources.ut_tulevalley ALTER COLUMN gid SET DEFAULT nextval('sources.tulevalleyutgeology_gid_seq'::regclass);


ALTER TABLE ONLY sources.ut_tulevalley_lines ALTER COLUMN gid SET DEFAULT nextval('sources.tulevalley_faults_gid_seq'::regclass);


ALTER TABLE ONLY sources.ut_vernal ALTER COLUMN gid SET DEFAULT nextval('sources.vernalutahgeology_gid_seq'::regclass);


ALTER TABLE ONLY sources.ut_vernal_lines ALTER COLUMN gid SET DEFAULT nextval('sources.vernal_faults_gid_seq'::regclass);


ALTER TABLE ONLY sources.ut_wahwahmtns ALTER COLUMN gid SET DEFAULT nextval('sources.wahwahmountainutgeology_gid_seq'::regclass);


ALTER TABLE ONLY sources.ut_wahwahmtns_lines ALTER COLUMN gid SET DEFAULT nextval('sources.wahwahmtn_geolines_gid_seq'::regclass);


ALTER TABLE ONLY sources.ut_westwater ALTER COLUMN gid SET DEFAULT nextval('sources.westwater_gid_seq'::regclass);


ALTER TABLE ONLY sources.ut_westwater_lines ALTER COLUMN gid SET DEFAULT nextval('sources.ut_westwater_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.utquad_cedarcity ALTER COLUMN gid SET DEFAULT nextval('sources.utquad_cedarcity_gid_seq'::regclass);


ALTER TABLE ONLY sources.utquad_cedarcity_ln ALTER COLUMN gid SET DEFAULT nextval('sources.utquad_cedarcity_ln_gid_seq'::regclass);


ALTER TABLE ONLY sources.utquad_eastslc ALTER COLUMN gid SET DEFAULT nextval('sources.utquad_eastslc_gid_seq'::regclass);


ALTER TABLE ONLY sources.utquad_eastslc_ln ALTER COLUMN gid SET DEFAULT nextval('sources.utquad_eastslc_ln_gid_seq'::regclass);


ALTER TABLE ONLY sources.va_middletown ALTER COLUMN gid SET DEFAULT nextval('sources.va_middletown_gid_seq'::regclass);


ALTER TABLE ONLY sources.va_middletown_lines ALTER COLUMN gid SET DEFAULT nextval('sources.va_middletown_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.va_middletown_points ALTER COLUMN gid SET DEFAULT nextval('sources.points_ogc_fid_seq'::regclass);


ALTER TABLE ONLY sources.va_stephcity ALTER COLUMN gid SET DEFAULT nextval('sources.va_stephcity_gid_seq'::regclass);


ALTER TABLE ONLY sources.va_stephcity_lines ALTER COLUMN gid SET DEFAULT nextval('sources.va_stephcity_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.va_stephcity_points ALTER COLUMN gid SET DEFAULT nextval('sources.va_stephcity_points_gid_seq'::regclass);


ALTER TABLE ONLY sources.venezuela ALTER COLUMN gid SET DEFAULT nextval('sources.venezuela_geo_gid_seq'::regclass);


ALTER TABLE ONLY sources.venezuela_lines ALTER COLUMN gid SET DEFAULT nextval('sources.venez_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.wa100k ALTER COLUMN gid SET DEFAULT nextval('sources.wa100k_gid_seq'::regclass);


ALTER TABLE ONLY sources.wa100k_line ALTER COLUMN gid SET DEFAULT nextval('sources.wa100k_line_gid_seq'::regclass);


ALTER TABLE ONLY sources.wa_sanjuan_island ALTER COLUMN gid SET DEFAULT nextval('sources.sanjuanislandgeology_gid_seq'::regclass);


ALTER TABLE ONLY sources.wa_sanjuan_island_lines ALTER COLUMN gid SET DEFAULT nextval('sources.sanjuanfaults_gid_seq'::regclass);


ALTER TABLE ONLY sources.wi_ashland ALTER COLUMN gid SET DEFAULT nextval('sources.wi_ashland_gid_seq'::regclass);


ALTER TABLE ONLY sources.wi_ashland_lines ALTER COLUMN gid SET DEFAULT nextval('sources.wi_ashland_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.wi_ashland_points ALTER COLUMN gid SET DEFAULT nextval('sources.wi_ashland_points_gid_seq'::regclass);


ALTER TABLE ONLY sources.wi_brown ALTER COLUMN gid SET DEFAULT nextval('sources.wi_brown_geology_gid_seq'::regclass);


ALTER TABLE ONLY sources.wi_brown_lines ALTER COLUMN gid SET DEFAULT nextval('sources.wi_brown_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.wi_brown_points ALTER COLUMN gid SET DEFAULT nextval('sources.wi_brown_point_gid_seq'::regclass);


ALTER TABLE ONLY sources.wi_fond_du ALTER COLUMN gid SET DEFAULT nextval('sources.wi_fond_du_gid_seq'::regclass);


ALTER TABLE ONLY sources.wi_fond_du_lines ALTER COLUMN gid SET DEFAULT nextval('sources.wi_fond_du_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.wi_juneaucounty ALTER COLUMN gid SET DEFAULT nextval('sources.wi_juneaucounty_polygon_gid_seq'::regclass);


ALTER TABLE ONLY sources.wi_juneaucounty_lines ALTER COLUMN gid SET DEFAULT nextval('sources.wi_juneaucounty_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.wi_lacrosse ALTER COLUMN gid SET DEFAULT nextval('sources.lacrosse_geo_gid_seq'::regclass);


ALTER TABLE ONLY sources.wi_marathon ALTER COLUMN gid SET DEFAULT nextval('sources.wi_marathon_gid_seq'::regclass);


ALTER TABLE ONLY sources.wi_marathon_lines ALTER COLUMN gid SET DEFAULT nextval('sources.wi_marathon_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.wi_marathon_points ALTER COLUMN gid SET DEFAULT nextval('sources.wi_marathon_points_gid_seq'::regclass);


ALTER TABLE ONLY sources.wi_piercestcroix ALTER COLUMN gid SET DEFAULT nextval('sources.wi_piercestcroix_geology_gid_seq'::regclass);


ALTER TABLE ONLY sources.wi_piercestcroix_lines ALTER COLUMN gid SET DEFAULT nextval('sources.wi_piercestcroix_line_gid_seq'::regclass);


ALTER TABLE ONLY sources.wi_sauk_lines ALTER COLUMN gid SET DEFAULT nextval('sources.sauk_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.wi_sheboygan ALTER COLUMN gid SET DEFAULT nextval('sources.sheboygan_gid_seq'::regclass);


ALTER TABLE ONLY sources.wi_southeast ALTER COLUMN gid SET DEFAULT nextval('sources.se_wisconsin_geo_gid_seq'::regclass);


ALTER TABLE ONLY sources.wi_southeast_lines ALTER COLUMN gid SET DEFAULT nextval('sources.se_wisconsin_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.wi_wood ALTER COLUMN gid SET DEFAULT nextval('sources.wi_wood_gid_seq'::regclass);


ALTER TABLE ONLY sources.wi_wood_lines ALTER COLUMN gid SET DEFAULT nextval('sources.wi_wood_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.wi_wood_points ALTER COLUMN gid SET DEFAULT nextval('sources.wi_wood_points_gid_seq'::regclass);


ALTER TABLE ONLY sources.world_basins ALTER COLUMN gid SET DEFAULT nextval('sources.world_basins_gid_seq'::regclass);


ALTER TABLE ONLY sources.world_lines ALTER COLUMN gid SET DEFAULT nextval('sources.tiny_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.wv_gauley_river ALTER COLUMN gid SET DEFAULT nextval('sources.gauleyriver_geo_gid_seq'::regclass);


ALTER TABLE ONLY sources.wv_gauley_river_lines ALTER COLUMN gid SET DEFAULT nextval('sources.gauleyriver_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.wy_baggs ALTER COLUMN gid SET DEFAULT nextval('sources.wy_baggs_gid_seq'::regclass);


ALTER TABLE ONLY sources.wy_baggs_lines ALTER COLUMN gid SET DEFAULT nextval('sources.wy_baggs_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.wy_baggs_points ALTER COLUMN gid SET DEFAULT nextval('sources.wy_baggs_points_gid_seq'::regclass);


ALTER TABLE ONLY sources.wy_bairoil ALTER COLUMN gid SET DEFAULT nextval('sources.wy_bairoil_gid_seq'::regclass);


ALTER TABLE ONLY sources.wy_bairoil_lines ALTER COLUMN gid SET DEFAULT nextval('sources.wy_bairoil_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.wy_bill ALTER COLUMN gid SET DEFAULT nextval('sources.wy_bill_gid_seq'::regclass);


ALTER TABLE ONLY sources.wy_bill_lines ALTER COLUMN gid SET DEFAULT nextval('sources.wy_bill_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.wy_buffalo ALTER COLUMN gid SET DEFAULT nextval('sources.wy_buffalo_gid_seq'::regclass);


ALTER TABLE ONLY sources.wy_buffalo_lines ALTER COLUMN gid SET DEFAULT nextval('sources.wy_buffalo_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.wy_casper ALTER COLUMN gid SET DEFAULT nextval('sources.wy_caspar_polygon_gid_seq'::regclass);


ALTER TABLE ONLY sources.wy_casper_lines ALTER COLUMN gid SET DEFAULT nextval('sources.wy_caspar_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.wy_cheyenne ALTER COLUMN gid SET DEFAULT nextval('sources.wy_cheyenne_polygon_gid_seq'::regclass);


ALTER TABLE ONLY sources.wy_douglas ALTER COLUMN gid SET DEFAULT nextval('sources.wy_douglas_gid_seq'::regclass);


ALTER TABLE ONLY sources.wy_douglas_lines ALTER COLUMN gid SET DEFAULT nextval('sources.wy_douglas_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.wy_evanston ALTER COLUMN gid SET DEFAULT nextval('sources.wy_evanston_polygon_gid_seq'::regclass);


ALTER TABLE ONLY sources.wy_evanston_lines ALTER COLUMN gid SET DEFAULT nextval('sources.wy_evanston_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.wy_farson ALTER COLUMN gid SET DEFAULT nextval('sources.wy_farson_gid_seq'::regclass);


ALTER TABLE ONLY sources.wy_farson_lines ALTER COLUMN gid SET DEFAULT nextval('sources.wy_farson_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.wy_gillette ALTER COLUMN gid SET DEFAULT nextval('sources.wy_gillette_gid_seq'::regclass);


ALTER TABLE ONLY sources.wy_kaycee ALTER COLUMN gid SET DEFAULT nextval('sources.wy_kaycee_gid_seq'::regclass);


ALTER TABLE ONLY sources.wy_kaycee_lines ALTER COLUMN gid SET DEFAULT nextval('sources.wy_kaycee_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.wy_kemmerer ALTER COLUMN gid SET DEFAULT nextval('sources.wy_kemmerer_polygon_gid_seq'::regclass);


ALTER TABLE ONLY sources.wy_kemmerer_lines ALTER COLUMN gid SET DEFAULT nextval('sources.wy_kemmerer_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.wy_kinneyrim ALTER COLUMN gid SET DEFAULT nextval('sources.wy_kinneyrim_gid_seq'::regclass);


ALTER TABLE ONLY sources.wy_kinneyrim_lines ALTER COLUMN gid SET DEFAULT nextval('sources.wy_kinneyrim_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.wy_lancecreek ALTER COLUMN gid SET DEFAULT nextval('sources.wy_lanecreek_gid_seq'::regclass);


ALTER TABLE ONLY sources.wy_lancecreek_lines ALTER COLUMN gid SET DEFAULT nextval('sources.wy_lanecreek_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.wy_lander ALTER COLUMN gid SET DEFAULT nextval('sources.wyoming_lander_gid_seq'::regclass);


ALTER TABLE ONLY sources.wy_lander_lines ALTER COLUMN gid SET DEFAULT nextval('sources.wyoming_lander_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.wy_laramie ALTER COLUMN gid SET DEFAULT nextval('sources.laramie_geo_gid_seq'::regclass);


ALTER TABLE ONLY sources.wy_laramie_lines ALTER COLUMN gid SET DEFAULT nextval('sources.laramie_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.wy_midwest ALTER COLUMN gid SET DEFAULT nextval('sources.wy_midwest_gid_seq'::regclass);


ALTER TABLE ONLY sources.wy_midwest_lines ALTER COLUMN gid SET DEFAULT nextval('sources.wy_midwest_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.wy_newcastle ALTER COLUMN gid SET DEFAULT nextval('sources.wy_newcastle_gid_seq'::regclass);


ALTER TABLE ONLY sources.wy_newcastle_lines ALTER COLUMN gid SET DEFAULT nextval('sources.wy_newcastle_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.wy_nowater ALTER COLUMN gid SET DEFAULT nextval('sources.wy_nowater_gid_seq'::regclass);


ALTER TABLE ONLY sources.wy_nowater_lines ALTER COLUMN gid SET DEFAULT nextval('sources.wy_nowater_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.wy_rattlesnakehills ALTER COLUMN gid SET DEFAULT nextval('sources.wi_rattlesnakehills_polygon_gid_seq'::regclass);


ALTER TABLE ONLY sources.wy_rattlesnakehills_lines ALTER COLUMN gid SET DEFAULT nextval('sources.wy_rattlesnakehills_arcs_gid_seq'::regclass);


ALTER TABLE ONLY sources.wy_rawlins ALTER COLUMN gid SET DEFAULT nextval('sources.wy_rawlins_gid_seq'::regclass);


ALTER TABLE ONLY sources.wy_rawlins_lines ALTER COLUMN gid SET DEFAULT nextval('sources.wy_rawlins_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.wy_recluse ALTER COLUMN gid SET DEFAULT nextval('sources.wy_recluse_gid_seq'::regclass);


ALTER TABLE ONLY sources.wy_recluse_lines ALTER COLUMN gid SET DEFAULT nextval('sources.wy_recluse_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.wy_renojunction ALTER COLUMN gid SET DEFAULT nextval('sources.wy_renojunction_gid_seq'::regclass);


ALTER TABLE ONLY sources.wy_rock_springs ALTER COLUMN gid SET DEFAULT nextval('sources.rock_springs_geo_gid_seq'::regclass);


ALTER TABLE ONLY sources.wy_rock_springs_lines ALTER COLUMN gid SET DEFAULT nextval('sources.rock_springs_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.wy_rock_springs_points ALTER COLUMN gid SET DEFAULT nextval('sources.rock_springs_points_gid_seq'::regclass);


ALTER TABLE ONLY sources.wy_sheridan ALTER COLUMN gid SET DEFAULT nextval('sources.sheridan_gid_seq'::regclass);


ALTER TABLE ONLY sources.wy_sheridan_lines ALTER COLUMN gid SET DEFAULT nextval('sources.sheridan_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.wy_sundance ALTER COLUMN gid SET DEFAULT nextval('sources.wy_sundance_gid_seq'::regclass);


ALTER TABLE ONLY sources.wy_sundance_lines ALTER COLUMN gid SET DEFAULT nextval('sources.wy_sundance_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.wy_sundance_points ALTER COLUMN gid SET DEFAULT nextval('sources.wy_sundance_points_gid_seq'::regclass);


ALTER TABLE ONLY sources.wy_torrington ALTER COLUMN gid SET DEFAULT nextval('sources.wy_torrington_gid_seq'::regclass);


ALTER TABLE ONLY sources.wy_torrington_lines ALTER COLUMN gid SET DEFAULT nextval('sources.wy_torrington_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.yk_joyal ALTER COLUMN gid SET DEFAULT nextval('sources.yk_joyal_gid_seq'::regclass);


ALTER TABLE ONLY sources.yk_joyal_lines ALTER COLUMN gid SET DEFAULT nextval('sources.yk_joyal_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.yk_joyal_points ALTER COLUMN gid SET DEFAULT nextval('sources.yk_joyal_points_gid_seq'::regclass);


ALTER TABLE ONLY sources.yukon ALTER COLUMN gid SET DEFAULT nextval('sources.yukon_gid_seq'::regclass);


ALTER TABLE ONLY sources.yukon_folds ALTER COLUMN gid SET DEFAULT nextval('sources.yukon_folds_gid_seq'::regclass);


ALTER TABLE ONLY sources.yukon_lines ALTER COLUMN gid SET DEFAULT nextval('sources.yukon_lines_gid_seq'::regclass);


ALTER TABLE ONLY sources.yukon_mtmartin ALTER COLUMN gid SET DEFAULT nextval('sources.yukon_mtmartin_gid_seq'::regclass);


ALTER TABLE ONLY sources.yukon_mtmartin_folds ALTER COLUMN gid SET DEFAULT nextval('sources.yukon_mtmartin_folds_gid_seq'::regclass);


ALTER TABLE ONLY sources.yukon_mtmartin_points ALTER COLUMN gid SET DEFAULT nextval('sources.yukon_mtmartin_points_gid_seq'::regclass);


ALTER TABLE ONLY sources.yukon_mtmerril ALTER COLUMN gid SET DEFAULT nextval('sources.yukon_mtmerril_gid_seq'::regclass);


ALTER TABLE ONLY sources.yukon_mtmerril_folds ALTER COLUMN gid SET DEFAULT nextval('sources.yukon_mtmerril_folds_gid_seq'::regclass);


ALTER TABLE ONLY sources.yukon_mtmerril_points ALTER COLUMN gid SET DEFAULT nextval('sources.yukon_mtmerril_points_gid_seq'::regclass);


ALTER TABLE ONLY detrital_zircon.located_query_bounds
    ADD CONSTRAINT located_query_bounds_pkey PRIMARY KEY (id);


ALTER TABLE ONLY geologic_boundaries.sources
    ADD CONSTRAINT sources_pkey PRIMARY KEY (source_id);


ALTER TABLE ONLY hexgrids.hexgrids
    ADD CONSTRAINT hexgrids_pkey PRIMARY KEY (hex_id);


ALTER TABLE ONLY hexgrids.r10
    ADD CONSTRAINT r10_pkey PRIMARY KEY (hex_id);


ALTER TABLE ONLY hexgrids.r11
    ADD CONSTRAINT r11_pkey PRIMARY KEY (hex_id);


ALTER TABLE ONLY hexgrids.r12
    ADD CONSTRAINT r12_pkey PRIMARY KEY (hex_id);


ALTER TABLE ONLY hexgrids.r5
    ADD CONSTRAINT r5_pkey PRIMARY KEY (hex_id);


ALTER TABLE ONLY hexgrids.r6
    ADD CONSTRAINT r6_pkey PRIMARY KEY (hex_id);


ALTER TABLE ONLY hexgrids.r7
    ADD CONSTRAINT r7_pkey PRIMARY KEY (hex_id);


ALTER TABLE ONLY hexgrids.r8
    ADD CONSTRAINT r8_pkey PRIMARY KEY (hex_id);


ALTER TABLE ONLY hexgrids.r9
    ADD CONSTRAINT r9_pkey PRIMARY KEY (hex_id);


ALTER TABLE ONLY lines.large
    ADD CONSTRAINT large_pkey PRIMARY KEY (line_id);


ALTER TABLE ONLY lines.medium
    ADD CONSTRAINT medium_pkey PRIMARY KEY (line_id);


ALTER TABLE ONLY lines.small
    ADD CONSTRAINT small_pkey PRIMARY KEY (line_id);


ALTER TABLE ONLY lines.tiny
    ADD CONSTRAINT tiny_pkey PRIMARY KEY (line_id);


ALTER TABLE ONLY macrostrat.col_areas
    ADD CONSTRAINT col_areas_new_pkey PRIMARY KEY (id);


ALTER TABLE ONLY macrostrat.col_groups
    ADD CONSTRAINT col_groups_new_pkey1 PRIMARY KEY (id);


ALTER TABLE ONLY macrostrat.col_refs
    ADD CONSTRAINT col_refs_new_pkey1 PRIMARY KEY (id);


ALTER TABLE ONLY macrostrat.cols
    ADD CONSTRAINT cols_new_pkey PRIMARY KEY (id);


ALTER TABLE ONLY macrostrat.econs
    ADD CONSTRAINT econs_new_pkey PRIMARY KEY (id);


ALTER TABLE ONLY macrostrat.environs
    ADD CONSTRAINT environs_new_pkey1 PRIMARY KEY (id);


ALTER TABLE ONLY macrostrat.grainsize
    ADD CONSTRAINT grainsize_pkey PRIMARY KEY (grain_id);


ALTER TABLE ONLY macrostrat.lith_atts
    ADD CONSTRAINT lith_atts_new_pkey1 PRIMARY KEY (id);


ALTER TABLE ONLY macrostrat.liths
    ADD CONSTRAINT liths_new_pkey1 PRIMARY KEY (id);


ALTER TABLE ONLY macrostrat.lookup_units
    ADD CONSTRAINT lookup_units_new_pkey1 PRIMARY KEY (unit_id);


ALTER TABLE ONLY macrostrat.measurements
    ADD CONSTRAINT measurements_new_pkey PRIMARY KEY (id);


ALTER TABLE ONLY macrostrat.measuremeta
    ADD CONSTRAINT measuremeta_new_pkey PRIMARY KEY (id);


ALTER TABLE ONLY macrostrat.places
    ADD CONSTRAINT places_new_pkey PRIMARY KEY (place_id);


ALTER TABLE ONLY macrostrat.refs
    ADD CONSTRAINT refs_new_pkey1 PRIMARY KEY (id);


ALTER TABLE ONLY macrostrat.strat_names_meta
    ADD CONSTRAINT strat_names_meta_new_pkey1 PRIMARY KEY (concept_id);


ALTER TABLE ONLY macrostrat.strat_names
    ADD CONSTRAINT strat_names_new_pkey PRIMARY KEY (id);


ALTER TABLE ONLY macrostrat.timescales
    ADD CONSTRAINT timescales_new_pkey1 PRIMARY KEY (id);


ALTER TABLE ONLY macrostrat.unit_econs
    ADD CONSTRAINT unit_econs_new_pkey1 PRIMARY KEY (id);


ALTER TABLE ONLY macrostrat.unit_environs
    ADD CONSTRAINT unit_environs_new_pkey1 PRIMARY KEY (id);


ALTER TABLE ONLY macrostrat.unit_lith_atts
    ADD CONSTRAINT unit_lith_atts_new_pkey1 PRIMARY KEY (id);


ALTER TABLE ONLY macrostrat.unit_liths
    ADD CONSTRAINT unit_liths_new_pkey1 PRIMARY KEY (id);


ALTER TABLE ONLY macrostrat.unit_measures
    ADD CONSTRAINT unit_measures_new_pkey PRIMARY KEY (id);


ALTER TABLE ONLY macrostrat.unit_strat_names
    ADD CONSTRAINT unit_strat_names_new_pkey1 PRIMARY KEY (id);


ALTER TABLE ONLY macrostrat.units
    ADD CONSTRAINT units_new_pkey PRIMARY KEY (id);


ALTER TABLE ONLY macrostrat.units_sections
    ADD CONSTRAINT units_sections_new_pkey PRIMARY KEY (id);


ALTER TABLE ONLY maps.large
    ADD CONSTRAINT large_pkey PRIMARY KEY (map_id);


ALTER TABLE ONLY maps.legend_liths
    ADD CONSTRAINT legend_liths_legend_id_lith_id_basis_col_key UNIQUE (legend_id, lith_id, basis_col);


ALTER TABLE ONLY maps.legend
    ADD CONSTRAINT legend_pkey PRIMARY KEY (legend_id);


ALTER TABLE ONLY maps.map_legend
    ADD CONSTRAINT map_legend_legend_id_map_id_key UNIQUE (legend_id, map_id);


ALTER TABLE ONLY maps.medium
    ADD CONSTRAINT medium_pkey PRIMARY KEY (map_id);


ALTER TABLE ONLY maps.small
    ADD CONSTRAINT small_pkey PRIMARY KEY (map_id);


ALTER TABLE ONLY maps.sources
    ADD CONSTRAINT sources_source_id_key UNIQUE (source_id);


ALTER TABLE ONLY maps.tiny
    ADD CONSTRAINT tiny_pkey PRIMARY KEY (map_id);


ALTER TABLE ONLY public.impervious
    ADD CONSTRAINT impervious_pkey PRIMARY KEY (rid);


ALTER TABLE ONLY public.land
    ADD CONSTRAINT land_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY public.macrostrat_union
    ADD CONSTRAINT macrostrat_union_pkey PRIMARY KEY (id);


ALTER TABLE ONLY public.test_rgeom
    ADD CONSTRAINT test_rgeom_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.ab_spray_lines
    ADD CONSTRAINT ab_spray_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.ab_spray
    ADD CONSTRAINT ab_spray_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.ab_spray_points
    ADD CONSTRAINT ab_spray_points_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.ab_stimson_lines
    ADD CONSTRAINT ab_stimson_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.ab_stimson
    ADD CONSTRAINT ab_stimson_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.ab_stimson_points
    ADD CONSTRAINT ab_stimson_points_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.afghan_lines
    ADD CONSTRAINT afghan_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.afghan
    ADD CONSTRAINT afghan_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.africa
    ADD CONSTRAINT africa_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.ak_lines
    ADD CONSTRAINT ak_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.ak
    ADD CONSTRAINT ak_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.ca_alameda_lines
    ADD CONSTRAINT alam_fault_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.ca_alameda
    ADD CONSTRAINT alamedageology2_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.endikai_lines
    ADD CONSTRAINT albanel_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.alberta_faults
    ADD CONSTRAINT alberta_faults_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.alberta
    ADD CONSTRAINT alberta_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.ar_buffalo_nriver_lines
    ADD CONSTRAINT ar_buffalo_nriver_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.ar_buffalo_nriver
    ADD CONSTRAINT ar_buffalo_nriver_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.arctic
    ADD CONSTRAINT arctic_newgeom_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.arctic_orig
    ADD CONSTRAINT arctic_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.arctic_lines
    ADD CONSTRAINT arcticrus_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.australia2_faults
    ADD CONSTRAINT australia2_faults_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.australia2
    ADD CONSTRAINT australia2_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.australia_faults
    ADD CONSTRAINT australia_faults_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.australia
    ADD CONSTRAINT australia_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.az_fredonia_lines
    ADD CONSTRAINT az_fredonia_lines_one_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.az_fredonia_points
    ADD CONSTRAINT az_fredonia_point_two_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.az_fredonia
    ADD CONSTRAINT az_fredonia_polygon_one_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.az_whitehills_lines
    ADD CONSTRAINT az_whitehills_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.az_whitehills
    ADD CONSTRAINT az_whitehills_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.az_whitehills_points
    ADD CONSTRAINT az_whitehills_points_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.az_winslow_lines
    ADD CONSTRAINT az_winslow_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.az_winslow
    ADD CONSTRAINT az_winslow_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.az_winslow_points
    ADD CONSTRAINT az_winslow_points_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.bc_2017_lines
    ADD CONSTRAINT bc_2017_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.bc_2017
    ADD CONSTRAINT bc_2017_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.bc_2017_quat
    ADD CONSTRAINT bc_2017_quat_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.bc_abruzzi_lines
    ADD CONSTRAINT bc_abruzzi_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.bc_abruzzi
    ADD CONSTRAINT bc_abruzzi_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.bc_abruzzi_points
    ADD CONSTRAINT bc_abruzzi_points_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.bc_assini_lines
    ADD CONSTRAINT bc_assini_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.bc_assini
    ADD CONSTRAINT bc_assini_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.bc_assini_points
    ADD CONSTRAINT bc_assini_points_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.bc_chinook_lines
    ADD CONSTRAINT bc_chinook_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.bc_chinook
    ADD CONSTRAINT bc_chinook_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.bc_chinook_points
    ADD CONSTRAINT bc_chinook_points_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.bc_eight_lines
    ADD CONSTRAINT bc_eight_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.bc_eight
    ADD CONSTRAINT bc_eight_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.bc_eight_points
    ADD CONSTRAINT bc_eight_points_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.bc_faults
    ADD CONSTRAINT bc_faults_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.bc_fernie_lines
    ADD CONSTRAINT bc_fernie_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.bc_fernie
    ADD CONSTRAINT bc_fernie_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.bc_fernie_points
    ADD CONSTRAINT bc_fernie_points_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.bc_grayling_lines
    ADD CONSTRAINT bc_grayling_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.bc_grayling
    ADD CONSTRAINT bc_grayling_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.bc_grayling_points
    ADD CONSTRAINT bc_grayling_points_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.bc_kananaskis_lines
    ADD CONSTRAINT bc_kananaskis_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.bc_kananaskis
    ADD CONSTRAINT bc_kananaskis_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.bc_kananaskis_points
    ADD CONSTRAINT bc_kananaskis_points_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.bc
    ADD CONSTRAINT bc_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.bc_prudence_lines
    ADD CONSTRAINT bc_prudence_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.bc_prudence
    ADD CONSTRAINT bc_prudence_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.bc_prudence_points
    ADD CONSTRAINT bc_prudence_points_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.bc_redfern_lines
    ADD CONSTRAINT bc_redfern_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.bc_redfern
    ADD CONSTRAINT bc_redfern_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.bc_redfern_points
    ADD CONSTRAINT bc_redfern_points_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.bc_tangle_lines
    ADD CONSTRAINT bc_tangle_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.bc_tangle
    ADD CONSTRAINT bc_tangle_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.bc_tangle_points
    ADD CONSTRAINT bc_tangle_points_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.bc_toad_lines
    ADD CONSTRAINT bc_toad_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.bc_toad_ne_lines
    ADD CONSTRAINT bc_toad_ne_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.bc_toad_ne
    ADD CONSTRAINT bc_toad_ne_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.bc_toad_ne_points
    ADD CONSTRAINT bc_toad_ne_points_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.bc_toad
    ADD CONSTRAINT bc_toad_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.bc_toad_points
    ADD CONSTRAINT bc_toad_points_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.bc_ware_lines
    ADD CONSTRAINT bc_ware_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.bc_ware
    ADD CONSTRAINT bc_ware_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.bigbend_lines
    ADD CONSTRAINT bigbend_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.bigbend
    ADD CONSTRAINT bigbend_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.blackhills_lines
    ADD CONSTRAINT blackhills_foldsfaults_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.blackhills
    ADD CONSTRAINT blackhillsgeology_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.boulder_lines
    ADD CONSTRAINT boulder_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.boulder
    ADD CONSTRAINT boulder_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.brazil
    ADD CONSTRAINT brazil_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.brazil_sp
    ADD CONSTRAINT brazil_sp_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.brycecanyon_lines
    ADD CONSTRAINT brycecanyon_faults_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.brycecanyonnationalparkgeology
    ADD CONSTRAINT brycecanyonnationalparkgeology_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.ca_carizoplain_lines
    ADD CONSTRAINT ca_carizonplains_geo_arc_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.ca_carizoplain
    ADD CONSTRAINT ca_carizonplains_geo_polygon_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.ca_carizoplain_points
    ADD CONSTRAINT ca_carizonplains_point_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.ca_elcajon_lines
    ADD CONSTRAINT ca_elcajon_geo_arc_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.ca_elcajon
    ADD CONSTRAINT ca_elcajon_geo_polygon_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.ca_funeralmtns_lines
    ADD CONSTRAINT ca_funeralmtns_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.ca_funeralmtns
    ADD CONSTRAINT ca_funeralmtns_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.ca_funeralmtns_points
    ADD CONSTRAINT ca_funeralmtns_points_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.ca_marin_lines_nad27
    ADD CONSTRAINT ca_marin_lines_nad27_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.ca_marin_nad27
    ADD CONSTRAINT ca_marin_nad27_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.ca_monterey_lines
    ADD CONSTRAINT ca_monterey_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.ca_monterey
    ADD CONSTRAINT ca_monterrey_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.ca_napa_lines
    ADD CONSTRAINT ca_napa_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.ca_napa
    ADD CONSTRAINT ca_napa_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.ca_napa_points
    ADD CONSTRAINT ca_napa_points_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.ca_point_reyes
    ADD CONSTRAINT ca_point_reyes_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.ca_providence_mtns_lines
    ADD CONSTRAINT ca_providence_mtns_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.ca_providence_mtns
    ADD CONSTRAINT ca_providence_mtns_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.ca_providence_mtns_points
    ADD CONSTRAINT ca_providence_mtns_points_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.ca_providencemountains_lines
    ADD CONSTRAINT ca_providencemountains_arc_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.ca_providencemountains
    ADD CONSTRAINT ca_providencemountains_polygon_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.ca_santabarbara_lines
    ADD CONSTRAINT ca_santabarbara_geol_arc_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.ca_santabarbara
    ADD CONSTRAINT ca_santabarbara_geol_polygon_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.ca_santabarbara_points
    ADD CONSTRAINT ca_santabarbara_structure_point_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.ca_yosemite_lines
    ADD CONSTRAINT ca_yosemite_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.ca_yosemite_units
    ADD CONSTRAINT ca_yosemite_units_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.ca_cambria_lines
    ADD CONSTRAINT cambria_faults_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.ca_cambria
    ADD CONSTRAINT cambriacageology_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.catalunya50k_lines
    ADD CONSTRAINT catalunya50k_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.catalunya50k
    ADD CONSTRAINT catalunya50k_redo_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.co_arkansa_riv_lines
    ADD CONSTRAINT co_arkansa_riv_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.co_arkansa_riv
    ADD CONSTRAINT co_arkansa_riv_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.co_arkansa_riv_points
    ADD CONSTRAINT co_arkansa_riv_points_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.co_ftcollins_lines
    ADD CONSTRAINT co_ftcollins_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.co_ftcollins
    ADD CONSTRAINT co_ftcollins_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.co_ftcollins_points
    ADD CONSTRAINT co_ftcollins_points_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.co_greatsanddunes_lines
    ADD CONSTRAINT co_greatsanddunes_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.co_homestake_lines
    ADD CONSTRAINT co_homestake_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.co_homestake
    ADD CONSTRAINT co_homestake_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.co_homestake_points
    ADD CONSTRAINT co_homestake_points_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.colombia_lines
    ADD CONSTRAINT colombia_faults_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.colombia
    ADD CONSTRAINT colombia_geo_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.congareenationalpark_lines
    ADD CONSTRAINT congaree_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.congareenationalparkgeology
    ADD CONSTRAINT congareenationalparkgeology_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.ca_contracosta_lines
    ADD CONSTRAINT contracostafaults_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.ca_contracosta
    ADD CONSTRAINT contracostageology_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.dane_co
    ADD CONSTRAINT dane_co_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.dane_faults
    ADD CONSTRAINT dane_faults_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.dc_lines
    ADD CONSTRAINT dc_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.ut_delta_lines
    ADD CONSTRAINT delta_faults_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.ut_delta
    ADD CONSTRAINT deltautah_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.denver_lines
    ADD CONSTRAINT denver_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.denver
    ADD CONSTRAINT denver_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.co_denver
    ADD CONSTRAINT denvergeology_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.devils_tower
    ADD CONSTRAINT devils_tower_geo_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.devils_tower_lines
    ADD CONSTRAINT devils_tower_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.ut_dutchjohn_lines
    ADD CONSTRAINT dutchjohn_faults_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.ut_dutchjohn
    ADD CONSTRAINT dutchjohn_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.endikai
    ADD CONSTRAINT endikai_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.europe_5m_lines
    ADD CONSTRAINT europe_5m_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.europe_5m
    ADD CONSTRAINT europe_5m_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.gmna_faults
    ADD CONSTRAINT faults_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.florissant_lines
    ADD CONSTRAINT "florissant-lines_pkey" PRIMARY KEY (gid);


ALTER TABLE ONLY sources.florissant
    ADD CONSTRAINT florissant_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.france_lines
    ADD CONSTRAINT france_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.france
    ADD CONSTRAINT france_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.wv_gauley_river
    ADD CONSTRAINT gauleyriver_geo_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.wv_gauley_river_lines
    ADD CONSTRAINT gauleyriver_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.geo_lgm
    ADD CONSTRAINT geo_ice_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.geo_regions_canada
    ADD CONSTRAINT geo_regions_canada_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.geo_regions_europe
    ADD CONSTRAINT geo_regions_europe_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.geo_regions
    ADD CONSTRAINT geo_regions_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.geo_regions_us
    ADD CONSTRAINT geo_regions_us_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.german_nuremburg_lines
    ADD CONSTRAINT german_nuremburg_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.german_nuremburg
    ADD CONSTRAINT german_nurenburg_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.germany
    ADD CONSTRAINT germanygeology_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.glacier_np_lines
    ADD CONSTRAINT glacier_dikes_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.glaciernationalparkgeology
    ADD CONSTRAINT glaciernationalparkgeology_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.germany_lines
    ADD CONSTRAINT glines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.global2_lines
    ADD CONSTRAINT global2_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.global2
    ADD CONSTRAINT global2_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.global_ecoregions
    ADD CONSTRAINT global_ecoregions_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.ma_glouster
    ADD CONSTRAINT gloucester_rockport_geo2_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.gmus2_lines
    ADD CONSTRAINT gmus2_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.gmus2
    ADD CONSTRAINT gmus2_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.gmus_faults
    ADD CONSTRAINT gmus_faults_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.co_grandjunction
    ADD CONSTRAINT grand_junction_geo_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.co_grandjunction_lines
    ADD CONSTRAINT grand_junction_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.grandcanyon_lines
    ADD CONSTRAINT grandcanyon_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.grandcanyon
    ADD CONSTRAINT grandcanyon_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.grandcanyon_points
    ADD CONSTRAINT grandcanyon_points_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.greatbasinnationalpark_lines
    ADD CONSTRAINT greatbasin_contacts_faults_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.greatbasinnationalparkgeology
    ADD CONSTRAINT greatbasinnationalparkgeology_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.al_greenwood_lines
    ADD CONSTRAINT greenwood_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.al_greenwood_points
    ADD CONSTRAINT greenwood_points_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.al_greenwood
    ADD CONSTRAINT greenwoodalgeology_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.co_greatsanddunes
    ADD CONSTRAINT gsd_co_geology_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.guam
    ADD CONSTRAINT guamgeology_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.gumo_lines
    ADD CONSTRAINT gumo_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.gumo
    ADD CONSTRAINT gumo_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.gumo_points
    ADD CONSTRAINT gumo_points_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.ar_hasty
    ADD CONSTRAINT hasty_geo_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.ar_hasty_points
    ADD CONSTRAINT hasty_points_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.ar_hasty_lines
    ADD CONSTRAINT hastylines2_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.hawaii_lines
    ADD CONSTRAINT hawaii_dikes_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.hawaii
    ADD CONSTRAINT hawaii_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.honduras
    ADD CONSTRAINT honduras_geo_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.ar_hotsprings_np_lines
    ADD CONSTRAINT hot_springs_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.ar_hotsprings_np_points
    ADD CONSTRAINT hot_springs_points_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.ar_hotsprings_np
    ADD CONSTRAINT hotspringsnationalparkgeology_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.ut_huntington_lines
    ADD CONSTRAINT huntington_faults_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.ut_huntington
    ADD CONSTRAINT huntingtonutahgeology_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.id_arco_lines
    ADD CONSTRAINT id_arco_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.id_arco
    ADD CONSTRAINT id_arco_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.id_bonners_lines
    ADD CONSTRAINT id_bonners_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.id_bonners
    ADD CONSTRAINT id_bonners_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.id_deadwood_lines
    ADD CONSTRAINT id_deadwood_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.id_deadwood
    ADD CONSTRAINT id_deadwood_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.id_deadwood_points
    ADD CONSTRAINT id_deadwood_points_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.id_fairfield_lines
    ADD CONSTRAINT id_fairfield_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.id_fairfield
    ADD CONSTRAINT id_fairfield_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.id_grangeville_lines
    ADD CONSTRAINT id_grangeville_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.id_grangeville
    ADD CONSTRAINT id_grangeville_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.id_idahocity_lines
    ADD CONSTRAINT id_idahocity_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.id_idahocity
    ADD CONSTRAINT id_idahocity_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.id_murphy_lines
    ADD CONSTRAINT id_murphy_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.id_murphy
    ADD CONSTRAINT id_murphy_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.id_salmon_lines
    ADD CONSTRAINT id_salmon_lines_pkey PRIMARY KEY (objectid);


ALTER TABLE ONLY sources.id_salmon
    ADD CONSTRAINT id_salmon_pkey PRIMARY KEY (objectid);


ALTER TABLE ONLY sources.id_sandpoint_lines
    ADD CONSTRAINT id_sandpoint_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.id_sandpoint
    ADD CONSTRAINT id_sandpoint_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.id_twinfalls_lines
    ADD CONSTRAINT id_twinfalls_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.id_twinfalls
    ADD CONSTRAINT id_twinfalls_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.in_allen
    ADD CONSTRAINT in_allen_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.in_bartholomew
    ADD CONSTRAINT in_bartholomew_units_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.in_lawrence_lines
    ADD CONSTRAINT in_lawrence_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.in_lawrence
    ADD CONSTRAINT in_lawrence_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.in_marion
    ADD CONSTRAINT in_marion_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.in_morresville_w
    ADD CONSTRAINT in_morresville_w_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.in_swhitleyw
    ADD CONSTRAINT in_swhitleyw_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.iowa_co_wi
    ADD CONSTRAINT iowa_co_wi_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.iowa_lines
    ADD CONSTRAINT iowa_lines2_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.iowa
    ADD CONSTRAINT iowa_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.iran_lines
    ADD CONSTRAINT iran_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.iran
    ADD CONSTRAINT iran_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.ar_jasper
    ADD CONSTRAINT jaspergeo_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.ar_jasper_lines
    ADD CONSTRAINT jasperlines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.joshuatree_faults
    ADD CONSTRAINT joshuatree_faults_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.joshuatree
    ADD CONSTRAINT joshuatree_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.ky24k_faults
    ADD CONSTRAINT ky24k_faults_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.ky24k
    ADD CONSTRAINT ky24k_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.ky_descrip
    ADD CONSTRAINT ky_descrip_pkey PRIMARY KEY (id);


ALTER TABLE ONLY sources.wi_lacrosse
    ADD CONSTRAINT lacrosse_geo_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.lake_mead
    ADD CONSTRAINT lake_mead_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.laketahoe
    ADD CONSTRAINT laketahoe_geology_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.laketahoe_lines
    ADD CONSTRAINT laketahoe_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.laketahoe_point
    ADD CONSTRAINT laketahoe_point_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.wy_laramie
    ADD CONSTRAINT laramie_geo_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.wy_laramie_lines
    ADD CONSTRAINT laramie_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.africa_lines
    ADD CONSTRAINT lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.lissadellaustralia
    ADD CONSTRAINT lissadellaustralia_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.ut_logan_lines
    ADD CONSTRAINT logan_faults_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.ca_long_beach
    ADD CONSTRAINT long_beach_ca_geo_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.ca_long_beach_lines
    ADD CONSTRAINT long_beach_ca_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.ca_long_beach_points
    ADD CONSTRAINT long_beach_ca_points_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.ca_los_angeles
    ADD CONSTRAINT los_angeles_geo_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.ca_los_angeles_lines
    ADD CONSTRAINT los_angeles_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.manitoba_faults
    ADD CONSTRAINT manitoba_faults_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.manitoba
    ADD CONSTRAINT manitoba_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.ut_manti_lines
    ADD CONSTRAINT manti_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.ut_manti
    ADD CONSTRAINT mantiutgeology_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.saipan
    ADD CONSTRAINT marianaislandsgeology_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.ca_marin
    ADD CONSTRAINT marin_co_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.md_catocinfurnace_lines
    ADD CONSTRAINT md_catocinfurnace_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.md_catocinfurnace
    ADD CONSTRAINT md_catocinfurnace_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.md_catocinfurnace_points
    ADD CONSTRAINT md_catocinfurnace_points_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.md_clearspring_lines
    ADD CONSTRAINT md_clearspring_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.md_clearspring
    ADD CONSTRAINT md_clearspring_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.md_clearspring_points
    ADD CONSTRAINT md_clearspring_points_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.md_frederick_lines
    ADD CONSTRAINT md_frederick_linestwo_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.md_frederick
    ADD CONSTRAINT md_frederick_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.md_frederick_point
    ADD CONSTRAINT md_frederick_point_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.md_keedysville
    ADD CONSTRAINT md_keedysville_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.md_myerssmith_lines
    ADD CONSTRAINT md_myerssmith_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.md_myerssmith
    ADD CONSTRAINT md_myerssmith_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.md_newwindsor_lines
    ADD CONSTRAINT md_newwindsor_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.md_newwindsor
    ADD CONSTRAINT md_newwindsor_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.md_newwindsor_points
    ADD CONSTRAINT md_newwindsor_points_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.md_western_lines
    ADD CONSTRAINT md_western_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.md_western
    ADD CONSTRAINT md_western_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.mexico
    ADD CONSTRAINT mexicogeology_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.mexico_lines
    ADD CONSTRAINT mexicolines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.mn_houston_co_lines
    ADD CONSTRAINT mn_houston_co_faults_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.mn_houston_co
    ADD CONSTRAINT mn_houston_co_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.mn_redwood_co_lines
    ADD CONSTRAINT mn_redwood_co_faults_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.mn_redwood_co
    ADD CONSTRAINT mn_redwood_co_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.mn_washington_co_lines
    ADD CONSTRAINT mn_washington_co_faults_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.mn_washington_co
    ADD CONSTRAINT mn_washington_co_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.mn_winona_co_lines
    ADD CONSTRAINT mn_winona_co_fold_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.mn_winona_co
    ADD CONSTRAINT mn_winona_co_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.az_mohave
    ADD CONSTRAINT mohaveazgeology_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.az_peachsprings_lines
    ADD CONSTRAINT mohavecoconino_faults_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.az_peachsprings
    ADD CONSTRAINT mohavecoconinoazgeology_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.az_mohave_lines
    ADD CONSTRAINT mohavefault_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.mt_trumbull_lines
    ADD CONSTRAINT mt_trumbull_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.mt_trumbull
    ADD CONSTRAINT mt_trumbull_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.ut_nephi_lines
    ADD CONSTRAINT nephi_faults_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.ut_nephi
    ADD CONSTRAINT nephiutahgeology_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.ca_northeastsanfran_lines
    ADD CONSTRAINT nesffaults_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.new_river_gorge_lines
    ADD CONSTRAINT new_river_gorge_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.new_river_gorge
    ADD CONSTRAINT newrivergorge_geo_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.newzealand_faults
    ADD CONSTRAINT newzealand_faults_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.newzealand
    ADD CONSTRAINT newzealand_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.newzealandq_dikes
    ADD CONSTRAINT newzealandq_dikes_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.newzealandq_faults
    ADD CONSTRAINT newzealandq_faults_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.newzealandq
    ADD CONSTRAINT newzealandq_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.nh_lisbon_lines
    ADD CONSTRAINT nh_lisbon_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.nh_lisbon
    ADD CONSTRAINT nh_lisbon_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.nh_lisbon_points
    ADD CONSTRAINT nh_lisbon_points_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.nl_baieverte_lines
    ADD CONSTRAINT nl_baieverte_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.nl_baieverte
    ADD CONSTRAINT nl_baieverte_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.nl_baieverte_points
    ADD CONSTRAINT nl_baieverte_points_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.nl_king_lines
    ADD CONSTRAINT nl_king_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.nl_king
    ADD CONSTRAINT nl_king_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.nl_king_points
    ADD CONSTRAINT nl_king_points_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.nl_nippers_lines
    ADD CONSTRAINT nl_nippers_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.nl_nippers
    ADD CONSTRAINT nl_nippers_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.nl_nippers_points
    ADD CONSTRAINT nl_nippers_points_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.nm_albuquerque_lines
    ADD CONSTRAINT nm_albuquerque_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.nm_albuquerque
    ADD CONSTRAINT nm_albuquerque_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.nm_albuquerque_points
    ADD CONSTRAINT nm_albuquerque_points_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.nm_espanola_lines
    ADD CONSTRAINT nm_espanola_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.nm_espanola
    ADD CONSTRAINT nm_espanola_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.nm_espanola_points
    ADD CONSTRAINT nm_espanola_points_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.nm_latir_lines
    ADD CONSTRAINT nm_latir_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.nm_latir
    ADD CONSTRAINT nm_latir_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.nm_latir_points
    ADD CONSTRAINT nm_latir_points_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.nm_petroglyps_lines
    ADD CONSTRAINT nm_petroglyps_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.nm_petroglyps
    ADD CONSTRAINT nm_petroglyps_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.nm_vermejo_lines
    ADD CONSTRAINT nm_vermejo_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.nm_vermejo
    ADD CONSTRAINT nm_vermejo_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.nm_vermejo_points
    ADD CONSTRAINT nm_vermejo_points_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.ca_marin_lines
    ADD CONSTRAINT northbay_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.ca_northofsanfran
    ADD CONSTRAINT northofsanfrangeology_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.ca_northofsanfran_lines
    ADD CONSTRAINT northofsanfranlines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.nova_scotia_lines
    ADD CONSTRAINT nova_scotia_faults_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.nova_scotia
    ADD CONSTRAINT nova_scotia_geo_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.ca_north_santabarb
    ADD CONSTRAINT nsantabarbgeology_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.ca_north_santabarb_lines
    ADD CONSTRAINT nsbarblines2_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.nsw_bathurst_lines
    ADD CONSTRAINT nsw_bathurst_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.nsw_bathurst
    ADD CONSTRAINT nsw_bathurst_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.nsw_bogangate_lines
    ADD CONSTRAINT nsw_bogangate_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.nsw_bogangate
    ADD CONSTRAINT nsw_bogangate_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.nsw_boorowa_lines
    ADD CONSTRAINT nsw_boorowa_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.nsw_boorowa
    ADD CONSTRAINT nsw_boorowa_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.nsw_boorowa_points
    ADD CONSTRAINT nsw_boorowa_points_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.nsw_bunda_lines
    ADD CONSTRAINT nsw_bunda_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.nsw_bunda
    ADD CONSTRAINT nsw_bunda_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.nsw_bunda_points
    ADD CONSTRAINT nsw_bunda_points_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.nsw_cobar_lines
    ADD CONSTRAINT nsw_cobar_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.nsw_cobar
    ADD CONSTRAINT nsw_cobar_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.nsw_cobbora_lines
    ADD CONSTRAINT nsw_cobbora_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.nsw_cobbora
    ADD CONSTRAINT nsw_cobbora_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.nsw_cobbora_points
    ADD CONSTRAINT nsw_cobbora_points_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.nsw_cobham_lines
    ADD CONSTRAINT nsw_cobham_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.nsw_cobham
    ADD CONSTRAINT nsw_cobham_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.nsw_cobham_points
    ADD CONSTRAINT nsw_cobham_points_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.nsw_cool_lines
    ADD CONSTRAINT nsw_cool_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.nsw_cool
    ADD CONSTRAINT nsw_cool_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.nsw_cool_points
    ADD CONSTRAINT nsw_cool_points_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.nsw_gosford_lines
    ADD CONSTRAINT nsw_gosford_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.nsw_gosford
    ADD CONSTRAINT nsw_gosford_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.nsw_gosford_points
    ADD CONSTRAINT nsw_gosford_points_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.nsw_goul_lines
    ADD CONSTRAINT nsw_goul_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.nsw_goul
    ADD CONSTRAINT nsw_goul_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.nsw_goul_points
    ADD CONSTRAINT nsw_goul_points_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.nsw_sussex_lines
    ADD CONSTRAINT nsw_sussex_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.nsw_sussex
    ADD CONSTRAINT nsw_sussex_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.nsw_sussex_points
    ADD CONSTRAINT nsw_sussex_points_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.nsw_wonnaminta_lines
    ADD CONSTRAINT nsw_wonnaminta_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.nsw_wonnaminta
    ADD CONSTRAINT nsw_wonnaminta_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.nsw_wonnaminta_points
    ADD CONSTRAINT nsw_wonnaminta_points_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.nu_chidliak_n
    ADD CONSTRAINT nu_chidliak_n_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.nu_chidliak_s_lines
    ADD CONSTRAINT nu_chidliak_s_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.nu_chidliak_s
    ADD CONSTRAINT nu_chidliak_s_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.nu_circle_lines
    ADD CONSTRAINT nu_circle_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.nu_circle
    ADD CONSTRAINT nu_circle_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.nu_circle_points
    ADD CONSTRAINT nu_circle_points_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.nu_ellef_s_lines
    ADD CONSTRAINT nu_ellef_s_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.nu_ellef_s
    ADD CONSTRAINT nu_ellef_s_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.nu_ellef_s_points
    ADD CONSTRAINT nu_ellef_s_points_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.nu_grinnell_lines
    ADD CONSTRAINT nu_grinnell_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.nu_grinnell
    ADD CONSTRAINT nu_grinnell_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.nu_grinnell_points
    ADD CONSTRAINT nu_grinnell_points_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.nu_irvine_s_lines
    ADD CONSTRAINT nu_irvine_s_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.nu_irvine_s
    ADD CONSTRAINT nu_irvine_s_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.nu_irvine_s_points
    ADD CONSTRAINT nu_irvine_s_points_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.nu_mumiksaa_lines
    ADD CONSTRAINT nu_mumiksaa_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.nu_mumiksaa
    ADD CONSTRAINT nu_mumiksaa_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.nu_mumiksaa_points
    ADD CONSTRAINT nu_mumiksaa_points_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.nu_paquet_lines
    ADD CONSTRAINT nu_paquet_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.nu_paquet
    ADD CONSTRAINT nu_paquet_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.nu_paquet_points
    ADD CONSTRAINT nu_paquet_points_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.nu_pritzler_lines
    ADD CONSTRAINT nu_pritzler_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.nu_pritzler
    ADD CONSTRAINT nu_pritzler_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.nu_pritzler_points
    ADD CONSTRAINT nu_pritzler_points_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.nu_rae_lines
    ADD CONSTRAINT nu_rae_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.nu_rae
    ADD CONSTRAINT nu_rae_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.nu_sunneshine_lines
    ADD CONSTRAINT nu_sunneshine_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.nu_sunneshine
    ADD CONSTRAINT nu_sunneshine_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.nu_sunneshine_points
    ADD CONSTRAINT nu_sunneshine_points_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.nu_sylvia_s_lines
    ADD CONSTRAINT nu_sylvia_s_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.nu_sylvia_s
    ADD CONSTRAINT nu_sylvia_s_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.nu_sylvia_s_points
    ADD CONSTRAINT nu_sylvia_s_points_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.nu_tebesjuak_lines
    ADD CONSTRAINT nu_tebesjuak_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.nu_tebesjuak
    ADD CONSTRAINT nu_tebesjuak_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.nu_tebesjuak_points
    ADD CONSTRAINT nu_tebesjuak_points_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.nu_terra_lines
    ADD CONSTRAINT nu_terra_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.nu_terra
    ADD CONSTRAINT nu_terra_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.nu_terra_points
    ADD CONSTRAINT nu_terra_points_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.nv_beatty
    ADD CONSTRAINT nv_beatty_geo_poly_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.nv_beatty_lines
    ADD CONSTRAINT nv_beatty_line_annotation_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.nv_las_vegas_lines
    ADD CONSTRAINT nv_las_vegas_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.nv_las_vegas_units
    ADD CONSTRAINT nv_las_vegas_units_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.nw_lacmaunoir_drift
    ADD CONSTRAINT nw_lacmaunoir_drift_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.nw_lacmaunoir_folds
    ADD CONSTRAINT nw_lacmaunoir_folds_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.nw_lacmaunoir
    ADD CONSTRAINT nw_lacmaunoir_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.nw_lacmaunoir_points
    ADD CONSTRAINT nw_lacmaunoir_points_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.nw_slave_lines
    ADD CONSTRAINT nw_slave_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.nw_slave_rv
    ADD CONSTRAINT nw_slave_rv_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.nwt_calder_lines
    ADD CONSTRAINT nwt_calder_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.nwt_calder
    ADD CONSTRAINT nwt_calder_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.nwt_calder_points
    ADD CONSTRAINT nwt_calder_points_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.nwt_campbell_lines
    ADD CONSTRAINT nwt_campbell_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.nwt_campbell
    ADD CONSTRAINT nwt_campbell_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.nwt_campbell_points
    ADD CONSTRAINT nwt_campbell_points_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.nwt_carcajou_lines
    ADD CONSTRAINT nwt_carcajou_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.nwt_carcajou_ne_lines
    ADD CONSTRAINT nwt_carcajou_ne_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.nwt_carcajou_ne
    ADD CONSTRAINT nwt_carcajou_ne_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.nwt_carcajou_ne_points
    ADD CONSTRAINT nwt_carcajou_ne_points_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.nwt_carcajou
    ADD CONSTRAINT nwt_carcajou_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.nwt_carcajou_points
    ADD CONSTRAINT nwt_carcajou_points_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.nwt_carcajou_se_lines
    ADD CONSTRAINT nwt_carcajou_se_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.nwt_carcajou_se
    ADD CONSTRAINT nwt_carcajou_se_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.nwt_carcajou_se_points
    ADD CONSTRAINT nwt_carcajou_se_points_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.nwt_carcajou_sw_lines
    ADD CONSTRAINT nwt_carcajou_sw_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.nwt_carcajou_sw
    ADD CONSTRAINT nwt_carcajou_sw_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.nwt_carcajou_sw_points
    ADD CONSTRAINT nwt_carcajou_sw_points_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.nwt_mahony_sw_lines
    ADD CONSTRAINT nwt_mahony_sw_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.nwt_mahony_sw
    ADD CONSTRAINT nwt_mahony_sw_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.nwt_mahony_sw_points
    ADD CONSTRAINT nwt_mahony_sw_points_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.nwt_norman_nw_lines
    ADD CONSTRAINT nwt_norman_nw_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.nwt_norman_nw
    ADD CONSTRAINT nwt_norman_nw_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.nwt_norman_nw_points
    ADD CONSTRAINT nwt_norman_nw_points_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.nwt_norman_se_lines
    ADD CONSTRAINT nwt_norman_se_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.nwt_norman_se
    ADD CONSTRAINT nwt_norman_se_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.nwt_norman_se_points
    ADD CONSTRAINT nwt_norman_se_points_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.nwt_taki_lines
    ADD CONSTRAINT nwt_taki_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.nwt_taki
    ADD CONSTRAINT nwt_taki_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.nwt_taki_points
    ADD CONSTRAINT nwt_taki_points_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.ca_oakland
    ADD CONSTRAINT oakri_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.ca_oceanside_points
    ADD CONSTRAINT oceanside_pointorn_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.ontario_dikes
    ADD CONSTRAINT ontario_dikes_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.ontario
    ADD CONSTRAINT ontario_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.ontario_pz_mod
    ADD CONSTRAINT ontario_pz_mod_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.oregon_faults
    ADD CONSTRAINT oregon_faults_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.oregon
    ADD CONSTRAINT oregon_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.ontario_pz_lines
    ADD CONSTRAINT paleo_fault_arc_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.ontario_pz_points
    ADD CONSTRAINT paleo_point_point_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.ontario_pz
    ADD CONSTRAINT paleo_poly_polygon_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.va_middletown_points
    ADD CONSTRAINT points_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.ar_ponca_lines
    ADD CONSTRAINT poncafaults_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.ar_ponca
    ADD CONSTRAINT poncageo_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.az_prescott
    ADD CONSTRAINT prescottgeology_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.az_prescott_lines
    ADD CONSTRAINT prescottlines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.ut_price
    ADD CONSTRAINT price_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.ut_provo_lines
    ADD CONSTRAINT provo_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.ut_provo
    ADD CONSTRAINT provoutahgeology_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.puerto_rico
    ADD CONSTRAINT puerto_rico_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.puerto_rico_lines
    ADD CONSTRAINT puertorico_nfaults_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.ut_richfield_lines
    ADD CONSTRAINT richfield_faults_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.ut_richfield
    ADD CONSTRAINT richfieldutgeology_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.wy_rock_springs
    ADD CONSTRAINT rock_springs_geo_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.wy_rock_springs_lines
    ADD CONSTRAINT rock_springs_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.wy_rock_springs_points
    ADD CONSTRAINT rock_springs_points_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.rockies_lines
    ADD CONSTRAINT rockies_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.rockies
    ADD CONSTRAINT rockies_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.ma_glouster_lines
    ADD CONSTRAINT rockport_l2_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.rockymountainnationalparkgeology
    ADD CONSTRAINT rockymountainnationalparkgeology_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.rockymtn_np_lines
    ADD CONSTRAINT rockymtn_faults_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.brazil_lines
    ADD CONSTRAINT rondinia_dikes_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.saipan_lines
    ADD CONSTRAINT saipan_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.ca_san_diego_lines
    ADD CONSTRAINT san_diego_ca_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.ca_san_diego_points
    ADD CONSTRAINT san_diego_ca_points_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.san_salvador
    ADD CONSTRAINT san_salvador_geo_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.ca_sanberno_lines
    ADD CONSTRAINT sanberno_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.ca_sanberno
    ADD CONSTRAINT sanberno_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.ca_sanjose
    ADD CONSTRAINT sanjosegeology_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.ca_sanjose_lines
    ADD CONSTRAINT sanjoselines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.wa_sanjuan_island_lines
    ADD CONSTRAINT sanjuanfaults_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.wa_sanjuan_island
    ADD CONSTRAINT sanjuanislandgeology_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.ca_sanmateo_lines
    ADD CONSTRAINT sanmateofaults_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.ca_sanmateo
    ADD CONSTRAINT sanmateogeology_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.ca_santacruz
    ADD CONSTRAINT santacruz_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.saskatchewan_dikes
    ADD CONSTRAINT saskatchewan_dikes_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.saskatchewan
    ADD CONSTRAINT saskatchewan_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.wi_sauk_lines
    ADD CONSTRAINT sauk_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.ca_santacruz_lines
    ADD CONSTRAINT scruz_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.wi_southeast
    ADD CONSTRAINT se_wisconsin_geo_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.wi_southeast_lines
    ADD CONSTRAINT se_wisconsin_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.ut_seepridge_lines
    ADD CONSTRAINT seepridge_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.wi_sheboygan
    ADD CONSTRAINT sheboygan_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.wy_sheridan_lines
    ADD CONSTRAINT sheridan_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.wy_sheridan
    ADD CONSTRAINT sheridan_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.ut_smokymtns_lines
    ADD CONSTRAINT smkymtns_faults_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.smokies
    ADD CONSTRAINT smokies_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.smokies_lines
    ADD CONSTRAINT smokymountainsnationalpark_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.ut_smokymtns
    ADD CONSTRAINT smokymtnsutgeology_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.so_africa_lines
    ADD CONSTRAINT so_africa_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.so_africa
    ADD CONSTRAINT so_africa_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.md_keedysville_line
    ADD CONSTRAINT "sources.md_keedysville_line_pkey" PRIMARY KEY (gid);


ALTER TABLE ONLY sources.ca_southsanfran
    ADD CONSTRAINT southsanfrangeology_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.ca_southsanfran_lines
    ADD CONSTRAINT southsanfranlines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.spain_lines
    ADD CONSTRAINT spainlines1_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.spain
    ADD CONSTRAINT spainpbgeology_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.texas_mexico_lines
    ADD CONSTRAINT stexasmexico_geolines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.texas_mexico
    ADD CONSTRAINT stexasmexicogeology_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.sweden_lines
    ADD CONSTRAINT sweden_faults_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.sweden
    ADD CONSTRAINT swedengeology2_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.switzerland_lines
    ADD CONSTRAINT switzerland_faults_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.switzerland
    ADD CONSTRAINT switzerland_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.ca_oceanside
    ADD CONSTRAINT table_name_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.tanzania_oldonyo
    ADD CONSTRAINT tanzania_geo2_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.tanzania_oldonyo_lines
    ADD CONSTRAINT tanzania_structures_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.world_lines
    ADD CONSTRAINT tiny_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.nm_tularosa_lines
    ADD CONSTRAINT tularosafaults_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.nm_tularosa
    ADD CONSTRAINT tularosageo_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.ut_tulevalley_lines
    ADD CONSTRAINT tulevalley_faults_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.ut_tulevalley
    ADD CONSTRAINT tulevalleyutgeology_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.twincitiesmn_lines
    ADD CONSTRAINT twincities_faults_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.twincitiesmngeology
    ADD CONSTRAINT twincitiesmngeology_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.tx_bexar_lines
    ADD CONSTRAINT tx_bexar_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.tx_bexar
    ADD CONSTRAINT tx_bexar_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.tx_blanco_lines
    ADD CONSTRAINT tx_blanco_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.tx_blanco
    ADD CONSTRAINT tx_blanco_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.tx_chisos_lines
    ADD CONSTRAINT tx_chisos_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.tx_chisos
    ADD CONSTRAINT tx_chisos_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.tx_chisos_points
    ADD CONSTRAINT tx_chisos_points_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.tx_hays_lines
    ADD CONSTRAINT tx_hays_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.tx_hays
    ADD CONSTRAINT tx_hays_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.tx_laredo_lines
    ADD CONSTRAINT tx_laredo_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.tx_laredo
    ADD CONSTRAINT tx_laredo_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.tx_laredo_points
    ADD CONSTRAINT tx_laredo_points_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.uk_lines
    ADD CONSTRAINT uk_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.uk
    ADD CONSTRAINT uk_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.usgs_world_lines
    ADD CONSTRAINT usgs_world_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.usgs_world
    ADD CONSTRAINT usgs_world_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.ut_beaver_lines
    ADD CONSTRAINT ut_beaver_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.ut_beaver
    ADD CONSTRAINT ut_beaver_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.ut_dugway_lines
    ADD CONSTRAINT ut_dugwayprovinggrounds_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.ut_dugway
    ADD CONSTRAINT ut_dugwayprovinggrounds_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.ut_dugway_points
    ADD CONSTRAINT ut_dugwayprovinggrounds_points_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.ut_escalante_lines
    ADD CONSTRAINT ut_escalante_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.ut_escalante
    ADD CONSTRAINT ut_escalante_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.ut_kanab_lines
    ADD CONSTRAINT ut_kanab_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.ut_kanab
    ADD CONSTRAINT ut_kanab_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.ut_lasal_lines
    ADD CONSTRAINT ut_lasal_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.ut_lasal
    ADD CONSTRAINT ut_lasal_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.ut_logan
    ADD CONSTRAINT ut_logan_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.ut_lynndyl_lines
    ADD CONSTRAINT ut_lynndyl_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.ut_lynndyl
    ADD CONSTRAINT ut_lynndyl_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.ut_moab_lines
    ADD CONSTRAINT ut_moab_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.ut_moab
    ADD CONSTRAINT ut_moab_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.ut_ogden_lines
    ADD CONSTRAINT ut_ogden_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.ut_ogden
    ADD CONSTRAINT ut_ogden_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.ut_ogden_points
    ADD CONSTRAINT ut_ogden_points_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.ut_panguitch_lines
    ADD CONSTRAINT ut_panguitch_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.ut_panguitch
    ADD CONSTRAINT ut_panguitch_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.ut_price_lines
    ADD CONSTRAINT ut_price_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.ut_prommontorymtns_folds
    ADD CONSTRAINT ut_prommontorymtns_folds_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.ut_prommontorymtns
    ADD CONSTRAINT ut_prommontorymtns_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.ut_prommontorymtns_points
    ADD CONSTRAINT ut_prommontorymtns_points_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.ut_salina_lines
    ADD CONSTRAINT ut_salina_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.ut_salina
    ADD CONSTRAINT ut_salina_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.ut_salina_points
    ADD CONSTRAINT ut_salina_points_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.ut_saltlake_lines
    ADD CONSTRAINT ut_saltlake_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.ut_saltlake
    ADD CONSTRAINT ut_saltlake_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.ut_seepridge
    ADD CONSTRAINT ut_seepridge_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.ut_stgeorge_lines
    ADD CONSTRAINT ut_stgeorge_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.ut_stgeorge
    ADD CONSTRAINT ut_stgeorge_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.ut_tooele_lines
    ADD CONSTRAINT ut_tooele_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.ut_tooele
    ADD CONSTRAINT ut_tooele_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.ut_tooele_points
    ADD CONSTRAINT ut_tooele_points_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.ut_westwater_lines
    ADD CONSTRAINT ut_westwater_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.utquad_cedarcity_ln
    ADD CONSTRAINT utquad_cedarcity_ln_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.utquad_cedarcity
    ADD CONSTRAINT utquad_cedarcity_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.utquad_eastslc_ln
    ADD CONSTRAINT utquad_eastslc_ln_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.utquad_eastslc
    ADD CONSTRAINT utquad_eastslc_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.va_middletown_lines
    ADD CONSTRAINT va_middletown_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.va_middletown
    ADD CONSTRAINT va_middletown_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.va_stephcity_lines
    ADD CONSTRAINT va_stephcity_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.va_stephcity
    ADD CONSTRAINT va_stephcity_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.va_stephcity_points
    ADD CONSTRAINT va_stephcity_points_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.venezuela_lines
    ADD CONSTRAINT venez_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.venezuela
    ADD CONSTRAINT venezuela_geo_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.ut_vernal_lines
    ADD CONSTRAINT vernal_faults_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.ut_vernal
    ADD CONSTRAINT vernalutahgeology_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.wa100k_line
    ADD CONSTRAINT wa100k_line_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.wa100k
    ADD CONSTRAINT wa100k_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.ut_wahwahmtns
    ADD CONSTRAINT wahwahmountainutgeology_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.ut_wahwahmtns_lines
    ADD CONSTRAINT wahwahmtn_geolines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.pakistan_westcentral
    ADD CONSTRAINT westcentralpakistangeology_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.ut_westwater
    ADD CONSTRAINT westwater_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.wi_ashland_lines
    ADD CONSTRAINT wi_ashland_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.wi_ashland
    ADD CONSTRAINT wi_ashland_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.wi_ashland_points
    ADD CONSTRAINT wi_ashland_points_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.wi_brown
    ADD CONSTRAINT wi_brown_geology_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.wi_brown_lines
    ADD CONSTRAINT wi_brown_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.wi_brown_points
    ADD CONSTRAINT wi_brown_point_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.wi_fond_du_lines
    ADD CONSTRAINT wi_fond_du_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.wi_fond_du
    ADD CONSTRAINT wi_fond_du_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.wi_juneaucounty_lines
    ADD CONSTRAINT wi_juneaucounty_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.wi_juneaucounty
    ADD CONSTRAINT wi_juneaucounty_polygon_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.wi_marathon_lines
    ADD CONSTRAINT wi_marathon_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.wi_marathon
    ADD CONSTRAINT wi_marathon_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.wi_marathon_points
    ADD CONSTRAINT wi_marathon_points_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.wi_piercestcroix
    ADD CONSTRAINT wi_piercestcroix_geology_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.wi_piercestcroix_lines
    ADD CONSTRAINT wi_piercestcroix_line_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.wy_rattlesnakehills
    ADD CONSTRAINT wi_rattlesnakehills_polygon_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.wi_wood_lines
    ADD CONSTRAINT wi_wood_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.wi_wood
    ADD CONSTRAINT wi_wood_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.wi_wood_points
    ADD CONSTRAINT wi_wood_points_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.world_basins
    ADD CONSTRAINT world_basins_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.pakistan_westcentral_lines
    ADD CONSTRAINT wpakistan_faults_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.wy_baggs_lines
    ADD CONSTRAINT wy_baggs_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.wy_baggs
    ADD CONSTRAINT wy_baggs_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.wy_baggs_points
    ADD CONSTRAINT wy_baggs_points_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.wy_bairoil_lines
    ADD CONSTRAINT wy_bairoil_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.wy_bairoil
    ADD CONSTRAINT wy_bairoil_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.wy_bill_lines
    ADD CONSTRAINT wy_bill_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.wy_bill
    ADD CONSTRAINT wy_bill_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.wy_buffalo_lines
    ADD CONSTRAINT wy_buffalo_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.wy_buffalo
    ADD CONSTRAINT wy_buffalo_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.wy_casper_lines
    ADD CONSTRAINT wy_caspar_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.wy_casper
    ADD CONSTRAINT wy_caspar_polygon_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.wy_cheyenne
    ADD CONSTRAINT wy_cheyenne_polygon_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.wy_douglas_lines
    ADD CONSTRAINT wy_douglas_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.wy_douglas
    ADD CONSTRAINT wy_douglas_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.wy_evanston_lines
    ADD CONSTRAINT wy_evanston_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.wy_evanston
    ADD CONSTRAINT wy_evanston_polygon_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.wy_farson_lines
    ADD CONSTRAINT wy_farson_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.wy_farson
    ADD CONSTRAINT wy_farson_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.wy_gillette
    ADD CONSTRAINT wy_gillette_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.wy_kaycee_lines
    ADD CONSTRAINT wy_kaycee_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.wy_kaycee
    ADD CONSTRAINT wy_kaycee_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.wy_kemmerer_lines
    ADD CONSTRAINT wy_kemmerer_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.wy_kemmerer
    ADD CONSTRAINT wy_kemmerer_polygon_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.wy_kinneyrim_lines
    ADD CONSTRAINT wy_kinneyrim_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.wy_kinneyrim
    ADD CONSTRAINT wy_kinneyrim_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.wy_lancecreek_lines
    ADD CONSTRAINT wy_lanecreek_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.wy_lancecreek
    ADD CONSTRAINT wy_lanecreek_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.wy_midwest_lines
    ADD CONSTRAINT wy_midwest_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.wy_midwest
    ADD CONSTRAINT wy_midwest_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.wy_newcastle_lines
    ADD CONSTRAINT wy_newcastle_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.wy_newcastle
    ADD CONSTRAINT wy_newcastle_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.wy_nowater_lines
    ADD CONSTRAINT wy_nowater_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.wy_nowater
    ADD CONSTRAINT wy_nowater_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.wy_rattlesnakehills_lines
    ADD CONSTRAINT wy_rattlesnakehills_arcs_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.wy_rawlins_lines
    ADD CONSTRAINT wy_rawlins_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.wy_rawlins
    ADD CONSTRAINT wy_rawlins_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.wy_recluse_lines
    ADD CONSTRAINT wy_recluse_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.wy_recluse
    ADD CONSTRAINT wy_recluse_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.wy_renojunction
    ADD CONSTRAINT wy_renojunction_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.wy_sundance_lines
    ADD CONSTRAINT wy_sundance_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.wy_sundance
    ADD CONSTRAINT wy_sundance_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.wy_sundance_points
    ADD CONSTRAINT wy_sundance_points_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.wy_torrington_lines
    ADD CONSTRAINT wy_torrington_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.wy_torrington
    ADD CONSTRAINT wy_torrington_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.wy_lander_lines
    ADD CONSTRAINT wyoming_lander_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.wy_lander
    ADD CONSTRAINT wyoming_lander_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.yk_joyal_lines
    ADD CONSTRAINT yk_joyal_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.yk_joyal
    ADD CONSTRAINT yk_joyal_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.yk_joyal_points
    ADD CONSTRAINT yk_joyal_points_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.yukon_folds
    ADD CONSTRAINT yukon_folds_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.yukon_lines
    ADD CONSTRAINT yukon_lines_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.yukon_mtmartin_folds
    ADD CONSTRAINT yukon_mtmartin_folds_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.yukon_mtmartin
    ADD CONSTRAINT yukon_mtmartin_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.yukon_mtmartin_points
    ADD CONSTRAINT yukon_mtmartin_points_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.yukon_mtmerril_folds
    ADD CONSTRAINT yukon_mtmerril_folds_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.yukon_mtmerril
    ADD CONSTRAINT yukon_mtmerril_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.yukon_mtmerril_points
    ADD CONSTRAINT yukon_mtmerril_points_pkey PRIMARY KEY (gid);


ALTER TABLE ONLY sources.yukon
    ADD CONSTRAINT yukon_pkey PRIMARY KEY (gid);


CREATE INDEX flat_large_geom_idx ON carto.flat_large USING gist (geom);


CREATE INDEX flat_large_map_id_idx ON carto.flat_large USING btree (map_id);


CREATE INDEX large_new_geom_idx ON carto.large USING gist (geom);


CREATE INDEX large_new_map_id_idx ON carto.large USING btree (map_id);


CREATE INDEX lines_large_new_geom_idx1 ON carto.lines_large USING gist (geom);


CREATE INDEX lines_large_new_line_id_idx1 ON carto.lines_large USING btree (line_id);


CREATE INDEX lines_medium_new_geom_idx1 ON carto.lines_medium USING gist (geom);


CREATE INDEX lines_medium_new_line_id_idx1 ON carto.lines_medium USING btree (line_id);


CREATE INDEX lines_small_new_geom_idx1 ON carto.lines_small USING gist (geom);


CREATE INDEX lines_small_new_line_id_idx1 ON carto.lines_small USING btree (line_id);


CREATE INDEX lines_tiny_new_geom_idx1 ON carto.lines_tiny USING gist (geom);


CREATE INDEX lines_tiny_new_line_id_idx1 ON carto.lines_tiny USING btree (line_id);


CREATE INDEX medium_new_geom_idx ON carto.medium USING gist (geom);


CREATE INDEX medium_new_map_id_idx ON carto.medium USING btree (map_id);


CREATE INDEX small_new_geom_idx ON carto.small USING gist (geom);


CREATE INDEX small_new_map_id_idx ON carto.small USING btree (map_id);


CREATE INDEX tiny_new_geom_idx ON carto.tiny USING gist (geom);


CREATE INDEX tiny_new_map_id_idx ON carto.tiny USING btree (map_id);


CREATE INDEX hex_index_hex_id_idx ON carto_new.hex_index USING btree (hex_id);


CREATE INDEX hex_index_map_id_idx ON carto_new.hex_index USING btree (map_id);


CREATE INDEX hex_index_scale_idx ON carto_new.hex_index USING btree (scale);


CREATE INDEX large_geom_idx ON carto_new.large USING gist (geom);


CREATE INDEX large_map_id_idx ON carto_new.large USING btree (map_id);


CREATE INDEX lines_large_geom_idx ON carto_new.lines_large USING gist (geom);


CREATE INDEX lines_large_line_id_idx ON carto_new.lines_large USING btree (line_id);


CREATE INDEX lines_medium_geom_idx ON carto_new.lines_medium USING gist (geom);


CREATE INDEX lines_medium_line_id_idx ON carto_new.lines_medium USING btree (line_id);


CREATE INDEX lines_small_geom_idx ON carto_new.lines_small USING gist (geom);


CREATE INDEX lines_small_line_id_idx ON carto_new.lines_small USING btree (line_id);


CREATE INDEX lines_tiny_geom_idx ON carto_new.lines_tiny USING gist (geom);


CREATE INDEX lines_tiny_line_id_idx ON carto_new.lines_tiny USING btree (line_id);


CREATE INDEX medium_geom_idx ON carto_new.medium USING gist (geom);


CREATE INDEX medium_map_id_idx ON carto_new.medium USING btree (map_id);


CREATE INDEX pbdb_hex_index_collection_no_idx ON carto_new.pbdb_hex_index USING btree (collection_no);


CREATE INDEX pbdb_hex_index_hex_id_idx ON carto_new.pbdb_hex_index USING btree (hex_id);


CREATE INDEX pbdb_hex_index_scale_idx ON carto_new.pbdb_hex_index USING btree (scale);


CREATE INDEX small_geom_idx ON carto_new.small USING gist (geom);


CREATE INDEX small_map_id_idx ON carto_new.small USING btree (map_id);


CREATE INDEX tiny_geom_idx ON carto_new.tiny USING gist (geom);


CREATE INDEX tiny_map_id_idx ON carto_new.tiny USING btree (map_id);


CREATE INDEX boundaries_boundary_class_idx ON geologic_boundaries.boundaries USING btree (boundary_class);


CREATE INDEX boundaries_boundary_id_idx ON geologic_boundaries.boundaries USING btree (boundary_id);


CREATE INDEX boundaries_geom_idx ON geologic_boundaries.boundaries USING gist (geom);


CREATE INDEX boundaries_orig_id_idx ON geologic_boundaries.boundaries USING btree (orig_id);


CREATE INDEX boundaries_source_id_idx ON geologic_boundaries.boundaries USING btree (source_id);


CREATE INDEX bedrock_index_hex_id_idx ON hexgrids.bedrock_index USING btree (hex_id);


CREATE UNIQUE INDEX bedrock_index_legend_id_hex_id_idx ON hexgrids.bedrock_index USING btree (legend_id, hex_id);


CREATE INDEX bedrock_index_legend_id_idx ON hexgrids.bedrock_index USING btree (legend_id);


CREATE INDEX hexgrids_geom_idx ON hexgrids.hexgrids USING gist (geom);


CREATE INDEX hexgrids_res_idx ON hexgrids.hexgrids USING btree (res);


CREATE UNIQUE INDEX pbdb_index_collection_no_hex_id_idx ON hexgrids.pbdb_index USING btree (collection_no, hex_id);


CREATE INDEX pbdb_index_collection_no_idx ON hexgrids.pbdb_index USING btree (collection_no);


CREATE INDEX pbdb_index_hex_id_idx ON hexgrids.pbdb_index USING btree (hex_id);


CREATE INDEX r10_geom_geom_idx ON hexgrids.r10 USING gist (geom);


CREATE INDEX r10_geom_idx ON hexgrids.r10 USING gist (geom);


CREATE INDEX r10_web_geom_idx ON hexgrids.r10 USING gist (web_geom);


CREATE INDEX r11_geom_geom_idx ON hexgrids.r11 USING gist (geom);


CREATE INDEX r11_web_geom_idx ON hexgrids.r11 USING gist (web_geom);


CREATE INDEX r12_geom_geom_idx ON hexgrids.r12 USING gist (geom);


CREATE INDEX r12_web_geom_idx ON hexgrids.r12 USING gist (web_geom);


CREATE INDEX r5_geom_idx ON hexgrids.r5 USING gist (geom);


CREATE INDEX r5_web_geom_idx ON hexgrids.r5 USING gist (web_geom);


CREATE INDEX r6_geom_idx ON hexgrids.r6 USING gist (geom);


CREATE INDEX r6_web_geom_idx ON hexgrids.r6 USING gist (web_geom);


CREATE INDEX r7_geom_idx ON hexgrids.r7 USING gist (geom);


CREATE INDEX r7_geom_idx1 ON hexgrids.r7 USING gist (geom);


CREATE INDEX r7_geom_idx2 ON hexgrids.r7 USING gist (geom);


CREATE INDEX r7_web_geom_idx ON hexgrids.r7 USING gist (web_geom);


CREATE INDEX r8_geom_idx ON hexgrids.r8 USING gist (geom);


CREATE INDEX r8_geom_idx1 ON hexgrids.r8 USING gist (geom);


CREATE INDEX r8_geom_idx2 ON hexgrids.r8 USING gist (geom);


CREATE INDEX r8_web_geom_idx ON hexgrids.r8 USING gist (web_geom);


CREATE INDEX r9_geom_idx ON hexgrids.r9 USING gist (geom);


CREATE INDEX r9_geom_idx1 ON hexgrids.r9 USING gist (geom);


CREATE INDEX r9_web_geom_idx ON hexgrids.r9 USING gist (web_geom);


CREATE INDEX large_geom_idx ON lines.large USING gist (geom);


CREATE INDEX large_line_id_idx ON lines.large USING btree (line_id);


CREATE INDEX large_orig_id_idx ON lines.large USING btree (orig_id);


CREATE INDEX large_source_id_idx ON lines.large USING btree (source_id);


CREATE INDEX medium_geom_idx ON lines.medium USING gist (geom);


CREATE INDEX medium_line_id_idx ON lines.medium USING btree (line_id);


CREATE INDEX medium_orig_id_idx ON lines.medium USING btree (orig_id);


CREATE INDEX medium_source_id_idx ON lines.medium USING btree (source_id);


CREATE INDEX small_geom_idx ON lines.small USING gist (geom);


CREATE INDEX small_source_id_idx ON lines.small USING btree (source_id);


CREATE INDEX tiny_geom_idx ON lines.tiny USING gist (geom);


CREATE INDEX tiny_source_id_idx ON lines.tiny USING btree (source_id);


CREATE INDEX autocomplete_new_category_idx1 ON macrostrat.autocomplete USING btree (category);


CREATE INDEX autocomplete_new_id_idx1 ON macrostrat.autocomplete USING btree (id);


CREATE INDEX autocomplete_new_name_idx1 ON macrostrat.autocomplete USING btree (name);


CREATE INDEX autocomplete_new_type_idx1 ON macrostrat.autocomplete USING btree (type);


CREATE INDEX col_areas_new_col_area_idx ON macrostrat.col_areas USING gist (col_area);


CREATE INDEX col_areas_new_col_id_idx ON macrostrat.col_areas USING btree (col_id);


CREATE INDEX col_groups_new_id_idx1 ON macrostrat.col_groups USING btree (id);


CREATE INDEX col_refs_new_col_id_idx1 ON macrostrat.col_refs USING btree (col_id);


CREATE INDEX col_refs_new_ref_id_idx1 ON macrostrat.col_refs USING btree (ref_id);


CREATE INDEX cols_new_col_group_id_idx ON macrostrat.cols USING btree (col_group_id);


CREATE INDEX cols_new_coordinate_idx ON macrostrat.cols USING gist (coordinate);


CREATE INDEX cols_new_poly_geom_idx ON macrostrat.cols USING gist (poly_geom);


CREATE INDEX cols_new_project_id_idx ON macrostrat.cols USING btree (project_id);


CREATE INDEX cols_new_status_code_idx ON macrostrat.cols USING btree (status_code);


CREATE INDEX concepts_places_new_concept_id_idx ON macrostrat.concepts_places USING btree (concept_id);


CREATE INDEX concepts_places_new_place_id_idx ON macrostrat.concepts_places USING btree (place_id);


CREATE INDEX intervals_new_age_bottom_idx1 ON macrostrat.intervals USING btree (age_bottom);


CREATE INDEX intervals_new_age_top_idx1 ON macrostrat.intervals USING btree (age_top);


CREATE INDEX intervals_new_id_idx1 ON macrostrat.intervals USING btree (id);


CREATE INDEX intervals_new_interval_name_idx1 ON macrostrat.intervals USING btree (interval_name);


CREATE INDEX intervals_new_interval_type_idx1 ON macrostrat.intervals USING btree (interval_type);


CREATE INDEX lith_atts_new_att_type_idx1 ON macrostrat.lith_atts USING btree (att_type);


CREATE INDEX lith_atts_new_lith_att_idx1 ON macrostrat.lith_atts USING btree (lith_att);


CREATE INDEX liths_new_lith_class_idx1 ON macrostrat.liths USING btree (lith_class);


CREATE INDEX liths_new_lith_idx1 ON macrostrat.liths USING btree (lith);


CREATE INDEX liths_new_lith_type_idx1 ON macrostrat.liths USING btree (lith_type);


CREATE INDEX lookup_strat_names_new_bed_id_idx ON macrostrat.lookup_strat_names USING btree (bed_id);


CREATE INDEX lookup_strat_names_new_concept_id_idx ON macrostrat.lookup_strat_names USING btree (concept_id);


CREATE INDEX lookup_strat_names_new_fm_id_idx ON macrostrat.lookup_strat_names USING btree (fm_id);


CREATE INDEX lookup_strat_names_new_gp_id_idx ON macrostrat.lookup_strat_names USING btree (gp_id);


CREATE INDEX lookup_strat_names_new_mbr_id_idx ON macrostrat.lookup_strat_names USING btree (mbr_id);


CREATE INDEX lookup_strat_names_new_sgp_id_idx ON macrostrat.lookup_strat_names USING btree (sgp_id);


CREATE INDEX lookup_strat_names_new_strat_name_id_idx ON macrostrat.lookup_strat_names USING btree (strat_name_id);


CREATE INDEX lookup_strat_names_new_strat_name_idx ON macrostrat.lookup_strat_names USING btree (strat_name);


CREATE INDEX lookup_unit_attrs_api_new_unit_id_idx1 ON macrostrat.lookup_unit_attrs_api USING btree (unit_id);


CREATE INDEX lookup_unit_intervals_new_best_interval_id_idx ON macrostrat.lookup_unit_intervals USING btree (best_interval_id);


CREATE INDEX lookup_unit_intervals_new_unit_id_idx ON macrostrat.lookup_unit_intervals USING btree (unit_id);


CREATE INDEX lookup_unit_liths_new_unit_id_idx ON macrostrat.lookup_unit_liths USING btree (unit_id);


CREATE INDEX lookup_units_new_b_int_idx1 ON macrostrat.lookup_units USING btree (b_int);


CREATE INDEX lookup_units_new_project_id_idx1 ON macrostrat.lookup_units USING btree (project_id);


CREATE INDEX lookup_units_new_t_int_idx1 ON macrostrat.lookup_units USING btree (t_int);


CREATE INDEX measurements_new_id_idx ON macrostrat.measurements USING btree (id);


CREATE INDEX measurements_new_measurement_class_idx ON macrostrat.measurements USING btree (measurement_class);


CREATE INDEX measurements_new_measurement_type_idx ON macrostrat.measurements USING btree (measurement_type);


CREATE INDEX measuremeta_new_lith_att_id_idx1 ON macrostrat.measuremeta USING btree (lith_att_id);


CREATE INDEX measuremeta_new_lith_id_idx1 ON macrostrat.measuremeta USING btree (lith_id);


CREATE INDEX measuremeta_new_ref_id_idx1 ON macrostrat.measuremeta USING btree (ref_id);


CREATE INDEX measures_new_measurement_id_idx1 ON macrostrat.measures USING btree (measurement_id);


CREATE INDEX measures_new_measuremeta_id_idx1 ON macrostrat.measures USING btree (measuremeta_id);


CREATE INDEX pbdb_collections_new_collection_no_idx1 ON macrostrat.pbdb_collections USING btree (collection_no);


CREATE INDEX pbdb_collections_new_early_age_idx1 ON macrostrat.pbdb_collections USING btree (early_age);


CREATE INDEX pbdb_collections_new_geom_idx1 ON macrostrat.pbdb_collections USING gist (geom);


CREATE INDEX pbdb_collections_new_late_age_idx1 ON macrostrat.pbdb_collections USING btree (late_age);


CREATE INDEX places_new_geom_idx ON macrostrat.places USING gist (geom);


CREATE INDEX refs_new_rgeom_idx1 ON macrostrat.refs USING gist (rgeom);


CREATE INDEX strat_name_footprints_new_geom_idx ON macrostrat.strat_name_footprints USING gist (geom);


CREATE INDEX strat_name_footprints_new_strat_name_id_idx ON macrostrat.strat_name_footprints USING btree (strat_name_id);


CREATE INDEX strat_names_meta_new_b_int_idx1 ON macrostrat.strat_names_meta USING btree (b_int);


CREATE INDEX strat_names_meta_new_interval_id_idx1 ON macrostrat.strat_names_meta USING btree (interval_id);


CREATE INDEX strat_names_meta_new_ref_id_idx1 ON macrostrat.strat_names_meta USING btree (ref_id);


CREATE INDEX strat_names_meta_new_t_int_idx1 ON macrostrat.strat_names_meta USING btree (t_int);


CREATE INDEX strat_names_new_concept_id_idx ON macrostrat.strat_names USING btree (concept_id);


CREATE INDEX strat_names_new_rank_idx ON macrostrat.strat_names USING btree (rank);


CREATE INDEX strat_names_new_ref_id_idx ON macrostrat.strat_names USING btree (ref_id);


CREATE INDEX strat_names_new_strat_name_idx ON macrostrat.strat_names USING btree (strat_name);


CREATE INDEX strat_names_places_new_place_id_idx1 ON macrostrat.strat_names_places USING btree (place_id);


CREATE INDEX strat_names_places_new_strat_name_id_idx1 ON macrostrat.strat_names_places USING btree (strat_name_id);


CREATE INDEX timescales_intervals_new_interval_id_idx1 ON macrostrat.timescales_intervals USING btree (interval_id);


CREATE INDEX timescales_intervals_new_timescale_id_idx1 ON macrostrat.timescales_intervals USING btree (timescale_id);


CREATE INDEX timescales_new_ref_id_idx1 ON macrostrat.timescales USING btree (ref_id);


CREATE INDEX timescales_new_timescale_idx1 ON macrostrat.timescales USING btree (timescale);


CREATE INDEX unit_econs_new_econ_id_idx1 ON macrostrat.unit_econs USING btree (econ_id);


CREATE INDEX unit_econs_new_ref_id_idx1 ON macrostrat.unit_econs USING btree (ref_id);


CREATE INDEX unit_econs_new_unit_id_idx1 ON macrostrat.unit_econs USING btree (unit_id);


CREATE INDEX unit_environs_new_environ_id_idx1 ON macrostrat.unit_environs USING btree (environ_id);


CREATE INDEX unit_environs_new_ref_id_idx1 ON macrostrat.unit_environs USING btree (ref_id);


CREATE INDEX unit_environs_new_unit_id_idx1 ON macrostrat.unit_environs USING btree (unit_id);


CREATE INDEX unit_lith_atts_new_lith_att_id_idx1 ON macrostrat.unit_lith_atts USING btree (lith_att_id);


CREATE INDEX unit_lith_atts_new_ref_id_idx1 ON macrostrat.unit_lith_atts USING btree (ref_id);


CREATE INDEX unit_lith_atts_new_unit_lith_id_idx1 ON macrostrat.unit_lith_atts USING btree (unit_lith_id);


CREATE INDEX unit_liths_new_lith_id_idx1 ON macrostrat.unit_liths USING btree (lith_id);


CREATE INDEX unit_liths_new_ref_id_idx1 ON macrostrat.unit_liths USING btree (ref_id);


CREATE INDEX unit_liths_new_unit_id_idx1 ON macrostrat.unit_liths USING btree (unit_id);


CREATE INDEX unit_measures_new_measuremeta_id_idx ON macrostrat.unit_measures USING btree (measuremeta_id);


CREATE INDEX unit_measures_new_strat_name_id_idx ON macrostrat.unit_measures USING btree (strat_name_id);


CREATE INDEX unit_measures_new_unit_id_idx ON macrostrat.unit_measures USING btree (unit_id);


CREATE INDEX unit_strat_names_new_strat_name_id_idx1 ON macrostrat.unit_strat_names USING btree (strat_name_id);


CREATE INDEX unit_strat_names_new_unit_id_idx1 ON macrostrat.unit_strat_names USING btree (unit_id);


CREATE INDEX units_new_col_id_idx ON macrostrat.units USING btree (col_id);


CREATE INDEX units_new_color_idx ON macrostrat.units USING btree (color);


CREATE INDEX units_new_section_id_idx ON macrostrat.units USING btree (section_id);


CREATE INDEX units_new_strat_name_idx ON macrostrat.units USING btree (strat_name);


CREATE INDEX units_sections_new_col_id_idx ON macrostrat.units_sections USING btree (col_id);


CREATE INDEX units_sections_new_section_id_idx ON macrostrat.units_sections USING btree (section_id);


CREATE INDEX units_sections_new_unit_id_idx ON macrostrat.units_sections USING btree (unit_id);


CREATE INDEX large_b_interval_idx ON maps.large USING btree (b_interval);


CREATE INDEX large_geom_idx ON maps.large USING gist (geom);


CREATE INDEX large_name_idx ON maps.large USING btree (name);


CREATE INDEX large_orig_id_idx ON maps.large USING btree (orig_id);


CREATE INDEX large_source_id_idx ON maps.large USING btree (source_id);


CREATE INDEX large_t_interval_idx ON maps.large USING btree (t_interval);


CREATE INDEX legend_liths_legend_id_idx ON maps.legend_liths USING btree (legend_id);


CREATE INDEX legend_liths_lith_id_idx ON maps.legend_liths USING btree (lith_id);


CREATE INDEX legend_source_id_idx ON maps.legend USING btree (source_id);


CREATE INDEX manual_matches_map_id_idx ON maps.manual_matches USING btree (map_id);


CREATE INDEX manual_matches_strat_name_id_idx ON maps.manual_matches USING btree (strat_name_id);


CREATE INDEX manual_matches_unit_id_idx ON maps.manual_matches USING btree (unit_id);


CREATE INDEX map_legend_legend_id_idx ON maps.map_legend USING btree (legend_id);


CREATE INDEX map_legend_map_id_idx ON maps.map_legend USING btree (map_id);


CREATE INDEX map_liths_lith_id_idx ON maps.map_liths USING btree (lith_id);


CREATE INDEX map_liths_map_id_idx ON maps.map_liths USING btree (map_id);


CREATE INDEX map_strat_names_map_id_idx ON maps.map_strat_names USING btree (map_id);


CREATE INDEX map_strat_names_strat_name_id_idx ON maps.map_strat_names USING btree (strat_name_id);


CREATE INDEX map_units_map_id_idx ON maps.map_units USING btree (map_id);


CREATE INDEX map_units_unit_id_idx ON maps.map_units USING btree (unit_id);


CREATE INDEX medium_b_interval_idx ON maps.medium USING btree (b_interval);


CREATE INDEX medium_geom_idx ON maps.medium USING gist (geom);


CREATE INDEX medium_orig_id_idx ON maps.medium USING btree (orig_id);


CREATE INDEX medium_source_id_idx ON maps.medium USING btree (source_id);


CREATE INDEX medium_t_interval_idx ON maps.medium USING btree (t_interval);


CREATE INDEX small_b_interval_idx ON maps.small USING btree (b_interval);


CREATE INDEX small_geom_idx ON maps.small USING gist (geom);


CREATE INDEX small_orig_id_idx ON maps.small USING btree (orig_id);


CREATE INDEX small_source_id_idx ON maps.small USING btree (source_id);


CREATE INDEX small_t_interval_idx ON maps.small USING btree (t_interval);


CREATE INDEX sources_rgeom_idx ON maps.sources USING gist (rgeom);


CREATE INDEX sources_web_geom_idx ON maps.sources USING gist (web_geom);


CREATE INDEX tiny_b_interval_idx ON maps.tiny USING btree (b_interval);


CREATE INDEX tiny_geom_idx ON maps.tiny USING gist (geom);


CREATE INDEX tiny_orig_id_idx ON maps.tiny USING btree (orig_id);


CREATE INDEX tiny_source_id_idx ON maps.tiny USING btree (source_id);


CREATE INDEX tiny_t_interval_idx ON maps.tiny USING btree (t_interval);


CREATE INDEX points_geom_idx ON points.points USING gist (geom);


CREATE INDEX points_source_id_idx ON points.points USING btree (source_id);


CREATE INDEX agebzepllj_geom_idx ON public.agebzepllj USING gist (geom);


CREATE INDEX aofhmuuyjq_geom_idx ON public.aofhmuuyjq USING gist (geom);


CREATE INDEX bmbtwjmdgn_geom_idx ON public.bmbtwjmdgn USING gist (geom);


CREATE INDEX emma5k5jzl_geom_idx ON public.emma5k5jzl USING gist (geom);


CREATE INDEX i9kzotjhgr_geom_idx ON public.i9kzotjhgr USING gist (geom);


CREATE INDEX impervious_st_convexhull_idx ON public.impervious USING gist (public.st_convexhull(rast));


CREATE INDEX land_geom_idx ON public.land USING gist (geom);


CREATE INDEX lookup_large_concept_ids_idx ON public.lookup_large USING gin (concept_ids);


CREATE INDEX lookup_large_legend_id_idx ON public.lookup_large USING btree (legend_id);


CREATE INDEX lookup_large_lith_ids_idx ON public.lookup_large USING gin (lith_ids);


CREATE INDEX lookup_large_map_id_idx ON public.lookup_large USING btree (map_id);


CREATE INDEX lookup_large_strat_name_children_idx ON public.lookup_large USING gin (strat_name_children);


CREATE INDEX lookup_medium_concept_ids_idx ON public.lookup_medium USING gin (concept_ids);


CREATE INDEX lookup_medium_legend_id_idx ON public.lookup_medium USING btree (legend_id);


CREATE INDEX lookup_medium_lith_ids_idx ON public.lookup_medium USING gin (lith_ids);


CREATE INDEX lookup_medium_map_id_idx ON public.lookup_medium USING btree (map_id);


CREATE INDEX lookup_medium_strat_name_children_idx ON public.lookup_medium USING gin (strat_name_children);


CREATE INDEX lookup_small_concept_ids_idx ON public.lookup_small USING gin (concept_ids);


CREATE INDEX lookup_small_legend_id_idx ON public.lookup_small USING btree (legend_id);


CREATE INDEX lookup_small_lith_ids_idx ON public.lookup_small USING gin (lith_ids);


CREATE INDEX lookup_small_map_id_idx ON public.lookup_small USING btree (map_id);


CREATE INDEX lookup_small_strat_name_children_idx ON public.lookup_small USING gin (strat_name_children);


CREATE INDEX lookup_tiny_concept_ids_idx ON public.lookup_tiny USING gin (concept_ids);


CREATE INDEX lookup_tiny_legend_id_idx ON public.lookup_tiny USING btree (legend_id);


CREATE INDEX lookup_tiny_lith_ids_idx ON public.lookup_tiny USING gin (lith_ids);


CREATE INDEX lookup_tiny_map_id_idx ON public.lookup_tiny USING btree (map_id);


CREATE INDEX lookup_tiny_strat_name_children_idx ON public.lookup_tiny USING gin (strat_name_children);


CREATE INDEX npb9s0ubia_geom_idx ON public.npb9s0ubia USING gist (geom);


CREATE INDEX temp_names_name_no_lith_idx ON public.temp_names USING btree (name_no_lith);


CREATE INDEX temp_names_rank_name_idx ON public.temp_names USING btree (rank_name);


CREATE INDEX temp_names_strat_name_id_idx ON public.temp_names USING btree (strat_name_id);


CREATE INDEX temp_names_strat_name_idx ON public.temp_names USING btree (strat_name);


CREATE INDEX temp_rocks_b_interval_idx ON public.temp_rocks USING btree (b_interval);


CREATE INDEX temp_rocks_envelope_idx ON public.temp_rocks USING gist (envelope);


CREATE INDEX temp_rocks_strat_name_clean_idx ON public.temp_rocks USING btree (strat_name_clean);


CREATE INDEX temp_rocks_strat_name_idx ON public.temp_rocks USING btree (strat_name);


CREATE INDEX temp_rocks_t_interval_idx ON public.temp_rocks USING btree (t_interval);


CREATE INDEX test_rgeom_geom_idx ON public.test_rgeom USING gist (geom);


CREATE INDEX zphuctzzhp_geom_idx ON public.zphuctzzhp USING gist (geom);


CREATE INDEX co_homestake_lines_shape_geom_idx ON sources.co_homestake_lines USING gist (shape);


CREATE INDEX co_homestake_points_shape_geom_idx ON sources.co_homestake_points USING gist (shape);


CREATE INDEX co_homestake_shape_geom_idx ON sources.co_homestake USING gist (shape);


CREATE INDEX faults_arc_code_idx ON sources.gmus_faults USING btree (arc_code);


CREATE INDEX faults_the_geom_idx ON sources.gmus_faults USING gist (the_geom);


CREATE UNIQUE INDEX gid_idx ON sources.id_salmon USING btree (gid);


CREATE INDEX gmus2_unit_link_idx ON sources.gmus2 USING btree (unit_link);


CREATE INDEX gmus_age_bottom_idx1 ON sources.gmus USING btree (age_bottom);


CREATE INDEX gmus_geom_idx1 ON sources.gmus USING gist (geom);


CREATE INDEX gmus_state_idx1 ON sources.gmus USING btree (state);


CREATE INDEX gmus_text_search_idx1 ON sources.gmus USING gin (text_search);


CREATE INDEX gmus_unit_link_idx1 ON sources.gmus USING btree (unit_link);


CREATE INDEX gmus_unit_name_idx1 ON sources.gmus USING btree (unit_name);


CREATE INDEX id_fairfield_wkb_geometry_geom_idx ON sources.id_fairfield USING gist (wkb_geometry);


CREATE INDEX id_murphy_lines_wkb_geometry_geom_idx ON sources.id_murphy_lines USING gist (wkb_geometry);


CREATE INDEX id_murphy_wkb_geometry_geom_idx ON sources.id_murphy USING gist (wkb_geometry);


CREATE UNIQUE INDEX id_salmon_gid_lines_idx ON sources.id_salmon_lines USING btree (gid);


CREATE INDEX id_sandpoint_lines_wkb_geometry_geom_idx ON sources.id_sandpoint_lines USING gist (wkb_geometry);


CREATE INDEX id_sandpoint_wkb_geometry_geom_idx ON sources.id_sandpoint USING gist (wkb_geometry);


CREATE INDEX id_twinfalls_lines_wkb_geometry_geom_idx ON sources.id_twinfalls_lines USING gist (wkb_geometry);


CREATE INDEX id_twinfalls_wkb_geometry_geom_idx ON sources.id_twinfalls USING gist (wkb_geometry);


CREATE INDEX in_bartholomew_units_geom_geom_idx ON sources.in_bartholomew USING gist (geom);


CREATE INDEX lookup_units_new_geom_idx ON sources.gmna USING gist (geom);


CREATE INDEX lookup_units_new_gid_idx ON sources.gmna USING btree (gid);


CREATE INDEX lookup_units_new_gid_idx1 ON sources.gmus USING btree (gid);


CREATE INDEX lookup_units_new_lith_class_idx ON sources.gmna USING btree (lith_class);


CREATE INDEX lookup_units_new_lith_type_idx ON sources.gmna USING btree (lith_type);


CREATE INDEX lookup_units_new_macro_interval_id_idx1 ON sources.gmus USING btree (macro_interval_id);


CREATE INDEX lookup_units_new_max_age_idx ON sources.gmna USING btree (max_age);


CREATE INDEX lookup_units_new_min_age_idx ON sources.gmna USING btree (min_age);


CREATE INDEX nm_petroglyps_lines_shape_geom_idx ON sources.nm_petroglyps_lines USING gist (shape);


CREATE INDEX nm_petroglyps_shape_geom_idx ON sources.nm_petroglyps USING gist (shape);


CREATE INDEX paleo_point_point_wkb_geometry_geom_idx ON sources.ontario_pz_points USING gist (geom);


CREATE INDEX san_diego_ca_units_geom_idx ON sources.ca_san_diego USING gist (geom);


CREATE INDEX san_diego_ca_units_objectid_idx ON sources.ca_san_diego USING btree (objectid);


CREATE INDEX ut_prommontorymtns_folds_wkb_geometry_geom_idx ON sources.ut_prommontorymtns_folds USING gist (wkb_geometry);


CREATE INDEX ut_prommontorymtns_points_wkb_geometry_geom_idx ON sources.ut_prommontorymtns_points USING gist (wkb_geometry);


CREATE INDEX ut_prommontorymtns_wkb_geometry_geom_idx ON sources.ut_prommontorymtns USING gist (wkb_geometry);


CREATE INDEX world_basins_geom_idx ON sources.world_basins USING gist (geom);


