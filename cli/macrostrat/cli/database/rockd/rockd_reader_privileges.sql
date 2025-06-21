--granting read only access for the rockd api to read macrostrat.public
ALTER TABLE public.lookup_tiny OWNER TO postgres;
GRANT USAGE ON SCHEMA public TO "rockd-reader";
GRANT SELECT ON ALL TABLES IN SCHEMA public TO "rockd-reader";
ALTER DEFAULT PRIVILEGES IN SCHEMA public
GRANT SELECT ON TABLES TO "rockd-reader";