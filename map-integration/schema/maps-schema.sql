CREATE EXTENSION IF NOT EXISTS postgis;
CREATE SCHEMA maps;

CREATE FUNCTION maps.lines_geom_is_valid(geom public.geometry) RETURNS boolean
    LANGUAGE sql IMMUTABLE
    AS $$
  SELECT ST_IsValid(geom) AND ST_GeometryType(geom) IN ('ST_LineString', 'ST_MultiLineString');
$$;

CREATE FUNCTION maps.polygons_geom_is_valid(geom public.geometry) RETURNS boolean
    LANGUAGE sql IMMUTABLE
    AS $$
  SELECT ST_IsValid(geom) AND ST_GeometryType(geom) IN ('ST_Polygon', 'ST_MultiPolygon');
$$;

CREATE TYPE maps.map_scale AS ENUM (
    'tiny',
    'small',
    'medium',
    'large'
);

CREATE TABLE maps.sources (
    source_id serial PRIMARY KEY,
    name character varying(255),
    url character varying(255),
    ref_title text,
    authors character varying(255),
    ref_year text,
    ref_source character varying(255),
    isbn_doi character varying(100),
    scale character varying(20),
    license character varying(100),
    features integer,
    area integer,
    rgeom public.geometry,
    display_scales text[],
    web_geom public.geometry,
    priority integer DEFAULT 0,
    status_code text DEFAULT 'active'::text,
    slug text UNIQUE NOT NULL,
    raster_url text
);

CREATE TABLE maps.polygons (
    map_id serial PRIMARY KEY,
    source_id integer NOT NULL REFERENCES maps.sources(source_id),
    scale maps.map_scale NOT NULL,
    orig_id integer,
    name text,
    strat_name text,
    age character varying(255),
    lith text,
    descrip text,
    comments text,
    t_interval integer,
    b_interval integer,
    geom public.geometry(Geometry,4326) NOT NULL,
    CONSTRAINT maps_polygons_geom_check CHECK (maps.polygons_geom_is_valid(geom))
);

CREATE TABLE maps.lines (
    line_id serial PRIMARY KEY,
    source_id integer NOT NULL REFERENCES maps.sources(source_id),
    orig_id integer,
    name character varying(255),
    type_legacy character varying(100),
    direction_legacy character varying(40),
    descrip text,
    geom geometry(Geometry,4326) NOT NULL,
    type character varying(100),
    direction character varying(40),
    scale maps.map_scale NOT NULL,
    CONSTRAINT maps_lines_geom_check CHECK (maps.lines_geom_is_valid(geom))
);

CREATE TABLE maps.points (
    point_id serial PRIMARY KEY,
    source_id integer NOT NULL REFERENCES maps.sources(source_id),
    strike integer,
    dip integer,
    dip_dir integer,
    point_type character varying(100),
    certainty character varying(100),
    comments text,
    geom public.geometry(Geometry,4326),
    orig_id integer,
    CONSTRAINT dip_lt_90 CHECK ((dip <= 90)),
    CONSTRAINT dip_positive CHECK ((dip >= 0)),
    CONSTRAINT direction_lt_360 CHECK ((dip_dir <= 360)),
    CONSTRAINT direction_positive CHECK ((dip_dir >= 0)),
    CONSTRAINT enforce_point_geom CHECK (public.st_isvalid(geom)),
    CONSTRAINT strike_lt_360 CHECK ((strike <= 360)),
    CONSTRAINT strike_positive CHECK ((strike >= 0))
);

CREATE TABLE maps.legend (
    legend_id serial PRIMARY KEY,
    source_id integer NOT NULL REFERENCES maps.sources(source_id),
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
    -- Macrostrat data links (synthesized by scripts)
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

-- Used for linking Macrostrat lexicon to map data  

CREATE TABLE maps.legend_liths (
    legend_id integer NOT NULL REFERENCES maps.legend(legend_id) ON DELETE CASCADE,
    lith_id integer NOT NULL, -- Refers to Macrostrat lexicon (not keyed for now)
    basis_col text NOT NULL,
    UNIQUE (legend_id, lith_id, basis_col)
);

CREATE TABLE maps.manual_matches (
    match_id serial PRIMARY KEY,
    map_id integer NOT NULL REFERENCES maps.polygons(map_id),
    strat_name_id integer,  -- Refers to Macrostrat lexicon (not keyed for now)
    unit_id integer,
    addition boolean DEFAULT false,
    removal boolean DEFAULT false,
    type character varying(20)
);

CREATE TABLE maps.map_legend (
    legend_id integer REFERENCES maps.legend(legend_id) ON DELETE CASCADE,
    map_id integer REFERENCES maps.polygons(map_id) ON DELETE CASCADE,
    PRIMARY KEY (legend_id, map_id)
);

CREATE TABLE maps.map_liths (
    map_id integer REFERENCES maps.polygons(map_id) ON DELETE CASCADE,
    lith_id integer NOT NULL,
    basis_col character varying(50),
    PRIMARY KEY (map_id, lith_id)
);

CREATE TABLE maps.map_strat_names (
    map_id integer NOT NULL REFERENCES maps.polygons(map_id) ON DELETE CASCADE,
    strat_name_id integer NOT NULL,
    basis_col character varying(50),
    PRIMARY KEY (map_id, strat_name_id, basis_col)
);

CREATE TABLE maps.map_units (
    map_id integer NOT NULL REFERENCES maps.polygons(map_id) ON DELETE CASCADE,
    unit_id integer NOT NULL,
    basis_col character varying(50),
    PRIMARY KEY (map_id, unit_id, basis_col)
);

-- Map indexes
CREATE INDEX polygons_b_interval_idx ON ONLY maps.polygons USING btree (b_interval);
CREATE INDEX polygons_geom_idx ON ONLY maps.polygons USING gist (geom);
CREATE INDEX polygons_name_idx ON ONLY maps.polygons USING btree (name);
CREATE INDEX polygons_orig_id_idx ON ONLY maps.polygons USING btree (orig_id);
CREATE INDEX polygons_source_id_idx ON ONLY maps.polygons USING btree (source_id);
CREATE INDEX polygons_t_interval_idx ON ONLY maps.polygons USING btree (t_interval);

CREATE INDEX lines_geom_idx ON ONLY maps.lines USING gist (geom);
CREATE INDEX lines_line_id_idx ON ONLY maps.lines USING btree (line_id);
CREATE INDEX lines_orig_id_idx ON ONLY maps.lines USING btree (orig_id);

CREATE INDEX points_geom_idx ON maps.points USING gist (geom);
CREATE INDEX points_source_id_idx ON maps.points USING btree (source_id);

-- Legend indexes
CREATE INDEX legend_source_id_idx ON maps.legend USING btree (source_id);

CREATE INDEX legend_liths_legend_id_idx ON maps.legend_liths USING btree (legend_id);
CREATE INDEX legend_liths_lith_id_idx ON maps.legend_liths USING btree (lith_id);

-- Macrostrat link indexes
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

CREATE INDEX sources_rgeom_idx ON maps.sources USING gist (rgeom);
CREATE INDEX sources_web_geom_idx ON maps.sources USING gist (web_geom);
