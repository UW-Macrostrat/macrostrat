--
-- pgschema database dump
--

-- Dumped from database version PostgreSQL 15.15
-- Dumped by pgschema version 1.5.1


--
-- Name: addbandarg; Type: TYPE; Schema: -; Owner: -
--

CREATE TYPE addbandarg AS (index integer, pixeltype text, initialvalue double precision, nodataval double precision);

--
-- Name: agg_count; Type: TYPE; Schema: -; Owner: -
--

CREATE TYPE agg_count AS (count bigint, nband integer, exclude_nodata_value boolean, sample_percent double precision);

--
-- Name: agg_samealignment; Type: TYPE; Schema: -; Owner: -
--

CREATE TYPE agg_samealignment AS (refraster raster, aligned boolean);

--
-- Name: boundary_status; Type: TYPE; Schema: -; Owner: -
--

CREATE TYPE boundary_status AS ENUM (
    '',
    'modeled',
    'relative',
    'absolute',
    'spike'
);

--
-- Name: boundary_type; Type: TYPE; Schema: -; Owner: -
--

CREATE TYPE boundary_type AS ENUM (
    '',
    'unconformity',
    'conformity',
    'fault',
    'disconformity',
    'non-conformity',
    'angular unconformity'
);

--
-- Name: geometry_dump; Type: TYPE; Schema: -; Owner: -
--

CREATE TYPE geometry_dump AS (path integer[], geom geometry);

--
-- Name: geomval; Type: TYPE; Schema: -; Owner: -
--

CREATE TYPE geomval AS (geom geometry, val double precision);

--
-- Name: measurement_class; Type: TYPE; Schema: -; Owner: -
--

CREATE TYPE measurement_class AS ENUM (
    '',
    'geophysical',
    'geochemical',
    'sedimentological'
);

--
-- Name: measurement_class_new; Type: TYPE; Schema: -; Owner: -
--

CREATE TYPE measurement_class_new AS ENUM (
    '',
    'geophysical',
    'geochemical',
    'sedimentological'
);

--
-- Name: measurement_type; Type: TYPE; Schema: -; Owner: -
--

CREATE TYPE measurement_type AS ENUM (
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

--
-- Name: measurement_type_new; Type: TYPE; Schema: -; Owner: -
--

CREATE TYPE measurement_type_new AS ENUM (
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

--
-- Name: rastbandarg; Type: TYPE; Schema: -; Owner: -
--

CREATE TYPE rastbandarg AS (rast raster, nband integer);

--
-- Name: reclassarg; Type: TYPE; Schema: -; Owner: -
--

CREATE TYPE reclassarg AS (nband integer, reclassexpr text, pixeltype text, nodataval double precision);

--
-- Name: saved_locations_enum; Type: TYPE; Schema: -; Owner: -
--

CREATE TYPE saved_locations_enum AS ENUM (
    'Favorites',
    'Want to go',
    'Geological wonder'
);

--
-- Name: schemeenum; Type: TYPE; Schema: -; Owner: -
--

CREATE TYPE schemeenum AS ENUM (
    'http',
    's3'
);

--
-- Name: summarystats; Type: TYPE; Schema: -; Owner: -
--

CREATE TYPE summarystats AS (count bigint, sum double precision, mean double precision, stddev double precision, min double precision, max double precision);

--
-- Name: unionarg; Type: TYPE; Schema: -; Owner: -
--

CREATE TYPE unionarg AS (nband integer, uniontype text);

--
-- Name: valid_detail; Type: TYPE; Schema: -; Owner: -
--

CREATE TYPE valid_detail AS (valid boolean, reason character varying, location geometry);

--
-- Name: geologic_boundary_source_seq; Type: SEQUENCE; Schema: -; Owner: -
--

CREATE SEQUENCE IF NOT EXISTS geologic_boundary_source_seq;

--
-- Name: line_ids; Type: SEQUENCE; Schema: -; Owner: -
--

CREATE SEQUENCE IF NOT EXISTS line_ids;

--
-- Name: map_ids; Type: SEQUENCE; Schema: -; Owner: -
--

CREATE SEQUENCE IF NOT EXISTS map_ids;

--
-- Name: export_table; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS export_table (
    source_id integer,
    name varchar(255),
    primary_table varchar(255),
    url varchar(255),
    ref_title text,
    authors varchar(255),
    ref_year text,
    ref_source varchar(255),
    isbn_doi varchar(100),
    scale varchar(20),
    primary_line_table varchar(50),
    licence varchar(100),
    features integer,
    area integer,
    priority boolean,
    rgeom geometry,
    display_scales text[],
    web_geom geometry,
    new_priority integer,
    status_code text,
    slug text,
    raster_url text
);

--
-- Name: impervious; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS impervious (
    rid SERIAL,
    rast raster,
    CONSTRAINT impervious_pkey PRIMARY KEY (rid)
);

--
-- Name: impervious_st_convexhull_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS impervious_st_convexhull_idx ON impervious USING gist (public.st_convexhull(rast));

--
-- Name: land; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS land (
    gid SERIAL,
    scalerank numeric(10,0),
    featurecla varchar(32),
    geom geometry,
    CONSTRAINT land_pkey PRIMARY KEY (gid)
);

--
-- Name: land_geom_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS land_geom_idx ON land USING gist (geom);

--
-- Name: lookup_large; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS lookup_large (
    map_id integer,
    unit_ids integer[],
    strat_name_ids integer[],
    lith_ids integer[],
    best_age_top numeric,
    best_age_bottom numeric,
    color varchar(20),
    lith_types text[],
    lith_classes text[],
    concept_ids integer[],
    strat_name_children integer[],
    legend_id integer
);

--
-- Name: lookup_large_concept_ids_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS lookup_large_concept_ids_idx ON lookup_large USING gin (concept_ids);

--
-- Name: lookup_large_legend_id_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS lookup_large_legend_id_idx ON lookup_large (legend_id);

--
-- Name: lookup_large_lith_ids_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS lookup_large_lith_ids_idx ON lookup_large USING gin (lith_ids);

--
-- Name: lookup_large_map_id_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS lookup_large_map_id_idx ON lookup_large (map_id);

--
-- Name: lookup_large_strat_name_children_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS lookup_large_strat_name_children_idx ON lookup_large USING gin (strat_name_children);

--
-- Name: lookup_medium; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS lookup_medium (
    map_id integer,
    unit_ids integer[],
    strat_name_ids integer[],
    lith_ids integer[],
    best_age_top numeric,
    best_age_bottom numeric,
    color varchar(20),
    lith_types text[],
    lith_classes text[],
    concept_ids integer[],
    strat_name_children integer[],
    legend_id integer
);

--
-- Name: lookup_medium_concept_ids_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS lookup_medium_concept_ids_idx ON lookup_medium USING gin (concept_ids);

--
-- Name: lookup_medium_legend_id_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS lookup_medium_legend_id_idx ON lookup_medium (legend_id);

--
-- Name: lookup_medium_lith_ids_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS lookup_medium_lith_ids_idx ON lookup_medium USING gin (lith_ids);

--
-- Name: lookup_medium_map_id_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS lookup_medium_map_id_idx ON lookup_medium (map_id);

--
-- Name: lookup_medium_strat_name_children_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS lookup_medium_strat_name_children_idx ON lookup_medium USING gin (strat_name_children);

--
-- Name: lookup_small; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS lookup_small (
    map_id integer,
    unit_ids integer[],
    strat_name_ids integer[],
    lith_ids integer[],
    best_age_top numeric,
    best_age_bottom numeric,
    color varchar(20),
    lith_types text[],
    lith_classes text[],
    concept_ids integer[],
    strat_name_children integer[],
    legend_id integer
);

--
-- Name: lookup_small_concept_ids_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS lookup_small_concept_ids_idx ON lookup_small USING gin (concept_ids);

--
-- Name: lookup_small_legend_id_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS lookup_small_legend_id_idx ON lookup_small (legend_id);

--
-- Name: lookup_small_lith_ids_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS lookup_small_lith_ids_idx ON lookup_small USING gin (lith_ids);

--
-- Name: lookup_small_map_id_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS lookup_small_map_id_idx ON lookup_small (map_id);

--
-- Name: lookup_small_strat_name_children_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS lookup_small_strat_name_children_idx ON lookup_small USING gin (strat_name_children);

--
-- Name: lookup_tiny; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS lookup_tiny (
    map_id integer,
    unit_ids integer[],
    strat_name_ids integer[],
    lith_ids integer[],
    best_age_top numeric,
    best_age_bottom numeric,
    color varchar(20),
    lith_types text[],
    lith_classes text[],
    concept_ids integer[],
    strat_name_children integer[],
    legend_id integer
);

--
-- Name: lookup_tiny_concept_ids_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS lookup_tiny_concept_ids_idx ON lookup_tiny USING gin (concept_ids);

--
-- Name: lookup_tiny_legend_id_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS lookup_tiny_legend_id_idx ON lookup_tiny (legend_id);

--
-- Name: lookup_tiny_lith_ids_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS lookup_tiny_lith_ids_idx ON lookup_tiny USING gin (lith_ids);

--
-- Name: lookup_tiny_map_id_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS lookup_tiny_map_id_idx ON lookup_tiny (map_id);

--
-- Name: lookup_tiny_strat_name_children_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS lookup_tiny_strat_name_children_idx ON lookup_tiny USING gin (strat_name_children);

--
-- Name: macrostrat_union; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS macrostrat_union (
    id SERIAL,
    geom geometry,
    CONSTRAINT macrostrat_union_pkey PRIMARY KEY (id)
);

--
-- Name: next_id; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS next_id (
    id integer
);

--
-- Name: ref_boundaries; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS ref_boundaries (
    ref_id integer,
    ref text,
    geom geometry
);

--
-- Name: spatial_ref_sys; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS spatial_ref_sys (
    srid integer,
    auth_name varchar(256),
    auth_srid integer,
    srtext varchar(2048),
    proj4text varchar(2048),
    CONSTRAINT spatial_ref_sys_pkey PRIMARY KEY (srid),
    CONSTRAINT spatial_ref_sys_srid_check CHECK (srid > 0 AND srid <= 998999)
);

--
-- Name: temp_names; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS temp_names (
    strat_name_id integer,
    strat_name varchar(100),
    concept_id integer,
    rank_name varchar(100),
    bed_id integer,
    bed_name varchar(100),
    mbr_id integer,
    mbr_name varchar(100),
    fm_id integer,
    fm_name varchar(100),
    subgp_id integer,
    subgp_name varchar(100),
    gp_id integer,
    gp_name varchar(100),
    sgp_id integer,
    sgp_name varchar(100),
    early_age numeric(8,4),
    late_age numeric(8,4),
    gsc_lexicon character(15),
    parent integer,
    tree integer,
    t_units integer,
    b_period varchar(100),
    t_period varchar(100),
    name_no_lith varchar(100),
    ref_id integer,
    c_interval varchar(100),
    map_id integer,
    match_text text
);

--
-- Name: temp_names_name_no_lith_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS temp_names_name_no_lith_idx ON temp_names (name_no_lith);

--
-- Name: temp_names_rank_name_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS temp_names_rank_name_idx ON temp_names (rank_name);

--
-- Name: temp_names_strat_name_id_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS temp_names_strat_name_id_idx ON temp_names (strat_name_id);

--
-- Name: temp_names_strat_name_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS temp_names_strat_name_idx ON temp_names (strat_name);

--
-- Name: temp_rocks; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS temp_rocks (
    map_ids integer[],
    name text,
    orig_strat_name text[],
    strat_name text,
    strat_name_clean text,
    age varchar(255),
    lith text,
    descrip text,
    comments text,
    t_interval integer,
    b_interval integer,
    envelope geometry
);

--
-- Name: temp_rocks_b_interval_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS temp_rocks_b_interval_idx ON temp_rocks (b_interval);

--
-- Name: temp_rocks_envelope_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS temp_rocks_envelope_idx ON temp_rocks USING gist (envelope);

--
-- Name: temp_rocks_strat_name_clean_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS temp_rocks_strat_name_clean_idx ON temp_rocks (strat_name_clean);

--
-- Name: temp_rocks_strat_name_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS temp_rocks_strat_name_idx ON temp_rocks (strat_name);

--
-- Name: temp_rocks_t_interval_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS temp_rocks_t_interval_idx ON temp_rocks (t_interval);

--
-- Name: units; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS units (
    mapunit text,
    description text
);

--
-- Name: usage_stats; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS usage_stats (
    id SERIAL,
    date timestamptz DEFAULT now() NOT NULL,
    ip text NOT NULL,
    lat double precision NOT NULL,
    lng double precision NOT NULL,
    CONSTRAINT usage_stats_pkey PRIMARY KEY (id)
);

--
-- Name: count_estimate(text); Type: FUNCTION; Schema: -; Owner: -
--

CREATE OR REPLACE FUNCTION count_estimate(
    query text
)
RETURNS integer
LANGUAGE plpgsql
VOLATILE
STRICT
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

--
-- Name: current_app_role(); Type: FUNCTION; Schema: -; Owner: -
--

CREATE OR REPLACE FUNCTION current_app_role()
RETURNS text
LANGUAGE sql
STABLE
AS $$
  SELECT (current_setting('request.jwt.claims', true)::json ->> 'role')::text;
$$;

--
-- Name: current_app_user_id(); Type: FUNCTION; Schema: -; Owner: -
--

CREATE OR REPLACE FUNCTION current_app_user_id()
RETURNS integer
LANGUAGE sql
STABLE
AS $$
  SELECT (current_setting('request.jwt.claims', true)::json ->> 'user_id')::int;
$$;

--
-- Name: group_items_by_type(text); Type: FUNCTION; Schema: -; Owner: -
--

CREATE OR REPLACE FUNCTION group_items_by_type(
    name_filter text DEFAULT NULL
)
RETURNS json
LANGUAGE plpgsql
STABLE
AS $$
BEGIN
  RETURN (
    SELECT json_agg(grouped)
    FROM (
      SELECT
        type,
        json_agg(to_jsonb(t) - 'type') AS items
      FROM your_table t
      WHERE (name_filter IS NULL OR t.name ILIKE name_filter)
      GROUP BY type
    ) grouped
  );
END;
$$;

--
-- Name: update_updated_on(); Type: FUNCTION; Schema: -; Owner: -
--

CREATE OR REPLACE FUNCTION update_updated_on()
RETURNS trigger
LANGUAGE plpgsql
VOLATILE
AS $$
BEGIN
    NEW.updated_on = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$;

--
-- Name: geography_columns; Type: VIEW; Schema: -; Owner: -
--

