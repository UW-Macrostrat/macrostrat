--
-- PostgreSQL database dump
--

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

--
-- Name: carto; Type: SCHEMA; Schema: -; Owner: postgres
--

CREATE SCHEMA carto;


ALTER SCHEMA carto OWNER TO postgres;

--
-- Name: carto_new; Type: SCHEMA; Schema: -; Owner: postgres
--

CREATE SCHEMA carto_new;


ALTER SCHEMA carto_new OWNER TO postgres;

--
-- Name: detrital_zircon; Type: SCHEMA; Schema: -; Owner: postgres
--

CREATE SCHEMA detrital_zircon;


ALTER SCHEMA detrital_zircon OWNER TO postgres;

--
-- Name: geologic_boundaries; Type: SCHEMA; Schema: -; Owner: postgres
--

CREATE SCHEMA geologic_boundaries;


ALTER SCHEMA geologic_boundaries OWNER TO postgres;

--
-- Name: hexgrids; Type: SCHEMA; Schema: -; Owner: postgres
--

CREATE SCHEMA hexgrids;


ALTER SCHEMA hexgrids OWNER TO postgres;

--
-- Name: lines; Type: SCHEMA; Schema: -; Owner: postgres
--

CREATE SCHEMA lines;


ALTER SCHEMA lines OWNER TO postgres;

--
-- Name: macrostrat; Type: SCHEMA; Schema: -; Owner: postgres
--

CREATE SCHEMA macrostrat;


ALTER SCHEMA macrostrat OWNER TO postgres;

--
-- Name: maps; Type: SCHEMA; Schema: -; Owner: postgres
--

CREATE SCHEMA maps;


ALTER SCHEMA maps OWNER TO postgres;

--
-- Name: points; Type: SCHEMA; Schema: -; Owner: postgres
--

CREATE SCHEMA points;


ALTER SCHEMA points OWNER TO postgres;

--
-- Name: sources; Type: SCHEMA; Schema: -; Owner: postgres
--

CREATE SCHEMA sources;


ALTER SCHEMA sources OWNER TO postgres;

--
-- Name: topology; Type: SCHEMA; Schema: -; Owner: postgres
--

CREATE SCHEMA topology;


ALTER SCHEMA topology OWNER TO postgres;

--
-- Name: pg_stat_statements; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS pg_stat_statements WITH SCHEMA public;


--
-- Name: pgaudit; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS pgaudit WITH SCHEMA public;


--
-- Name: postgis; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS postgis WITH SCHEMA public;


--
-- Name: postgis_raster; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS postgis_raster WITH SCHEMA public;


--
-- Name: postgis_topology; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS postgis_topology WITH SCHEMA topology;


--
-- Name: postgres_fdw; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS postgres_fdw WITH SCHEMA public;


--
-- Name: measurement_class; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.measurement_class AS ENUM (
    '',
    'geophysical',
    'geochemical',
    'sedimentological'
);


ALTER TYPE public.measurement_class OWNER TO postgres;

--
-- Name: measurement_class_new; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.measurement_class_new AS ENUM (
    '',
    'geophysical',
    'geochemical',
    'sedimentological'
);


ALTER TYPE public.measurement_class_new OWNER TO postgres;

--
-- Name: measurement_type; Type: TYPE; Schema: public; Owner: postgres
--

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


ALTER TYPE public.measurement_type OWNER TO postgres;

--
-- Name: measurement_type_new; Type: TYPE; Schema: public; Owner: postgres
--

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


ALTER TYPE public.measurement_type_new OWNER TO postgres;

--
-- Name: count_estimate(text); Type: FUNCTION; Schema: public; Owner: postgres
--

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


ALTER FUNCTION public.count_estimate(query text) OWNER TO postgres;

--
-- Name: array_agg_mult(anycompatiblearray); Type: AGGREGATE; Schema: public; Owner: postgres
--

CREATE AGGREGATE public.array_agg_mult(anycompatiblearray) (
    SFUNC = array_cat,
    STYPE = anycompatiblearray,
    INITCOND = '{}'
);


ALTER AGGREGATE public.array_agg_mult(anycompatiblearray) OWNER TO postgres;

--
-- Name: elevation; Type: SERVER; Schema: -; Owner: postgres
--

CREATE SERVER elevation FOREIGN DATA WRAPPER postgres_fdw OPTIONS (
    dbname 'elevation',
    host 'localhost',
    port '5432',
    use_remote_estimate 'true'
);


ALTER SERVER elevation OWNER TO postgres;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: flat_large; Type: TABLE; Schema: carto; Owner: postgres
--

CREATE TABLE carto.flat_large (
    map_id integer,
    geom public.geometry
);


ALTER TABLE carto.flat_large OWNER TO postgres;

--
-- Name: flat_medium; Type: TABLE; Schema: carto; Owner: postgres
--

CREATE TABLE carto.flat_medium (
    map_id integer,
    geom public.geometry
);


ALTER TABLE carto.flat_medium OWNER TO postgres;

--
-- Name: large; Type: TABLE; Schema: carto; Owner: postgres
--

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


ALTER TABLE carto.large OWNER TO postgres;

--
-- Name: lines_large; Type: TABLE; Schema: carto; Owner: postgres
--

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


ALTER TABLE carto.lines_large OWNER TO postgres;

--
-- Name: lines_medium; Type: TABLE; Schema: carto; Owner: postgres
--

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


ALTER TABLE carto.lines_medium OWNER TO postgres;

--
-- Name: lines_small; Type: TABLE; Schema: carto; Owner: postgres
--

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


ALTER TABLE carto.lines_small OWNER TO postgres;

--
-- Name: lines_tiny; Type: TABLE; Schema: carto; Owner: postgres
--

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


ALTER TABLE carto.lines_tiny OWNER TO postgres;

--
-- Name: medium; Type: TABLE; Schema: carto; Owner: postgres
--

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


ALTER TABLE carto.medium OWNER TO postgres;

--
-- Name: small; Type: TABLE; Schema: carto; Owner: postgres
--

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


ALTER TABLE carto.small OWNER TO postgres;

--
-- Name: tiny; Type: TABLE; Schema: carto; Owner: postgres
--

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


ALTER TABLE carto.tiny OWNER TO postgres;

--
-- Name: hex_index; Type: TABLE; Schema: carto_new; Owner: postgres
--

CREATE TABLE carto_new.hex_index (
    map_id integer NOT NULL,
    scale text,
    hex_id integer
);


ALTER TABLE carto_new.hex_index OWNER TO postgres;

--
-- Name: large; Type: TABLE; Schema: carto_new; Owner: postgres
--

CREATE TABLE carto_new.large (
    map_id integer,
    source_id integer,
    scale text,
    geom public.geometry
);


ALTER TABLE carto_new.large OWNER TO postgres;

--
-- Name: lines_large; Type: TABLE; Schema: carto_new; Owner: postgres
--

CREATE TABLE carto_new.lines_large (
    line_id integer,
    source_id integer,
    scale text,
    geom public.geometry
);


ALTER TABLE carto_new.lines_large OWNER TO postgres;

--
-- Name: lines_medium; Type: TABLE; Schema: carto_new; Owner: postgres
--

CREATE TABLE carto_new.lines_medium (
    line_id integer,
    source_id integer,
    scale text,
    geom public.geometry
);


ALTER TABLE carto_new.lines_medium OWNER TO postgres;

--
-- Name: lines_small; Type: TABLE; Schema: carto_new; Owner: postgres
--

CREATE TABLE carto_new.lines_small (
    line_id integer,
    source_id integer,
    scale text,
    geom public.geometry
);


ALTER TABLE carto_new.lines_small OWNER TO postgres;

--
-- Name: lines_tiny; Type: TABLE; Schema: carto_new; Owner: postgres
--

CREATE TABLE carto_new.lines_tiny (
    line_id integer,
    source_id integer,
    scale text,
    geom public.geometry(Geometry,4326)
);


ALTER TABLE carto_new.lines_tiny OWNER TO postgres;

--
-- Name: medium; Type: TABLE; Schema: carto_new; Owner: postgres
--

CREATE TABLE carto_new.medium (
    map_id integer,
    source_id integer,
    scale text,
    geom public.geometry
);


ALTER TABLE carto_new.medium OWNER TO postgres;

--
-- Name: pbdb_hex_index; Type: TABLE; Schema: carto_new; Owner: postgres
--

CREATE TABLE carto_new.pbdb_hex_index (
    collection_no integer NOT NULL,
    scale text,
    hex_id integer
);


ALTER TABLE carto_new.pbdb_hex_index OWNER TO postgres;

--
-- Name: small; Type: TABLE; Schema: carto_new; Owner: postgres
--

CREATE TABLE carto_new.small (
    map_id integer,
    source_id integer,
    scale text,
    geom public.geometry
);


ALTER TABLE carto_new.small OWNER TO postgres;

--
-- Name: tiny; Type: TABLE; Schema: carto_new; Owner: postgres
--

CREATE TABLE carto_new.tiny (
    map_id integer,
    source_id integer,
    scale text,
    geom public.geometry
);


ALTER TABLE carto_new.tiny OWNER TO postgres;

--
-- Name: located_query_bounds; Type: TABLE; Schema: detrital_zircon; Owner: postgres
--

CREATE TABLE detrital_zircon.located_query_bounds (
    id integer NOT NULL,
    geometry public.geometry(MultiPolygon,4326) NOT NULL,
    name text,
    notes text
);


ALTER TABLE detrital_zircon.located_query_bounds OWNER TO postgres;

--
-- Name: located_query_bounds_id_seq; Type: SEQUENCE; Schema: detrital_zircon; Owner: postgres
--

CREATE SEQUENCE detrital_zircon.located_query_bounds_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE detrital_zircon.located_query_bounds_id_seq OWNER TO postgres;

--
-- Name: located_query_bounds_id_seq; Type: SEQUENCE OWNED BY; Schema: detrital_zircon; Owner: postgres
--

ALTER SEQUENCE detrital_zircon.located_query_bounds_id_seq OWNED BY detrital_zircon.located_query_bounds.id;


--
-- Name: boundaries; Type: TABLE; Schema: geologic_boundaries; Owner: postgres
--

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


ALTER TABLE geologic_boundaries.boundaries OWNER TO postgres;

--
-- Name: boundaries_boundary_id_seq; Type: SEQUENCE; Schema: geologic_boundaries; Owner: postgres
--

CREATE SEQUENCE geologic_boundaries.boundaries_boundary_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE geologic_boundaries.boundaries_boundary_id_seq OWNER TO postgres;

--
-- Name: boundaries_boundary_id_seq; Type: SEQUENCE OWNED BY; Schema: geologic_boundaries; Owner: postgres
--

ALTER SEQUENCE geologic_boundaries.boundaries_boundary_id_seq OWNED BY geologic_boundaries.boundaries.boundary_id;


--
-- Name: geologic_boundary_source_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.geologic_boundary_source_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.geologic_boundary_source_seq OWNER TO postgres;

--
-- Name: sources; Type: TABLE; Schema: geologic_boundaries; Owner: postgres
--

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


ALTER TABLE geologic_boundaries.sources OWNER TO postgres;

--
-- Name: bedrock_index; Type: TABLE; Schema: hexgrids; Owner: postgres
--

CREATE TABLE hexgrids.bedrock_index (
    legend_id integer NOT NULL,
    hex_id integer NOT NULL,
    coverage numeric
);


ALTER TABLE hexgrids.bedrock_index OWNER TO postgres;

--
-- Name: hexgrids; Type: TABLE; Schema: hexgrids; Owner: postgres
--

CREATE TABLE hexgrids.hexgrids (
    hex_id integer NOT NULL,
    res integer,
    geom public.geometry
);


ALTER TABLE hexgrids.hexgrids OWNER TO postgres;

--
-- Name: pbdb_index; Type: TABLE; Schema: hexgrids; Owner: postgres
--

CREATE TABLE hexgrids.pbdb_index (
    collection_no integer NOT NULL,
    hex_id integer NOT NULL
);


ALTER TABLE hexgrids.pbdb_index OWNER TO postgres;

--
-- Name: r10; Type: TABLE; Schema: hexgrids; Owner: postgres
--

CREATE TABLE hexgrids.r10 (
    hex_id integer NOT NULL,
    geom public.geometry(MultiPolygon,4326),
    web_geom public.geometry
);


ALTER TABLE hexgrids.r10 OWNER TO postgres;

--
-- Name: r10_ogc_fid_seq; Type: SEQUENCE; Schema: hexgrids; Owner: postgres
--

CREATE SEQUENCE hexgrids.r10_ogc_fid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE hexgrids.r10_ogc_fid_seq OWNER TO postgres;

--
-- Name: r10_ogc_fid_seq; Type: SEQUENCE OWNED BY; Schema: hexgrids; Owner: postgres
--

ALTER SEQUENCE hexgrids.r10_ogc_fid_seq OWNED BY hexgrids.r10.hex_id;


--
-- Name: r11; Type: TABLE; Schema: hexgrids; Owner: postgres
--

CREATE TABLE hexgrids.r11 (
    hex_id integer NOT NULL,
    geom public.geometry(MultiPolygon,4326),
    web_geom public.geometry
);


ALTER TABLE hexgrids.r11 OWNER TO postgres;

--
-- Name: r11_ogc_fid_seq; Type: SEQUENCE; Schema: hexgrids; Owner: postgres
--

CREATE SEQUENCE hexgrids.r11_ogc_fid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE hexgrids.r11_ogc_fid_seq OWNER TO postgres;

--
-- Name: r11_ogc_fid_seq; Type: SEQUENCE OWNED BY; Schema: hexgrids; Owner: postgres
--

ALTER SEQUENCE hexgrids.r11_ogc_fid_seq OWNED BY hexgrids.r11.hex_id;


--
-- Name: r12; Type: TABLE; Schema: hexgrids; Owner: postgres
--

CREATE TABLE hexgrids.r12 (
    hex_id integer NOT NULL,
    geom public.geometry(MultiPolygon,4326),
    web_geom public.geometry
);


ALTER TABLE hexgrids.r12 OWNER TO postgres;

--
-- Name: r12_ogc_fid_seq; Type: SEQUENCE; Schema: hexgrids; Owner: postgres
--

CREATE SEQUENCE hexgrids.r12_ogc_fid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE hexgrids.r12_ogc_fid_seq OWNER TO postgres;

--
-- Name: r12_ogc_fid_seq; Type: SEQUENCE OWNED BY; Schema: hexgrids; Owner: postgres
--

ALTER SEQUENCE hexgrids.r12_ogc_fid_seq OWNED BY hexgrids.r12.hex_id;


--
-- Name: r5; Type: TABLE; Schema: hexgrids; Owner: postgres
--

CREATE TABLE hexgrids.r5 (
    hex_id integer NOT NULL,
    geom public.geometry(MultiPolygon,4326),
    web_geom public.geometry
);


ALTER TABLE hexgrids.r5 OWNER TO postgres;

--
-- Name: r5_ogc_fid_seq; Type: SEQUENCE; Schema: hexgrids; Owner: postgres
--

CREATE SEQUENCE hexgrids.r5_ogc_fid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE hexgrids.r5_ogc_fid_seq OWNER TO postgres;

--
-- Name: r5_ogc_fid_seq; Type: SEQUENCE OWNED BY; Schema: hexgrids; Owner: postgres
--

ALTER SEQUENCE hexgrids.r5_ogc_fid_seq OWNED BY hexgrids.r5.hex_id;


--
-- Name: r6; Type: TABLE; Schema: hexgrids; Owner: postgres
--

CREATE TABLE hexgrids.r6 (
    hex_id integer NOT NULL,
    geom public.geometry(MultiPolygon,4326),
    web_geom public.geometry
);


ALTER TABLE hexgrids.r6 OWNER TO postgres;

--
-- Name: r6_ogc_fid_seq; Type: SEQUENCE; Schema: hexgrids; Owner: postgres
--

CREATE SEQUENCE hexgrids.r6_ogc_fid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE hexgrids.r6_ogc_fid_seq OWNER TO postgres;

--
-- Name: r6_ogc_fid_seq; Type: SEQUENCE OWNED BY; Schema: hexgrids; Owner: postgres
--

ALTER SEQUENCE hexgrids.r6_ogc_fid_seq OWNED BY hexgrids.r6.hex_id;


--
-- Name: r7; Type: TABLE; Schema: hexgrids; Owner: postgres
--

CREATE TABLE hexgrids.r7 (
    hex_id integer NOT NULL,
    geom public.geometry(MultiPolygon,4326),
    web_geom public.geometry
);


ALTER TABLE hexgrids.r7 OWNER TO postgres;

--
-- Name: r7_ogc_fid_seq; Type: SEQUENCE; Schema: hexgrids; Owner: postgres
--

CREATE SEQUENCE hexgrids.r7_ogc_fid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE hexgrids.r7_ogc_fid_seq OWNER TO postgres;

--
-- Name: r7_ogc_fid_seq; Type: SEQUENCE OWNED BY; Schema: hexgrids; Owner: postgres
--

ALTER SEQUENCE hexgrids.r7_ogc_fid_seq OWNED BY hexgrids.r7.hex_id;


--
-- Name: r8; Type: TABLE; Schema: hexgrids; Owner: postgres
--

CREATE TABLE hexgrids.r8 (
    hex_id integer NOT NULL,
    geom public.geometry(MultiPolygon,4326),
    web_geom public.geometry
);


ALTER TABLE hexgrids.r8 OWNER TO postgres;

--
-- Name: r8_ogc_fid_seq; Type: SEQUENCE; Schema: hexgrids; Owner: postgres
--

CREATE SEQUENCE hexgrids.r8_ogc_fid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE hexgrids.r8_ogc_fid_seq OWNER TO postgres;

--
-- Name: r8_ogc_fid_seq; Type: SEQUENCE OWNED BY; Schema: hexgrids; Owner: postgres
--

ALTER SEQUENCE hexgrids.r8_ogc_fid_seq OWNED BY hexgrids.r8.hex_id;


--
-- Name: r9; Type: TABLE; Schema: hexgrids; Owner: postgres
--

CREATE TABLE hexgrids.r9 (
    hex_id integer NOT NULL,
    geom public.geometry(MultiPolygon,4326),
    web_geom public.geometry
);


ALTER TABLE hexgrids.r9 OWNER TO postgres;

--
-- Name: r9_ogc_fid_seq; Type: SEQUENCE; Schema: hexgrids; Owner: postgres
--

CREATE SEQUENCE hexgrids.r9_ogc_fid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE hexgrids.r9_ogc_fid_seq OWNER TO postgres;

--
-- Name: r9_ogc_fid_seq; Type: SEQUENCE OWNED BY; Schema: hexgrids; Owner: postgres
--

ALTER SEQUENCE hexgrids.r9_ogc_fid_seq OWNED BY hexgrids.r9.hex_id;


--
-- Name: line_ids; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.line_ids
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.line_ids OWNER TO postgres;

--
-- Name: large; Type: TABLE; Schema: lines; Owner: postgres
--

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


ALTER TABLE lines.large OWNER TO postgres;

--
-- Name: medium; Type: TABLE; Schema: lines; Owner: postgres
--

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


ALTER TABLE lines.medium OWNER TO postgres;

--
-- Name: small; Type: TABLE; Schema: lines; Owner: postgres
--

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


ALTER TABLE lines.small OWNER TO postgres;

--
-- Name: tiny; Type: TABLE; Schema: lines; Owner: postgres
--

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


ALTER TABLE lines.tiny OWNER TO postgres;

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
-- Name: col_areas; Type: TABLE; Schema: macrostrat; Owner: postgres
--

CREATE TABLE macrostrat.col_areas (
    id integer NOT NULL,
    col_id integer,
    col_area public.geometry,
    wkt text
);


ALTER TABLE macrostrat.col_areas OWNER TO postgres;

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
-- Name: col_refs; Type: TABLE; Schema: macrostrat; Owner: postgres
--

CREATE TABLE macrostrat.col_refs (
    id integer NOT NULL,
    col_id integer,
    ref_id integer
);


ALTER TABLE macrostrat.col_refs OWNER TO postgres;

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
    coordinate public.geometry,
    wkt text,
    created text,
    poly_geom public.geometry
);


ALTER TABLE macrostrat.cols OWNER TO postgres;

--
-- Name: concepts_places; Type: TABLE; Schema: macrostrat; Owner: postgres
--

CREATE TABLE macrostrat.concepts_places (
    concept_id integer NOT NULL,
    place_id integer NOT NULL
);


ALTER TABLE macrostrat.concepts_places OWNER TO postgres;

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
-- Name: measurements; Type: TABLE; Schema: macrostrat; Owner: postgres
--

CREATE TABLE macrostrat.measurements (
    id integer NOT NULL,
    measurement_class public.measurement_class NOT NULL,
    measurement_type public.measurement_type NOT NULL,
    measurement text NOT NULL
);


ALTER TABLE macrostrat.measurements OWNER TO postgres;

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
-- Name: measurements_new_id_seq; Type: SEQUENCE OWNED BY; Schema: macrostrat; Owner: postgres
--

ALTER SEQUENCE macrostrat.measurements_new_id_seq OWNED BY macrostrat.measurements.id;


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
-- Name: measures_new_id_seq1; Type: SEQUENCE; Schema: macrostrat; Owner: postgres
--

CREATE SEQUENCE macrostrat.measures_new_id_seq1
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE macrostrat.measures_new_id_seq1 OWNER TO postgres;

--
-- Name: measures_new_id_seq1; Type: SEQUENCE OWNED BY; Schema: macrostrat; Owner: postgres
--

ALTER SEQUENCE macrostrat.measures_new_id_seq1 OWNED BY macrostrat.measures.id;


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
    geom public.geometry
);


ALTER TABLE macrostrat.pbdb_collections OWNER TO postgres;

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
    geom public.geometry
);


ALTER TABLE macrostrat.places OWNER TO postgres;

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
    rgeom public.geometry
);


ALTER TABLE macrostrat.refs OWNER TO postgres;

--
-- Name: strat_name_footprints; Type: TABLE; Schema: macrostrat; Owner: postgres
--

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
-- Name: timescales; Type: TABLE; Schema: macrostrat; Owner: postgres
--

CREATE TABLE macrostrat.timescales (
    id integer NOT NULL,
    timescale character varying(100),
    ref_id integer
);


ALTER TABLE macrostrat.timescales OWNER TO postgres;

--
-- Name: timescales_intervals; Type: TABLE; Schema: macrostrat; Owner: postgres
--

CREATE TABLE macrostrat.timescales_intervals (
    timescale_id integer,
    interval_id integer
);


ALTER TABLE macrostrat.timescales_intervals OWNER TO postgres;

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
-- Name: units_sections_new_id_seq; Type: SEQUENCE; Schema: macrostrat; Owner: postgres
--

CREATE SEQUENCE macrostrat.units_sections_new_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE macrostrat.units_sections_new_id_seq OWNER TO postgres;

--
-- Name: units_sections_new_id_seq; Type: SEQUENCE OWNED BY; Schema: macrostrat; Owner: postgres
--

ALTER SEQUENCE macrostrat.units_sections_new_id_seq OWNED BY macrostrat.units_sections.id;


--
-- Name: map_ids; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.map_ids
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.map_ids OWNER TO postgres;

--
-- Name: large; Type: TABLE; Schema: maps; Owner: postgres
--

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


ALTER TABLE maps.large OWNER TO postgres;

--
-- Name: legend; Type: TABLE; Schema: maps; Owner: postgres
--

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


ALTER TABLE maps.legend OWNER TO postgres;

--
-- Name: legend_legend_id_seq; Type: SEQUENCE; Schema: maps; Owner: postgres
--

CREATE SEQUENCE maps.legend_legend_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE maps.legend_legend_id_seq OWNER TO postgres;

--
-- Name: legend_legend_id_seq; Type: SEQUENCE OWNED BY; Schema: maps; Owner: postgres
--

ALTER SEQUENCE maps.legend_legend_id_seq OWNED BY maps.legend.legend_id;


--
-- Name: legend_liths; Type: TABLE; Schema: maps; Owner: postgres
--

CREATE TABLE maps.legend_liths (
    legend_id integer NOT NULL,
    lith_id integer NOT NULL,
    basis_col text NOT NULL
);


ALTER TABLE maps.legend_liths OWNER TO postgres;

--
-- Name: manual_matches; Type: TABLE; Schema: maps; Owner: postgres
--

CREATE TABLE maps.manual_matches (
    match_id integer NOT NULL,
    map_id integer NOT NULL,
    strat_name_id integer,
    unit_id integer,
    addition boolean DEFAULT false,
    removal boolean DEFAULT false,
    type character varying(20)
);


ALTER TABLE maps.manual_matches OWNER TO postgres;

--
-- Name: manual_matches_match_id_seq; Type: SEQUENCE; Schema: maps; Owner: postgres
--

CREATE SEQUENCE maps.manual_matches_match_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE maps.manual_matches_match_id_seq OWNER TO postgres;

--
-- Name: manual_matches_match_id_seq; Type: SEQUENCE OWNED BY; Schema: maps; Owner: postgres
--

ALTER SEQUENCE maps.manual_matches_match_id_seq OWNED BY maps.manual_matches.match_id;


--
-- Name: map_legend; Type: TABLE; Schema: maps; Owner: postgres
--

CREATE TABLE maps.map_legend (
    legend_id integer NOT NULL,
    map_id integer NOT NULL
);


ALTER TABLE maps.map_legend OWNER TO postgres;

--
-- Name: map_liths; Type: TABLE; Schema: maps; Owner: postgres
--

CREATE TABLE maps.map_liths (
    map_id integer NOT NULL,
    lith_id integer NOT NULL,
    basis_col character varying(50)
);


ALTER TABLE maps.map_liths OWNER TO postgres;

--
-- Name: map_strat_names; Type: TABLE; Schema: maps; Owner: postgres
--

CREATE TABLE maps.map_strat_names (
    map_id integer NOT NULL,
    strat_name_id integer NOT NULL,
    basis_col character varying(50)
);


ALTER TABLE maps.map_strat_names OWNER TO postgres;

--
-- Name: map_units; Type: TABLE; Schema: maps; Owner: postgres
--

CREATE TABLE maps.map_units (
    map_id integer NOT NULL,
    unit_id integer NOT NULL,
    basis_col character varying(50)
);


ALTER TABLE maps.map_units OWNER TO postgres;

--
-- Name: medium; Type: TABLE; Schema: maps; Owner: postgres
--

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


ALTER TABLE maps.medium OWNER TO postgres;

--
-- Name: small; Type: TABLE; Schema: maps; Owner: postgres
--

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


ALTER TABLE maps.small OWNER TO postgres;

--
-- Name: sources; Type: TABLE; Schema: maps; Owner: postgres
--

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


ALTER TABLE maps.sources OWNER TO postgres;

--
-- Name: sources_source_id_seq; Type: SEQUENCE; Schema: maps; Owner: postgres
--

CREATE SEQUENCE maps.sources_source_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE maps.sources_source_id_seq OWNER TO postgres;

--
-- Name: sources_source_id_seq; Type: SEQUENCE OWNED BY; Schema: maps; Owner: postgres
--

ALTER SEQUENCE maps.sources_source_id_seq OWNED BY maps.sources.source_id;


--
-- Name: tiny; Type: TABLE; Schema: maps; Owner: postgres
--

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


ALTER TABLE maps.tiny OWNER TO postgres;

--
-- Name: points; Type: TABLE; Schema: points; Owner: postgres
--

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


ALTER TABLE points.points OWNER TO postgres;

--
-- Name: points_point_id_seq; Type: SEQUENCE; Schema: points; Owner: postgres
--

CREATE SEQUENCE points.points_point_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE points.points_point_id_seq OWNER TO postgres;

--
-- Name: points_point_id_seq; Type: SEQUENCE OWNED BY; Schema: points; Owner: postgres
--

ALTER SEQUENCE points.points_point_id_seq OWNED BY points.points.point_id;


--
-- Name: agebzepllj; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.agebzepllj (
    id integer,
    geom public.geometry
);


ALTER TABLE public.agebzepllj OWNER TO postgres;

--
-- Name: aofhmuuyjq; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.aofhmuuyjq (
    id integer,
    geom public.geometry
);


ALTER TABLE public.aofhmuuyjq OWNER TO postgres;

--
-- Name: bmbtwjmdgn; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.bmbtwjmdgn (
    id integer,
    geom public.geometry
);


ALTER TABLE public.bmbtwjmdgn OWNER TO postgres;

--
-- Name: emma5k5jzl; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.emma5k5jzl (
    id integer,
    geom public.geometry
);


ALTER TABLE public.emma5k5jzl OWNER TO postgres;

--
-- Name: i9kzotjhgr; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.i9kzotjhgr (
    id integer,
    geom public.geometry
);


ALTER TABLE public.i9kzotjhgr OWNER TO postgres;

--
-- Name: impervious; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.impervious (
    rid integer NOT NULL,
    rast public.raster
);


ALTER TABLE public.impervious OWNER TO postgres;

--
-- Name: impervious_rid_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.impervious_rid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.impervious_rid_seq OWNER TO postgres;

--
-- Name: impervious_rid_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.impervious_rid_seq OWNED BY public.impervious.rid;


--
-- Name: land; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.land (
    gid integer NOT NULL,
    scalerank numeric(10,0),
    featurecla character varying(32),
    geom public.geometry(MultiPolygon,4326)
);


ALTER TABLE public.land OWNER TO postgres;

--
-- Name: land_gid_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.land_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.land_gid_seq OWNER TO postgres;

--
-- Name: land_gid_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.land_gid_seq OWNED BY public.land.gid;


--
-- Name: lookup_large; Type: TABLE; Schema: public; Owner: postgres
--

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


ALTER TABLE public.lookup_large OWNER TO postgres;

--
-- Name: lookup_medium; Type: TABLE; Schema: public; Owner: postgres
--

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


ALTER TABLE public.lookup_medium OWNER TO postgres;

--
-- Name: lookup_small; Type: TABLE; Schema: public; Owner: postgres
--

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


ALTER TABLE public.lookup_small OWNER TO postgres;

--
-- Name: lookup_tiny; Type: TABLE; Schema: public; Owner: postgres
--

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


ALTER TABLE public.lookup_tiny OWNER TO postgres;

--
-- Name: macrostrat_union; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.macrostrat_union (
    id integer NOT NULL,
    geom public.geometry
);


ALTER TABLE public.macrostrat_union OWNER TO postgres;

--
-- Name: macrostrat_union_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.macrostrat_union_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.macrostrat_union_id_seq OWNER TO postgres;

--
-- Name: macrostrat_union_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.macrostrat_union_id_seq OWNED BY public.macrostrat_union.id;


--
-- Name: npb9s0ubia; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.npb9s0ubia (
    id integer,
    geom public.geometry
);


ALTER TABLE public.npb9s0ubia OWNER TO postgres;

--
-- Name: ref_boundaries; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.ref_boundaries (
    ref_id integer,
    ref text,
    geom public.geometry
);


ALTER TABLE public.ref_boundaries OWNER TO postgres;

--
-- Name: srtm1; Type: FOREIGN TABLE; Schema: public; Owner: postgres
--

CREATE FOREIGN TABLE public.srtm1 (
    rid integer,
    rast public.raster
)
SERVER elevation
OPTIONS (
    schema_name 'sources',
    table_name 'srtm1'
);


ALTER FOREIGN TABLE public.srtm1 OWNER TO postgres;

--
-- Name: temp_containers; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.temp_containers (
    geom public.geometry,
    row_no bigint
);


ALTER TABLE public.temp_containers OWNER TO postgres;

--
-- Name: temp_names; Type: TABLE; Schema: public; Owner: postgres
--

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


ALTER TABLE public.temp_names OWNER TO postgres;

--
-- Name: temp_rings; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.temp_rings (
    geom public.geometry,
    row_no bigint
);


ALTER TABLE public.temp_rings OWNER TO postgres;

--
-- Name: temp_rocks; Type: TABLE; Schema: public; Owner: postgres
--

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


ALTER TABLE public.temp_rocks OWNER TO postgres;

--
-- Name: test_rgeom; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.test_rgeom (
    gid integer NOT NULL,
    fid smallint,
    geom public.geometry(MultiPolygon,4326)
);


ALTER TABLE public.test_rgeom OWNER TO postgres;

--
-- Name: test_rgeom_gid_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.test_rgeom_gid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.test_rgeom_gid_seq OWNER TO postgres;

--
-- Name: test_rgeom_gid_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.test_rgeom_gid_seq OWNED BY public.test_rgeom.gid;


--
-- Name: units; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.units (
    mapunit text,
    description text
);


ALTER TABLE public.units OWNER TO postgres;

--
-- Name: zphuctzzhp; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.zphuctzzhp (
    id integer,
    geom public.geometry
);


ALTER TABLE public.zphuctzzhp OWNER TO postgres;

--
-- Name: flat_large_geom_idx; Type: INDEX; Schema: carto; Owner: postgres
--

CREATE INDEX flat_large_geom_idx ON carto.flat_large USING gist (geom);


--
-- Name: flat_large_map_id_idx; Type: INDEX; Schema: carto; Owner: postgres
--

CREATE INDEX flat_large_map_id_idx ON carto.flat_large USING btree (map_id);


--
-- Name: large_new_geom_idx; Type: INDEX; Schema: carto; Owner: postgres
--

CREATE INDEX large_new_geom_idx ON carto.large USING gist (geom);


--
-- Name: large_new_map_id_idx; Type: INDEX; Schema: carto; Owner: postgres
--

CREATE INDEX large_new_map_id_idx ON carto.large USING btree (map_id);


--
-- Name: lines_large_new_geom_idx1; Type: INDEX; Schema: carto; Owner: postgres
--

CREATE INDEX lines_large_new_geom_idx1 ON carto.lines_large USING gist (geom);


--
-- Name: lines_large_new_line_id_idx1; Type: INDEX; Schema: carto; Owner: postgres
--

CREATE INDEX lines_large_new_line_id_idx1 ON carto.lines_large USING btree (line_id);


--
-- Name: lines_medium_new_geom_idx1; Type: INDEX; Schema: carto; Owner: postgres
--

CREATE INDEX lines_medium_new_geom_idx1 ON carto.lines_medium USING gist (geom);


--
-- Name: lines_medium_new_line_id_idx1; Type: INDEX; Schema: carto; Owner: postgres
--

CREATE INDEX lines_medium_new_line_id_idx1 ON carto.lines_medium USING btree (line_id);


--
-- Name: lines_small_new_geom_idx1; Type: INDEX; Schema: carto; Owner: postgres
--

CREATE INDEX lines_small_new_geom_idx1 ON carto.lines_small USING gist (geom);


--
-- Name: lines_small_new_line_id_idx1; Type: INDEX; Schema: carto; Owner: postgres
--

CREATE INDEX lines_small_new_line_id_idx1 ON carto.lines_small USING btree (line_id);


--
-- Name: lines_tiny_new_geom_idx1; Type: INDEX; Schema: carto; Owner: postgres
--

CREATE INDEX lines_tiny_new_geom_idx1 ON carto.lines_tiny USING gist (geom);


--
-- Name: lines_tiny_new_line_id_idx1; Type: INDEX; Schema: carto; Owner: postgres
--

CREATE INDEX lines_tiny_new_line_id_idx1 ON carto.lines_tiny USING btree (line_id);


--
-- Name: medium_new_geom_idx; Type: INDEX; Schema: carto; Owner: postgres
--

CREATE INDEX medium_new_geom_idx ON carto.medium USING gist (geom);


--
-- Name: medium_new_map_id_idx; Type: INDEX; Schema: carto; Owner: postgres
--

CREATE INDEX medium_new_map_id_idx ON carto.medium USING btree (map_id);


--
-- Name: small_new_geom_idx; Type: INDEX; Schema: carto; Owner: postgres
--

CREATE INDEX small_new_geom_idx ON carto.small USING gist (geom);


--
-- Name: small_new_map_id_idx; Type: INDEX; Schema: carto; Owner: postgres
--

CREATE INDEX small_new_map_id_idx ON carto.small USING btree (map_id);


--
-- Name: tiny_new_geom_idx; Type: INDEX; Schema: carto; Owner: postgres
--

CREATE INDEX tiny_new_geom_idx ON carto.tiny USING gist (geom);


--
-- Name: tiny_new_map_id_idx; Type: INDEX; Schema: carto; Owner: postgres
--

CREATE INDEX tiny_new_map_id_idx ON carto.tiny USING btree (map_id);


--
-- Name: hex_index_hex_id_idx; Type: INDEX; Schema: carto_new; Owner: postgres
--

CREATE INDEX hex_index_hex_id_idx ON carto_new.hex_index USING btree (hex_id);


--
-- Name: hex_index_map_id_idx; Type: INDEX; Schema: carto_new; Owner: postgres
--

CREATE INDEX hex_index_map_id_idx ON carto_new.hex_index USING btree (map_id);


--
-- Name: hex_index_scale_idx; Type: INDEX; Schema: carto_new; Owner: postgres
--

CREATE INDEX hex_index_scale_idx ON carto_new.hex_index USING btree (scale);


--
-- Name: large_geom_idx; Type: INDEX; Schema: carto_new; Owner: postgres
--

CREATE INDEX large_geom_idx ON carto_new.large USING gist (geom);


--
-- Name: large_map_id_idx; Type: INDEX; Schema: carto_new; Owner: postgres
--

CREATE INDEX large_map_id_idx ON carto_new.large USING btree (map_id);


--
-- Name: lines_large_geom_idx; Type: INDEX; Schema: carto_new; Owner: postgres
--

CREATE INDEX lines_large_geom_idx ON carto_new.lines_large USING gist (geom);


--
-- Name: lines_large_line_id_idx; Type: INDEX; Schema: carto_new; Owner: postgres
--

CREATE INDEX lines_large_line_id_idx ON carto_new.lines_large USING btree (line_id);


--
-- Name: lines_medium_geom_idx; Type: INDEX; Schema: carto_new; Owner: postgres
--

CREATE INDEX lines_medium_geom_idx ON carto_new.lines_medium USING gist (geom);


--
-- Name: lines_medium_line_id_idx; Type: INDEX; Schema: carto_new; Owner: postgres
--

CREATE INDEX lines_medium_line_id_idx ON carto_new.lines_medium USING btree (line_id);


--
-- Name: lines_small_geom_idx; Type: INDEX; Schema: carto_new; Owner: postgres
--

CREATE INDEX lines_small_geom_idx ON carto_new.lines_small USING gist (geom);


--
-- Name: lines_small_line_id_idx; Type: INDEX; Schema: carto_new; Owner: postgres
--

CREATE INDEX lines_small_line_id_idx ON carto_new.lines_small USING btree (line_id);


--
-- Name: lines_tiny_geom_idx; Type: INDEX; Schema: carto_new; Owner: postgres
--

CREATE INDEX lines_tiny_geom_idx ON carto_new.lines_tiny USING gist (geom);


--
-- Name: lines_tiny_line_id_idx; Type: INDEX; Schema: carto_new; Owner: postgres
--

CREATE INDEX lines_tiny_line_id_idx ON carto_new.lines_tiny USING btree (line_id);


--
-- Name: medium_geom_idx; Type: INDEX; Schema: carto_new; Owner: postgres
--

CREATE INDEX medium_geom_idx ON carto_new.medium USING gist (geom);


--
-- Name: medium_map_id_idx; Type: INDEX; Schema: carto_new; Owner: postgres
--

CREATE INDEX medium_map_id_idx ON carto_new.medium USING btree (map_id);


--
-- Name: pbdb_hex_index_collection_no_idx; Type: INDEX; Schema: carto_new; Owner: postgres
--

CREATE INDEX pbdb_hex_index_collection_no_idx ON carto_new.pbdb_hex_index USING btree (collection_no);


--
-- Name: pbdb_hex_index_hex_id_idx; Type: INDEX; Schema: carto_new; Owner: postgres
--

CREATE INDEX pbdb_hex_index_hex_id_idx ON carto_new.pbdb_hex_index USING btree (hex_id);


--
-- Name: pbdb_hex_index_scale_idx; Type: INDEX; Schema: carto_new; Owner: postgres
--

CREATE INDEX pbdb_hex_index_scale_idx ON carto_new.pbdb_hex_index USING btree (scale);


--
-- Name: small_geom_idx; Type: INDEX; Schema: carto_new; Owner: postgres
--

CREATE INDEX small_geom_idx ON carto_new.small USING gist (geom);


--
-- Name: small_map_id_idx; Type: INDEX; Schema: carto_new; Owner: postgres
--

CREATE INDEX small_map_id_idx ON carto_new.small USING btree (map_id);


--
-- Name: tiny_geom_idx; Type: INDEX; Schema: carto_new; Owner: postgres
--

CREATE INDEX tiny_geom_idx ON carto_new.tiny USING gist (geom);


--
-- Name: tiny_map_id_idx; Type: INDEX; Schema: carto_new; Owner: postgres
--

CREATE INDEX tiny_map_id_idx ON carto_new.tiny USING btree (map_id);


--
-- Name: boundaries_boundary_class_idx; Type: INDEX; Schema: geologic_boundaries; Owner: postgres
--

CREATE INDEX boundaries_boundary_class_idx ON geologic_boundaries.boundaries USING btree (boundary_class);


--
-- Name: boundaries_boundary_id_idx; Type: INDEX; Schema: geologic_boundaries; Owner: postgres
--

CREATE INDEX boundaries_boundary_id_idx ON geologic_boundaries.boundaries USING btree (boundary_id);


--
-- Name: boundaries_geom_idx; Type: INDEX; Schema: geologic_boundaries; Owner: postgres
--

CREATE INDEX boundaries_geom_idx ON geologic_boundaries.boundaries USING gist (geom);


--
-- Name: boundaries_orig_id_idx; Type: INDEX; Schema: geologic_boundaries; Owner: postgres
--

CREATE INDEX boundaries_orig_id_idx ON geologic_boundaries.boundaries USING btree (orig_id);


--
-- Name: boundaries_source_id_idx; Type: INDEX; Schema: geologic_boundaries; Owner: postgres
--

CREATE INDEX boundaries_source_id_idx ON geologic_boundaries.boundaries USING btree (source_id);


--
-- Name: bedrock_index_hex_id_idx; Type: INDEX; Schema: hexgrids; Owner: postgres
--

CREATE INDEX bedrock_index_hex_id_idx ON hexgrids.bedrock_index USING btree (hex_id);


--
-- Name: bedrock_index_legend_id_hex_id_idx; Type: INDEX; Schema: hexgrids; Owner: postgres
--

CREATE UNIQUE INDEX bedrock_index_legend_id_hex_id_idx ON hexgrids.bedrock_index USING btree (legend_id, hex_id);


--
-- Name: bedrock_index_legend_id_idx; Type: INDEX; Schema: hexgrids; Owner: postgres
--

CREATE INDEX bedrock_index_legend_id_idx ON hexgrids.bedrock_index USING btree (legend_id);


--
-- Name: hexgrids_geom_idx; Type: INDEX; Schema: hexgrids; Owner: postgres
--

CREATE INDEX hexgrids_geom_idx ON hexgrids.hexgrids USING gist (geom);


--
-- Name: hexgrids_res_idx; Type: INDEX; Schema: hexgrids; Owner: postgres
--

CREATE INDEX hexgrids_res_idx ON hexgrids.hexgrids USING btree (res);


--
-- Name: pbdb_index_collection_no_hex_id_idx; Type: INDEX; Schema: hexgrids; Owner: postgres
--

CREATE UNIQUE INDEX pbdb_index_collection_no_hex_id_idx ON hexgrids.pbdb_index USING btree (collection_no, hex_id);


--
-- Name: pbdb_index_collection_no_idx; Type: INDEX; Schema: hexgrids; Owner: postgres
--

CREATE INDEX pbdb_index_collection_no_idx ON hexgrids.pbdb_index USING btree (collection_no);


--
-- Name: pbdb_index_hex_id_idx; Type: INDEX; Schema: hexgrids; Owner: postgres
--

CREATE INDEX pbdb_index_hex_id_idx ON hexgrids.pbdb_index USING btree (hex_id);


--
-- Name: r10_geom_geom_idx; Type: INDEX; Schema: hexgrids; Owner: postgres
--

CREATE INDEX r10_geom_geom_idx ON hexgrids.r10 USING gist (geom);


--
-- Name: r10_geom_idx; Type: INDEX; Schema: hexgrids; Owner: postgres
--

CREATE INDEX r10_geom_idx ON hexgrids.r10 USING gist (geom);


--
-- Name: r10_web_geom_idx; Type: INDEX; Schema: hexgrids; Owner: postgres
--

CREATE INDEX r10_web_geom_idx ON hexgrids.r10 USING gist (web_geom);


--
-- Name: r11_geom_geom_idx; Type: INDEX; Schema: hexgrids; Owner: postgres
--

CREATE INDEX r11_geom_geom_idx ON hexgrids.r11 USING gist (geom);


--
-- Name: r11_web_geom_idx; Type: INDEX; Schema: hexgrids; Owner: postgres
--

CREATE INDEX r11_web_geom_idx ON hexgrids.r11 USING gist (web_geom);


--
-- Name: r12_geom_geom_idx; Type: INDEX; Schema: hexgrids; Owner: postgres
--

CREATE INDEX r12_geom_geom_idx ON hexgrids.r12 USING gist (geom);


--
-- Name: r12_web_geom_idx; Type: INDEX; Schema: hexgrids; Owner: postgres
--

CREATE INDEX r12_web_geom_idx ON hexgrids.r12 USING gist (web_geom);


--
-- Name: r5_geom_idx; Type: INDEX; Schema: hexgrids; Owner: postgres
--

CREATE INDEX r5_geom_idx ON hexgrids.r5 USING gist (geom);


--
-- Name: r5_web_geom_idx; Type: INDEX; Schema: hexgrids; Owner: postgres
--

CREATE INDEX r5_web_geom_idx ON hexgrids.r5 USING gist (web_geom);


--
-- Name: r6_geom_idx; Type: INDEX; Schema: hexgrids; Owner: postgres
--

CREATE INDEX r6_geom_idx ON hexgrids.r6 USING gist (geom);


--
-- Name: r6_web_geom_idx; Type: INDEX; Schema: hexgrids; Owner: postgres
--

CREATE INDEX r6_web_geom_idx ON hexgrids.r6 USING gist (web_geom);


--
-- Name: r7_geom_idx; Type: INDEX; Schema: hexgrids; Owner: postgres
--

CREATE INDEX r7_geom_idx ON hexgrids.r7 USING gist (geom);


--
-- Name: r7_geom_idx1; Type: INDEX; Schema: hexgrids; Owner: postgres
--

CREATE INDEX r7_geom_idx1 ON hexgrids.r7 USING gist (geom);


--
-- Name: r7_geom_idx2; Type: INDEX; Schema: hexgrids; Owner: postgres
--

CREATE INDEX r7_geom_idx2 ON hexgrids.r7 USING gist (geom);


--
-- Name: r7_web_geom_idx; Type: INDEX; Schema: hexgrids; Owner: postgres
--

CREATE INDEX r7_web_geom_idx ON hexgrids.r7 USING gist (web_geom);


--
-- Name: r8_geom_idx; Type: INDEX; Schema: hexgrids; Owner: postgres
--

CREATE INDEX r8_geom_idx ON hexgrids.r8 USING gist (geom);


--
-- Name: r8_geom_idx1; Type: INDEX; Schema: hexgrids; Owner: postgres
--

CREATE INDEX r8_geom_idx1 ON hexgrids.r8 USING gist (geom);


--
-- Name: r8_geom_idx2; Type: INDEX; Schema: hexgrids; Owner: postgres
--

CREATE INDEX r8_geom_idx2 ON hexgrids.r8 USING gist (geom);


--
-- Name: r8_web_geom_idx; Type: INDEX; Schema: hexgrids; Owner: postgres
--

CREATE INDEX r8_web_geom_idx ON hexgrids.r8 USING gist (web_geom);


--
-- Name: r9_geom_idx; Type: INDEX; Schema: hexgrids; Owner: postgres
--

CREATE INDEX r9_geom_idx ON hexgrids.r9 USING gist (geom);


--
-- Name: r9_geom_idx1; Type: INDEX; Schema: hexgrids; Owner: postgres
--

CREATE INDEX r9_geom_idx1 ON hexgrids.r9 USING gist (geom);


--
-- Name: r9_web_geom_idx; Type: INDEX; Schema: hexgrids; Owner: postgres
--

CREATE INDEX r9_web_geom_idx ON hexgrids.r9 USING gist (web_geom);


--
-- Name: large_geom_idx; Type: INDEX; Schema: lines; Owner: postgres
--

CREATE INDEX large_geom_idx ON lines.large USING gist (geom);


--
-- Name: large_line_id_idx; Type: INDEX; Schema: lines; Owner: postgres
--

CREATE INDEX large_line_id_idx ON lines.large USING btree (line_id);


--
-- Name: large_orig_id_idx; Type: INDEX; Schema: lines; Owner: postgres
--

CREATE INDEX large_orig_id_idx ON lines.large USING btree (orig_id);


--
-- Name: large_source_id_idx; Type: INDEX; Schema: lines; Owner: postgres
--

CREATE INDEX large_source_id_idx ON lines.large USING btree (source_id);


--
-- Name: medium_geom_idx; Type: INDEX; Schema: lines; Owner: postgres
--

CREATE INDEX medium_geom_idx ON lines.medium USING gist (geom);


--
-- Name: medium_line_id_idx; Type: INDEX; Schema: lines; Owner: postgres
--

CREATE INDEX medium_line_id_idx ON lines.medium USING btree (line_id);


--
-- Name: medium_orig_id_idx; Type: INDEX; Schema: lines; Owner: postgres
--

CREATE INDEX medium_orig_id_idx ON lines.medium USING btree (orig_id);


--
-- Name: medium_source_id_idx; Type: INDEX; Schema: lines; Owner: postgres
--

CREATE INDEX medium_source_id_idx ON lines.medium USING btree (source_id);


--
-- Name: small_geom_idx; Type: INDEX; Schema: lines; Owner: postgres
--

CREATE INDEX small_geom_idx ON lines.small USING gist (geom);


--
-- Name: small_source_id_idx; Type: INDEX; Schema: lines; Owner: postgres
--

CREATE INDEX small_source_id_idx ON lines.small USING btree (source_id);


--
-- Name: tiny_geom_idx; Type: INDEX; Schema: lines; Owner: postgres
--

CREATE INDEX tiny_geom_idx ON lines.tiny USING gist (geom);


--
-- Name: tiny_source_id_idx; Type: INDEX; Schema: lines; Owner: postgres
--

CREATE INDEX tiny_source_id_idx ON lines.tiny USING btree (source_id);


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
-- Name: cols_new_col_group_id_idx; Type: INDEX; Schema: macrostrat; Owner: postgres
--

CREATE INDEX cols_new_col_group_id_idx ON macrostrat.cols USING btree (col_group_id);


--
-- Name: cols_new_coordinate_idx; Type: INDEX; Schema: macrostrat; Owner: postgres
--

CREATE INDEX cols_new_coordinate_idx ON macrostrat.cols USING gist (coordinate);


--
-- Name: cols_new_poly_geom_idx; Type: INDEX; Schema: macrostrat; Owner: postgres
--

CREATE INDEX cols_new_poly_geom_idx ON macrostrat.cols USING gist (poly_geom);


--
-- Name: cols_new_project_id_idx; Type: INDEX; Schema: macrostrat; Owner: postgres
--

CREATE INDEX cols_new_project_id_idx ON macrostrat.cols USING btree (project_id);


--
-- Name: cols_new_status_code_idx; Type: INDEX; Schema: macrostrat; Owner: postgres
--

CREATE INDEX cols_new_status_code_idx ON macrostrat.cols USING btree (status_code);


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
-- Name: lookup_strat_names_new_bed_id_idx; Type: INDEX; Schema: macrostrat; Owner: postgres
--

CREATE INDEX lookup_strat_names_new_bed_id_idx ON macrostrat.lookup_strat_names USING btree (bed_id);


--
-- Name: lookup_strat_names_new_concept_id_idx; Type: INDEX; Schema: macrostrat; Owner: postgres
--

CREATE INDEX lookup_strat_names_new_concept_id_idx ON macrostrat.lookup_strat_names USING btree (concept_id);


--
-- Name: lookup_strat_names_new_fm_id_idx; Type: INDEX; Schema: macrostrat; Owner: postgres
--

CREATE INDEX lookup_strat_names_new_fm_id_idx ON macrostrat.lookup_strat_names USING btree (fm_id);


--
-- Name: lookup_strat_names_new_gp_id_idx; Type: INDEX; Schema: macrostrat; Owner: postgres
--

CREATE INDEX lookup_strat_names_new_gp_id_idx ON macrostrat.lookup_strat_names USING btree (gp_id);


--
-- Name: lookup_strat_names_new_mbr_id_idx; Type: INDEX; Schema: macrostrat; Owner: postgres
--

CREATE INDEX lookup_strat_names_new_mbr_id_idx ON macrostrat.lookup_strat_names USING btree (mbr_id);


--
-- Name: lookup_strat_names_new_sgp_id_idx; Type: INDEX; Schema: macrostrat; Owner: postgres
--

CREATE INDEX lookup_strat_names_new_sgp_id_idx ON macrostrat.lookup_strat_names USING btree (sgp_id);


--
-- Name: lookup_strat_names_new_strat_name_id_idx; Type: INDEX; Schema: macrostrat; Owner: postgres
--

CREATE INDEX lookup_strat_names_new_strat_name_id_idx ON macrostrat.lookup_strat_names USING btree (strat_name_id);


--
-- Name: lookup_strat_names_new_strat_name_idx; Type: INDEX; Schema: macrostrat; Owner: postgres
--

CREATE INDEX lookup_strat_names_new_strat_name_idx ON macrostrat.lookup_strat_names USING btree (strat_name);


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
-- Name: measurements_new_id_idx; Type: INDEX; Schema: macrostrat; Owner: postgres
--

CREATE INDEX measurements_new_id_idx ON macrostrat.measurements USING btree (id);


--
-- Name: measurements_new_measurement_class_idx; Type: INDEX; Schema: macrostrat; Owner: postgres
--

CREATE INDEX measurements_new_measurement_class_idx ON macrostrat.measurements USING btree (measurement_class);


--
-- Name: measurements_new_measurement_type_idx; Type: INDEX; Schema: macrostrat; Owner: postgres
--

CREATE INDEX measurements_new_measurement_type_idx ON macrostrat.measurements USING btree (measurement_type);


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
-- Name: measures_new_measurement_id_idx1; Type: INDEX; Schema: macrostrat; Owner: postgres
--

CREATE INDEX measures_new_measurement_id_idx1 ON macrostrat.measures USING btree (measurement_id);


--
-- Name: measures_new_measuremeta_id_idx1; Type: INDEX; Schema: macrostrat; Owner: postgres
--

CREATE INDEX measures_new_measuremeta_id_idx1 ON macrostrat.measures USING btree (measuremeta_id);


--
-- Name: pbdb_collections_new_collection_no_idx1; Type: INDEX; Schema: macrostrat; Owner: postgres
--

CREATE INDEX pbdb_collections_new_collection_no_idx1 ON macrostrat.pbdb_collections USING btree (collection_no);


--
-- Name: pbdb_collections_new_early_age_idx1; Type: INDEX; Schema: macrostrat; Owner: postgres
--

CREATE INDEX pbdb_collections_new_early_age_idx1 ON macrostrat.pbdb_collections USING btree (early_age);


--
-- Name: pbdb_collections_new_geom_idx1; Type: INDEX; Schema: macrostrat; Owner: postgres
--

CREATE INDEX pbdb_collections_new_geom_idx1 ON macrostrat.pbdb_collections USING gist (geom);


--
-- Name: pbdb_collections_new_late_age_idx1; Type: INDEX; Schema: macrostrat; Owner: postgres
--

CREATE INDEX pbdb_collections_new_late_age_idx1 ON macrostrat.pbdb_collections USING btree (late_age);


--
-- Name: places_new_geom_idx; Type: INDEX; Schema: macrostrat; Owner: postgres
--

CREATE INDEX places_new_geom_idx ON macrostrat.places USING gist (geom);


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
-- Name: units_sections_new_col_id_idx; Type: INDEX; Schema: macrostrat; Owner: postgres
--

CREATE INDEX units_sections_new_col_id_idx ON macrostrat.units_sections USING btree (col_id);


--
-- Name: units_sections_new_section_id_idx; Type: INDEX; Schema: macrostrat; Owner: postgres
--

CREATE INDEX units_sections_new_section_id_idx ON macrostrat.units_sections USING btree (section_id);


--
-- Name: units_sections_new_unit_id_idx; Type: INDEX; Schema: macrostrat; Owner: postgres
--

CREATE INDEX units_sections_new_unit_id_idx ON macrostrat.units_sections USING btree (unit_id);


--
-- Name: large_b_interval_idx; Type: INDEX; Schema: maps; Owner: postgres
--

CREATE INDEX large_b_interval_idx ON maps.large USING btree (b_interval);


--
-- Name: large_geom_idx; Type: INDEX; Schema: maps; Owner: postgres
--

CREATE INDEX large_geom_idx ON maps.large USING gist (geom);


--
-- Name: large_name_idx; Type: INDEX; Schema: maps; Owner: postgres
--

CREATE INDEX large_name_idx ON maps.large USING btree (name);


--
-- Name: large_orig_id_idx; Type: INDEX; Schema: maps; Owner: postgres
--

CREATE INDEX large_orig_id_idx ON maps.large USING btree (orig_id);


--
-- Name: large_source_id_idx; Type: INDEX; Schema: maps; Owner: postgres
--

CREATE INDEX large_source_id_idx ON maps.large USING btree (source_id);


--
-- Name: large_t_interval_idx; Type: INDEX; Schema: maps; Owner: postgres
--

CREATE INDEX large_t_interval_idx ON maps.large USING btree (t_interval);


--
-- Name: legend_liths_legend_id_idx; Type: INDEX; Schema: maps; Owner: postgres
--

CREATE INDEX legend_liths_legend_id_idx ON maps.legend_liths USING btree (legend_id);


--
-- Name: legend_liths_lith_id_idx; Type: INDEX; Schema: maps; Owner: postgres
--

CREATE INDEX legend_liths_lith_id_idx ON maps.legend_liths USING btree (lith_id);


--
-- Name: legend_source_id_idx; Type: INDEX; Schema: maps; Owner: postgres
--

CREATE INDEX legend_source_id_idx ON maps.legend USING btree (source_id);


--
-- Name: manual_matches_map_id_idx; Type: INDEX; Schema: maps; Owner: postgres
--

CREATE INDEX manual_matches_map_id_idx ON maps.manual_matches USING btree (map_id);


--
-- Name: manual_matches_strat_name_id_idx; Type: INDEX; Schema: maps; Owner: postgres
--

CREATE INDEX manual_matches_strat_name_id_idx ON maps.manual_matches USING btree (strat_name_id);


--
-- Name: manual_matches_unit_id_idx; Type: INDEX; Schema: maps; Owner: postgres
--

CREATE INDEX manual_matches_unit_id_idx ON maps.manual_matches USING btree (unit_id);


--
-- Name: map_legend_legend_id_idx; Type: INDEX; Schema: maps; Owner: postgres
--

CREATE INDEX map_legend_legend_id_idx ON maps.map_legend USING btree (legend_id);


--
-- Name: map_legend_map_id_idx; Type: INDEX; Schema: maps; Owner: postgres
--

CREATE INDEX map_legend_map_id_idx ON maps.map_legend USING btree (map_id);


--
-- Name: map_liths_lith_id_idx; Type: INDEX; Schema: maps; Owner: postgres
--

CREATE INDEX map_liths_lith_id_idx ON maps.map_liths USING btree (lith_id);


--
-- Name: map_liths_map_id_idx; Type: INDEX; Schema: maps; Owner: postgres
--

CREATE INDEX map_liths_map_id_idx ON maps.map_liths USING btree (map_id);


--
-- Name: map_strat_names_map_id_idx; Type: INDEX; Schema: maps; Owner: postgres
--

CREATE INDEX map_strat_names_map_id_idx ON maps.map_strat_names USING btree (map_id);


--
-- Name: map_strat_names_strat_name_id_idx; Type: INDEX; Schema: maps; Owner: postgres
--

CREATE INDEX map_strat_names_strat_name_id_idx ON maps.map_strat_names USING btree (strat_name_id);


--
-- Name: map_units_map_id_idx; Type: INDEX; Schema: maps; Owner: postgres
--

CREATE INDEX map_units_map_id_idx ON maps.map_units USING btree (map_id);


--
-- Name: map_units_unit_id_idx; Type: INDEX; Schema: maps; Owner: postgres
--

CREATE INDEX map_units_unit_id_idx ON maps.map_units USING btree (unit_id);


--
-- Name: medium_b_interval_idx; Type: INDEX; Schema: maps; Owner: postgres
--

CREATE INDEX medium_b_interval_idx ON maps.medium USING btree (b_interval);


--
-- Name: medium_geom_idx; Type: INDEX; Schema: maps; Owner: postgres
--

CREATE INDEX medium_geom_idx ON maps.medium USING gist (geom);


--
-- Name: medium_orig_id_idx; Type: INDEX; Schema: maps; Owner: postgres
--

CREATE INDEX medium_orig_id_idx ON maps.medium USING btree (orig_id);


--
-- Name: medium_source_id_idx; Type: INDEX; Schema: maps; Owner: postgres
--

CREATE INDEX medium_source_id_idx ON maps.medium USING btree (source_id);


--
-- Name: medium_t_interval_idx; Type: INDEX; Schema: maps; Owner: postgres
--

CREATE INDEX medium_t_interval_idx ON maps.medium USING btree (t_interval);


--
-- Name: small_b_interval_idx; Type: INDEX; Schema: maps; Owner: postgres
--

CREATE INDEX small_b_interval_idx ON maps.small USING btree (b_interval);


--
-- Name: small_geom_idx; Type: INDEX; Schema: maps; Owner: postgres
--

CREATE INDEX small_geom_idx ON maps.small USING gist (geom);


--
-- Name: small_orig_id_idx; Type: INDEX; Schema: maps; Owner: postgres
--

CREATE INDEX small_orig_id_idx ON maps.small USING btree (orig_id);


--
-- Name: small_source_id_idx; Type: INDEX; Schema: maps; Owner: postgres
--

CREATE INDEX small_source_id_idx ON maps.small USING btree (source_id);


--
-- Name: small_t_interval_idx; Type: INDEX; Schema: maps; Owner: postgres
--

CREATE INDEX small_t_interval_idx ON maps.small USING btree (t_interval);


--
-- Name: sources_rgeom_idx; Type: INDEX; Schema: maps; Owner: postgres
--

CREATE INDEX sources_rgeom_idx ON maps.sources USING gist (rgeom);


--
-- Name: sources_web_geom_idx; Type: INDEX; Schema: maps; Owner: postgres
--

CREATE INDEX sources_web_geom_idx ON maps.sources USING gist (web_geom);


--
-- Name: tiny_b_interval_idx; Type: INDEX; Schema: maps; Owner: postgres
--

CREATE INDEX tiny_b_interval_idx ON maps.tiny USING btree (b_interval);


--
-- Name: tiny_geom_idx; Type: INDEX; Schema: maps; Owner: postgres
--

CREATE INDEX tiny_geom_idx ON maps.tiny USING gist (geom);


--
-- Name: tiny_orig_id_idx; Type: INDEX; Schema: maps; Owner: postgres
--

CREATE INDEX tiny_orig_id_idx ON maps.tiny USING btree (orig_id);


--
-- Name: tiny_source_id_idx; Type: INDEX; Schema: maps; Owner: postgres
--

CREATE INDEX tiny_source_id_idx ON maps.tiny USING btree (source_id);


--
-- Name: tiny_t_interval_idx; Type: INDEX; Schema: maps; Owner: postgres
--

CREATE INDEX tiny_t_interval_idx ON maps.tiny USING btree (t_interval);


--
-- Name: points_geom_idx; Type: INDEX; Schema: points; Owner: postgres
--

CREATE INDEX points_geom_idx ON points.points USING gist (geom);


--
-- Name: points_source_id_idx; Type: INDEX; Schema: points; Owner: postgres
--

CREATE INDEX points_source_id_idx ON points.points USING btree (source_id);


--
-- Name: agebzepllj_geom_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX agebzepllj_geom_idx ON public.agebzepllj USING gist (geom);


--
-- Name: aofhmuuyjq_geom_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX aofhmuuyjq_geom_idx ON public.aofhmuuyjq USING gist (geom);


--
-- Name: bmbtwjmdgn_geom_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX bmbtwjmdgn_geom_idx ON public.bmbtwjmdgn USING gist (geom);


--
-- Name: emma5k5jzl_geom_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX emma5k5jzl_geom_idx ON public.emma5k5jzl USING gist (geom);


--
-- Name: i9kzotjhgr_geom_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX i9kzotjhgr_geom_idx ON public.i9kzotjhgr USING gist (geom);


--
-- Name: impervious_st_convexhull_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX impervious_st_convexhull_idx ON public.impervious USING gist (public.st_convexhull(rast));


--
-- Name: land_geom_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX land_geom_idx ON public.land USING gist (geom);


--
-- Name: lookup_large_concept_ids_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX lookup_large_concept_ids_idx ON public.lookup_large USING gin (concept_ids);


--
-- Name: lookup_large_legend_id_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX lookup_large_legend_id_idx ON public.lookup_large USING btree (legend_id);


--
-- Name: lookup_large_lith_ids_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX lookup_large_lith_ids_idx ON public.lookup_large USING gin (lith_ids);


--
-- Name: lookup_large_map_id_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX lookup_large_map_id_idx ON public.lookup_large USING btree (map_id);


--
-- Name: lookup_large_strat_name_children_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX lookup_large_strat_name_children_idx ON public.lookup_large USING gin (strat_name_children);


--
-- Name: lookup_medium_concept_ids_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX lookup_medium_concept_ids_idx ON public.lookup_medium USING gin (concept_ids);


--
-- Name: lookup_medium_legend_id_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX lookup_medium_legend_id_idx ON public.lookup_medium USING btree (legend_id);


--
-- Name: lookup_medium_lith_ids_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX lookup_medium_lith_ids_idx ON public.lookup_medium USING gin (lith_ids);


--
-- Name: lookup_medium_map_id_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX lookup_medium_map_id_idx ON public.lookup_medium USING btree (map_id);


--
-- Name: lookup_medium_strat_name_children_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX lookup_medium_strat_name_children_idx ON public.lookup_medium USING gin (strat_name_children);


--
-- Name: lookup_small_concept_ids_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX lookup_small_concept_ids_idx ON public.lookup_small USING gin (concept_ids);


--
-- Name: lookup_small_legend_id_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX lookup_small_legend_id_idx ON public.lookup_small USING btree (legend_id);


--
-- Name: lookup_small_lith_ids_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX lookup_small_lith_ids_idx ON public.lookup_small USING gin (lith_ids);


--
-- Name: lookup_small_map_id_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX lookup_small_map_id_idx ON public.lookup_small USING btree (map_id);


--
-- Name: lookup_small_strat_name_children_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX lookup_small_strat_name_children_idx ON public.lookup_small USING gin (strat_name_children);


--
-- Name: lookup_tiny_concept_ids_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX lookup_tiny_concept_ids_idx ON public.lookup_tiny USING gin (concept_ids);


--
-- Name: lookup_tiny_legend_id_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX lookup_tiny_legend_id_idx ON public.lookup_tiny USING btree (legend_id);


--
-- Name: lookup_tiny_lith_ids_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX lookup_tiny_lith_ids_idx ON public.lookup_tiny USING gin (lith_ids);


--
-- Name: lookup_tiny_map_id_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX lookup_tiny_map_id_idx ON public.lookup_tiny USING btree (map_id);


--
-- Name: lookup_tiny_strat_name_children_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX lookup_tiny_strat_name_children_idx ON public.lookup_tiny USING gin (strat_name_children);


--
-- Name: npb9s0ubia_geom_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX npb9s0ubia_geom_idx ON public.npb9s0ubia USING gist (geom);


--
-- Name: temp_names_name_no_lith_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX temp_names_name_no_lith_idx ON public.temp_names USING btree (name_no_lith);


--
-- Name: temp_names_rank_name_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX temp_names_rank_name_idx ON public.temp_names USING btree (rank_name);


--
-- Name: temp_names_strat_name_id_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX temp_names_strat_name_id_idx ON public.temp_names USING btree (strat_name_id);


--
-- Name: temp_names_strat_name_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX temp_names_strat_name_idx ON public.temp_names USING btree (strat_name);


--
-- Name: temp_rocks_b_interval_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX temp_rocks_b_interval_idx ON public.temp_rocks USING btree (b_interval);


--
-- Name: temp_rocks_envelope_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX temp_rocks_envelope_idx ON public.temp_rocks USING gist (envelope);


--
-- Name: temp_rocks_strat_name_clean_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX temp_rocks_strat_name_clean_idx ON public.temp_rocks USING btree (strat_name_clean);


--
-- Name: temp_rocks_strat_name_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX temp_rocks_strat_name_idx ON public.temp_rocks USING btree (strat_name);


--
-- Name: temp_rocks_t_interval_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX temp_rocks_t_interval_idx ON public.temp_rocks USING btree (t_interval);


--
-- Name: test_rgeom_geom_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX test_rgeom_geom_idx ON public.test_rgeom USING gist (geom);


--
-- Name: zphuctzzhp_geom_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX zphuctzzhp_geom_idx ON public.zphuctzzhp USING gist (geom);


--
-- Name: co_homestake_lines_shape_geom_idx; Type: INDEX; Schema: sources; Owner: postgres
--

CREATE INDEX co_homestake_lines_shape_geom_idx ON sources.co_homestake_lines USING gist (shape);


