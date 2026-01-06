--granting read only access for the rockd api to read macrostrat.public
--ALTER ROLE rockd WITH SUPERUSER;

--/opt/homebrew/bin/pg_restore --dbname=rockd --clean --username=rockd --host=db.development.svc.macrostrat.org --port=5432 /Users/afromandi/Macrostrat/Pgdump/2025-08-11T00:00:10.rockd.pg_dump


DO
$$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'rockd') THEN
        CREATE ROLE rockd NOLOGIN ;
    END IF;

    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'rockd-reader') THEN
        CREATE ROLE "rockd-reader" NOLOGIN ;
    END IF;
END
$$;

ALTER DATABASE rockd OWNER TO rockd;
ALTER SCHEMA public OWNER TO rockd;
ALTER SCHEMA modules OWNER TO rockd;

--REASSIGN OWNED BY "macrostrat-admin" TO rockd;
GRANT CREATE ON DATABASE rockd TO rockd;
GRANT CREATE ON SCHEMA public TO rockd;

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
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO rockd;
GRANT USAGE, SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA public TO rockd;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA modules TO rockd;
GRANT USAGE, SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA modules TO rockd;


--permission denied for schema macrostrat

