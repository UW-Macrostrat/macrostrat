-- copied straight from the Postgrest config
CREATE ROLE postgrest LOGIN NOINHERIT NOCREATEDB NOCREATEROLE NOSUPERUSER;

-- For someone who is not logged in
CREATE ROLE web_anon NOLOGIN;

-- For a general logged-in user
CREATE ROLE web_user NOLOGIN;

-- For a Macrostrat administrator
CREATE ROLE web_admin NOLOGIN;

CREATE ROLE web_anon NOLOGIN;

-- Postgrest is our 'authenticator' role
-- We need to allow it to switch to the web roles
GRANT web_anon TO postgrest;
GRANT web_user TO postgrest;
GRANT web_admin TO postgrest;

GRANT USAGE ON SCHEMA macrostrat TO web_anon;
GRANT SELECT ON ALL TABLES IN SCHEMA macrostrat TO web_anon;

-- Grant web_anon capabilities to web_user
GRANT web_anon TO web_user;

-- Grant web_user capabilities to web_admin
GRANT web_user TO web_admin;


--POSTGREST helper functions for RLS security
--Pull `"user_id"` out of the JWT that PostgREST stores in request.jwt.claims
CREATE OR REPLACE FUNCTION current_app_user_id()
RETURNS int
STABLE
LANGUAGE sql
AS $$
  SELECT (current_setting('request.jwt.claims', true)::json ->> 'user_id')::int
$$;

