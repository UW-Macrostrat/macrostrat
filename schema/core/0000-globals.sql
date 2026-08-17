-- General options modified from PGDump outputs
SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

CREATE EXTENSION IF NOT EXISTS postgis WITH SCHEMA public;
CREATE EXTENSION IF NOT EXISTS pg_stat_statements WITH SCHEMA public;
CREATE EXTENSION IF NOT EXISTS pgaudit WITH SCHEMA public;
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_raster;
CREATE EXTENSION IF NOT EXISTS postgis_topology;
CREATE EXTENSION IF NOT EXISTS postgres_fdw WITH SCHEMA public;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS vector;
-- H3 hexagonal geospatial index, used by the usage_stats grids. h3_postgis
-- bridges it to PostGIS geometry and depends on postgis + postgis_raster, both
-- created above. Requires the h3 build in base-images/database/Dockerfile --
-- a database whose image predates that will fail here.
CREATE EXTENSION IF NOT EXISTS h3;
CREATE EXTENSION IF NOT EXISTS h3_postgis;

SET search_path TO public, topology, pg_catalog;

SELECT pg_catalog.set_config('search_path', 'public, topology, pg_catalog', false);
