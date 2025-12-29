--
-- pgschema database dump
--

-- Dumped from database version PostgreSQL 15.15
-- Dumped by pgschema version 1.5.1


--
-- Name: flat_large; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS flat_large (
    map_id integer,
    geom public.geometry
);

--
-- Name: flat_large_geom_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS flat_large_geom_idx ON flat_large USING gist (geom);

--
-- Name: flat_large_map_id_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS flat_large_map_id_idx ON flat_large (map_id);

--
-- Name: flat_medium; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS flat_medium (
    map_id integer,
    geom public.geometry
);

--
-- Name: large; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS large (
    map_id integer,
    orig_id integer,
    source_id integer,
    scale text,
    name text,
    strat_name text,
    age text,
    lith text,
    descrip text,
    comments text,
    t_int_id integer,
    t_int text,
    best_age_top numeric,
    b_int_id integer,
    b_int text,
    best_age_bottom numeric,
    color text,
    unit_ids integer[],
    strat_name_ids integer[],
    lith_ids integer[],
    geom public.geometry
);

--
-- Name: large_new_geom_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS large_new_geom_idx ON large USING gist (geom);

--
-- Name: large_new_map_id_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS large_new_map_id_idx ON large (map_id);

--
-- Name: lines; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS lines (
    line_id integer NOT NULL,
    source_id integer,
    geom public.geometry NOT NULL,
    geom_scale maps.map_scale NOT NULL,
    scale maps.map_scale NOT NULL
) PARTITION BY LIST (scale);

--
-- Name: lines_large; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS lines_large (
    line_id integer NOT NULL,
    source_id integer,
    geom_scale maps.map_scale NOT NULL,
    geom public.geometry NOT NULL,
    scale maps.map_scale DEFAULT 'large' NOT NULL,
    CONSTRAINT lines_large_scale_check CHECK (scale = 'large'::maps.map_scale)
);

--
-- Name: lines_large_geom_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS lines_large_geom_idx ON lines_large USING gist (geom);

--
-- Name: lines_large_line_id_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS lines_large_line_id_idx ON lines_large (line_id);

--
-- Name: lines_large_new_geom_idx1; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS lines_large_new_geom_idx1 ON lines_large USING gist (geom);

--
-- Name: lines_large_new_line_id_idx1; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS lines_large_new_line_id_idx1 ON lines_large (line_id);

--
-- Name: lines_medium; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS lines_medium (
    line_id integer NOT NULL,
    source_id integer,
    geom_scale maps.map_scale NOT NULL,
    geom public.geometry NOT NULL,
    scale maps.map_scale DEFAULT 'medium' NOT NULL,
    CONSTRAINT lines_medium_scale_check CHECK (scale = 'medium'::maps.map_scale)
);

--
-- Name: lines_medium_geom_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS lines_medium_geom_idx ON lines_medium USING gist (geom);

--
-- Name: lines_medium_line_id_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS lines_medium_line_id_idx ON lines_medium (line_id);

--
-- Name: lines_medium_new_geom_idx1; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS lines_medium_new_geom_idx1 ON lines_medium USING gist (geom);

--
-- Name: lines_medium_new_line_id_idx1; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS lines_medium_new_line_id_idx1 ON lines_medium (line_id);

--
-- Name: lines_small; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS lines_small (
    line_id integer NOT NULL,
    source_id integer,
    geom_scale maps.map_scale NOT NULL,
    geom public.geometry NOT NULL,
    scale maps.map_scale DEFAULT 'small' NOT NULL,
    CONSTRAINT lines_small_scale_check CHECK (scale = 'small'::maps.map_scale)
);

--
-- Name: lines_small_geom_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS lines_small_geom_idx ON lines_small USING gist (geom);

--
-- Name: lines_small_line_id_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS lines_small_line_id_idx ON lines_small (line_id);

--
-- Name: lines_small_new_geom_idx1; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS lines_small_new_geom_idx1 ON lines_small USING gist (geom);

--
-- Name: lines_small_new_line_id_idx1; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS lines_small_new_line_id_idx1 ON lines_small (line_id);

--
-- Name: lines_tiny; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS lines_tiny (
    line_id integer NOT NULL,
    source_id integer,
    geom_scale maps.map_scale NOT NULL,
    geom public.geometry NOT NULL,
    scale maps.map_scale DEFAULT 'tiny' NOT NULL,
    CONSTRAINT lines_tiny_scale_check CHECK (scale = 'tiny'::maps.map_scale)
);

--
-- Name: lines_tiny_geom_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS lines_tiny_geom_idx ON lines_tiny USING gist (geom);

--
-- Name: lines_tiny_line_id_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS lines_tiny_line_id_idx ON lines_tiny (line_id);

--
-- Name: lines_tiny_new_geom_idx1; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS lines_tiny_new_geom_idx1 ON lines_tiny USING gist (geom);

--
-- Name: lines_tiny_new_line_id_idx1; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS lines_tiny_new_line_id_idx1 ON lines_tiny (line_id);

--
-- Name: medium; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS medium (
    map_id integer,
    orig_id integer,
    source_id integer,
    scale text,
    name text,
    strat_name text,
    age text,
    lith text,
    descrip text,
    comments text,
    t_int_id integer,
    t_int text,
    best_age_top numeric,
    b_int_id integer,
    b_int text,
    best_age_bottom numeric,
    color text,
    unit_ids integer[],
    strat_name_ids integer[],
    lith_ids integer[],
    geom public.geometry
);

--
-- Name: medium_new_geom_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS medium_new_geom_idx ON medium USING gist (geom);

--
-- Name: medium_new_map_id_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS medium_new_map_id_idx ON medium (map_id);

--
-- Name: polygons; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS polygons (
    map_id integer,
    source_id integer,
    geom public.geometry NOT NULL,
    geom_scale maps.map_scale NOT NULL,
    scale maps.map_scale,
    CONSTRAINT polygons_pkey PRIMARY KEY (scale, map_id),
    CONSTRAINT polygons_unique UNIQUE (map_id, scale)
) PARTITION BY LIST (scale);

--
-- Name: carto_polygons_geom_gist; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS carto_polygons_geom_gist ON polygons USING gist (geom);

--
-- Name: polygons_large; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS polygons_large (
    map_id integer,
    source_id integer,
    geom_scale maps.map_scale NOT NULL,
    geom public.geometry NOT NULL,
    scale maps.map_scale DEFAULT 'large',
    CONSTRAINT polygons_large_pkey PRIMARY KEY (scale, map_id),
    CONSTRAINT polygons_large_map_id_scale_key UNIQUE (map_id, scale),
    CONSTRAINT polygons_large_scale_check CHECK (scale = 'large'::maps.map_scale)
);

--
-- Name: large_geom_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS large_geom_idx ON polygons_large USING gist (geom);

--
-- Name: large_map_id_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS large_map_id_idx ON polygons_large (map_id);

--
-- Name: polygons_medium; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS polygons_medium (
    map_id integer,
    source_id integer,
    geom_scale maps.map_scale NOT NULL,
    geom public.geometry NOT NULL,
    scale maps.map_scale DEFAULT 'medium',
    CONSTRAINT polygons_medium_pkey PRIMARY KEY (scale, map_id),
    CONSTRAINT polygons_medium_map_id_scale_key UNIQUE (map_id, scale),
    CONSTRAINT polygons_medium_scale_check CHECK (scale = 'medium'::maps.map_scale)
);

--
-- Name: medium_geom_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS medium_geom_idx ON polygons_medium USING gist (geom);

--
-- Name: medium_map_id_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS medium_map_id_idx ON polygons_medium (map_id);

--
-- Name: polygons_small; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS polygons_small (
    map_id integer,
    source_id integer,
    geom_scale maps.map_scale NOT NULL,
    geom public.geometry NOT NULL,
    scale maps.map_scale DEFAULT 'small',
    CONSTRAINT polygons_small_pkey PRIMARY KEY (scale, map_id),
    CONSTRAINT polygons_small_map_id_scale_key UNIQUE (map_id, scale),
    CONSTRAINT polygons_small_scale_check CHECK (scale = 'small'::maps.map_scale)
);

--
-- Name: small_geom_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS small_geom_idx ON polygons_small USING gist (geom);

--
-- Name: small_map_id_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS small_map_id_idx ON polygons_small (map_id);

--
-- Name: polygons_tiny; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS polygons_tiny (
    map_id integer,
    source_id integer,
    geom_scale maps.map_scale NOT NULL,
    geom public.geometry NOT NULL,
    scale maps.map_scale DEFAULT 'tiny',
    CONSTRAINT polygons_tiny_pkey PRIMARY KEY (scale, map_id),
    CONSTRAINT polygons_tiny_map_id_scale_key UNIQUE (map_id, scale),
    CONSTRAINT polygons_tiny_scale_check CHECK (scale = 'tiny'::maps.map_scale)
);

--
-- Name: tiny_geom_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS tiny_geom_idx ON polygons_tiny USING gist (geom);

--
-- Name: tiny_map_id_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS tiny_map_id_idx ON polygons_tiny (map_id);

--
-- Name: small; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS small (
    map_id integer,
    orig_id integer,
    source_id integer,
    scale text,
    name text,
    strat_name text,
    age text,
    lith text,
    descrip text,
    comments text,
    t_int_id integer,
    t_int text,
    best_age_top numeric,
    b_int_id integer,
    b_int text,
    best_age_bottom numeric,
    color text,
    unit_ids integer[],
    strat_name_ids integer[],
    lith_ids integer[],
    geom public.geometry
);

--
-- Name: small_new_geom_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS small_new_geom_idx ON small USING gist (geom);

--
-- Name: small_new_map_id_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS small_new_map_id_idx ON small (map_id);

--
-- Name: tiny; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS tiny (
    map_id integer,
    orig_id integer,
    source_id integer,
    scale text,
    name text,
    strat_name text,
    age varchar,
    lith text,
    descrip text,
    comments text,
    t_int_id integer,
    t_int varchar(200),
    best_age_top numeric,
    b_int_id integer,
    b_int varchar(200),
    best_age_bottom numeric,
    color varchar(20),
    unit_ids integer[],
    strat_name_ids integer[],
    lith_ids integer[],
    geom public.geometry
);

--
-- Name: tiny_new_geom_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS tiny_new_geom_idx ON tiny USING gist (geom);

--
-- Name: tiny_new_map_id_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS tiny_new_map_id_idx ON tiny (map_id);

--
-- Name: lines_source_id_fkey; Type: CONSTRAINT; Schema: -; Owner: -
--

ALTER TABLE lines
ADD CONSTRAINT lines_source_id_fkey FOREIGN KEY (source_id) REFERENCES maps.sources (source_id);

--
-- Name: lines_source_id_fkey; Type: CONSTRAINT; Schema: -; Owner: -
--

ALTER TABLE lines_large
ADD CONSTRAINT lines_source_id_fkey FOREIGN KEY (source_id) REFERENCES maps.sources (source_id);

--
-- Name: lines_source_id_fkey; Type: CONSTRAINT; Schema: -; Owner: -
--

ALTER TABLE lines_medium
ADD CONSTRAINT lines_source_id_fkey FOREIGN KEY (source_id) REFERENCES maps.sources (source_id);

--
-- Name: lines_source_id_fkey; Type: CONSTRAINT; Schema: -; Owner: -
--

ALTER TABLE lines_small
ADD CONSTRAINT lines_source_id_fkey FOREIGN KEY (source_id) REFERENCES maps.sources (source_id);

--
-- Name: lines_source_id_fkey; Type: CONSTRAINT; Schema: -; Owner: -
--

ALTER TABLE lines_tiny
ADD CONSTRAINT lines_source_id_fkey FOREIGN KEY (source_id) REFERENCES maps.sources (source_id);

--
-- Name: polygons_source_id_fkey; Type: CONSTRAINT; Schema: -; Owner: -
--

ALTER TABLE polygons
ADD CONSTRAINT polygons_source_id_fkey FOREIGN KEY (source_id) REFERENCES maps.sources (source_id);

--
-- Name: polygons_source_id_fkey; Type: CONSTRAINT; Schema: -; Owner: -
--

ALTER TABLE polygons_large
ADD CONSTRAINT polygons_source_id_fkey FOREIGN KEY (source_id) REFERENCES maps.sources (source_id);

--
-- Name: polygons_source_id_fkey; Type: CONSTRAINT; Schema: -; Owner: -
--

ALTER TABLE polygons_medium
ADD CONSTRAINT polygons_source_id_fkey FOREIGN KEY (source_id) REFERENCES maps.sources (source_id);

--
-- Name: polygons_source_id_fkey; Type: CONSTRAINT; Schema: -; Owner: -
--

ALTER TABLE polygons_small
ADD CONSTRAINT polygons_source_id_fkey FOREIGN KEY (source_id) REFERENCES maps.sources (source_id);

--
-- Name: polygons_source_id_fkey; Type: CONSTRAINT; Schema: -; Owner: -
--

ALTER TABLE polygons_tiny
ADD CONSTRAINT polygons_source_id_fkey FOREIGN KEY (source_id) REFERENCES maps.sources (source_id);

