
/** The Postgres Operator can only create roles with dashes, not underscores.
    We try to inherit important roles here. **/

CREATE ROLE macrostrat_admin;
GRANT macrostrat_admin TO "macrostrat-admin";
GRANT "macrostrat-admin" TO macrostrat_admin;

CREATE ROLE macrostrat;

-- Roles for auth/PostgREST system
CREATE ROLE postgrest;
CREATE ROLE web_admin;
CREATE ROLE web_user;
CREATE ROLE web_anon;

GRANT web_admin TO macrostrat_admin;
GRANT macrostrat TO postgres;
GRANT web_user TO postgres;

-- Role for read-only access from Rockd
CREATE ROLE rockd_reader;
GRANT rockd_reader TO "rockd-reader";
GRANT "rockd-reader" TO rockd_reader;

CREATE ROLE xdd_writer;
GRANT xdd_writer TO "xdd-writer";
GRANT "xdd-writer" TO xdd_writer;
