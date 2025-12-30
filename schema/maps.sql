--
-- pgschema database dump
--

-- Dumped from database version PostgreSQL 15.15
-- Dumped by pgschema version 1.5.1


--
-- Name: ingest_state; Type: TYPE; Schema: -; Owner: -
--

CREATE TYPE ingest_state AS ENUM (
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

--
-- Name: ingest_type; Type: TYPE; Schema: -; Owner: -
--

CREATE TYPE ingest_type AS ENUM (
    'vector',
    'ta1_output'
);

--
-- Name: map_scale; Type: TYPE; Schema: -; Owner: -
--

CREATE TYPE map_scale AS ENUM (
    'tiny',
    'small',
    'medium',
    'large'
);

--
-- Name: legend; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS legend (
    legend_id SERIAL,
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
    large_area numeric,
    CONSTRAINT legend_pkey PRIMARY KEY (legend_id)
);

--
-- Name: legend_source_id_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS legend_source_id_idx ON legend (source_id);

--
-- Name: legend_liths; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS legend_liths (
    legend_id integer NOT NULL,
    lith_id integer NOT NULL,
    basis_col text NOT NULL,
    CONSTRAINT legend_liths_legend_id_lith_id_basis_col_key UNIQUE (legend_id, lith_id, basis_col)
);

--
-- Name: legend_liths_legend_id_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS legend_liths_legend_id_idx ON legend_liths (legend_id);

--
-- Name: legend_liths_lith_id_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS legend_liths_lith_id_idx ON legend_liths (lith_id);

--
-- Name: manual_matches; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS manual_matches (
    match_id SERIAL,
    map_id integer NOT NULL,
    strat_name_id integer,
    unit_id integer,
    addition boolean DEFAULT false,
    removal boolean DEFAULT false,
    type varchar(20)
);

--
-- Name: manual_matches_map_id_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS manual_matches_map_id_idx ON manual_matches (map_id);

--
-- Name: manual_matches_strat_name_id_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS manual_matches_strat_name_id_idx ON manual_matches (strat_name_id);

--
-- Name: manual_matches_unit_id_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS manual_matches_unit_id_idx ON manual_matches (unit_id);

--
-- Name: map_legend; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS map_legend (
    legend_id integer NOT NULL,
    map_id integer NOT NULL,
    CONSTRAINT map_legend_legend_id_map_id_key UNIQUE (legend_id, map_id)
);

--
-- Name: map_legend_legend_id_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS map_legend_legend_id_idx ON map_legend (legend_id);

--
-- Name: map_legend_map_id_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS map_legend_map_id_idx ON map_legend (map_id);

--
-- Name: map_liths; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS map_liths (
    map_id integer NOT NULL,
    lith_id integer NOT NULL,
    basis_col varchar(50)
);

--
-- Name: map_liths_lith_id_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS map_liths_lith_id_idx ON map_liths (lith_id);

--
-- Name: map_liths_map_id_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS map_liths_map_id_idx ON map_liths (map_id);

--
-- Name: map_strat_names; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS map_strat_names (
    map_id integer NOT NULL,
    strat_name_id integer NOT NULL,
    basis_col varchar(50)
);

--
-- Name: map_strat_names_map_id_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS map_strat_names_map_id_idx ON map_strat_names (map_id);

--
-- Name: map_strat_names_strat_name_id_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS map_strat_names_strat_name_id_idx ON map_strat_names (strat_name_id);

--
-- Name: map_units; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS map_units (
    map_id integer NOT NULL,
    unit_id integer NOT NULL,
    basis_col varchar(50)
);

--
-- Name: map_units_map_id_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS map_units_map_id_idx ON map_units (map_id);

--
-- Name: map_units_unit_id_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS map_units_unit_id_idx ON map_units (unit_id);

--
-- Name: sources; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS sources (
    source_id SERIAL,
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
    license varchar(100),
    features integer,
    area integer,
    priority boolean DEFAULT false,
    rgeom public.geometry,
    display_scales text[],
    web_geom public.geometry,
    new_priority integer DEFAULT 0,
    status_code text DEFAULT 'active',
    slug text NOT NULL,
    raster_url text,
    scale_denominator integer,
    is_finalized boolean DEFAULT false,
    lines_oriented boolean,
    date_finalized timestamptz,
    ingested_by text,
    keywords text[],
    language text,
    description varchar,
    CONSTRAINT sources_pkey PRIMARY KEY (source_id),
    CONSTRAINT map_sources_name_key UNIQUE (primary_table),
    CONSTRAINT sources_slug_key1 UNIQUE (slug),
    CONSTRAINT sources_slug_key2 UNIQUE (slug),
    CONSTRAINT sources_slug_key3 UNIQUE (slug),
    CONSTRAINT sources_source_id_key UNIQUE (source_id)
);


COMMENT ON COLUMN sources.slug IS 'Unique identifier for each Macrostrat source';

--
-- Name: sources_rgeom_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS sources_rgeom_idx ON sources USING gist (rgeom);

--
-- Name: sources_web_geom_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS sources_web_geom_idx ON sources USING gist (web_geom);

--
-- Name: points; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS points (
    source_id integer NOT NULL,
    strike integer,
    dip integer,
    dip_dir integer,
    point_type varchar(100),
    certainty varchar(100),
    comments text,
    geom geometry,
    point_id SERIAL,
    orig_id text,
    CONSTRAINT points_source_id_fkey FOREIGN KEY (source_id) REFERENCES sources (source_id),
    CONSTRAINT dip_lt_90 CHECK (dip <= 90),
    CONSTRAINT dip_positive CHECK (dip >= 0),
    CONSTRAINT direction_lt_360 CHECK (dip_dir <= 360),
    CONSTRAINT direction_positive CHECK (dip_dir >= 0),
    CONSTRAINT enforce_point_geom CHECK (st_isvalid(geom)),
    CONSTRAINT strike_lt_360 CHECK (strike <= 360),
    CONSTRAINT strike_positive CHECK (strike >= 0)
);

--
-- Name: points_geom_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS points_geom_idx ON points USING gist (geom);

--
-- Name: points_source_id_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS points_source_id_idx ON points (source_id);

--
-- Name: source_operations; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS source_operations (
    id SERIAL,
    source_id integer NOT NULL,
    user_id integer,
    operation text NOT NULL,
    app text NOT NULL,
    comments text,
    details jsonb,
    date timestamptz DEFAULT now() NOT NULL,
    CONSTRAINT source_operations_pkey PRIMARY KEY (id),
    CONSTRAINT source_operations_source_id_fkey FOREIGN KEY (source_id) REFERENCES sources (source_id) ON DELETE CASCADE
);


COMMENT ON TABLE source_operations IS 'Tracks management operations for Macrostrat maps';

--
-- Name: source_operations_user_id_fkey; Type: CONSTRAINT; Schema: -; Owner: -
--

ALTER TABLE source_operations
ADD CONSTRAINT source_operations_user_id_fkey FOREIGN KEY (user_id) REFERENCES macrostrat_auth."user" (id) ON DELETE SET NULL;

--
-- Name: lines_geom_is_valid(geometry); Type: FUNCTION; Schema: -; Owner: -
--

CREATE OR REPLACE FUNCTION lines_geom_is_valid(
    geom geometry
)
RETURNS boolean
LANGUAGE sql
IMMUTABLE
AS $$
  SELECT ST_IsValid(geom) AND ST_GeometryType(geom) IN ('ST_LineString', 'ST_MultiLineString');
$$;

--
-- Name: polygons_geom_is_valid(geometry); Type: FUNCTION; Schema: -; Owner: -
--

CREATE OR REPLACE FUNCTION polygons_geom_is_valid(
    geom geometry
)
RETURNS boolean
LANGUAGE sql
IMMUTABLE
AS $$
  SELECT ST_IsValid(geom) AND ST_GeometryType(geom) IN ('ST_Polygon', 'ST_MultiPolygon');
$$;

--
-- Name: lines; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS lines (
    line_id SERIAL,
    orig_id text,
    source_id integer,
    name varchar(255),
    type_legacy varchar(100),
    direction_legacy varchar(40),
    descrip text,
    geom public.geometry NOT NULL,
    type varchar(100),
    direction varchar(40),
    scale map_scale,
    CONSTRAINT lines_pkey PRIMARY KEY (scale, line_id),
    CONSTRAINT maps_lines_geom_check CHECK (maps.lines_geom_is_valid(geom))
) PARTITION BY LIST (scale);

--
-- Name: lines_geom_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS lines_geom_idx ON lines USING gist (geom);

--
-- Name: lines_line_id_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS lines_line_id_idx ON lines (line_id);

--
-- Name: lines_orig_id_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS lines_orig_id_idx ON lines (orig_id);

--
-- Name: lines_source_id_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS lines_source_id_idx ON lines (source_id);

--
-- Name: lines_large; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS lines_large (
    line_id SERIAL,
    orig_id text,
    source_id integer,
    name varchar(255),
    type_legacy varchar(100),
    direction_legacy varchar(40),
    descrip text,
    geom public.geometry NOT NULL,
    type varchar(100),
    direction varchar(40),
    scale map_scale DEFAULT 'large',
    CONSTRAINT lines_large_pkey PRIMARY KEY (scale, line_id),
    CONSTRAINT lines_large_scale_check CHECK (scale = 'large'::maps.map_scale),
    CONSTRAINT maps_lines_geom_check CHECK (maps.lines_geom_is_valid(geom))
);

--
-- Name: lines_large_geom_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS lines_large_geom_idx ON lines_large USING gist (geom);

--
-- Name: lines_large_line_id_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS lines_large_line_id_idx ON lines_large (line_id);

--
-- Name: lines_large_orig_id_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS lines_large_orig_id_idx ON lines_large (orig_id);

--
-- Name: lines_large_source_id_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS lines_large_source_id_idx ON lines_large (source_id);

--
-- Name: lines_medium; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS lines_medium (
    line_id SERIAL,
    orig_id text,
    source_id integer,
    name varchar(255),
    type_legacy varchar(100),
    direction_legacy varchar(40),
    descrip text,
    geom public.geometry NOT NULL,
    type varchar(100),
    direction varchar(40),
    scale map_scale DEFAULT 'medium',
    CONSTRAINT lines_medium_pkey PRIMARY KEY (scale, line_id),
    CONSTRAINT lines_medium_scale_check CHECK (scale = 'medium'::maps.map_scale),
    CONSTRAINT maps_lines_geom_check CHECK (maps.lines_geom_is_valid(geom))
);

--
-- Name: lines_medium_geom_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS lines_medium_geom_idx ON lines_medium USING gist (geom);

--
-- Name: lines_medium_line_id_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS lines_medium_line_id_idx ON lines_medium (line_id);

--
-- Name: lines_medium_orig_id_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS lines_medium_orig_id_idx ON lines_medium (orig_id);

--
-- Name: lines_medium_source_id_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS lines_medium_source_id_idx ON lines_medium (source_id);

--
-- Name: lines_small; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS lines_small (
    line_id SERIAL,
    orig_id text,
    source_id integer,
    name varchar(255),
    type_legacy varchar(100),
    direction_legacy varchar(40),
    descrip text,
    geom public.geometry NOT NULL,
    type varchar(100),
    direction varchar(40),
    scale map_scale DEFAULT 'small',
    CONSTRAINT lines_small_pkey PRIMARY KEY (scale, line_id),
    CONSTRAINT lines_small_scale_check CHECK (scale = 'small'::maps.map_scale),
    CONSTRAINT maps_lines_geom_check CHECK (maps.lines_geom_is_valid(geom))
);

--
-- Name: lines_small_geom_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS lines_small_geom_idx ON lines_small USING gist (geom);

--
-- Name: lines_small_line_id_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS lines_small_line_id_idx ON lines_small (line_id);

--
-- Name: lines_small_orig_id_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS lines_small_orig_id_idx ON lines_small (orig_id);

--
-- Name: lines_small_source_id_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS lines_small_source_id_idx ON lines_small (source_id);

--
-- Name: lines_tiny; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS lines_tiny (
    line_id SERIAL,
    orig_id text,
    source_id integer,
    name varchar(255),
    type_legacy varchar(100),
    direction_legacy varchar(40),
    descrip text,
    geom public.geometry NOT NULL,
    type varchar(100),
    direction varchar(40),
    scale map_scale DEFAULT 'tiny',
    CONSTRAINT lines_tiny_pkey PRIMARY KEY (scale, line_id),
    CONSTRAINT isvalid CHECK (st_isvalid(geom)),
    CONSTRAINT lines_tiny_scale_check CHECK (scale = 'tiny'::maps.map_scale),
    CONSTRAINT maps_lines_geom_check CHECK (maps.lines_geom_is_valid(geom))
);

--
-- Name: lines_tiny_geom_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS lines_tiny_geom_idx ON lines_tiny USING gist (geom);

--
-- Name: lines_tiny_line_id_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS lines_tiny_line_id_idx ON lines_tiny (line_id);

--
-- Name: lines_tiny_orig_id_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS lines_tiny_orig_id_idx ON lines_tiny (orig_id);

--
-- Name: lines_tiny_source_id_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS lines_tiny_source_id_idx ON lines_tiny (source_id);

--
-- Name: polygons; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS polygons (
    map_id SERIAL,
    source_id integer NOT NULL,
    scale map_scale,
    orig_id text,
    name text,
    strat_name text,
    age varchar(255),
    lith text,
    descrip text,
    comments text,
    t_interval integer,
    b_interval integer,
    geom public.geometry NOT NULL,
    CONSTRAINT maps_polygons_pkey PRIMARY KEY (scale, map_id),
    CONSTRAINT maps_polygons_geom_check CHECK (maps.polygons_geom_is_valid(geom))
) PARTITION BY LIST (scale);

--
-- Name: polygons_b_interval_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS polygons_b_interval_idx ON polygons (b_interval);

--
-- Name: polygons_geom_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS polygons_geom_idx ON polygons USING gist (geom);

--
-- Name: polygons_name_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS polygons_name_idx ON polygons (name);

--
-- Name: polygons_orig_id_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS polygons_orig_id_idx ON polygons (orig_id);

--
-- Name: polygons_source_id_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS polygons_source_id_idx ON polygons (source_id);

--
-- Name: polygons_t_interval_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS polygons_t_interval_idx ON polygons (t_interval);

--
-- Name: polygons_large; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS polygons_large (
    map_id SERIAL,
    orig_id text,
    source_id integer NOT NULL,
    name text,
    strat_name text,
    age varchar(255),
    lith text,
    descrip text,
    comments text,
    t_interval integer,
    b_interval integer,
    geom public.geometry NOT NULL,
    scale map_scale DEFAULT 'large',
    CONSTRAINT maps_polygons_large_pkey PRIMARY KEY (scale, map_id),
    CONSTRAINT enforce_valid_geom_large CHECK (st_isvalid(geom)),
    CONSTRAINT maps_polygons_geom_check CHECK (maps.polygons_geom_is_valid(geom)),
    CONSTRAINT polygons_large_scale_check CHECK (scale = 'large'::maps.map_scale)
);

--
-- Name: large_b_interval_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS large_b_interval_idx ON polygons_large (b_interval);

--
-- Name: large_geom_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS large_geom_idx ON polygons_large USING gist (geom);

--
-- Name: large_name_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS large_name_idx ON polygons_large (name);

--
-- Name: large_orig_id_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS large_orig_id_idx ON polygons_large (orig_id);

--
-- Name: large_source_id_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS large_source_id_idx ON polygons_large (source_id);

--
-- Name: large_t_interval_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS large_t_interval_idx ON polygons_large (t_interval);

--
-- Name: polygons_medium; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS polygons_medium (
    map_id SERIAL,
    orig_id text,
    source_id integer NOT NULL,
    name text,
    strat_name text,
    age varchar(255),
    lith text,
    descrip text,
    comments text,
    t_interval integer,
    b_interval integer,
    geom public.geometry NOT NULL,
    scale map_scale DEFAULT 'medium',
    CONSTRAINT maps_polygons_medium_pkey PRIMARY KEY (scale, map_id),
    CONSTRAINT enforce_valid_geom_medium CHECK (st_isvalid(geom)),
    CONSTRAINT maps_polygons_geom_check CHECK (maps.polygons_geom_is_valid(geom)),
    CONSTRAINT polygons_medium_scale_check CHECK (scale = 'medium'::maps.map_scale)
);

--
-- Name: medium_b_interval_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS medium_b_interval_idx ON polygons_medium (b_interval);

--
-- Name: medium_geom_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS medium_geom_idx ON polygons_medium USING gist (geom);

--
-- Name: medium_orig_id_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS medium_orig_id_idx ON polygons_medium (orig_id);

--
-- Name: medium_source_id_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS medium_source_id_idx ON polygons_medium (source_id);

--
-- Name: medium_t_interval_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS medium_t_interval_idx ON polygons_medium (t_interval);

--
-- Name: polygons_medium_name_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS polygons_medium_name_idx ON polygons_medium (name);

--
-- Name: polygons_small; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS polygons_small (
    map_id SERIAL,
    orig_id text,
    source_id integer NOT NULL,
    name text,
    strat_name text,
    age varchar(255),
    lith text,
    descrip text,
    comments text,
    t_interval integer,
    b_interval integer,
    geom public.geometry NOT NULL,
    scale map_scale DEFAULT 'small',
    CONSTRAINT maps_polygons_small_pkey PRIMARY KEY (scale, map_id),
    CONSTRAINT maps_polygons_geom_check CHECK (maps.polygons_geom_is_valid(geom)),
    CONSTRAINT polygons_small_scale_check CHECK (scale = 'small'::maps.map_scale)
);

--
-- Name: polygons_small_name_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS polygons_small_name_idx ON polygons_small (name);

--
-- Name: small_b_interval_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS small_b_interval_idx ON polygons_small (b_interval);

--
-- Name: small_geom_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS small_geom_idx ON polygons_small USING gist (geom);

--
-- Name: small_orig_id_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS small_orig_id_idx ON polygons_small (orig_id);

--
-- Name: small_source_id_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS small_source_id_idx ON polygons_small (source_id);

--
-- Name: small_t_interval_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS small_t_interval_idx ON polygons_small (t_interval);

--
-- Name: polygons_tiny; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS polygons_tiny (
    map_id SERIAL,
    orig_id text,
    source_id integer NOT NULL,
    name text,
    strat_name text,
    age varchar(255),
    lith text,
    descrip text,
    comments text,
    t_interval integer,
    b_interval integer,
    geom public.geometry NOT NULL,
    scale map_scale DEFAULT 'tiny',
    CONSTRAINT maps_polygons_tiny_pkey PRIMARY KEY (scale, map_id),
    CONSTRAINT maps_polygons_geom_check CHECK (maps.polygons_geom_is_valid(geom)),
    CONSTRAINT polygons_tiny_scale_check CHECK (scale = 'tiny'::maps.map_scale)
);

--
-- Name: polygons_tiny_name_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS polygons_tiny_name_idx ON polygons_tiny (name);

--
-- Name: tiny_b_interval_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS tiny_b_interval_idx ON polygons_tiny (b_interval);

--
-- Name: tiny_geom_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS tiny_geom_idx ON polygons_tiny USING gist (geom);

--
-- Name: tiny_orig_id_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS tiny_orig_id_idx ON polygons_tiny (orig_id);

--
-- Name: tiny_source_id_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS tiny_source_id_idx ON polygons_tiny (source_id);

--
-- Name: tiny_t_interval_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS tiny_t_interval_idx ON polygons_tiny (t_interval);

--
-- Name: lines_source_id_fkey; Type: CONSTRAINT; Schema: -; Owner: -
--

ALTER TABLE lines
ADD CONSTRAINT lines_source_id_fkey FOREIGN KEY (source_id) REFERENCES sources (source_id);

--
-- Name: lines_source_id_fkey; Type: CONSTRAINT; Schema: -; Owner: -
--

ALTER TABLE lines_large
ADD CONSTRAINT lines_source_id_fkey FOREIGN KEY (source_id) REFERENCES sources (source_id);

--
-- Name: lines_source_id_fkey; Type: CONSTRAINT; Schema: -; Owner: -
--

ALTER TABLE lines_medium
ADD CONSTRAINT lines_source_id_fkey FOREIGN KEY (source_id) REFERENCES sources (source_id);

--
-- Name: lines_source_id_fkey; Type: CONSTRAINT; Schema: -; Owner: -
--

ALTER TABLE lines_small
ADD CONSTRAINT lines_source_id_fkey FOREIGN KEY (source_id) REFERENCES sources (source_id);

--
-- Name: lines_source_id_fkey; Type: CONSTRAINT; Schema: -; Owner: -
--

ALTER TABLE lines_tiny
ADD CONSTRAINT lines_source_id_fkey FOREIGN KEY (source_id) REFERENCES sources (source_id);

--
-- Name: polygons_source_id_fkey; Type: CONSTRAINT; Schema: -; Owner: -
--

ALTER TABLE polygons
ADD CONSTRAINT polygons_source_id_fkey FOREIGN KEY (source_id) REFERENCES sources (source_id);

--
-- Name: polygons_source_id_fkey; Type: CONSTRAINT; Schema: -; Owner: -
--

ALTER TABLE polygons_large
ADD CONSTRAINT polygons_source_id_fkey FOREIGN KEY (source_id) REFERENCES sources (source_id);

--
-- Name: polygons_source_id_fkey; Type: CONSTRAINT; Schema: -; Owner: -
--

ALTER TABLE polygons_medium
ADD CONSTRAINT polygons_source_id_fkey FOREIGN KEY (source_id) REFERENCES sources (source_id);

--
-- Name: polygons_source_id_fkey; Type: CONSTRAINT; Schema: -; Owner: -
--

ALTER TABLE polygons_small
ADD CONSTRAINT polygons_source_id_fkey FOREIGN KEY (source_id) REFERENCES sources (source_id);

--
-- Name: polygons_source_id_fkey; Type: CONSTRAINT; Schema: -; Owner: -
--

ALTER TABLE polygons_tiny
ADD CONSTRAINT polygons_source_id_fkey FOREIGN KEY (source_id) REFERENCES sources (source_id);

--
-- Name: ingest_process; Type: VIEW; Schema: -; Owner: -
--

CREATE OR REPLACE VIEW ingest_process AS
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

--
-- Name: large; Type: VIEW; Schema: -; Owner: -
--

CREATE OR REPLACE VIEW large AS
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
   FROM polygons_large;

--
-- Name: medium; Type: VIEW; Schema: -; Owner: -
--

CREATE OR REPLACE VIEW medium AS
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
   FROM polygons_medium;

--
-- Name: small; Type: VIEW; Schema: -; Owner: -
--

CREATE OR REPLACE VIEW small AS
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
   FROM polygons_small;

--
-- Name: sources_metadata; Type: VIEW; Schema: -; Owner: -
--

CREATE OR REPLACE VIEW sources_metadata AS
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
   FROM sources s
  ORDER BY s.source_id DESC;


COMMENT ON VIEW sources_metadata IS 'Convenience view for maps.sources with only metadata fields';

--
-- Name: tiny; Type: VIEW; Schema: -; Owner: -
--

CREATE OR REPLACE VIEW tiny AS
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
   FROM polygons_tiny;

--
-- Name: vw_legend_with_liths; Type: VIEW; Schema: -; Owner: -
--

CREATE OR REPLACE VIEW vw_legend_with_liths AS
 SELECT l.legend_id,
    l.source_id,
    l.name AS map_unit_name,
    array_agg(ll.lith_id) FILTER (WHERE ll.lith_id IS NOT NULL) AS lith_ids
   FROM legend l
     LEFT JOIN legend_liths ll ON ll.legend_id = l.legend_id
  GROUP BY l.legend_id, l.source_id, l.name;

