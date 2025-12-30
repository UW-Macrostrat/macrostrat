--
-- PostgreSQL database dump
--

-- Dumped from database version 15.15 (Debian 15.15-1.pgdg12+1)
-- Dumped by pg_dump version 15.13 (Debian 15.13-1.pgdg120+1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: lines; Type: SCHEMA; Schema: -; Owner: macrostrat
--

CREATE SCHEMA lines;


ALTER SCHEMA lines OWNER TO macrostrat;

--
-- Name: large; Type: VIEW; Schema: lines; Owner: macrostrat_admin
--

CREATE VIEW lines.large AS
 SELECT lines.line_id,
    lines.orig_id,
    lines.source_id,
    lines.name,
    lines.type_legacy AS type,
    lines.direction_legacy AS direction,
    lines.descrip,
    lines.geom,
    lines.type AS new_type,
    lines.direction AS new_direction
   FROM maps.lines
  WHERE (lines.scale = 'large'::maps.map_scale);


ALTER TABLE lines.large OWNER TO macrostrat_admin;

--
-- Name: medium; Type: VIEW; Schema: lines; Owner: macrostrat_admin
--

CREATE VIEW lines.medium AS
 SELECT lines.line_id,
    lines.orig_id,
    lines.source_id,
    lines.name,
    lines.type_legacy AS type,
    lines.direction_legacy AS direction,
    lines.descrip,
    lines.geom,
    lines.type AS new_type,
    lines.direction AS new_direction
   FROM maps.lines
  WHERE (lines.scale = 'medium'::maps.map_scale);


ALTER TABLE lines.medium OWNER TO macrostrat_admin;

--
-- Name: small; Type: VIEW; Schema: lines; Owner: macrostrat_admin
--

CREATE VIEW lines.small AS
 SELECT lines.line_id,
    lines.orig_id,
    lines.source_id,
    lines.name,
    lines.type_legacy AS type,
    lines.direction_legacy AS direction,
    lines.descrip,
    lines.geom,
    lines.type AS new_type,
    lines.direction AS new_direction
   FROM maps.lines
  WHERE (lines.scale = 'small'::maps.map_scale);


ALTER TABLE lines.small OWNER TO macrostrat_admin;

--
-- Name: tiny; Type: VIEW; Schema: lines; Owner: macrostrat_admin
--

CREATE VIEW lines.tiny AS
 SELECT lines.line_id,
    lines.orig_id,
    lines.source_id,
    lines.name,
    lines.type_legacy AS type,
    lines.direction_legacy AS direction,
    lines.descrip,
    lines.geom,
    lines.type AS new_type,
    lines.direction AS new_direction
   FROM maps.lines
  WHERE (lines.scale = 'tiny'::maps.map_scale);


ALTER TABLE lines.tiny OWNER TO macrostrat_admin;

--
-- Name: DEFAULT PRIVILEGES FOR SEQUENCES; Type: DEFAULT ACL; Schema: lines; Owner: macrostrat-admin
--

ALTER DEFAULT PRIVILEGES FOR ROLE "macrostrat-admin" IN SCHEMA lines GRANT SELECT,USAGE ON SEQUENCES  TO macrostrat;


--
-- Name: DEFAULT PRIVILEGES FOR TABLES; Type: DEFAULT ACL; Schema: lines; Owner: macrostrat-admin
--

ALTER DEFAULT PRIVILEGES FOR ROLE "macrostrat-admin" IN SCHEMA lines GRANT SELECT ON TABLES  TO macrostrat;


--
-- PostgreSQL database dump complete
--

