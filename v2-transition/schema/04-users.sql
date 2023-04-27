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

