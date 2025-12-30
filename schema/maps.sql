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
SELECT pg_catalog.set_config('search_path', 'public', false);
SET check_function_bodies = true;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: maps; Type: SCHEMA; Schema: -; Owner: macrostrat
--

CREATE SCHEMA maps;

ALTER SCHEMA maps OWNER TO macrostrat;

--
-- Name: ingest_state; Type: TYPE; Schema: maps; Owner: macrostrat
--

CREATE TYPE maps.ingest_state AS ENUM (
    'pending',
    'ingested',
    'prepared',
    'failed',
    'abandoned',
    'post_harmonization',
    'pre-processed',
    'post-processed',
    'needs review',
    'finalized'
);


ALTER TYPE maps.ingest_state OWNER TO macrostrat;

--
-- Name: ingest_type; Type: TYPE; Schema: maps; Owner: macrostrat
--

CREATE TYPE maps.ingest_type AS ENUM (
    'vector',
    'ta1_output'
);


ALTER TYPE maps.ingest_type OWNER TO macrostrat;

--
-- Name: map_scale; Type: TYPE; Schema: maps; Owner: macrostrat
--

CREATE TYPE maps.map_scale AS ENUM (
    'tiny',
    'small',
    'medium',
    'large'
);


ALTER TYPE maps.map_scale OWNER TO macrostrat;

--
-- Name: lines_geom_is_valid(geometry); Type: FUNCTION; Schema: maps; Owner: macrostrat
--

CREATE FUNCTION maps.lines_geom_is_valid(geom geometry) RETURNS boolean
    LANGUAGE sql IMMUTABLE
    AS $$
  SELECT ST_IsValid(geom) AND ST_GeometryType(geom) IN ('ST_LineString', 'ST_MultiLineString');
$$;


ALTER FUNCTION maps.lines_geom_is_valid(geom geometry) OWNER TO macrostrat;

--
-- Name: polygons_geom_is_valid(geometry); Type: FUNCTION; Schema: maps; Owner: macrostrat
--

CREATE FUNCTION maps.polygons_geom_is_valid(geom geometry) RETURNS boolean
    LANGUAGE sql IMMUTABLE
    AS $$
  SELECT ST_IsValid(geom) AND ST_GeometryType(geom) IN ('ST_Polygon', 'ST_MultiPolygon');
$$;


ALTER FUNCTION maps.polygons_geom_is_valid(geom geometry) OWNER TO macrostrat;

SET default_tablespace = '';

--
-- Name: lines; Type: TABLE; Schema: maps; Owner: macrostrat
--

CREATE TABLE maps.lines (
    line_id integer DEFAULT nextval('line_ids'::regclass) NOT NULL,
    orig_id text,
    source_id integer,
    name character varying(255),
    type_legacy character varying(100),
    direction_legacy character varying(40),
    descrip text,
    geom geometry(Geometry,4326) NOT NULL,
    type character varying(100),
    direction character varying(40),
    scale maps.map_scale NOT NULL,
    CONSTRAINT maps_lines_geom_check CHECK (maps.lines_geom_is_valid(geom))
)
PARTITION BY LIST (scale);


ALTER TABLE maps.lines OWNER TO macrostrat;

SET default_table_access_method = heap;

--
-- Name: legend; Type: TABLE; Schema: maps; Owner: macrostrat
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


ALTER TABLE maps.legend OWNER TO macrostrat;

--
-- Name: legend_liths; Type: TABLE; Schema: maps; Owner: macrostrat
--

CREATE TABLE maps.legend_liths (
    legend_id integer NOT NULL,
    lith_id integer NOT NULL,
    basis_col text NOT NULL
);


ALTER TABLE maps.legend_liths OWNER TO macrostrat;

--
-- Name: map_ids; Type: SEQUENCE; Schema: maps; Owner: macrostrat
--

CREATE SEQUENCE maps.map_ids
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE maps.map_ids OWNER TO macrostrat;

--
-- Name: polygons; Type: TABLE; Schema: maps; Owner: macrostrat
--

CREATE TABLE maps.polygons (
    map_id integer DEFAULT nextval('maps.map_ids'::regclass) NOT NULL,
    source_id integer NOT NULL,
    scale maps.map_scale NOT NULL,
    orig_id text,
    name text,
    strat_name text,
    age character varying(255),
    lith text,
    descrip text,
    comments text,
    t_interval integer,
    b_interval integer,
    geom geometry(Geometry,4326) NOT NULL,
    CONSTRAINT maps_polygons_geom_check CHECK (maps.polygons_geom_is_valid(geom))
)
PARTITION BY LIST (scale);


ALTER TABLE maps.polygons OWNER TO macrostrat;

--
-- Name: sources; Type: TABLE; Schema: maps; Owner: macrostrat
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
    license character varying(100),
    features integer,
    area integer,
    priority boolean DEFAULT false,
    rgeom geometry,
    display_scales text[],
    web_geom geometry,
    new_priority integer DEFAULT 0,
    status_code text DEFAULT 'active'::text,
    slug text NOT NULL,
    raster_url text,
    scale_denominator integer,
    is_finalized boolean DEFAULT false,
    lines_oriented boolean,
    date_finalized timestamp with time zone,
    ingested_by text,
    keywords text[],
    language text,
    description character varying
);


ALTER TABLE maps.sources OWNER TO macrostrat;

--
-- Name: COLUMN sources.slug; Type: COMMENT; Schema: maps; Owner: macrostrat
--

COMMENT ON COLUMN maps.sources.slug IS 'Unique identifier for each Macrostrat source';


--
-- Name: sources_metadata; Type: VIEW; Schema: maps; Owner: macrostrat_admin
--

CREATE VIEW maps.sources_metadata AS
 SELECT s.source_id,
    s.slug,
    s.name,
    s.url,
    s.ref_title,
    s.authors,
    s.ref_year,
    s.ref_source,
    s.isbn_doi,
    s.scale,
    s.license,
    s.features,
    s.area,
    s.display_scales,
    s.new_priority AS priority,
    s.status_code,
    s.raster_url,
    s.scale_denominator,
    s.is_finalized,
    s.lines_oriented
   FROM maps.sources s
  ORDER BY s.source_id DESC;


ALTER TABLE maps.sources_metadata OWNER TO macrostrat_admin;

--
-- Name: VIEW sources_metadata; Type: COMMENT; Schema: maps; Owner: macrostrat_admin
--

COMMENT ON VIEW maps.sources_metadata IS 'Convenience view for maps.sources with only metadata fields';


--
-- Name: points; Type: TABLE; Schema: maps; Owner: macrostrat
--

CREATE TABLE maps.points (
    source_id integer NOT NULL,
    strike integer,
    dip integer,
    dip_dir integer,
    point_type character varying(100),
    certainty character varying(100),
    comments text,
    geom geometry(Geometry,4326),
    point_id integer NOT NULL,
    orig_id text,
    CONSTRAINT dip_lt_90 CHECK ((dip <= 90)),
    CONSTRAINT dip_positive CHECK ((dip >= 0)),
    CONSTRAINT direction_lt_360 CHECK ((dip_dir <= 360)),
    CONSTRAINT direction_positive CHECK ((dip_dir >= 0)),
    CONSTRAINT enforce_point_geom CHECK (st_isvalid(geom)),
    CONSTRAINT strike_lt_360 CHECK ((strike <= 360)),
    CONSTRAINT strike_positive CHECK ((strike >= 0))
);


ALTER TABLE maps.points OWNER TO macrostrat;

--
-- Name: ingest_process; Type: VIEW; Schema: maps; Owner: macrostrat_admin
--

CREATE VIEW maps.ingest_process AS
 SELECT ingest_process.id,
    ingest_process.state,
    ingest_process.comments,
    ingest_process.source_id,
    ingest_process.created_on,
    ingest_process.completed_on,
    ingest_process.map_id,
    ingest_process.type,
    ingest_process.polygon_state,
    ingest_process.line_state,
    ingest_process.point_state,
    ingest_process.ingest_pipeline,
    ingest_process.map_url,
    ingest_process.ingested_by,
    ingest_process.slug
   FROM maps_metadata.ingest_process;


ALTER TABLE maps.ingest_process OWNER TO macrostrat_admin;

--
-- Name: polygons_large; Type: TABLE; Schema: maps; Owner: macrostrat
--

CREATE TABLE maps.polygons_large (
    map_id integer DEFAULT nextval('map_ids'::regclass) NOT NULL,
    orig_id text,
    source_id integer NOT NULL,
    name text,
    strat_name text,
    age character varying(255),
    lith text,
    descrip text,
    comments text,
    t_interval integer,
    b_interval integer,
    geom geometry(Geometry,4326) NOT NULL,
    scale maps.map_scale DEFAULT 'large'::maps.map_scale NOT NULL,
    CONSTRAINT enforce_valid_geom_large CHECK (st_isvalid(geom)),
    CONSTRAINT maps_polygons_geom_check CHECK (maps.polygons_geom_is_valid(geom)),
    CONSTRAINT polygons_large_scale_check CHECK ((scale = 'large'::maps.map_scale))
);


ALTER TABLE maps.polygons_large OWNER TO macrostrat;

--
-- Name: large; Type: VIEW; Schema: maps; Owner: macrostrat_admin
--

CREATE VIEW maps.large AS
 SELECT polygons_large.map_id,
    polygons_large.orig_id,
    polygons_large.source_id,
    polygons_large.name,
    polygons_large.strat_name,
    polygons_large.age,
    polygons_large.lith,
    polygons_large.descrip,
    polygons_large.comments,
    polygons_large.t_interval,
    polygons_large.b_interval,
    polygons_large.geom
   FROM maps.polygons_large;


ALTER TABLE maps.large OWNER TO macrostrat_admin;

--
-- Name: legend_legend_id_seq; Type: SEQUENCE; Schema: maps; Owner: macrostrat
--

CREATE SEQUENCE maps.legend_legend_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE maps.legend_legend_id_seq OWNER TO macrostrat;

--
-- Name: legend_legend_id_seq; Type: SEQUENCE OWNED BY; Schema: maps; Owner: macrostrat
--

ALTER SEQUENCE maps.legend_legend_id_seq OWNED BY maps.legend.legend_id;


--
-- Name: lines_large; Type: TABLE; Schema: maps; Owner: macrostrat
--

CREATE TABLE maps.lines_large (
    line_id integer DEFAULT nextval('line_ids'::regclass) NOT NULL,
    orig_id text,
    source_id integer,
    name character varying(255),
    type_legacy character varying(100),
    direction_legacy character varying(40),
    descrip text,
    geom geometry(Geometry,4326) NOT NULL,
    type character varying(100),
    direction character varying(40),
    scale maps.map_scale DEFAULT 'large'::maps.map_scale NOT NULL,
    CONSTRAINT lines_large_scale_check CHECK ((scale = 'large'::maps.map_scale)),
    CONSTRAINT maps_lines_geom_check CHECK (maps.lines_geom_is_valid(geom))
);


ALTER TABLE maps.lines_large OWNER TO macrostrat;

--
-- Name: lines_medium; Type: TABLE; Schema: maps; Owner: macrostrat
--

CREATE TABLE maps.lines_medium (
    line_id integer DEFAULT nextval('line_ids'::regclass) NOT NULL,
    orig_id text,
    source_id integer,
    name character varying(255),
    type_legacy character varying(100),
    direction_legacy character varying(40),
    descrip text,
    geom geometry(Geometry,4326) NOT NULL,
    type character varying(100),
    direction character varying(40),
    scale maps.map_scale DEFAULT 'medium'::maps.map_scale NOT NULL,
    CONSTRAINT lines_medium_scale_check CHECK ((scale = 'medium'::maps.map_scale)),
    CONSTRAINT maps_lines_geom_check CHECK (maps.lines_geom_is_valid(geom))
);


ALTER TABLE maps.lines_medium OWNER TO macrostrat;

--
-- Name: lines_small; Type: TABLE; Schema: maps; Owner: macrostrat
--

CREATE TABLE maps.lines_small (
    line_id integer DEFAULT nextval('line_ids'::regclass) NOT NULL,
    orig_id text,
    source_id integer,
    name character varying(255),
    type_legacy character varying(100),
    direction_legacy character varying(40),
    descrip text,
    geom geometry(Geometry,4326) NOT NULL,
    type character varying(100),
    direction character varying(40),
    scale maps.map_scale DEFAULT 'small'::maps.map_scale NOT NULL,
    CONSTRAINT lines_small_scale_check CHECK ((scale = 'small'::maps.map_scale)),
    CONSTRAINT maps_lines_geom_check CHECK (maps.lines_geom_is_valid(geom))
);


ALTER TABLE maps.lines_small OWNER TO macrostrat;

--
-- Name: lines_tiny; Type: TABLE; Schema: maps; Owner: macrostrat
--

CREATE TABLE maps.lines_tiny (
    line_id integer DEFAULT nextval('line_ids'::regclass) NOT NULL,
    orig_id text,
    source_id integer,
    name character varying(255),
    type_legacy character varying(100),
    direction_legacy character varying(40),
    descrip text,
    geom geometry(Geometry,4326) NOT NULL,
    type character varying(100),
    direction character varying(40),
    scale maps.map_scale DEFAULT 'tiny'::maps.map_scale NOT NULL,
    CONSTRAINT isvalid CHECK (st_isvalid(geom)),
    CONSTRAINT lines_tiny_scale_check CHECK ((scale = 'tiny'::maps.map_scale)),
    CONSTRAINT maps_lines_geom_check CHECK (maps.lines_geom_is_valid(geom))
);


ALTER TABLE maps.lines_tiny OWNER TO macrostrat;

--
-- Name: manual_matches; Type: TABLE; Schema: maps; Owner: macrostrat
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


ALTER TABLE maps.manual_matches OWNER TO macrostrat;

--
-- Name: manual_matches_match_id_seq; Type: SEQUENCE; Schema: maps; Owner: macrostrat
--

CREATE SEQUENCE maps.manual_matches_match_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE maps.manual_matches_match_id_seq OWNER TO macrostrat;

--
-- Name: manual_matches_match_id_seq; Type: SEQUENCE OWNED BY; Schema: maps; Owner: macrostrat
--

ALTER SEQUENCE maps.manual_matches_match_id_seq OWNED BY maps.manual_matches.match_id;


--
-- Name: map_legend; Type: TABLE; Schema: maps; Owner: macrostrat
--

CREATE TABLE maps.map_legend (
    legend_id integer NOT NULL,
    map_id integer NOT NULL
);


ALTER TABLE maps.map_legend OWNER TO macrostrat;

--
-- Name: map_liths; Type: TABLE; Schema: maps; Owner: macrostrat
--

CREATE TABLE maps.map_liths (
    map_id integer NOT NULL,
    lith_id integer NOT NULL,
    basis_col character varying(50)
);


ALTER TABLE maps.map_liths OWNER TO macrostrat;

--
-- Name: map_strat_names; Type: TABLE; Schema: maps; Owner: macrostrat
--

CREATE TABLE maps.map_strat_names (
    map_id integer NOT NULL,
    strat_name_id integer NOT NULL,
    basis_col character varying(50)
);


ALTER TABLE maps.map_strat_names OWNER TO macrostrat;

--
-- Name: map_units; Type: TABLE; Schema: maps; Owner: macrostrat
--

CREATE TABLE maps.map_units (
    map_id integer NOT NULL,
    unit_id integer NOT NULL,
    basis_col character varying(50)
);


ALTER TABLE maps.map_units OWNER TO macrostrat;

--
-- Name: polygons_medium; Type: TABLE; Schema: maps; Owner: macrostrat
--

CREATE TABLE maps.polygons_medium (
    map_id integer DEFAULT nextval('map_ids'::regclass) NOT NULL,
    orig_id text,
    source_id integer NOT NULL,
    name text,
    strat_name text,
    age character varying(255),
    lith text,
    descrip text,
    comments text,
    t_interval integer,
    b_interval integer,
    geom geometry(Geometry,4326) NOT NULL,
    scale maps.map_scale DEFAULT 'medium'::maps.map_scale NOT NULL,
    CONSTRAINT enforce_valid_geom_medium CHECK (st_isvalid(geom)),
    CONSTRAINT maps_polygons_geom_check CHECK (maps.polygons_geom_is_valid(geom)),
    CONSTRAINT polygons_medium_scale_check CHECK ((scale = 'medium'::maps.map_scale))
);


ALTER TABLE maps.polygons_medium OWNER TO macrostrat;

--
-- Name: medium; Type: VIEW; Schema: maps; Owner: macrostrat_admin
--

CREATE VIEW maps.medium AS
 SELECT polygons_medium.map_id,
    polygons_medium.orig_id,
    polygons_medium.source_id,
    polygons_medium.name,
    polygons_medium.strat_name,
    polygons_medium.age,
    polygons_medium.lith,
    polygons_medium.descrip,
    polygons_medium.comments,
    polygons_medium.t_interval,
    polygons_medium.b_interval,
    polygons_medium.geom
   FROM maps.polygons_medium;


ALTER TABLE maps.medium OWNER TO macrostrat_admin;

--
-- Name: points_point_id_seq; Type: SEQUENCE; Schema: maps; Owner: macrostrat
--

CREATE SEQUENCE maps.points_point_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE maps.points_point_id_seq OWNER TO macrostrat;

--
-- Name: points_point_id_seq; Type: SEQUENCE OWNED BY; Schema: maps; Owner: macrostrat
--

ALTER SEQUENCE maps.points_point_id_seq OWNED BY maps.points.point_id;


--
-- Name: polygons_small; Type: TABLE; Schema: maps; Owner: macrostrat
--

CREATE TABLE maps.polygons_small (
    map_id integer DEFAULT nextval('map_ids'::regclass) NOT NULL,
    orig_id text,
    source_id integer NOT NULL,
    name text,
    strat_name text,
    age character varying(255),
    lith text,
    descrip text,
    comments text,
    t_interval integer,
    b_interval integer,
    geom geometry(Geometry,4326) NOT NULL,
    scale maps.map_scale DEFAULT 'small'::maps.map_scale NOT NULL,
    CONSTRAINT maps_polygons_geom_check CHECK (maps.polygons_geom_is_valid(geom)),
    CONSTRAINT polygons_small_scale_check CHECK ((scale = 'small'::maps.map_scale))
);


ALTER TABLE maps.polygons_small OWNER TO macrostrat;

--
-- Name: polygons_tiny; Type: TABLE; Schema: maps; Owner: macrostrat
--

CREATE TABLE maps.polygons_tiny (
    map_id integer DEFAULT nextval('map_ids'::regclass) NOT NULL,
    orig_id text,
    source_id integer NOT NULL,
    name text,
    strat_name text,
    age character varying(255),
    lith text,
    descrip text,
    comments text,
    t_interval integer,
    b_interval integer,
    geom geometry(Geometry,4326) NOT NULL,
    scale maps.map_scale DEFAULT 'tiny'::maps.map_scale NOT NULL,
    CONSTRAINT maps_polygons_geom_check CHECK (maps.polygons_geom_is_valid(geom)),
    CONSTRAINT polygons_tiny_scale_check CHECK ((scale = 'tiny'::maps.map_scale))
);


ALTER TABLE maps.polygons_tiny OWNER TO macrostrat;

--
-- Name: small; Type: VIEW; Schema: maps; Owner: macrostrat_admin
--

CREATE VIEW maps.small AS
 SELECT polygons_small.map_id,
    polygons_small.orig_id,
    polygons_small.source_id,
    polygons_small.name,
    polygons_small.strat_name,
    polygons_small.age,
    polygons_small.lith,
    polygons_small.descrip,
    polygons_small.comments,
    polygons_small.t_interval,
    polygons_small.b_interval,
    polygons_small.geom
   FROM maps.polygons_small;


ALTER TABLE maps.small OWNER TO macrostrat_admin;

--
-- Name: source_operations; Type: TABLE; Schema: maps; Owner: macrostrat
--

CREATE TABLE maps.source_operations (
    id integer NOT NULL,
    source_id integer NOT NULL,
    user_id integer,
    operation text NOT NULL,
    app text NOT NULL,
    comments text,
    details jsonb,
    date timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE maps.source_operations OWNER TO macrostrat;

--
-- Name: TABLE source_operations; Type: COMMENT; Schema: maps; Owner: macrostrat
--

COMMENT ON TABLE maps.source_operations IS 'Tracks management operations for Macrostrat maps';


--
-- Name: source_operations_id_seq; Type: SEQUENCE; Schema: maps; Owner: macrostrat
--

CREATE SEQUENCE maps.source_operations_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE maps.source_operations_id_seq OWNER TO macrostrat;

--
-- Name: source_operations_id_seq; Type: SEQUENCE OWNED BY; Schema: maps; Owner: macrostrat
--

ALTER SEQUENCE maps.source_operations_id_seq OWNED BY maps.source_operations.id;


--
-- Name: sources_source_id_seq; Type: SEQUENCE; Schema: maps; Owner: macrostrat
--

CREATE SEQUENCE maps.sources_source_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE maps.sources_source_id_seq OWNER TO macrostrat;

--
-- Name: sources_source_id_seq; Type: SEQUENCE OWNED BY; Schema: maps; Owner: macrostrat
--

ALTER SEQUENCE maps.sources_source_id_seq OWNED BY maps.sources.source_id;


--
-- Name: tiny; Type: VIEW; Schema: maps; Owner: macrostrat_admin
--

CREATE VIEW maps.tiny AS
 SELECT polygons_tiny.map_id,
    polygons_tiny.orig_id,
    polygons_tiny.source_id,
    polygons_tiny.name,
    polygons_tiny.strat_name,
    polygons_tiny.age,
    polygons_tiny.lith,
    polygons_tiny.descrip,
    polygons_tiny.comments,
    polygons_tiny.t_interval,
    polygons_tiny.b_interval,
    polygons_tiny.geom
   FROM maps.polygons_tiny;


ALTER TABLE maps.tiny OWNER TO macrostrat_admin;

--
-- Name: vw_legend_with_liths; Type: VIEW; Schema: maps; Owner: macrostrat-admin
--

CREATE VIEW maps.vw_legend_with_liths AS
 SELECT l.legend_id,
    l.source_id,
    l.name AS map_unit_name,
    array_agg(ll.lith_id) FILTER (WHERE (ll.lith_id IS NOT NULL)) AS lith_ids
   FROM (maps.legend l
     LEFT JOIN maps.legend_liths ll ON ((ll.legend_id = l.legend_id)))
  GROUP BY l.legend_id, l.source_id, l.name;


ALTER TABLE maps.vw_legend_with_liths OWNER TO "macrostrat-admin";

--
-- Name: lines_large; Type: TABLE ATTACH; Schema: maps; Owner: macrostrat
--

ALTER TABLE ONLY maps.lines ATTACH PARTITION maps.lines_large FOR VALUES IN ('large');


--
-- Name: lines_medium; Type: TABLE ATTACH; Schema: maps; Owner: macrostrat
--

ALTER TABLE ONLY maps.lines ATTACH PARTITION maps.lines_medium FOR VALUES IN ('medium');


--
-- Name: lines_small; Type: TABLE ATTACH; Schema: maps; Owner: macrostrat
--

ALTER TABLE ONLY maps.lines ATTACH PARTITION maps.lines_small FOR VALUES IN ('small');


--
-- Name: lines_tiny; Type: TABLE ATTACH; Schema: maps; Owner: macrostrat
--

ALTER TABLE ONLY maps.lines ATTACH PARTITION maps.lines_tiny FOR VALUES IN ('tiny');


--
-- Name: polygons_large; Type: TABLE ATTACH; Schema: maps; Owner: macrostrat
--

ALTER TABLE ONLY maps.polygons ATTACH PARTITION maps.polygons_large FOR VALUES IN ('large');


--
-- Name: polygons_medium; Type: TABLE ATTACH; Schema: maps; Owner: macrostrat
--

ALTER TABLE ONLY maps.polygons ATTACH PARTITION maps.polygons_medium FOR VALUES IN ('medium');


--
-- Name: polygons_small; Type: TABLE ATTACH; Schema: maps; Owner: macrostrat
--

ALTER TABLE ONLY maps.polygons ATTACH PARTITION maps.polygons_small FOR VALUES IN ('small');


--
-- Name: polygons_tiny; Type: TABLE ATTACH; Schema: maps; Owner: macrostrat
--

ALTER TABLE ONLY maps.polygons ATTACH PARTITION maps.polygons_tiny FOR VALUES IN ('tiny');


--
-- Name: legend legend_id; Type: DEFAULT; Schema: maps; Owner: macrostrat
--

ALTER TABLE ONLY maps.legend ALTER COLUMN legend_id SET DEFAULT nextval('maps.legend_legend_id_seq'::regclass);


--
-- Name: manual_matches match_id; Type: DEFAULT; Schema: maps; Owner: macrostrat
--

ALTER TABLE ONLY maps.manual_matches ALTER COLUMN match_id SET DEFAULT nextval('maps.manual_matches_match_id_seq'::regclass);


--
-- Name: points point_id; Type: DEFAULT; Schema: maps; Owner: macrostrat
--

ALTER TABLE ONLY maps.points ALTER COLUMN point_id SET DEFAULT nextval('maps.points_point_id_seq'::regclass);


--
-- Name: source_operations id; Type: DEFAULT; Schema: maps; Owner: macrostrat
--

ALTER TABLE ONLY maps.source_operations ALTER COLUMN id SET DEFAULT nextval('maps.source_operations_id_seq'::regclass);


--
-- Name: sources source_id; Type: DEFAULT; Schema: maps; Owner: macrostrat
--

ALTER TABLE ONLY maps.sources ALTER COLUMN source_id SET DEFAULT nextval('maps.sources_source_id_seq'::regclass);


--
-- Name: legend_liths legend_liths_legend_id_lith_id_basis_col_key; Type: CONSTRAINT; Schema: maps; Owner: macrostrat
--

ALTER TABLE ONLY maps.legend_liths
    ADD CONSTRAINT legend_liths_legend_id_lith_id_basis_col_key UNIQUE (legend_id, lith_id, basis_col);


--
-- Name: legend legend_pkey; Type: CONSTRAINT; Schema: maps; Owner: macrostrat
--

ALTER TABLE ONLY maps.legend
    ADD CONSTRAINT legend_pkey PRIMARY KEY (legend_id);


--
-- Name: lines lines_pkey; Type: CONSTRAINT; Schema: maps; Owner: macrostrat
--

ALTER TABLE ONLY maps.lines
    ADD CONSTRAINT lines_pkey PRIMARY KEY (line_id, scale);


--
-- Name: lines_large lines_large_pkey; Type: CONSTRAINT; Schema: maps; Owner: macrostrat
--

ALTER TABLE ONLY maps.lines_large
    ADD CONSTRAINT lines_large_pkey PRIMARY KEY (line_id, scale);


--
-- Name: lines_medium lines_medium_pkey; Type: CONSTRAINT; Schema: maps; Owner: macrostrat
--

ALTER TABLE ONLY maps.lines_medium
    ADD CONSTRAINT lines_medium_pkey PRIMARY KEY (line_id, scale);


--
-- Name: lines_small lines_small_pkey; Type: CONSTRAINT; Schema: maps; Owner: macrostrat
--

ALTER TABLE ONLY maps.lines_small
    ADD CONSTRAINT lines_small_pkey PRIMARY KEY (line_id, scale);


--
-- Name: lines_tiny lines_tiny_pkey; Type: CONSTRAINT; Schema: maps; Owner: macrostrat
--

ALTER TABLE ONLY maps.lines_tiny
    ADD CONSTRAINT lines_tiny_pkey PRIMARY KEY (line_id, scale);


--
-- Name: map_legend map_legend_legend_id_map_id_key; Type: CONSTRAINT; Schema: maps; Owner: macrostrat
--

ALTER TABLE ONLY maps.map_legend
    ADD CONSTRAINT map_legend_legend_id_map_id_key UNIQUE (legend_id, map_id);


--
-- Name: sources map_sources_name_key; Type: CONSTRAINT; Schema: maps; Owner: macrostrat
--

ALTER TABLE ONLY maps.sources
    ADD CONSTRAINT map_sources_name_key UNIQUE (primary_table);


--
-- Name: polygons maps_polygons_pkey; Type: CONSTRAINT; Schema: maps; Owner: macrostrat
--

ALTER TABLE ONLY maps.polygons
    ADD CONSTRAINT maps_polygons_pkey PRIMARY KEY (map_id, scale);


--
-- Name: polygons_large maps_polygons_large_pkey; Type: CONSTRAINT; Schema: maps; Owner: macrostrat
--

ALTER TABLE ONLY maps.polygons_large
    ADD CONSTRAINT maps_polygons_large_pkey PRIMARY KEY (map_id, scale);


--
-- Name: polygons_medium maps_polygons_medium_pkey; Type: CONSTRAINT; Schema: maps; Owner: macrostrat
--

ALTER TABLE ONLY maps.polygons_medium
    ADD CONSTRAINT maps_polygons_medium_pkey PRIMARY KEY (map_id, scale);


--
-- Name: polygons_small maps_polygons_small_pkey; Type: CONSTRAINT; Schema: maps; Owner: macrostrat
--

ALTER TABLE ONLY maps.polygons_small
    ADD CONSTRAINT maps_polygons_small_pkey PRIMARY KEY (map_id, scale);


--
-- Name: polygons_tiny maps_polygons_tiny_pkey; Type: CONSTRAINT; Schema: maps; Owner: macrostrat
--

ALTER TABLE ONLY maps.polygons_tiny
    ADD CONSTRAINT maps_polygons_tiny_pkey PRIMARY KEY (map_id, scale);


--
-- Name: source_operations source_operations_pkey; Type: CONSTRAINT; Schema: maps; Owner: macrostrat
--

ALTER TABLE ONLY maps.source_operations
    ADD CONSTRAINT source_operations_pkey PRIMARY KEY (id);


--
-- Name: sources sources_pkey; Type: CONSTRAINT; Schema: maps; Owner: macrostrat
--

ALTER TABLE ONLY maps.sources
    ADD CONSTRAINT sources_pkey PRIMARY KEY (source_id);


--
-- Name: sources sources_slug_key1; Type: CONSTRAINT; Schema: maps; Owner: macrostrat
--

ALTER TABLE ONLY maps.sources
    ADD CONSTRAINT sources_slug_key1 UNIQUE (slug);


--
-- Name: sources sources_slug_key2; Type: CONSTRAINT; Schema: maps; Owner: macrostrat
--

ALTER TABLE ONLY maps.sources
    ADD CONSTRAINT sources_slug_key2 UNIQUE (slug);


--
-- Name: sources sources_slug_key3; Type: CONSTRAINT; Schema: maps; Owner: macrostrat
--

ALTER TABLE ONLY maps.sources
    ADD CONSTRAINT sources_slug_key3 UNIQUE (slug);


--
-- Name: sources sources_source_id_key; Type: CONSTRAINT; Schema: maps; Owner: macrostrat
--

ALTER TABLE ONLY maps.sources
    ADD CONSTRAINT sources_source_id_key UNIQUE (source_id);


--
-- Name: polygons_b_interval_idx; Type: INDEX; Schema: maps; Owner: macrostrat
--

CREATE INDEX polygons_b_interval_idx ON ONLY maps.polygons USING btree (b_interval);


--
-- Name: large_b_interval_idx; Type: INDEX; Schema: maps; Owner: macrostrat
--

CREATE INDEX large_b_interval_idx ON maps.polygons_large USING btree (b_interval);


--
-- Name: polygons_geom_idx; Type: INDEX; Schema: maps; Owner: macrostrat
--

CREATE INDEX polygons_geom_idx ON ONLY maps.polygons USING gist (geom);


--
-- Name: large_geom_idx; Type: INDEX; Schema: maps; Owner: macrostrat
--

CREATE INDEX large_geom_idx ON maps.polygons_large USING gist (geom);


--
-- Name: polygons_name_idx; Type: INDEX; Schema: maps; Owner: macrostrat
--

CREATE INDEX polygons_name_idx ON ONLY maps.polygons USING btree (name);


--
-- Name: large_name_idx; Type: INDEX; Schema: maps; Owner: macrostrat
--

CREATE INDEX large_name_idx ON maps.polygons_large USING btree (name);


--
-- Name: polygons_orig_id_idx; Type: INDEX; Schema: maps; Owner: macrostrat
--

CREATE INDEX polygons_orig_id_idx ON ONLY maps.polygons USING btree (orig_id);


--
-- Name: large_orig_id_idx; Type: INDEX; Schema: maps; Owner: macrostrat
--

CREATE INDEX large_orig_id_idx ON maps.polygons_large USING btree (orig_id);


--
-- Name: polygons_source_id_idx; Type: INDEX; Schema: maps; Owner: macrostrat
--

CREATE INDEX polygons_source_id_idx ON ONLY maps.polygons USING btree (source_id);


--
-- Name: large_source_id_idx; Type: INDEX; Schema: maps; Owner: macrostrat
--

CREATE INDEX large_source_id_idx ON maps.polygons_large USING btree (source_id);


--
-- Name: polygons_t_interval_idx; Type: INDEX; Schema: maps; Owner: macrostrat
--

CREATE INDEX polygons_t_interval_idx ON ONLY maps.polygons USING btree (t_interval);


--
-- Name: large_t_interval_idx; Type: INDEX; Schema: maps; Owner: macrostrat
--

CREATE INDEX large_t_interval_idx ON maps.polygons_large USING btree (t_interval);


--
-- Name: legend_liths_legend_id_idx; Type: INDEX; Schema: maps; Owner: macrostrat
--

CREATE INDEX legend_liths_legend_id_idx ON maps.legend_liths USING btree (legend_id);


--
-- Name: legend_liths_lith_id_idx; Type: INDEX; Schema: maps; Owner: macrostrat
--

CREATE INDEX legend_liths_lith_id_idx ON maps.legend_liths USING btree (lith_id);


--
-- Name: legend_source_id_idx; Type: INDEX; Schema: maps; Owner: macrostrat
--

CREATE INDEX legend_source_id_idx ON maps.legend USING btree (source_id);


--
-- Name: lines_geom_idx; Type: INDEX; Schema: maps; Owner: macrostrat
--

CREATE INDEX lines_geom_idx ON ONLY maps.lines USING gist (geom);


--
-- Name: lines_large_geom_idx; Type: INDEX; Schema: maps; Owner: macrostrat
--

CREATE INDEX lines_large_geom_idx ON maps.lines_large USING gist (geom);


--
-- Name: lines_line_id_idx; Type: INDEX; Schema: maps; Owner: macrostrat
--

CREATE INDEX lines_line_id_idx ON ONLY maps.lines USING btree (line_id);


--
-- Name: lines_large_line_id_idx; Type: INDEX; Schema: maps; Owner: macrostrat
--

CREATE INDEX lines_large_line_id_idx ON maps.lines_large USING btree (line_id);


--
-- Name: lines_orig_id_idx; Type: INDEX; Schema: maps; Owner: macrostrat
--

CREATE INDEX lines_orig_id_idx ON ONLY maps.lines USING btree (orig_id);


--
-- Name: lines_large_orig_id_idx; Type: INDEX; Schema: maps; Owner: macrostrat
--

CREATE INDEX lines_large_orig_id_idx ON maps.lines_large USING btree (orig_id);


--
-- Name: lines_source_id_idx; Type: INDEX; Schema: maps; Owner: macrostrat
--

CREATE INDEX lines_source_id_idx ON ONLY maps.lines USING btree (source_id);


--
-- Name: lines_large_source_id_idx; Type: INDEX; Schema: maps; Owner: macrostrat
--

CREATE INDEX lines_large_source_id_idx ON maps.lines_large USING btree (source_id);


--
-- Name: lines_medium_geom_idx; Type: INDEX; Schema: maps; Owner: macrostrat
--

CREATE INDEX lines_medium_geom_idx ON maps.lines_medium USING gist (geom);


--
-- Name: lines_medium_line_id_idx; Type: INDEX; Schema: maps; Owner: macrostrat
--

CREATE INDEX lines_medium_line_id_idx ON maps.lines_medium USING btree (line_id);


--
-- Name: lines_medium_orig_id_idx; Type: INDEX; Schema: maps; Owner: macrostrat
--

CREATE INDEX lines_medium_orig_id_idx ON maps.lines_medium USING btree (orig_id);


--
-- Name: lines_medium_source_id_idx; Type: INDEX; Schema: maps; Owner: macrostrat
--

CREATE INDEX lines_medium_source_id_idx ON maps.lines_medium USING btree (source_id);


--
-- Name: lines_small_geom_idx; Type: INDEX; Schema: maps; Owner: macrostrat
--

CREATE INDEX lines_small_geom_idx ON maps.lines_small USING gist (geom);


--
-- Name: lines_small_line_id_idx; Type: INDEX; Schema: maps; Owner: macrostrat
--

CREATE INDEX lines_small_line_id_idx ON maps.lines_small USING btree (line_id);


--
-- Name: lines_small_orig_id_idx; Type: INDEX; Schema: maps; Owner: macrostrat
--

CREATE INDEX lines_small_orig_id_idx ON maps.lines_small USING btree (orig_id);


--
-- Name: lines_small_source_id_idx; Type: INDEX; Schema: maps; Owner: macrostrat
--

CREATE INDEX lines_small_source_id_idx ON maps.lines_small USING btree (source_id);


--
-- Name: lines_tiny_geom_idx; Type: INDEX; Schema: maps; Owner: macrostrat
--

CREATE INDEX lines_tiny_geom_idx ON maps.lines_tiny USING gist (geom);


--
-- Name: lines_tiny_line_id_idx; Type: INDEX; Schema: maps; Owner: macrostrat
--

CREATE INDEX lines_tiny_line_id_idx ON maps.lines_tiny USING btree (line_id);


--
-- Name: lines_tiny_orig_id_idx; Type: INDEX; Schema: maps; Owner: macrostrat
--

CREATE INDEX lines_tiny_orig_id_idx ON maps.lines_tiny USING btree (orig_id);


--
-- Name: lines_tiny_source_id_idx; Type: INDEX; Schema: maps; Owner: macrostrat
--

CREATE INDEX lines_tiny_source_id_idx ON maps.lines_tiny USING btree (source_id);


--
-- Name: manual_matches_map_id_idx; Type: INDEX; Schema: maps; Owner: macrostrat
--

CREATE INDEX manual_matches_map_id_idx ON maps.manual_matches USING btree (map_id);


--
-- Name: manual_matches_strat_name_id_idx; Type: INDEX; Schema: maps; Owner: macrostrat
--

CREATE INDEX manual_matches_strat_name_id_idx ON maps.manual_matches USING btree (strat_name_id);


--
-- Name: manual_matches_unit_id_idx; Type: INDEX; Schema: maps; Owner: macrostrat
--

CREATE INDEX manual_matches_unit_id_idx ON maps.manual_matches USING btree (unit_id);


--
-- Name: map_legend_legend_id_idx; Type: INDEX; Schema: maps; Owner: macrostrat
--

CREATE INDEX map_legend_legend_id_idx ON maps.map_legend USING btree (legend_id);


--
-- Name: map_legend_map_id_idx; Type: INDEX; Schema: maps; Owner: macrostrat
--

CREATE INDEX map_legend_map_id_idx ON maps.map_legend USING btree (map_id);


--
-- Name: map_liths_lith_id_idx; Type: INDEX; Schema: maps; Owner: macrostrat
--

CREATE INDEX map_liths_lith_id_idx ON maps.map_liths USING btree (lith_id);


--
-- Name: map_liths_map_id_idx; Type: INDEX; Schema: maps; Owner: macrostrat
--

CREATE INDEX map_liths_map_id_idx ON maps.map_liths USING btree (map_id);


--
-- Name: map_strat_names_map_id_idx; Type: INDEX; Schema: maps; Owner: macrostrat
--

CREATE INDEX map_strat_names_map_id_idx ON maps.map_strat_names USING btree (map_id);


--
-- Name: map_strat_names_strat_name_id_idx; Type: INDEX; Schema: maps; Owner: macrostrat
--

CREATE INDEX map_strat_names_strat_name_id_idx ON maps.map_strat_names USING btree (strat_name_id);


--
-- Name: map_units_map_id_idx; Type: INDEX; Schema: maps; Owner: macrostrat
--

CREATE INDEX map_units_map_id_idx ON maps.map_units USING btree (map_id);


--
-- Name: map_units_unit_id_idx; Type: INDEX; Schema: maps; Owner: macrostrat
--

CREATE INDEX map_units_unit_id_idx ON maps.map_units USING btree (unit_id);


--
-- Name: medium_b_interval_idx; Type: INDEX; Schema: maps; Owner: macrostrat
--

CREATE INDEX medium_b_interval_idx ON maps.polygons_medium USING btree (b_interval);


--
-- Name: medium_geom_idx; Type: INDEX; Schema: maps; Owner: macrostrat
--

CREATE INDEX medium_geom_idx ON maps.polygons_medium USING gist (geom);


--
-- Name: medium_orig_id_idx; Type: INDEX; Schema: maps; Owner: macrostrat
--

CREATE INDEX medium_orig_id_idx ON maps.polygons_medium USING btree (orig_id);


--
-- Name: medium_source_id_idx; Type: INDEX; Schema: maps; Owner: macrostrat
--

CREATE INDEX medium_source_id_idx ON maps.polygons_medium USING btree (source_id);


--
-- Name: medium_t_interval_idx; Type: INDEX; Schema: maps; Owner: macrostrat
--

CREATE INDEX medium_t_interval_idx ON maps.polygons_medium USING btree (t_interval);


--
-- Name: points_geom_idx; Type: INDEX; Schema: maps; Owner: macrostrat
--

CREATE INDEX points_geom_idx ON maps.points USING gist (geom);


--
-- Name: points_source_id_idx; Type: INDEX; Schema: maps; Owner: macrostrat
--

CREATE INDEX points_source_id_idx ON maps.points USING btree (source_id);


--
-- Name: polygons_medium_name_idx; Type: INDEX; Schema: maps; Owner: macrostrat
--

CREATE INDEX polygons_medium_name_idx ON maps.polygons_medium USING btree (name);


--
-- Name: polygons_small_name_idx; Type: INDEX; Schema: maps; Owner: macrostrat
--

CREATE INDEX polygons_small_name_idx ON maps.polygons_small USING btree (name);


--
-- Name: polygons_tiny_name_idx; Type: INDEX; Schema: maps; Owner: macrostrat
--

CREATE INDEX polygons_tiny_name_idx ON maps.polygons_tiny USING btree (name);


--
-- Name: small_b_interval_idx; Type: INDEX; Schema: maps; Owner: macrostrat
--

CREATE INDEX small_b_interval_idx ON maps.polygons_small USING btree (b_interval);


--
-- Name: small_geom_idx; Type: INDEX; Schema: maps; Owner: macrostrat
--

CREATE INDEX small_geom_idx ON maps.polygons_small USING gist (geom);


--
-- Name: small_orig_id_idx; Type: INDEX; Schema: maps; Owner: macrostrat
--

CREATE INDEX small_orig_id_idx ON maps.polygons_small USING btree (orig_id);


--
-- Name: small_source_id_idx; Type: INDEX; Schema: maps; Owner: macrostrat
--

CREATE INDEX small_source_id_idx ON maps.polygons_small USING btree (source_id);


--
-- Name: small_t_interval_idx; Type: INDEX; Schema: maps; Owner: macrostrat
--

CREATE INDEX small_t_interval_idx ON maps.polygons_small USING btree (t_interval);


--
-- Name: sources_rgeom_idx; Type: INDEX; Schema: maps; Owner: macrostrat
--

CREATE INDEX sources_rgeom_idx ON maps.sources USING gist (rgeom);


--
-- Name: sources_web_geom_idx; Type: INDEX; Schema: maps; Owner: macrostrat
--

CREATE INDEX sources_web_geom_idx ON maps.sources USING gist (web_geom);


--
-- Name: tiny_b_interval_idx; Type: INDEX; Schema: maps; Owner: macrostrat
--

CREATE INDEX tiny_b_interval_idx ON maps.polygons_tiny USING btree (b_interval);


--
-- Name: tiny_geom_idx; Type: INDEX; Schema: maps; Owner: macrostrat
--

CREATE INDEX tiny_geom_idx ON maps.polygons_tiny USING gist (geom);


--
-- Name: tiny_orig_id_idx; Type: INDEX; Schema: maps; Owner: macrostrat
--

CREATE INDEX tiny_orig_id_idx ON maps.polygons_tiny USING btree (orig_id);


--
-- Name: tiny_source_id_idx; Type: INDEX; Schema: maps; Owner: macrostrat
--

CREATE INDEX tiny_source_id_idx ON maps.polygons_tiny USING btree (source_id);


--
-- Name: tiny_t_interval_idx; Type: INDEX; Schema: maps; Owner: macrostrat
--

CREATE INDEX tiny_t_interval_idx ON maps.polygons_tiny USING btree (t_interval);


--
-- Name: large_b_interval_idx; Type: INDEX ATTACH; Schema: maps; Owner: macrostrat
--

ALTER INDEX maps.polygons_b_interval_idx ATTACH PARTITION maps.large_b_interval_idx;


--
-- Name: large_geom_idx; Type: INDEX ATTACH; Schema: maps; Owner: macrostrat
--

ALTER INDEX maps.polygons_geom_idx ATTACH PARTITION maps.large_geom_idx;


--
-- Name: large_name_idx; Type: INDEX ATTACH; Schema: maps; Owner: macrostrat
--

ALTER INDEX maps.polygons_name_idx ATTACH PARTITION maps.large_name_idx;


--
-- Name: large_orig_id_idx; Type: INDEX ATTACH; Schema: maps; Owner: macrostrat
--

ALTER INDEX maps.polygons_orig_id_idx ATTACH PARTITION maps.large_orig_id_idx;


--
-- Name: large_source_id_idx; Type: INDEX ATTACH; Schema: maps; Owner: macrostrat
--

ALTER INDEX maps.polygons_source_id_idx ATTACH PARTITION maps.large_source_id_idx;


--
-- Name: large_t_interval_idx; Type: INDEX ATTACH; Schema: maps; Owner: macrostrat
--

ALTER INDEX maps.polygons_t_interval_idx ATTACH PARTITION maps.large_t_interval_idx;


--
-- Name: lines_large_geom_idx; Type: INDEX ATTACH; Schema: maps; Owner: macrostrat
--

ALTER INDEX maps.lines_geom_idx ATTACH PARTITION maps.lines_large_geom_idx;


--
-- Name: lines_large_line_id_idx; Type: INDEX ATTACH; Schema: maps; Owner: macrostrat
--

ALTER INDEX maps.lines_line_id_idx ATTACH PARTITION maps.lines_large_line_id_idx;


--
-- Name: lines_large_orig_id_idx; Type: INDEX ATTACH; Schema: maps; Owner: macrostrat
--

ALTER INDEX maps.lines_orig_id_idx ATTACH PARTITION maps.lines_large_orig_id_idx;


--
-- Name: lines_large_pkey; Type: INDEX ATTACH; Schema: maps; Owner: macrostrat
--

ALTER INDEX maps.lines_pkey ATTACH PARTITION maps.lines_large_pkey;


--
-- Name: lines_large_source_id_idx; Type: INDEX ATTACH; Schema: maps; Owner: macrostrat
--

ALTER INDEX maps.lines_source_id_idx ATTACH PARTITION maps.lines_large_source_id_idx;


--
-- Name: lines_medium_geom_idx; Type: INDEX ATTACH; Schema: maps; Owner: macrostrat
--

ALTER INDEX maps.lines_geom_idx ATTACH PARTITION maps.lines_medium_geom_idx;


--
-- Name: lines_medium_line_id_idx; Type: INDEX ATTACH; Schema: maps; Owner: macrostrat
--

ALTER INDEX maps.lines_line_id_idx ATTACH PARTITION maps.lines_medium_line_id_idx;


--
-- Name: lines_medium_orig_id_idx; Type: INDEX ATTACH; Schema: maps; Owner: macrostrat
--

ALTER INDEX maps.lines_orig_id_idx ATTACH PARTITION maps.lines_medium_orig_id_idx;


--
-- Name: lines_medium_pkey; Type: INDEX ATTACH; Schema: maps; Owner: macrostrat
--

ALTER INDEX maps.lines_pkey ATTACH PARTITION maps.lines_medium_pkey;


--
-- Name: lines_medium_source_id_idx; Type: INDEX ATTACH; Schema: maps; Owner: macrostrat
--

ALTER INDEX maps.lines_source_id_idx ATTACH PARTITION maps.lines_medium_source_id_idx;


--
-- Name: lines_small_geom_idx; Type: INDEX ATTACH; Schema: maps; Owner: macrostrat
--

ALTER INDEX maps.lines_geom_idx ATTACH PARTITION maps.lines_small_geom_idx;


--
-- Name: lines_small_line_id_idx; Type: INDEX ATTACH; Schema: maps; Owner: macrostrat
--

ALTER INDEX maps.lines_line_id_idx ATTACH PARTITION maps.lines_small_line_id_idx;


--
-- Name: lines_small_orig_id_idx; Type: INDEX ATTACH; Schema: maps; Owner: macrostrat
--

ALTER INDEX maps.lines_orig_id_idx ATTACH PARTITION maps.lines_small_orig_id_idx;


--
-- Name: lines_small_pkey; Type: INDEX ATTACH; Schema: maps; Owner: macrostrat
--

ALTER INDEX maps.lines_pkey ATTACH PARTITION maps.lines_small_pkey;


--
-- Name: lines_small_source_id_idx; Type: INDEX ATTACH; Schema: maps; Owner: macrostrat
--

ALTER INDEX maps.lines_source_id_idx ATTACH PARTITION maps.lines_small_source_id_idx;


--
-- Name: lines_tiny_geom_idx; Type: INDEX ATTACH; Schema: maps; Owner: macrostrat
--

ALTER INDEX maps.lines_geom_idx ATTACH PARTITION maps.lines_tiny_geom_idx;


--
-- Name: lines_tiny_line_id_idx; Type: INDEX ATTACH; Schema: maps; Owner: macrostrat
--

ALTER INDEX maps.lines_line_id_idx ATTACH PARTITION maps.lines_tiny_line_id_idx;


--
-- Name: lines_tiny_orig_id_idx; Type: INDEX ATTACH; Schema: maps; Owner: macrostrat
--

ALTER INDEX maps.lines_orig_id_idx ATTACH PARTITION maps.lines_tiny_orig_id_idx;


--
-- Name: lines_tiny_pkey; Type: INDEX ATTACH; Schema: maps; Owner: macrostrat
--

ALTER INDEX maps.lines_pkey ATTACH PARTITION maps.lines_tiny_pkey;


--
-- Name: lines_tiny_source_id_idx; Type: INDEX ATTACH; Schema: maps; Owner: macrostrat
--

ALTER INDEX maps.lines_source_id_idx ATTACH PARTITION maps.lines_tiny_source_id_idx;


--
-- Name: maps_polygons_large_pkey; Type: INDEX ATTACH; Schema: maps; Owner: macrostrat
--

ALTER INDEX maps.maps_polygons_pkey ATTACH PARTITION maps.maps_polygons_large_pkey;


--
-- Name: maps_polygons_medium_pkey; Type: INDEX ATTACH; Schema: maps; Owner: macrostrat
--

ALTER INDEX maps.maps_polygons_pkey ATTACH PARTITION maps.maps_polygons_medium_pkey;


--
-- Name: maps_polygons_small_pkey; Type: INDEX ATTACH; Schema: maps; Owner: macrostrat
--

ALTER INDEX maps.maps_polygons_pkey ATTACH PARTITION maps.maps_polygons_small_pkey;


--
-- Name: maps_polygons_tiny_pkey; Type: INDEX ATTACH; Schema: maps; Owner: macrostrat
--

ALTER INDEX maps.maps_polygons_pkey ATTACH PARTITION maps.maps_polygons_tiny_pkey;


--
-- Name: medium_b_interval_idx; Type: INDEX ATTACH; Schema: maps; Owner: macrostrat
--

ALTER INDEX maps.polygons_b_interval_idx ATTACH PARTITION maps.medium_b_interval_idx;


--
-- Name: medium_geom_idx; Type: INDEX ATTACH; Schema: maps; Owner: macrostrat
--

ALTER INDEX maps.polygons_geom_idx ATTACH PARTITION maps.medium_geom_idx;


--
-- Name: medium_orig_id_idx; Type: INDEX ATTACH; Schema: maps; Owner: macrostrat
--

ALTER INDEX maps.polygons_orig_id_idx ATTACH PARTITION maps.medium_orig_id_idx;


--
-- Name: medium_source_id_idx; Type: INDEX ATTACH; Schema: maps; Owner: macrostrat
--

ALTER INDEX maps.polygons_source_id_idx ATTACH PARTITION maps.medium_source_id_idx;


--
-- Name: medium_t_interval_idx; Type: INDEX ATTACH; Schema: maps; Owner: macrostrat
--

ALTER INDEX maps.polygons_t_interval_idx ATTACH PARTITION maps.medium_t_interval_idx;


--
-- Name: polygons_medium_name_idx; Type: INDEX ATTACH; Schema: maps; Owner: macrostrat
--

ALTER INDEX maps.polygons_name_idx ATTACH PARTITION maps.polygons_medium_name_idx;


--
-- Name: polygons_small_name_idx; Type: INDEX ATTACH; Schema: maps; Owner: macrostrat
--

ALTER INDEX maps.polygons_name_idx ATTACH PARTITION maps.polygons_small_name_idx;


--
-- Name: polygons_tiny_name_idx; Type: INDEX ATTACH; Schema: maps; Owner: macrostrat
--

ALTER INDEX maps.polygons_name_idx ATTACH PARTITION maps.polygons_tiny_name_idx;


--
-- Name: small_b_interval_idx; Type: INDEX ATTACH; Schema: maps; Owner: macrostrat
--

ALTER INDEX maps.polygons_b_interval_idx ATTACH PARTITION maps.small_b_interval_idx;


--
-- Name: small_geom_idx; Type: INDEX ATTACH; Schema: maps; Owner: macrostrat
--

ALTER INDEX maps.polygons_geom_idx ATTACH PARTITION maps.small_geom_idx;


--
-- Name: small_orig_id_idx; Type: INDEX ATTACH; Schema: maps; Owner: macrostrat
--

ALTER INDEX maps.polygons_orig_id_idx ATTACH PARTITION maps.small_orig_id_idx;


--
-- Name: small_source_id_idx; Type: INDEX ATTACH; Schema: maps; Owner: macrostrat
--

ALTER INDEX maps.polygons_source_id_idx ATTACH PARTITION maps.small_source_id_idx;


--
-- Name: small_t_interval_idx; Type: INDEX ATTACH; Schema: maps; Owner: macrostrat
--

ALTER INDEX maps.polygons_t_interval_idx ATTACH PARTITION maps.small_t_interval_idx;


--
-- Name: tiny_b_interval_idx; Type: INDEX ATTACH; Schema: maps; Owner: macrostrat
--

ALTER INDEX maps.polygons_b_interval_idx ATTACH PARTITION maps.tiny_b_interval_idx;


--
-- Name: tiny_geom_idx; Type: INDEX ATTACH; Schema: maps; Owner: macrostrat
--

ALTER INDEX maps.polygons_geom_idx ATTACH PARTITION maps.tiny_geom_idx;


--
-- Name: tiny_orig_id_idx; Type: INDEX ATTACH; Schema: maps; Owner: macrostrat
--

ALTER INDEX maps.polygons_orig_id_idx ATTACH PARTITION maps.tiny_orig_id_idx;


--
-- Name: tiny_source_id_idx; Type: INDEX ATTACH; Schema: maps; Owner: macrostrat
--

ALTER INDEX maps.polygons_source_id_idx ATTACH PARTITION maps.tiny_source_id_idx;


--
-- Name: tiny_t_interval_idx; Type: INDEX ATTACH; Schema: maps; Owner: macrostrat
--

ALTER INDEX maps.polygons_t_interval_idx ATTACH PARTITION maps.tiny_t_interval_idx;


--
-- Name: lines lines_source_id_fkey; Type: FK CONSTRAINT; Schema: maps; Owner: macrostrat
--

ALTER TABLE maps.lines
    ADD CONSTRAINT lines_source_id_fkey FOREIGN KEY (source_id) REFERENCES maps.sources(source_id);


--
-- Name: points points_source_id_fkey; Type: FK CONSTRAINT; Schema: maps; Owner: macrostrat
--

ALTER TABLE ONLY maps.points
    ADD CONSTRAINT points_source_id_fkey FOREIGN KEY (source_id) REFERENCES maps.sources(source_id);


--
-- Name: polygons polygons_source_id_fkey; Type: FK CONSTRAINT; Schema: maps; Owner: macrostrat
--

ALTER TABLE maps.polygons
    ADD CONSTRAINT polygons_source_id_fkey FOREIGN KEY (source_id) REFERENCES maps.sources(source_id);


--
-- Name: source_operations source_operations_source_id_fkey; Type: FK CONSTRAINT; Schema: maps; Owner: macrostrat
--

ALTER TABLE ONLY maps.source_operations
    ADD CONSTRAINT source_operations_source_id_fkey FOREIGN KEY (source_id) REFERENCES maps.sources(source_id) ON DELETE CASCADE;


--
-- Name: source_operations source_operations_user_id_fkey; Type: FK CONSTRAINT; Schema: maps; Owner: macrostrat
--

ALTER TABLE ONLY maps.source_operations
    ADD CONSTRAINT source_operations_user_id_fkey FOREIGN KEY (user_id) REFERENCES macrostrat_auth."user"(id) ON DELETE SET NULL;


--
-- Name: TABLE vw_legend_with_liths; Type: ACL; Schema: maps; Owner: macrostrat-admin
--

GRANT SELECT ON TABLE maps.vw_legend_with_liths TO macrostrat;


--
-- Name: DEFAULT PRIVILEGES FOR SEQUENCES; Type: DEFAULT ACL; Schema: maps; Owner: macrostrat-admin
--

ALTER DEFAULT PRIVILEGES FOR ROLE "macrostrat-admin" IN SCHEMA maps GRANT SELECT,USAGE ON SEQUENCES  TO macrostrat;


--
-- Name: DEFAULT PRIVILEGES FOR TABLES; Type: DEFAULT ACL; Schema: maps; Owner: macrostrat-admin
--

ALTER DEFAULT PRIVILEGES FOR ROLE "macrostrat-admin" IN SCHEMA maps GRANT SELECT ON TABLES  TO macrostrat;


--
-- PostgreSQL database dump complete
--

