/*
Create read-only user for Macrostrat databases
*/

CREATE USER macrostrat_read WITH PASSWORD '<redacted>';
GRANT CONNECT ON DATABASE burwell TO macrostrat_read;

GRANT USAGE ON SCHEMA macrostrat TO macrostrat_read;
GRANT SELECT ON ALL TABLES IN SCHEMA macrostrat TO macrostrat_read;

GRANT USAGE ON SCHEMA maps TO macrostrat_read;
GRANT SELECT ON ALL TABLES IN SCHEMA maps TO macrostrat_read;

GRANT USAGE ON SCHEMA public TO macrostrat_read;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO macrostrat_read;

GRANT USAGE ON SCHEMA carto_new TO macrostrat_read;
GRANT SELECT ON ALL TABLES IN SCHEMA carto_new TO macrostrat_read;

GRANT USAGE ON SCHEMA lines TO macrostrat_read;
GRANT SELECT ON ALL TABLES IN SCHEMA lines TO macrostrat_read;

--- API Schemas --
CREATE ROLE web_anon nologin;

GRANT USAGE ON SCHEMA weaver_api to web_anon;
GRANT SELECT ON ALL TABLES IN SCHEMA weaver_api TO web_anon;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA weaver_api TO web_anon;

GRANT USAGE ON SCHEMA macrostrat_api to web_anon;
GRANT SELECT ON ALL TABLES IN SCHEMA macrostrat_api TO web_anon;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA macrostrat_api TO web_anon;

GRANT web_anon TO postgres;