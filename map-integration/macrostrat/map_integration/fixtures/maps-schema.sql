--
-- Name: maps; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA IF NOT EXISTS maps;

CREATE SEQUENCE IF NOT EXISTS map_ids;

--
-- Name: small; Type: TABLE; Schema: maps; Owner: -
--

CREATE TABLE maps.small (
    map_id integer DEFAULT nextval('public.map_ids'::regclass) NOT NULL,
    orig_id integer,
    source_id integer,
    name text,
    strat_name text,
    age character varying(255),
    lith text,
    descrip text,
    comments text,
    t_interval integer,
    b_interval integer,
    geom public.geometry(Geometry,4326) NOT NULL,
    CONSTRAINT enforce_geom_type_small CHECK (((public.st_geometrytype(geom) <> 'ST_GeometryCollection'::text) AND (public.st_geometrytype(geom) IS NOT NULL))),
    CONSTRAINT enforce_valid_geom_small CHECK (public.st_isvalid(geom))
);


--
-- Name: tiny; Type: TABLE; Schema: maps; Owner: -
--

CREATE TABLE maps.tiny (
    map_id integer DEFAULT nextval('public.map_ids'::regclass) NOT NULL,
    orig_id integer,
    source_id integer,
    name text,
    strat_name text,
    age character varying(255),
    lith text,
    descrip text,
    comments text,
    t_interval integer,
    b_interval integer,
    geom public.geometry(Geometry,4326) NOT NULL,
    CONSTRAINT enforce_geom_type_tiny CHECK (((public.st_geometrytype(geom) <> 'ST_GeometryCollection'::text) AND (public.st_geometrytype(geom) IS NOT NULL))),
    CONSTRAINT enforce_valid_geom_medium CHECK (public.st_isvalid(geom))
);


--
-- Name: large; Type: TABLE; Schema: maps; Owner: -
--

CREATE TABLE maps.large (
    map_id integer DEFAULT nextval('public.map_ids'::regclass) NOT NULL,
    orig_id integer,
    source_id integer,
    name text,
    strat_name text,
    age character varying(255),
    lith text,
    descrip text,
    comments text,
    t_interval integer,
    b_interval integer,
    geom public.geometry(Geometry,4326) NOT NULL,
    CONSTRAINT enforce_geom_type_large CHECK (((public.st_geometrytype(geom) <> 'ST_GeometryCollection'::text) AND (public.st_geometrytype(geom) IS NOT NULL))),
    CONSTRAINT enforce_valid_geom_large CHECK (public.st_isvalid(geom))
);


--
-- Name: legend; Type: TABLE; Schema: maps; Owner: -
--

CREATE TABLE maps.legend (
    legend_id integer PRIMARY KEY,
    source_id integer NOT NULL,
    name text,
    strat_name text,
    age text,
    lith text,
    descrip text,
    comments text,
    b_interval integer,
    t_interval integer,
    best_age_bottom numeric,
    best_age_top numeric,
    color text,
    unit_ids integer[],
    concept_ids integer[],
    strat_name_ids integer[],
    strat_name_children integer[],
    lith_ids integer[],
    lith_types text[],
    lith_classes text[],
    all_lith_ids integer[],
    all_lith_types text[],
    all_lith_classes text[],
    area numeric,
    tiny_area numeric,
    small_area numeric,
    medium_area numeric,
    large_area numeric,
);


--
-- Name: legend_legend_id_seq; Type: SEQUENCE; Schema: maps; Owner: -
--

CREATE SEQUENCE maps.legend_legend_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: legend_legend_id_seq; Type: SEQUENCE OWNED BY; Schema: maps; Owner: -
--

ALTER SEQUENCE maps.legend_legend_id_seq OWNED BY maps.legend.legend_id;


--
-- Name: legend_liths; Type: TABLE; Schema: maps; Owner: -
--

CREATE TABLE maps.legend_liths (
    legend_id integer NOT NULL,
    lith_id integer NOT NULL,
    basis_col text NOT NULL
);


--
-- Name: manual_matches; Type: TABLE; Schema: maps; Owner: -
--

CREATE TABLE maps.manual_matches (
    match_id integer NOT NULL,
    map_id integer NOT NULL,
    strat_name_id integer,
    unit_id integer,
    addition boolean DEFAULT false,
    removal boolean DEFAULT false,
    type character varying(20)
);


--
-- Name: manual_matches_match_id_seq; Type: SEQUENCE; Schema: maps; Owner: -
--

CREATE SEQUENCE maps.manual_matches_match_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: manual_matches_match_id_seq; Type: SEQUENCE OWNED BY; Schema: maps; Owner: -
--

ALTER SEQUENCE maps.manual_matches_match_id_seq OWNED BY maps.manual_matches.match_id;


--
-- Name: map_legend; Type: TABLE; Schema: maps; Owner: -
--

CREATE TABLE maps.map_legend (
    legend_id integer NOT NULL,
    map_id integer NOT NULL
);


--
-- Name: map_liths; Type: TABLE; Schema: maps; Owner: -
--

CREATE TABLE maps.map_liths (
    map_id integer NOT NULL,
    lith_id integer NOT NULL,
    basis_col character varying(50)
);


--
-- Name: map_strat_names; Type: TABLE; Schema: maps; Owner: -
--

CREATE TABLE maps.map_strat_names (
    map_id integer NOT NULL,
    strat_name_id integer NOT NULL,
    basis_col character varying(50)
);


--
-- Name: map_units; Type: TABLE; Schema: maps; Owner: -
--

CREATE TABLE maps.map_units (
    map_id integer NOT NULL,
    unit_id integer NOT NULL,
    basis_col character varying(50)
);


--
-- Name: medium; Type: TABLE; Schema: maps; Owner: -
--

CREATE TABLE maps.medium (
    map_id integer DEFAULT nextval('public.map_ids'::regclass) NOT NULL,
    orig_id integer,
    source_id integer,
    name text,
    strat_name text,
    age character varying(255),
    lith text,
    descrip text,
    comments text,
    t_interval integer,
    b_interval integer,
    geom public.geometry(Geometry,4326) NOT NULL,
    CONSTRAINT enforce_geom_type_medium CHECK (((public.st_geometrytype(geom) <> 'ST_GeometryCollection'::text) AND (public.st_geometrytype(geom) IS NOT NULL))),
    CONSTRAINT enforce_valid_geom_medium CHECK (public.st_isvalid(geom))
);


--
-- Name: sources; Type: TABLE; Schema: maps; Owner: -
--

CREATE TABLE maps.sources (
    source_id integer NOT NULL,
    name character varying(255),
    primary_table character varying(255),
    url character varying(255),
    ref_title text,
    authors character varying(255),
    ref_year text,
    ref_source character varying(255),
    isbn_doi character varying(100),
    scale character varying(20),
    primary_line_table character varying(50),
    licence character varying(100),
    features integer,
    area integer,
    priority boolean DEFAULT false,
    rgeom public.geometry(Geometry,4326),
    display_scales text[],
    web_geom public.geometry(Geometry,4326),
    new_priority integer DEFAULT 0,
    status_code text DEFAULT 'active'::text,
    date_finalized timestamp with time zone DEFAULT null,
    ingested_by text
);


--
-- Name: sources_source_id_seq; Type: SEQUENCE; Schema: maps; Owner: -
--

CREATE SEQUENCE maps.sources_source_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: sources_source_id_seq; Type: SEQUENCE OWNED BY; Schema: maps; Owner: -
--

ALTER SEQUENCE maps.sources_source_id_seq OWNED BY maps.sources.source_id;


--
-- Name: legend legend_id; Type: DEFAULT; Schema: maps; Owner: -
--

ALTER TABLE ONLY maps.legend ALTER COLUMN legend_id SET DEFAULT nextval('maps.legend_legend_id_seq'::regclass);


--
-- Name: manual_matches match_id; Type: DEFAULT; Schema: maps; Owner: -
--

ALTER TABLE ONLY maps.manual_matches ALTER COLUMN match_id SET DEFAULT nextval('maps.manual_matches_match_id_seq'::regclass);


--
-- Name: sources source_id; Type: DEFAULT; Schema: maps; Owner: -
--

ALTER TABLE ONLY maps.sources ALTER COLUMN source_id SET DEFAULT nextval('maps.sources_source_id_seq'::regclass);


--
-- Name: large large_pkey; Type: CONSTRAINT; Schema: maps; Owner: -
--

ALTER TABLE ONLY maps.large
    ADD CONSTRAINT large_pkey PRIMARY KEY (map_id);


--
-- Name: legend_liths legend_liths_legend_id_lith_id_basis_col_key; Type: CONSTRAINT; Schema: maps; Owner: -
--

ALTER TABLE ONLY maps.legend_liths
    ADD CONSTRAINT legend_liths_legend_id_lith_id_basis_col_key UNIQUE (legend_id, lith_id, basis_col);


--
-- Name: legend legend_pkey; Type: CONSTRAINT; Schema: maps; Owner: -
--

ALTER TABLE ONLY maps.legend
    ADD CONSTRAINT legend_pkey PRIMARY KEY (legend_id);


--
-- Name: map_legend map_legend_legend_id_map_id_key; Type: CONSTRAINT; Schema: maps; Owner: -
--

ALTER TABLE ONLY maps.map_legend
    ADD CONSTRAINT map_legend_legend_id_map_id_key UNIQUE (legend_id, map_id);


--
-- Name: sources map_sources_name_key; Type: CONSTRAINT; Schema: maps; Owner: -
--

ALTER TABLE ONLY maps.sources
    ADD CONSTRAINT map_sources_name_key UNIQUE (primary_table);


--
-- Name: medium medium_pkey; Type: CONSTRAINT; Schema: maps; Owner: -
--

ALTER TABLE ONLY maps.medium
    ADD CONSTRAINT medium_pkey PRIMARY KEY (map_id);


--
-- Name: small small_pkey; Type: CONSTRAINT; Schema: maps; Owner: -
--

ALTER TABLE ONLY maps.small
    ADD CONSTRAINT small_pkey PRIMARY KEY (map_id);


--
-- Name: sources sources_source_id_key; Type: CONSTRAINT; Schema: maps; Owner: -
--

ALTER TABLE ONLY maps.sources
    ADD CONSTRAINT sources_source_id_key UNIQUE (source_id);


--
-- Name: tiny tiny_pkey; Type: CONSTRAINT; Schema: maps; Owner: -
--

ALTER TABLE ONLY maps.tiny
    ADD CONSTRAINT tiny_pkey PRIMARY KEY (map_id);


--
-- Name: large_b_interval_idx; Type: INDEX; Schema: maps; Owner: -
--

CREATE INDEX large_b_interval_idx ON maps.large USING btree (b_interval);


--
-- Name: large_geom_idx; Type: INDEX; Schema: maps; Owner: -
--

CREATE INDEX large_geom_idx ON maps.large USING gist (geom);


--
-- Name: large_name_idx; Type: INDEX; Schema: maps; Owner: -
--

CREATE INDEX large_name_idx ON maps.large USING btree (name);


--
-- Name: large_orig_id_idx; Type: INDEX; Schema: maps; Owner: -
--

CREATE INDEX large_orig_id_idx ON maps.large USING btree (orig_id);


--
-- Name: large_source_id_idx; Type: INDEX; Schema: maps; Owner: -
--

CREATE INDEX large_source_id_idx ON maps.large USING btree (source_id);


--
-- Name: large_t_interval_idx; Type: INDEX; Schema: maps; Owner: -
--

CREATE INDEX large_t_interval_idx ON maps.large USING btree (t_interval);


--
-- Name: legend_liths_legend_id_idx; Type: INDEX; Schema: maps; Owner: -
--

CREATE INDEX legend_liths_legend_id_idx ON maps.legend_liths USING btree (legend_id);


--
-- Name: legend_liths_lith_id_idx; Type: INDEX; Schema: maps; Owner: -
--

CREATE INDEX legend_liths_lith_id_idx ON maps.legend_liths USING btree (lith_id);


--
-- Name: legend_source_id_idx; Type: INDEX; Schema: maps; Owner: -
--

CREATE INDEX legend_source_id_idx ON maps.legend USING btree (source_id);


--
-- Name: manual_matches_map_id_idx; Type: INDEX; Schema: maps; Owner: -
--

CREATE INDEX manual_matches_map_id_idx ON maps.manual_matches USING btree (map_id);


--
-- Name: manual_matches_strat_name_id_idx; Type: INDEX; Schema: maps; Owner: -
--

CREATE INDEX manual_matches_strat_name_id_idx ON maps.manual_matches USING btree (strat_name_id);


--
-- Name: manual_matches_unit_id_idx; Type: INDEX; Schema: maps; Owner: -
--

CREATE INDEX manual_matches_unit_id_idx ON maps.manual_matches USING btree (unit_id);


--
-- Name: map_legend_legend_id_idx; Type: INDEX; Schema: maps; Owner: -
--

CREATE INDEX map_legend_legend_id_idx ON maps.map_legend USING btree (legend_id);


--
-- Name: map_legend_map_id_idx; Type: INDEX; Schema: maps; Owner: -
--

CREATE INDEX map_legend_map_id_idx ON maps.map_legend USING btree (map_id);


--
-- Name: map_liths_lith_id_idx; Type: INDEX; Schema: maps; Owner: -
--

CREATE INDEX map_liths_lith_id_idx ON maps.map_liths USING btree (lith_id);


--
-- Name: map_liths_map_id_idx; Type: INDEX; Schema: maps; Owner: -
--

CREATE INDEX map_liths_map_id_idx ON maps.map_liths USING btree (map_id);


--
-- Name: map_strat_names_map_id_idx; Type: INDEX; Schema: maps; Owner: -
--

CREATE INDEX map_strat_names_map_id_idx ON maps.map_strat_names USING btree (map_id);


--
-- Name: map_strat_names_strat_name_id_idx; Type: INDEX; Schema: maps; Owner: -
--

CREATE INDEX map_strat_names_strat_name_id_idx ON maps.map_strat_names USING btree (strat_name_id);


--
-- Name: map_units_map_id_idx; Type: INDEX; Schema: maps; Owner: -
--

CREATE INDEX map_units_map_id_idx ON maps.map_units USING btree (map_id);


--
-- Name: map_units_unit_id_idx; Type: INDEX; Schema: maps; Owner: -
--

CREATE INDEX map_units_unit_id_idx ON maps.map_units USING btree (unit_id);


--
-- Name: medium_b_interval_idx; Type: INDEX; Schema: maps; Owner: -
--

CREATE INDEX medium_b_interval_idx ON maps.medium USING btree (b_interval);


--
-- Name: medium_geom_idx; Type: INDEX; Schema: maps; Owner: -
--

CREATE INDEX medium_geom_idx ON maps.medium USING gist (geom);


--
-- Name: medium_orig_id_idx; Type: INDEX; Schema: maps; Owner: -
--

CREATE INDEX medium_orig_id_idx ON maps.medium USING btree (orig_id);


--
-- Name: medium_source_id_idx; Type: INDEX; Schema: maps; Owner: -
--

CREATE INDEX medium_source_id_idx ON maps.medium USING btree (source_id);


--
-- Name: medium_t_interval_idx; Type: INDEX; Schema: maps; Owner: -
--

CREATE INDEX medium_t_interval_idx ON maps.medium USING btree (t_interval);


--
-- Name: small_b_interval_idx; Type: INDEX; Schema: maps; Owner: -
--

CREATE INDEX small_b_interval_idx ON maps.small USING btree (b_interval);


--
-- Name: small_geom_idx; Type: INDEX; Schema: maps; Owner: -
--

CREATE INDEX small_geom_idx ON maps.small USING gist (geom);


--
-- Name: small_orig_id_idx; Type: INDEX; Schema: maps; Owner: -
--

CREATE INDEX small_orig_id_idx ON maps.small USING btree (orig_id);


--
-- Name: small_source_id_idx; Type: INDEX; Schema: maps; Owner: -
--

CREATE INDEX small_source_id_idx ON maps.small USING btree (source_id);


--
-- Name: small_t_interval_idx; Type: INDEX; Schema: maps; Owner: -
--

CREATE INDEX small_t_interval_idx ON maps.small USING btree (t_interval);


--
-- Name: sources_rgeom_idx; Type: INDEX; Schema: maps; Owner: -
--

CREATE INDEX sources_rgeom_idx ON maps.sources USING gist (rgeom);


--
-- Name: sources_web_geom_idx; Type: INDEX; Schema: maps; Owner: -
--

CREATE INDEX sources_web_geom_idx ON maps.sources USING gist (web_geom);


--
-- Name: tiny_b_interval_idx; Type: INDEX; Schema: maps; Owner: -
--

CREATE INDEX tiny_b_interval_idx ON maps.tiny USING btree (b_interval);


--
-- Name: tiny_geom_idx; Type: INDEX; Schema: maps; Owner: -
--

CREATE INDEX tiny_geom_idx ON maps.tiny USING gist (geom);


--
-- Name: tiny_orig_id_idx; Type: INDEX; Schema: maps; Owner: -
--

CREATE INDEX tiny_orig_id_idx ON maps.tiny USING btree (orig_id);


--
-- Name: tiny_source_id_idx; Type: INDEX; Schema: maps; Owner: -
--

CREATE INDEX tiny_source_id_idx ON maps.tiny USING btree (source_id);


--
-- Name: tiny_t_interval_idx; Type: INDEX; Schema: maps; Owner: -
--

CREATE INDEX tiny_t_interval_idx ON maps.tiny USING btree (t_interval);


--
-- PostgreSQL database dump complete
--

