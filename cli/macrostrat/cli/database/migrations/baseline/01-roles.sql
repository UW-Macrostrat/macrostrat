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
