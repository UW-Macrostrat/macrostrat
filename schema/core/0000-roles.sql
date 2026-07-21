
/** The Postgres Operator can only create roles with dashes, not underscores.
    We try to shadow important roles here. **/

CREATE ROLE macrostrat_admin;
GRANT macrostrat_admin TO "macrostrat-admin";

CREATE ROLE macrostrat;

-- The declarative build applies each subsystem as its owning role (SET ROLE), so
-- objects are born owned rather than re-owned with ALTER … OWNER TO. That needs:
--   1. the connector to be able to SET ROLE macrostrat — superusers already can;
--      this covers a non-superuser connector (it connects via macrostrat_admin).
GRANT macrostrat TO macrostrat_admin;
--   2. macrostrat to create (and thereby own) its own schemas in whatever database
--      it is applied to. current_database() can't appear in a plain GRANT, so wrap it.
DO $$ BEGIN
  EXECUTE format('GRANT CREATE ON DATABASE %I TO macrostrat', current_database());
END $$;

-- Role for read-only access from Rockd
CREATE ROLE rockd_reader;
GRANT rockd_reader TO "rockd-reader";

CREATE ROLE xdd_writer;
GRANT xdd_writer TO "xdd-writer";

-- Roles for auth/Postgrest system Macrostrat API
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

-- Grant web_anon capabilities to web_user
GRANT web_anon TO web_user;

-- Grant web_user capabilities to web_admin
GRANT web_user TO web_admin;


GRANT REFERENCES ON spatial_ref_sys TO macrostrat;
