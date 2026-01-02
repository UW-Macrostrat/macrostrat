

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

CREATE SCHEMA public;
ALTER SCHEMA public OWNER TO pg_database_owner;

COMMENT ON SCHEMA public IS 'standard public schema';

CREATE TYPE public.saved_locations_enum AS ENUM (
    'Favorites',
    'Want to go',
    'Geological wonder'
);
ALTER TYPE public.saved_locations_enum OWNER TO macrostrat_admin;

CREATE TYPE public.schemeenum AS ENUM (
    'http',
    's3'
);
ALTER TYPE public.schemeenum OWNER TO macrostrat;

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
ALTER FUNCTION public.count_estimate(query text) OWNER TO macrostrat;

CREATE FUNCTION public.current_app_role() RETURNS text
    LANGUAGE sql STABLE
    AS $$
  SELECT (current_setting('request.jwt.claims', true)::json ->> 'role')::text;
$$;
ALTER FUNCTION public.current_app_role() OWNER TO macrostrat_admin;

CREATE FUNCTION public.current_app_user_id() RETURNS integer
    LANGUAGE sql STABLE
    AS $$
  SELECT (current_setting('request.jwt.claims', true)::json ->> 'user_id')::int;
$$;
ALTER FUNCTION public.current_app_user_id() OWNER TO macrostrat_admin;

CREATE FUNCTION public.group_items_by_type(name_filter text DEFAULT NULL::text) RETURNS json
    LANGUAGE plpgsql STABLE
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
ALTER FUNCTION public.group_items_by_type(name_filter text) OWNER TO macrostrat_admin;

CREATE FUNCTION public.update_updated_on() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    NEW.updated_on = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$;
ALTER FUNCTION public.update_updated_on() OWNER TO postgres;

CREATE AGGREGATE public.array_agg_mult(anycompatiblearray) (
    SFUNC = array_cat,
    STYPE = anycompatiblearray,
    INITCOND = '{}'
);
ALTER AGGREGATE public.array_agg_mult(anycompatiblearray) OWNER TO postgres;
SET default_tablespace = '';
SET default_table_access_method = heap;

CREATE TABLE public.export_table (
    source_id integer,
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
    web_geom public.geometry,
    new_priority integer,
    status_code text,
    slug text,
    raster_url text
);
ALTER TABLE public.export_table OWNER TO postgres;

CREATE SEQUENCE public.geologic_boundary_source_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
ALTER TABLE public.geologic_boundary_source_seq OWNER TO macrostrat;

CREATE TABLE public.impervious (
    rid integer NOT NULL,
    rast public.raster
);
ALTER TABLE public.impervious OWNER TO macrostrat;

CREATE SEQUENCE public.impervious_rid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
ALTER TABLE public.impervious_rid_seq OWNER TO macrostrat;

ALTER SEQUENCE public.impervious_rid_seq OWNED BY public.impervious.rid;

CREATE TABLE public.land (
    gid integer NOT NULL,
    scalerank numeric(10,0),
    featurecla character varying(32),
    geom public.geometry(MultiPolygon,4326)
);
ALTER TABLE public.land OWNER TO macrostrat;

CREATE SEQUENCE public.land_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
ALTER TABLE public.land_gid_seq OWNER TO macrostrat;

ALTER SEQUENCE public.land_gid_seq OWNED BY public.land.gid;

CREATE SEQUENCE public.line_ids
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
ALTER TABLE public.line_ids OWNER TO macrostrat;

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
ALTER TABLE public.lookup_large OWNER TO macrostrat;

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
ALTER TABLE public.lookup_medium OWNER TO macrostrat;

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
ALTER TABLE public.lookup_small OWNER TO macrostrat;

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

CREATE TABLE public.macrostrat_union (
    id integer NOT NULL,
    geom public.geometry
);
ALTER TABLE public.macrostrat_union OWNER TO macrostrat;

CREATE SEQUENCE public.macrostrat_union_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
ALTER TABLE public.macrostrat_union_id_seq OWNER TO macrostrat;

ALTER SEQUENCE public.macrostrat_union_id_seq OWNED BY public.macrostrat_union.id;

CREATE SEQUENCE public.map_ids
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
ALTER TABLE public.map_ids OWNER TO macrostrat;

CREATE TABLE public.next_id (
    id integer
);
ALTER TABLE public.next_id OWNER TO macrostrat_admin;

CREATE TABLE public.ref_boundaries (
    ref_id integer,
    ref text,
    geom public.geometry
);
ALTER TABLE public.ref_boundaries OWNER TO macrostrat;

CREATE FOREIGN TABLE public.srtm1 (
    rid integer,
    rast public.raster
)
SERVER elevation
OPTIONS (
    schema_name 'sources',
    table_name 'srtm1'
);
ALTER FOREIGN TABLE public.srtm1 OWNER TO macrostrat;

CREATE TABLE public.temp_names (
    strat_name_id integer,
    strat_name character varying(100),
    concept_id integer,
    rank_name character varying(100),
    bed_id integer,
    bed_name character varying(100),
    mbr_id integer,
    mbr_name character varying(100),
    fm_id integer,
    fm_name character varying(100),
    subgp_id integer,
    subgp_name character varying(100),
    gp_id integer,
    gp_name character varying(100),
    sgp_id integer,
    sgp_name character varying(100),
    early_age numeric(8,4),
    late_age numeric(8,4),
    gsc_lexicon character(15),
    parent integer,
    tree integer,
    t_units integer,
    b_period character varying(100),
    t_period character varying(100),
    name_no_lith character varying(100),
    ref_id integer,
    c_interval character varying(100),
    map_id integer,
    match_text text
);
ALTER TABLE public.temp_names OWNER TO macrostrat_admin;

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
ALTER TABLE public.temp_rocks OWNER TO macrostrat_admin;

CREATE TABLE public.units (
    mapunit text,
    description text
);
ALTER TABLE public.units OWNER TO macrostrat;

CREATE TABLE public.usage_stats (
    id integer NOT NULL,
    date timestamp with time zone DEFAULT now() NOT NULL,
    ip text NOT NULL,
    lat double precision NOT NULL,
    lng double precision NOT NULL
);
ALTER TABLE public.usage_stats OWNER TO macrostrat_admin;

CREATE SEQUENCE public.usage_stats_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
ALTER TABLE public.usage_stats_id_seq OWNER TO macrostrat_admin;

ALTER SEQUENCE public.usage_stats_id_seq OWNED BY public.usage_stats.id;

ALTER TABLE ONLY public.impervious ALTER COLUMN rid SET DEFAULT nextval('public.impervious_rid_seq'::regclass);

ALTER TABLE ONLY public.land ALTER COLUMN gid SET DEFAULT nextval('public.land_gid_seq'::regclass);

ALTER TABLE ONLY public.macrostrat_union ALTER COLUMN id SET DEFAULT nextval('public.macrostrat_union_id_seq'::regclass);

ALTER TABLE ONLY public.usage_stats ALTER COLUMN id SET DEFAULT nextval('public.usage_stats_id_seq'::regclass);

ALTER TABLE ONLY public.impervious
    ADD CONSTRAINT impervious_pkey PRIMARY KEY (rid);

ALTER TABLE ONLY public.land
    ADD CONSTRAINT land_pkey PRIMARY KEY (gid);

ALTER TABLE ONLY public.macrostrat_union
    ADD CONSTRAINT macrostrat_union_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.usage_stats
    ADD CONSTRAINT usage_stats_pkey PRIMARY KEY (id);

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

CREATE INDEX temp_names_name_no_lith_idx ON public.temp_names USING btree (name_no_lith);

CREATE INDEX temp_names_rank_name_idx ON public.temp_names USING btree (rank_name);

CREATE INDEX temp_names_strat_name_id_idx ON public.temp_names USING btree (strat_name_id);

CREATE INDEX temp_names_strat_name_idx ON public.temp_names USING btree (strat_name);

CREATE INDEX temp_rocks_b_interval_idx ON public.temp_rocks USING btree (b_interval);

CREATE INDEX temp_rocks_envelope_idx ON public.temp_rocks USING gist (envelope);

CREATE INDEX temp_rocks_strat_name_clean_idx ON public.temp_rocks USING btree (strat_name_clean);

CREATE INDEX temp_rocks_strat_name_idx ON public.temp_rocks USING btree (strat_name);

CREATE INDEX temp_rocks_t_interval_idx ON public.temp_rocks USING btree (t_interval);

GRANT ALL ON FUNCTION public.current_app_role() TO macrostrat;

GRANT ALL ON FUNCTION public.current_app_user_id() TO macrostrat;

GRANT ALL ON FUNCTION public.group_items_by_type(name_filter text) TO macrostrat;

GRANT ALL ON FUNCTION public.update_updated_on() TO macrostrat;

GRANT ALL ON FUNCTION public.array_agg_mult(anycompatiblearray) TO macrostrat;

/** Legacy: superseded by macrostrat.measurement_*
  ...but retained because other schemas (e.g., macrostrat_bak2) depend on it
  */
CREATE TYPE public.measurement_class AS ENUM (
  '',
  'geophysical',
  'geochemical',
  'sedimentological'
  );
ALTER TYPE public.measurement_class OWNER TO macrostrat_admin;
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
ALTER TYPE public.measurement_type OWNER TO macrostrat_admin;
