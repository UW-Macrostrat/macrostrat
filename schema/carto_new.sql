--
-- PostgreSQL database dump
--

-- Dumped from database version 15.15 (Debian 15.15-1.pgdg12+1)
-- Dumped by pg_dump version 15.8 (Debian 15.8-1.pgdg120+1)

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
-- Name: carto_new; Type: SCHEMA; Schema: -; Owner: macrostrat-admin
--

CREATE SCHEMA carto_new;


ALTER SCHEMA carto_new OWNER TO "macrostrat-admin";

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: hex_index; Type: TABLE; Schema: carto_new; Owner: macrostrat
--

CREATE TABLE carto_new.hex_index (
    map_id integer NOT NULL,
    scale text,
    hex_id integer
);


ALTER TABLE carto_new.hex_index OWNER TO macrostrat;

--
-- Name: large; Type: VIEW; Schema: carto_new; Owner: macrostrat-admin
--

CREATE VIEW carto_new.large AS
 SELECT polygons.map_id,
    polygons.source_id,
    polygons.geom,
    (polygons.geom_scale)::text AS scale
   FROM carto.polygons
  WHERE (polygons.scale = 'large'::maps.map_scale);


ALTER TABLE carto_new.large OWNER TO "macrostrat-admin";

--
-- Name: lines_large; Type: VIEW; Schema: carto_new; Owner: macrostrat
--

CREATE VIEW carto_new.lines_large AS
 SELECT lines.line_id,
    lines.source_id,
    lines.geom,
    (lines.geom_scale)::text AS scale
   FROM carto.lines
  WHERE (lines.scale = 'large'::maps.map_scale);


ALTER TABLE carto_new.lines_large OWNER TO macrostrat;

--
-- Name: lines_medium; Type: VIEW; Schema: carto_new; Owner: macrostrat
--

CREATE VIEW carto_new.lines_medium AS
 SELECT lines.line_id,
    lines.source_id,
    lines.geom,
    (lines.geom_scale)::text AS scale
   FROM carto.lines
  WHERE (lines.scale = 'medium'::maps.map_scale);


ALTER TABLE carto_new.lines_medium OWNER TO macrostrat;

--
-- Name: lines_small; Type: VIEW; Schema: carto_new; Owner: macrostrat
--

CREATE VIEW carto_new.lines_small AS
 SELECT lines.line_id,
    lines.source_id,
    lines.geom,
    (lines.geom_scale)::text AS scale
   FROM carto.lines
  WHERE (lines.scale = 'small'::maps.map_scale);


ALTER TABLE carto_new.lines_small OWNER TO macrostrat;

--
-- Name: lines_tiny; Type: VIEW; Schema: carto_new; Owner: macrostrat
--

CREATE VIEW carto_new.lines_tiny AS
 SELECT lines.line_id,
    lines.source_id,
    lines.geom,
    (lines.geom_scale)::text AS scale
   FROM carto.lines
  WHERE (lines.scale = 'tiny'::maps.map_scale);


ALTER TABLE carto_new.lines_tiny OWNER TO macrostrat;

--
-- Name: medium; Type: VIEW; Schema: carto_new; Owner: macrostrat-admin
--

CREATE VIEW carto_new.medium AS
 SELECT polygons.map_id,
    polygons.source_id,
    polygons.geom,
    (polygons.geom_scale)::text AS scale
   FROM carto.polygons
  WHERE (polygons.scale = 'medium'::maps.map_scale);


ALTER TABLE carto_new.medium OWNER TO "macrostrat-admin";

--
-- Name: pbdb_hex_index; Type: TABLE; Schema: carto_new; Owner: macrostrat
--

CREATE TABLE carto_new.pbdb_hex_index (
    collection_no integer NOT NULL,
    scale text,
    hex_id integer
);


ALTER TABLE carto_new.pbdb_hex_index OWNER TO macrostrat;

--
-- Name: small; Type: VIEW; Schema: carto_new; Owner: macrostrat-admin
--

CREATE VIEW carto_new.small AS
 SELECT polygons.map_id,
    polygons.source_id,
    polygons.geom,
    (polygons.geom_scale)::text AS scale
   FROM carto.polygons
  WHERE (polygons.scale = 'small'::maps.map_scale);


ALTER TABLE carto_new.small OWNER TO "macrostrat-admin";

--
-- Name: tiny; Type: VIEW; Schema: carto_new; Owner: macrostrat-admin
--

CREATE VIEW carto_new.tiny AS
 SELECT polygons.map_id,
    polygons.source_id,
    polygons.geom,
    (polygons.geom_scale)::text AS scale
   FROM carto.polygons
  WHERE (polygons.scale = 'tiny'::maps.map_scale);


ALTER TABLE carto_new.tiny OWNER TO "macrostrat-admin";

--
-- Name: hex_index_hex_id_idx; Type: INDEX; Schema: carto_new; Owner: macrostrat
--

CREATE INDEX hex_index_hex_id_idx ON carto_new.hex_index USING btree (hex_id);


--
-- Name: hex_index_map_id_idx; Type: INDEX; Schema: carto_new; Owner: macrostrat
--

CREATE INDEX hex_index_map_id_idx ON carto_new.hex_index USING btree (map_id);


--
-- Name: hex_index_scale_idx; Type: INDEX; Schema: carto_new; Owner: macrostrat
--

CREATE INDEX hex_index_scale_idx ON carto_new.hex_index USING btree (scale);


--
-- Name: pbdb_hex_index_collection_no_idx; Type: INDEX; Schema: carto_new; Owner: macrostrat
--

CREATE INDEX pbdb_hex_index_collection_no_idx ON carto_new.pbdb_hex_index USING btree (collection_no);


--
-- Name: pbdb_hex_index_hex_id_idx; Type: INDEX; Schema: carto_new; Owner: macrostrat
--

CREATE INDEX pbdb_hex_index_hex_id_idx ON carto_new.pbdb_hex_index USING btree (hex_id);


--
-- Name: pbdb_hex_index_scale_idx; Type: INDEX; Schema: carto_new; Owner: macrostrat
--

CREATE INDEX pbdb_hex_index_scale_idx ON carto_new.pbdb_hex_index USING btree (scale);


--
-- Name: TABLE large; Type: ACL; Schema: carto_new; Owner: macrostrat-admin
--

GRANT SELECT ON TABLE carto_new.large TO macrostrat;


--
-- Name: TABLE medium; Type: ACL; Schema: carto_new; Owner: macrostrat-admin
--

GRANT SELECT ON TABLE carto_new.medium TO macrostrat;


--
-- Name: TABLE small; Type: ACL; Schema: carto_new; Owner: macrostrat-admin
--

GRANT SELECT ON TABLE carto_new.small TO macrostrat;


--
-- Name: TABLE tiny; Type: ACL; Schema: carto_new; Owner: macrostrat-admin
--

GRANT SELECT ON TABLE carto_new.tiny TO macrostrat;


--
-- Name: DEFAULT PRIVILEGES FOR SEQUENCES; Type: DEFAULT ACL; Schema: carto_new; Owner: macrostrat-admin
--

ALTER DEFAULT PRIVILEGES FOR ROLE "macrostrat-admin" IN SCHEMA carto_new GRANT SELECT,USAGE ON SEQUENCES  TO macrostrat;


--
-- Name: DEFAULT PRIVILEGES FOR TABLES; Type: DEFAULT ACL; Schema: carto_new; Owner: macrostrat-admin
--

ALTER DEFAULT PRIVILEGES FOR ROLE "macrostrat-admin" IN SCHEMA carto_new GRANT SELECT ON TABLES  TO macrostrat;


--
-- PostgreSQL database dump complete
--

