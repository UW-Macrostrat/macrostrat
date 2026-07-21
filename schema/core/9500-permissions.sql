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
  topology, public
  TO macrostrat;

GRANT SELECT ON ALL TABLES IN SCHEMA topology TO macrostrat;

-- xDD writer role
GRANT USAGE ON SCHEMA maps TO xdd_writer;
GRANT SELECT ON ALL TABLES IN SCHEMA maps TO xdd_writer;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA maps TO xdd_writer;
ALTER DEFAULT PRIVILEGES FOR ROLE macrostrat IN SCHEMA maps GRANT SELECT ON TABLES TO xdd_writer;

/** PostgREST helper functions */
GRANT USAGE ON SCHEMA macrostrat TO web_anon;
GRANT SELECT ON ALL TABLES IN SCHEMA macrostrat TO web_anon;

-- (The RLS helper functions public.current_app_user_id() / public.current_app_role()
--  are defined as structure in 0001-public.sql; this file is authorization only.)

