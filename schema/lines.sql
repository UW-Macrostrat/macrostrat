--
-- pgschema database dump
--

-- Dumped from database version PostgreSQL 15.15
-- Dumped by pgschema version 1.5.1


--
-- Name: large; Type: VIEW; Schema: -; Owner: -
--

CREATE OR REPLACE VIEW large AS
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
  WHERE lines.scale = 'large'::maps.map_scale;

--
-- Name: medium; Type: VIEW; Schema: -; Owner: -
--

CREATE OR REPLACE VIEW medium AS
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
  WHERE lines.scale = 'medium'::maps.map_scale;

--
-- Name: small; Type: VIEW; Schema: -; Owner: -
--

CREATE OR REPLACE VIEW small AS
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
  WHERE lines.scale = 'small'::maps.map_scale;

--
-- Name: tiny; Type: VIEW; Schema: -; Owner: -
--

CREATE OR REPLACE VIEW tiny AS
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
  WHERE lines.scale = 'tiny'::maps.map_scale;

