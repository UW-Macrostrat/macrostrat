--
-- TODO priviledges for roles
--
ALTER ROLE postgres INHERIT;
GRANT macrostrat TO postgres;


CREATE ROLE "macrostrat";

CREATE ROLE "postgrest";

CREATE ROLE "web_anon";

CREATE ROLE "web_user";

CREATE ROLE "macrostrat_admin";

GRANT macrostrat TO postgres;
GRANT web_user TO postgres;

GRANT CONNECT ON DATABASE macrostrat TO "rockd-reader";
GRANT USAGE ON SCHEMA macrostrat TO "rockd-reader";
GRANT USAGE ON SCHEMA public TO "rockd-reader";
GRANT USAGE ON SCHEMA topology TO "rockd-reader";

GRANT SELECT ON ALL TABLES IN SCHEMA macrostrat TO "rockd-reader";
GRANT SELECT ON ALL TABLES IN SCHEMA public TO "rockd-reader";
GRANT SELECT ON ALL TABLES IN SCHEMA topology TO "rockd-reader";

-- 1) Schema access
GRANT USAGE ON SCHEMA
  carto, carto_new, geologic_boundaries, hexgrids, lines,
  macrostrat, maps, points, sources, topology, public
TO macrostrat;

-- 2) Read all existing objects (tables/views + sequences)
GRANT SELECT ON ALL TABLES    IN SCHEMA
  carto, carto_new, geologic_boundaries, hexgrids, lines,
  macrostrat, maps, points, sources, topology, public
TO macrostrat;

GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA
  carto, carto_new, geologic_boundaries, hexgrids, lines,
  macrostrat, maps, points, sources, topology, public
TO macrostrat;

-- 3) Make future objects readable by default (run as each object-creating owner)
ALTER DEFAULT PRIVILEGES IN SCHEMA
  carto, carto_new, geologic_boundaries, hexgrids, lines,
  macrostrat, maps, points, sources, topology, public
GRANT SELECT ON TABLES TO macrostrat;

ALTER DEFAULT PRIVILEGES IN SCHEMA
  carto, carto_new, geologic_boundaries, hexgrids, lines,
  macrostrat, maps, points, sources, topology, public
GRANT USAGE, SELECT ON SEQUENCES TO macrostrat;

-- 4) Enums used in tables under public
GRANT USAGE ON TYPE
  public.measurement_class,
  public.measurement_class_new,
  public.measurement_type,
  public.measurement_type_new
TO macrostrat;

-- 5) Functions (your helper + PostGIS etc.) – safe & useful for read paths
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public, topology TO macrostrat;


--POSTGREST helper functions for RLS security
--Pull `"user_id"` out of the JWT that PostgREST stores in request.jwt.claims
CREATE OR REPLACE FUNCTION current_app_user_id()
RETURNS int
STABLE
LANGUAGE sql
AS $$
  SELECT (current_setting('request.jwt.claims', true)::json ->> 'user_id')::int;
$$;

CREATE OR REPLACE FUNCTION current_app_role()          -- returns text
RETURNS text
STABLE
LANGUAGE sql
AS $$
  SELECT (current_setting('request.jwt.claims', true)::json ->> 'role')::text;
$$;
