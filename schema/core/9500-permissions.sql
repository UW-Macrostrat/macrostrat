--
-- TODO priviledges for roles
--

GRANT CONNECT ON DATABASE macrostrat TO rockd_reader;
GRANT USAGE ON SCHEMA macrostrat TO rockd_reader;
GRANT USAGE ON SCHEMA public TO rockd_reader;
GRANT USAGE ON SCHEMA topology TO rockd_reader;

GRANT SELECT ON ALL TABLES IN SCHEMA macrostrat TO rockd_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO rockd_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA topology TO rockd_reader;

GRANT USAGE ON SCHEMA
  carto, carto_new, geologic_boundaries, hexgrids, lines,
  macrostrat, maps, points, sources, topology, public
  TO macrostrat;

GRANT SELECT ON ALL TABLES IN SCHEMA
  carto, carto_new, geologic_boundaries, hexgrids, lines,
  macrostrat, maps, points, sources, topology, public
  TO macrostrat;

GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA
  carto, carto_new, geologic_boundaries, hexgrids, lines,
  macrostrat, maps, points, sources, topology, public
  TO macrostrat;

ALTER DEFAULT PRIVILEGES IN SCHEMA
  carto, carto_new, geologic_boundaries, hexgrids, lines,
  macrostrat, maps, points, sources, topology, public
  GRANT SELECT ON TABLES TO macrostrat;

ALTER DEFAULT PRIVILEGES IN SCHEMA
  carto, carto_new, geologic_boundaries, hexgrids, lines,
  macrostrat, maps, points, sources, topology, public
  GRANT USAGE, SELECT ON SEQUENCES TO macrostrat;

GRANT USAGE ON SCHEMA macrostrat TO "macrostrat";
GRANT CREATE ON SCHEMA macrostrat TO "macrostrat";
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA macrostrat TO "macrostrat";
GRANT USAGE ON ALL SEQUENCES IN SCHEMA macrostrat TO "macrostrat";

GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public, topology TO macrostrat;

-- This is mostly here to ensure idempoence of replaying all GRANT statements
GRANT SELECT ON ALL TABLES IN SCHEMA public TO macrostrat;

-- xDD writer role
GRANT USAGE ON SCHEMA maps TO xdd_writer;
GRANT SELECT ON ALL TABLES IN SCHEMA maps TO xdd_writer;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA maps TO xdd_writer;
ALTER DEFAULT PRIVILEGES IN SCHEMA maps GRANT SELECT ON TABLES TO xdd_writer;

/** PostgREST helper functions */
GRANT USAGE ON SCHEMA macrostrat TO web_anon;
GRANT SELECT ON ALL TABLES IN SCHEMA macrostrat TO web_anon;

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

--tileserver permissions
GRANT USAGE ON SCHEMA tile_cache TO macrostrat;
GRANT SELECT ON TABLE tile_cache.tile TO macrostrat;
GRANT INSERT, UPDATE ON TABLE tile_cache.tile TO macrostrat;
ALTER DEFAULT PRIVILEGES IN SCHEMA tile_cache
GRANT SELECT ON TABLES TO macrostrat;

