--granting read only access for the rockd api to read macrostrat.public
ALTER TABLE public.lookup_tiny OWNER TO postgres;
GRANT USAGE ON SCHEMA public TO "rockd-reader";
GRANT SELECT ON ALL TABLES IN SCHEMA public TO "rockd-reader";
ALTER DEFAULT PRIVILEGES IN SCHEMA public
GRANT SELECT ON TABLES TO "rockd-reader";

--granting all permissions to the rockd user.
--TODO determine if we need to revoke macrostrat-admin access. They have read/write access to the rockd db too.
ALTER DEFAULT PRIVILEGES IN SCHEMA public
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO rockd;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO rockd;

--if we need to update permissions for all tables run query below
--GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO rockd;
--GRANT USAGE, SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA public TO rockd;

