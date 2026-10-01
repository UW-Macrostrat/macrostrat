
CREATE SCHEMA public;
ALTER SCHEMA public OWNER TO pg_database_owner;

COMMENT ON SCHEMA public IS 'standard public schema';

CREATE TYPE public.saved_locations_enum AS ENUM (
    'Favorites',
    'Want to go',
    'Geological wonder'
);
ALTER TYPE public.saved_locations_enum OWNER TO macrostrat;

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
ALTER FUNCTION public.current_app_role() OWNER TO macrostrat;

-- Derive the integer user id from the JWT `sub` (ORCID) claim. The access token
-- no longer carries a `user_id` claim (refactor-jwt), so we look the id up from
-- macrostrat_auth."user".sub
SET check_function_bodies = off;
CREATE OR REPLACE FUNCTION public.current_app_user_id() RETURNS integer
    LANGUAGE sql STABLE SECURITY DEFINER
    SET search_path = pg_catalog
    AS $$
  SELECT id
  FROM macrostrat_auth."user"
  WHERE sub = current_setting('request.jwt.claims', true)::json ->> 'sub';
$$;
SET check_function_bodies = on;
ALTER FUNCTION public.current_app_user_id() OWNER TO macrostrat;
GRANT EXECUTE ON FUNCTION public.current_app_user_id() TO web_anon, web_user, web_admin;

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

CREATE SEQUENCE public.geologic_boundary_source_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
ALTER TABLE public.geologic_boundary_source_seq OWNER TO macrostrat;

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

CREATE TABLE public.next_id (
    id integer
);
ALTER TABLE public.next_id OWNER TO macrostrat;

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
ALTER TABLE public.usage_stats OWNER TO macrostrat;

CREATE SEQUENCE public.usage_stats_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
ALTER TABLE public.usage_stats_id_seq OWNER TO macrostrat;

ALTER SEQUENCE public.usage_stats_id_seq OWNED BY public.usage_stats.id;

ALTER TABLE ONLY public.land ALTER COLUMN gid SET DEFAULT nextval('public.land_gid_seq'::regclass);

ALTER TABLE ONLY public.macrostrat_union ALTER COLUMN id SET DEFAULT nextval('public.macrostrat_union_id_seq'::regclass);

ALTER TABLE ONLY public.usage_stats ALTER COLUMN id SET DEFAULT nextval('public.usage_stats_id_seq'::regclass);

ALTER TABLE ONLY public.land
    ADD CONSTRAINT land_pkey PRIMARY KEY (gid);

ALTER TABLE ONLY public.macrostrat_union
    ADD CONSTRAINT macrostrat_union_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.usage_stats
    ADD CONSTRAINT usage_stats_pkey PRIMARY KEY (id);

CREATE INDEX land_geom_idx ON public.land USING gist (geom);

GRANT ALL ON FUNCTION public.current_app_role() TO macrostrat;

GRANT ALL ON FUNCTION public.current_app_user_id() TO macrostrat;

GRANT ALL ON FUNCTION public.update_updated_on() TO macrostrat;

GRANT ALL ON FUNCTION public.array_agg_mult(anycompatiblearray) TO macrostrat;

-- Allow further view creation in the public schema
GRANT USAGE, CREATE ON SCHEMA public TO macrostrat;
