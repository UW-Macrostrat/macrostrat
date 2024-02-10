-- copied straight from the Postgrest config
CREATE ROLE postgrest LOGIN NOINHERIT NOCREATEDB NOCREATEROLE NOSUPERUSER;
-- CREATE ROLE anonymous NOLOGIN;
CREATE ROLE web_anon NOLOGIN;
CREATE ROLE web_user NOLOGIN;

-- Postgrest is our 'authenticator' role
GRANT web_anon TO postgrest;
GRANT web_user TO postgrest;

GRANT USAGE ON SCHEMA macrostrat_api TO web_anon;
GRANT USAGE ON SCHEMA macrostrat_api TO web_user;
GRANT SELECT ON ALL TABLES IN SCHEMA macrostrat_api TO web_anon;
GRANT SELECT ON ALL TABLES IN SCHEMA macrostrat_api TO web_user;