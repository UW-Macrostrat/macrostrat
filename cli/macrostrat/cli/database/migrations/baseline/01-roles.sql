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
