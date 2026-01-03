-- General options modified from PGDump outputs
SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', 'public', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

CREATE EXTENSION IF NOT EXISTS postgis WITH SCHEMA public;
CREATE EXTENSION IF NOT EXISTS pg_stat_statements WITH SCHEMA public;
CREATE EXTENSION IF NOT EXISTS pgaudit WITH SCHEMA public;
CREATE EXTENSION IF NOT EXISTS postgis WITH SCHEMA public;
CREATE EXTENSION IF NOT EXISTS postgis_raster WITH SCHEMA public;
CREATE EXTENSION IF NOT EXISTS postgis_topology WITH SCHEMA topology;
CREATE EXTENSION IF NOT EXISTS postgres_fdw WITH SCHEMA public;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp" WITH SCHEMA public;
