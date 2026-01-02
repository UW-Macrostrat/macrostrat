
/** The Postgres Operator can only create roles with dashes, not underscores.
    We try to inherit important roles here. **/

CREATE ROLE macrostrat_admin;
GRANT macrostrat_admin TO "macrostrat-admin";
GRANT "macrostrat-admin" TO macrostrat_admin;

CREATE ROLE macrostrat;

-- Roles for auth/PostgREST system
CREATE ROLE web_admin;
CREATE ROLE web_user;
CREATE ROLE web_anon;
