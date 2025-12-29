--
-- pgschema database dump
--

-- Dumped from database version PostgreSQL 15.15
-- Dumped by pgschema version 1.5.1


--
-- Name: hex_index; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS hex_index (
    map_id integer NOT NULL,
    scale text,
    hex_id integer
);

--
-- Name: hex_index_hex_id_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS hex_index_hex_id_idx ON hex_index (hex_id);

--
-- Name: hex_index_map_id_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS hex_index_map_id_idx ON hex_index (map_id);

--
-- Name: hex_index_scale_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS hex_index_scale_idx ON hex_index (scale);

--
-- Name: pbdb_hex_index; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS pbdb_hex_index (
    collection_no integer NOT NULL,
    scale text,
    hex_id integer
);

--
-- Name: pbdb_hex_index_collection_no_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS pbdb_hex_index_collection_no_idx ON pbdb_hex_index (collection_no);

--
-- Name: pbdb_hex_index_hex_id_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS pbdb_hex_index_hex_id_idx ON pbdb_hex_index (hex_id);

--
-- Name: pbdb_hex_index_scale_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS pbdb_hex_index_scale_idx ON pbdb_hex_index (scale);

--
-- Name: large; Type: VIEW; Schema: -; Owner: -
--

CREATE OR REPLACE VIEW large AS
 SELECT polygons.map_id,
    polygons.source_id,
    polygons.geom,
    polygons.geom_scale::text AS scale
   FROM carto.polygons
  WHERE polygons.scale = 'large'::maps.map_scale;

--
-- Name: lines_large; Type: VIEW; Schema: -; Owner: -
--

CREATE OR REPLACE VIEW lines_large AS
 SELECT lines.line_id,
    lines.source_id,
    lines.geom,
    lines.geom_scale::text AS scale
   FROM carto.lines
  WHERE lines.scale = 'large'::maps.map_scale;

--
-- Name: medium; Type: VIEW; Schema: -; Owner: -
--

CREATE OR REPLACE VIEW medium AS
 SELECT polygons.map_id,
    polygons.source_id,
    polygons.geom,
    polygons.geom_scale::text AS scale
   FROM carto.polygons
  WHERE polygons.scale = 'medium'::maps.map_scale;

--
-- Name: lines_medium; Type: VIEW; Schema: -; Owner: -
--

CREATE OR REPLACE VIEW lines_medium AS
 SELECT lines.line_id,
    lines.source_id,
    lines.geom,
    lines.geom_scale::text AS scale
   FROM carto.lines
  WHERE lines.scale = 'medium'::maps.map_scale;

--
-- Name: small; Type: VIEW; Schema: -; Owner: -
--

CREATE OR REPLACE VIEW small AS
 SELECT polygons.map_id,
    polygons.source_id,
    polygons.geom,
    polygons.geom_scale::text AS scale
   FROM carto.polygons
  WHERE polygons.scale = 'small'::maps.map_scale;

--
-- Name: lines_small; Type: VIEW; Schema: -; Owner: -
--

CREATE OR REPLACE VIEW lines_small AS
 SELECT lines.line_id,
    lines.source_id,
    lines.geom,
    lines.geom_scale::text AS scale
   FROM carto.lines
  WHERE lines.scale = 'small'::maps.map_scale;

--
-- Name: tiny; Type: VIEW; Schema: -; Owner: -
--

CREATE OR REPLACE VIEW tiny AS
 SELECT polygons.map_id,
    polygons.source_id,
    polygons.geom,
    polygons.geom_scale::text AS scale
   FROM carto.polygons
  WHERE polygons.scale = 'tiny'::maps.map_scale;

--
-- Name: lines_tiny; Type: VIEW; Schema: -; Owner: -
--

CREATE OR REPLACE VIEW lines_tiny AS
 SELECT lines.line_id,
    lines.source_id,
    lines.geom,
    lines.geom_scale::text AS scale
   FROM carto.lines
  WHERE lines.scale = 'tiny'::maps.map_scale;

