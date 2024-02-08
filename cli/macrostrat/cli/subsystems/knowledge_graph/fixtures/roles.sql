-- copied straight from the Postgrest config
--CREATE ROLE authenticator LOGIN NOINHERIT NOCREATEDB NOCREATEROLE NOSUPERUSER;
-- CREATE ROLE anonymous NOLOGIN;
CREATE ROLE web_anon NOLOGIN;

-- Postgrest is our 'authenticator' role
GRANT web_anon TO postgrest;
