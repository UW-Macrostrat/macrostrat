CREATE SCHEMA carto;
CREATE SCHEMA carto_new;
CREATE SCHEMA geologic_boundaries;
CREATE SCHEMA hexgrids;

CREATE SCHEMA lines;

CREATE SCHEMA macrostrat;

CREATE SCHEMA maps;

CREATE SCHEMA points;

CREATE SCHEMA sources;

CREATE SCHEMA topology;

CREATE EXTENSION IF NOT EXISTS pg_stat_statements WITH SCHEMA public;

CREATE EXTENSION IF NOT EXISTS pgaudit WITH SCHEMA public;

CREATE EXTENSION IF NOT EXISTS postgis WITH SCHEMA public;

CREATE EXTENSION IF NOT EXISTS postgis_raster WITH SCHEMA public;

CREATE EXTENSION IF NOT EXISTS postgis_topology WITH SCHEMA topology;

CREATE EXTENSION IF NOT EXISTS postgres_fdw WITH SCHEMA public;

CREATE TYPE public.measurement_class AS ENUM (
    '',
    'geophysical',
    'geochemical',
    'sedimentological'
);

CREATE TYPE public.measurement_class_new AS ENUM (
    '',
    'geophysical',
    'geochemical',
    'sedimentological'
);

CREATE TYPE public.measurement_type AS ENUM (
    '',
    'material properties',
    'geochronological',
    'major elements',
    'minor elements',
    'radiogenic isotopes',
    'stable isotopes',
    'petrologic',
    'environmental'
);

CREATE TYPE public.measurement_type_new AS ENUM (
    '',
    'material properties',
    'geochronological',
    'major elements',
    'minor elements',
    'radiogenic isotopes',
    'stable isotopes',
    'petrologic',
    'environmental'
);

CREATE FUNCTION public.count_estimate(query text) RETURNS integer
    LANGUAGE plpgsql STRICT
    AS $$
DECLARE
  rec   record;
  rows  integer;
BEGIN
  FOR rec IN EXECUTE 'EXPLAIN ' || query LOOP
    rows := substring(rec."QUERY PLAN" FROM ' rows=([[:digit:]]+)');
    EXIT WHEN rows IS NOT NULL;
  END LOOP;
  RETURN rows;
END;
$$;

CREATE AGGREGATE public.array_agg_mult(anycompatiblearray) (
    SFUNC = array_cat,
    STYPE = anycompatiblearray,
    INITCOND = '{}'
);

CREATE TABLE carto.flat_large (
    map_id integer,
    geom public.geometry
);

CREATE TABLE carto.flat_medium (
    map_id integer,
    geom public.geometry
);

CREATE TABLE carto.large (
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

CREATE TABLE carto.lines_large (
    line_id integer,
    scale text,
    source_id integer,
    name text,
    type text,
    direction text,
    descrip text,
    geom public.geometry
);

CREATE TABLE carto.lines_medium (
    line_id integer,
    scale text,
    source_id integer,
    name text,
    type text,
    direction text,
    descrip text,
    geom public.geometry
);

CREATE TABLE carto.lines_small (
    line_id integer,
    scale text,
    source_id integer,
    name text,
    type text,
    direction text,
    descrip text,
    geom public.geometry
);

CREATE TABLE carto.lines_tiny (
    line_id integer,
    geom public.geometry(Geometry,4326),
    scale text,
    source_id integer,
    name character varying,
    type character varying,
    direction character varying,
    descrip text
);

CREATE TABLE carto.medium (
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

CREATE TABLE carto.small (
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

CREATE TABLE carto.tiny (
    map_id integer,
    orig_id integer,
    source_id integer,
    scale text,
    name text,
    strat_name text,
    age character varying,
    lith text,
    descrip text,
    comments text,
    t_int_id integer,
    t_int character varying(200),
    best_age_top numeric,
    b_int_id integer,
    b_int character varying(200),
    best_age_bottom numeric,
    color character varying(20),
    unit_ids integer[],
    strat_name_ids integer[],
    lith_ids integer[],
    geom public.geometry
);

CREATE TABLE carto_new.hex_index (
    map_id integer NOT NULL,
    scale text,
    hex_id integer
);

CREATE TABLE carto_new.large (
    map_id integer,
    source_id integer,
    scale text,
    geom public.geometry
);

CREATE TABLE carto_new.lines_large (
    line_id integer,
    source_id integer,
    scale text,
    geom public.geometry
);

CREATE TABLE carto_new.lines_medium (
    line_id integer,
    source_id integer,
    scale text,
    geom public.geometry
);

CREATE TABLE carto_new.lines_small (
    line_id integer,
    source_id integer,
    scale text,
    geom public.geometry
);

CREATE TABLE carto_new.lines_tiny (
    line_id integer,
    source_id integer,
    scale text,
    geom public.geometry(Geometry,4326)
);

CREATE TABLE carto_new.medium (
    map_id integer,
    source_id integer,
    scale text,
    geom public.geometry
);

CREATE TABLE carto_new.pbdb_hex_index (
    collection_no integer NOT NULL,
    scale text,
    hex_id integer
);

CREATE TABLE carto_new.small (
    map_id integer,
    source_id integer,
    scale text,
    geom public.geometry
);

CREATE TABLE carto_new.tiny (
    map_id integer,
    source_id integer,
    scale text,
    geom public.geometry
);

CREATE TABLE geologic_boundaries.boundaries (
    boundary_id integer NOT NULL,
    orig_id integer NOT NULL,
    source_id integer NOT NULL,
    name text,
    boundary_group text,
    boundary_type text,
    boundary_class text,
    descrip text,
    wiki_link text,
    geom public.geometry(Geometry,4326)
);

CREATE SEQUENCE geologic_boundaries.boundaries_boundary_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE geologic_boundaries.boundaries_boundary_id_seq OWNED BY geologic_boundaries.boundaries.boundary_id;

CREATE SEQUENCE public.geologic_boundary_source_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

CREATE TABLE geologic_boundaries.sources (
    source_id integer DEFAULT nextval('public.geologic_boundary_source_seq'::regclass) NOT NULL,
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
    priority boolean,
    rgeom public.geometry,
    display_scales text[],
    web_geom public.geometry
);

CREATE TABLE hexgrids.bedrock_index (
    legend_id integer NOT NULL,
    hex_id integer NOT NULL,
    coverage numeric
);

CREATE TABLE hexgrids.hexgrids (
    hex_id integer NOT NULL,
    res integer,
    geom public.geometry
);

CREATE TABLE hexgrids.pbdb_index (
    collection_no integer NOT NULL,
    hex_id integer NOT NULL
);

CREATE TABLE hexgrids.r10 (
    hex_id integer NOT NULL,
    geom public.geometry(MultiPolygon,4326),
    web_geom public.geometry
);

CREATE SEQUENCE hexgrids.r10_ogc_fid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE hexgrids.r10_ogc_fid_seq OWNED BY hexgrids.r10.hex_id;

CREATE TABLE hexgrids.r11 (
    hex_id integer NOT NULL,
    geom public.geometry(MultiPolygon,4326),
    web_geom public.geometry
);

CREATE SEQUENCE hexgrids.r11_ogc_fid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE hexgrids.r11_ogc_fid_seq OWNED BY hexgrids.r11.hex_id;

CREATE TABLE hexgrids.r12 (
    hex_id integer NOT NULL,
    geom public.geometry(MultiPolygon,4326),
    web_geom public.geometry
);

CREATE SEQUENCE hexgrids.r12_ogc_fid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE hexgrids.r12_ogc_fid_seq OWNED BY hexgrids.r12.hex_id;

CREATE TABLE hexgrids.r5 (
    hex_id integer NOT NULL,
    geom public.geometry(MultiPolygon,4326),
    web_geom public.geometry
);

CREATE SEQUENCE hexgrids.r5_ogc_fid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE hexgrids.r5_ogc_fid_seq OWNED BY hexgrids.r5.hex_id;

CREATE TABLE hexgrids.r6 (
    hex_id integer NOT NULL,
    geom public.geometry(MultiPolygon,4326),
    web_geom public.geometry
);

CREATE SEQUENCE hexgrids.r6_ogc_fid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE hexgrids.r6_ogc_fid_seq OWNED BY hexgrids.r6.hex_id;

CREATE TABLE hexgrids.r7 (
    hex_id integer NOT NULL,
    geom public.geometry(MultiPolygon,4326),
    web_geom public.geometry
);

CREATE SEQUENCE hexgrids.r7_ogc_fid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE hexgrids.r7_ogc_fid_seq OWNED BY hexgrids.r7.hex_id;

CREATE TABLE hexgrids.r8 (
    hex_id integer NOT NULL,
    geom public.geometry(MultiPolygon,4326),
    web_geom public.geometry
);

CREATE SEQUENCE hexgrids.r8_ogc_fid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE hexgrids.r8_ogc_fid_seq OWNED BY hexgrids.r8.hex_id;

CREATE TABLE hexgrids.r9 (
    hex_id integer NOT NULL,
    geom public.geometry(MultiPolygon,4326),
    web_geom public.geometry
);

CREATE SEQUENCE hexgrids.r9_ogc_fid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE hexgrids.r9_ogc_fid_seq OWNED BY hexgrids.r9.hex_id;

CREATE SEQUENCE public.line_ids
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

CREATE TABLE lines.large (
    line_id integer DEFAULT nextval('public.line_ids'::regclass) NOT NULL,
    orig_id integer,
    source_id integer,
    name character varying(255),
    type character varying(100),
    direction character varying(40),
    descrip text,
    geom public.geometry(Geometry,4326) NOT NULL,
    new_type character varying(100),
    new_direction character varying(40),
    CONSTRAINT "ST_IsValid(geom)" CHECK (public.st_isvalid(geom))
);

CREATE TABLE lines.medium (
    line_id integer DEFAULT nextval('public.line_ids'::regclass) NOT NULL,
    orig_id integer,
    source_id integer,
    name character varying(255),
    type character varying(100),
    direction character varying(20),
    descrip text,
    geom public.geometry(Geometry,4326) NOT NULL,
    new_type character varying(100),
    new_direction character varying(20),
    CONSTRAINT enforce_valid_geom_lines_medium CHECK (public.st_isvalid(geom))
);

CREATE TABLE lines.small (
    line_id integer DEFAULT nextval('public.line_ids'::regclass) NOT NULL,
    orig_id integer,
    source_id integer,
    name character varying(255),
    type character varying(100),
    direction character varying(20),
    descrip text,
    geom public.geometry(Geometry,4326) NOT NULL,
    new_type character varying(100),
    new_direction character varying(20),
    CONSTRAINT enforce_valid_geom_lines_small CHECK (public.st_isvalid(geom))
);

CREATE TABLE lines.tiny (
    line_id integer DEFAULT nextval('public.line_ids'::regclass) NOT NULL,
    orig_id integer,
    source_id integer,
    name character varying(255),
    type character varying(100),
    direction character varying(20),
    descrip text,
    geom public.geometry(Geometry,4326) NOT NULL,
    new_type character varying(100),
    new_direction character varying(20),
    CONSTRAINT isvalid CHECK (public.st_isvalid(geom))
);

CREATE TABLE macrostrat.autocomplete (
    id integer NOT NULL,
    name text,
    type text,
    category text
);

CREATE TABLE macrostrat.col_areas (
    id integer NOT NULL,
    col_id integer,
    col_area public.geometry,
    wkt text
);

CREATE TABLE macrostrat.col_groups (
    id integer NOT NULL,
    col_group character varying(100),
    col_group_long character varying(100)
);

CREATE TABLE macrostrat.col_refs (
    id integer NOT NULL,
    col_id integer,
    ref_id integer
);

CREATE TABLE macrostrat.cols (
    id integer NOT NULL,
    col_group_id smallint,
    project_id smallint,
    col_type text,
    status_code character varying(25),
    col_position character varying(25),
    col numeric,
    col_name character varying(100),
    lat numeric,
    lng numeric,
    col_area numeric,
    coordinate public.geometry,
    wkt text,
    created text,
    poly_geom public.geometry
);

CREATE TABLE macrostrat.concepts_places (
    concept_id integer NOT NULL,
    place_id integer NOT NULL
);

CREATE TABLE macrostrat.econs (
    id integer NOT NULL,
    econ text,
    econ_type text,
    econ_class text,
    econ_color text
);

CREATE TABLE macrostrat.environs (
    id integer NOT NULL,
    environ text,
    environ_type text,
    environ_class text,
    environ_color text
);

CREATE TABLE macrostrat.grainsize (
    grain_id integer NOT NULL,
    grain_symbol text,
    grain_name text,
    grain_group text,
    soil_group text,
    min_size numeric,
    max_size numeric,
    classification text
);

CREATE TABLE macrostrat.intervals (
    id integer NOT NULL,
    age_bottom numeric,
    age_top numeric,
    interval_name character varying(200),
    interval_abbrev character varying(50),
    interval_type character varying(50),
    interval_color character varying(20),
    rank integer
);

CREATE SEQUENCE macrostrat.intervals_new_id_seq1
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE macrostrat.intervals_new_id_seq1 OWNED BY macrostrat.intervals.id;

CREATE TABLE macrostrat.lith_atts (
    id integer NOT NULL,
    lith_att character varying(75),
    att_type character varying(25),
    lith_att_fill integer
);

CREATE TABLE macrostrat.liths (
    id integer NOT NULL,
    lith character varying(75),
    lith_group text,
    lith_type character varying(50),
    lith_class character varying(50),
    lith_equiv integer,
    lith_fill integer,
    comp_coef numeric,
    initial_porosity numeric,
    bulk_density numeric,
    lith_color character varying(12)
);

CREATE TABLE macrostrat.lookup_strat_names (
    strat_name_id integer,
    strat_name character varying(100),
    rank character varying(20),
    concept_id integer,
    rank_name character varying(200),
    bed_id integer,
    bed_name character varying(100),
    mbr_id integer,
    mbr_name character varying(100),
    fm_id integer,
    fm_name character varying(100),
    gp_id integer,
    gp_name character varying(100),
    sgp_id integer,
    sgp_name character varying(100),
    early_age numeric,
    late_age numeric,
    gsc_lexicon character varying(20),
    b_period character varying(100),
    t_period character varying(100),
    c_interval character varying(100),
    name_no_lith character varying(100)
);

CREATE TABLE macrostrat.lookup_unit_attrs_api (
    unit_id integer,
    lith json,
    environ json,
    econ json,
    measure_short json,
    measure_long json
);

CREATE TABLE macrostrat.lookup_unit_intervals (
    unit_id integer,
    fo_age numeric,
    b_age numeric,
    fo_interval character varying(50),
    fo_period character varying(50),
    lo_age numeric,
    t_age numeric,
    lo_interval character varying(50),
    lo_period character varying(50),
    age character varying(50),
    age_id integer,
    epoch character varying(50),
    epoch_id integer,
    period character varying(50),
    period_id integer,
    era character varying(50),
    era_id integer,
    eon character varying(50),
    eon_id integer,
    best_interval_id integer
);

CREATE TABLE macrostrat.lookup_unit_liths (
    unit_id integer,
    lith_class character varying(100),
    lith_type character varying(100),
    lith_short text,
    lith_long text,
    environ_class character varying(100),
    environ_type character varying(100),
    environ character varying(255)
);

CREATE TABLE macrostrat.lookup_units (
    unit_id integer NOT NULL,
    col_area numeric NOT NULL,
    project_id integer NOT NULL,
    t_int integer,
    t_int_name text,
    t_int_age numeric,
    t_age numeric,
    t_prop numeric,
    t_plat numeric,
    t_plng numeric,
    b_int integer,
    b_int_name text,
    b_int_age numeric,
    b_age numeric,
    b_prop numeric,
    b_plat numeric,
    b_plng numeric,
    clat numeric,
    clng numeric,
    color text,
    text_color text,
    units_above text,
    units_below text,
    pbdb_collections integer,
    pbdb_occurrences integer,
    age text,
    age_id integer,
    epoch text,
    epoch_id integer,
    period text,
    period_id integer,
    era text,
    era_id integer,
    eon text,
    eon_id integer
);

CREATE TABLE macrostrat.measurements (
    id integer NOT NULL,
    measurement_class public.measurement_class NOT NULL,
    measurement_type public.measurement_type NOT NULL,
    measurement text NOT NULL
);

CREATE SEQUENCE macrostrat.measurements_new_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE macrostrat.measurements_new_id_seq OWNED BY macrostrat.measurements.id;

CREATE TABLE macrostrat.measuremeta (
    id integer NOT NULL,
    sample_name text NOT NULL,
    lat numeric(8,5),
    lng numeric(8,5),
    sample_geo_unit text NOT NULL,
    sample_lith text,
    lith_id integer NOT NULL,
    lith_att_id bigint NOT NULL,
    age text NOT NULL,
    early_id bigint NOT NULL,
    late_id bigint NOT NULL,
    sample_descrip text,
    ref text NOT NULL,
    ref_id bigint NOT NULL
);

CREATE SEQUENCE macrostrat.measuremeta_new_id_seq1
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE macrostrat.measuremeta_new_id_seq1 OWNED BY macrostrat.measuremeta.id;

CREATE TABLE macrostrat.measures (
    id integer NOT NULL,
    measuremeta_id integer NOT NULL,
    measurement_id integer NOT NULL,
    sample_no character varying(50),
    measure_phase character varying(100) NOT NULL,
    method character varying(100) NOT NULL,
    units character varying(25) NOT NULL,
    measure_value numeric(10,5),
    v_error numeric(10,5),
    v_error_units character varying(25),
    v_type character varying(100),
    v_n integer
);

CREATE SEQUENCE macrostrat.measures_new_id_seq1
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE macrostrat.measures_new_id_seq1 OWNED BY macrostrat.measures.id;

CREATE TABLE macrostrat.pbdb_collections (
    collection_no integer NOT NULL,
    name text,
    early_age numeric,
    late_age numeric,
    grp text,
    grp_clean text,
    formation text,
    formation_clean text,
    member text,
    member_clean text,
    lithologies text[],
    environment text,
    reference_no integer,
    n_occs integer,
    geom public.geometry
);

CREATE TABLE macrostrat.pbdb_collections_strat_names (
    collection_no integer NOT NULL,
    strat_name_id integer NOT NULL,
    basis_col text
);

CREATE TABLE macrostrat.places (
    place_id integer NOT NULL,
    name text,
    abbrev text,
    postal text,
    country text,
    country_abbrev text,
    geom public.geometry
);

CREATE TABLE macrostrat.refs (
    id integer NOT NULL,
    pub_year integer,
    author character varying(255),
    ref text,
    doi character varying(40),
    compilation_code character varying(100),
    url text,
    rgeom public.geometry
);

CREATE TABLE macrostrat.strat_name_footprints (
    strat_name_id integer,
    name_no_lith character varying(100),
    rank_name character varying(200),
    concept_id integer,
    concept_names integer[],
    geom public.geometry,
    best_t_age numeric,
    best_b_age numeric
);

CREATE TABLE macrostrat.strat_names (
    id integer NOT NULL,
    strat_name character varying(100) NOT NULL,
    rank character varying(50),
    ref_id integer NOT NULL,
    concept_id integer
);

CREATE TABLE macrostrat.strat_names_meta (
    concept_id integer NOT NULL,
    orig_id integer NOT NULL,
    name character varying(40),
    geologic_age text,
    interval_id integer NOT NULL,
    b_int integer NOT NULL,
    t_int integer NOT NULL,
    usage_notes text,
    other text,
    province text,
    url character varying(150),
    ref_id integer NOT NULL
);

CREATE SEQUENCE macrostrat.strat_names_new_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE macrostrat.strat_names_new_id_seq OWNED BY macrostrat.strat_names.id;

CREATE TABLE macrostrat.strat_names_places (
    strat_name_id integer NOT NULL,
    place_id integer NOT NULL
);

CREATE TABLE macrostrat.timescales (
    id integer NOT NULL,
    timescale character varying(100),
    ref_id integer
);

CREATE TABLE macrostrat.timescales_intervals (
    timescale_id integer,
    interval_id integer
);

CREATE TABLE macrostrat.unit_econs (
    id integer NOT NULL,
    unit_id integer,
    econ_id integer,
    ref_id integer,
    date_mod text
);

CREATE TABLE macrostrat.unit_environs (
    id integer NOT NULL,
    unit_id integer,
    environ_id integer,
    ref_id integer,
    date_mod text
);

CREATE TABLE macrostrat.unit_lith_atts (
    id integer NOT NULL,
    unit_lith_id integer,
    lith_att_id integer,
    ref_id integer,
    date_mod text
);

CREATE TABLE macrostrat.unit_liths (
    id integer NOT NULL,
    lith_id integer,
    unit_id integer,
    prop text,
    dom text,
    comp_prop numeric,
    mod_prop numeric,
    toc numeric,
    ref_id integer,
    date_mod text
);

CREATE TABLE macrostrat.unit_measures (
    id integer NOT NULL,
    measuremeta_id integer NOT NULL,
    unit_id integer NOT NULL,
    strat_name_id integer NOT NULL,
    match_basis character varying(10) NOT NULL,
    rel_position numeric(6,5)
);

CREATE SEQUENCE macrostrat.unit_measures_new_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE macrostrat.unit_measures_new_id_seq OWNED BY macrostrat.unit_measures.id;

CREATE TABLE macrostrat.unit_strat_names (
    id integer NOT NULL,
    unit_id integer NOT NULL,
    strat_name_id integer NOT NULL
);

CREATE SEQUENCE macrostrat.unit_strat_names_new_id_seq1
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE macrostrat.unit_strat_names_new_id_seq1 OWNED BY macrostrat.unit_strat_names.id;

CREATE TABLE macrostrat.units (
    id integer NOT NULL,
    strat_name character varying(150),
    color character varying(20),
    outcrop character varying(20),
    fo integer,
    fo_h integer,
    lo integer,
    lo_h integer,
    position_bottom numeric,
    position_top numeric,
    max_thick numeric,
    min_thick numeric,
    section_id integer,
    col_id integer
);

CREATE TABLE macrostrat.units_sections (
    id integer NOT NULL,
    unit_id integer NOT NULL,
    section_id integer NOT NULL,
    col_id integer NOT NULL
);

CREATE SEQUENCE macrostrat.units_sections_new_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE macrostrat.units_sections_new_id_seq OWNED BY macrostrat.units_sections.id;

CREATE SEQUENCE public.map_ids
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

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

CREATE TABLE maps.legend (
    legend_id integer NOT NULL,
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
    large_area numeric
);

CREATE SEQUENCE maps.legend_legend_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE maps.legend_legend_id_seq OWNED BY maps.legend.legend_id;

CREATE TABLE maps.legend_liths (
    legend_id integer NOT NULL,
    lith_id integer NOT NULL,
    basis_col text NOT NULL
);

CREATE TABLE maps.manual_matches (
    match_id integer NOT NULL,
    map_id integer NOT NULL,
    strat_name_id integer,
    unit_id integer,
    addition boolean DEFAULT false,
    removal boolean DEFAULT false,
    type character varying(20)
);

CREATE SEQUENCE maps.manual_matches_match_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE maps.manual_matches_match_id_seq OWNED BY maps.manual_matches.match_id;

CREATE TABLE maps.map_legend (
    legend_id integer NOT NULL,
    map_id integer NOT NULL
);

CREATE TABLE maps.map_liths (
    map_id integer NOT NULL,
    lith_id integer NOT NULL,
    basis_col character varying(50)
);

CREATE TABLE maps.map_strat_names (
    map_id integer NOT NULL,
    strat_name_id integer NOT NULL,
    basis_col character varying(50)
);

CREATE TABLE maps.map_units (
    map_id integer NOT NULL,
    unit_id integer NOT NULL,
    basis_col character varying(50)
);

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
    rgeom public.geometry,
    display_scales text[],
    web_geom public.geometry,
    new_priority integer DEFAULT 0,
    status_code text DEFAULT 'active'::text
);

CREATE SEQUENCE maps.sources_source_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE maps.sources_source_id_seq OWNED BY maps.sources.source_id;

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

CREATE TABLE points.points (
    source_id integer NOT NULL,
    strike integer,
    dip integer,
    dip_dir integer,
    point_type character varying(100),
    certainty character varying(100),
    comments text,
    geom public.geometry(Geometry,4326),
    point_id integer NOT NULL,
    orig_id integer,
    CONSTRAINT dip_lt_90 CHECK ((dip <= 90)),
    CONSTRAINT dip_positive CHECK ((dip >= 0)),
    CONSTRAINT direction_lt_360 CHECK ((dip_dir <= 360)),
    CONSTRAINT direction_positive CHECK ((dip_dir >= 0)),
    CONSTRAINT enforce_point_geom CHECK (public.st_isvalid(geom)),
    CONSTRAINT strike_lt_360 CHECK ((strike <= 360)),
    CONSTRAINT strike_positive CHECK ((strike >= 0))
);

CREATE SEQUENCE points.points_point_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE points.points_point_id_seq OWNED BY points.points.point_id;

CREATE TABLE public.impervious (
    rid integer NOT NULL,
    rast public.raster
);

CREATE SEQUENCE public.impervious_rid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.impervious_rid_seq OWNED BY public.impervious.rid;

CREATE TABLE public.land (
    gid integer NOT NULL,
    scalerank numeric(10,0),
    featurecla character varying(32),
    geom public.geometry(MultiPolygon,4326)
);

CREATE SEQUENCE public.land_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.land_gid_seq OWNED BY public.land.gid;

CREATE TABLE public.lookup_large (
    map_id integer,
    unit_ids integer[],
    strat_name_ids integer[],
    lith_ids integer[],
    best_age_top numeric,
    best_age_bottom numeric,
    color character varying(20),
    lith_types text[],
    lith_classes text[],
    concept_ids integer[],
    strat_name_children integer[],
    legend_id integer
);

CREATE TABLE public.lookup_medium (
    map_id integer,
    unit_ids integer[],
    strat_name_ids integer[],
    lith_ids integer[],
    best_age_top numeric,
    best_age_bottom numeric,
    color character varying(20),
    lith_types text[],
    lith_classes text[],
    concept_ids integer[],
    strat_name_children integer[],
    legend_id integer
);

CREATE TABLE public.lookup_small (
    map_id integer,
    unit_ids integer[],
    strat_name_ids integer[],
    lith_ids integer[],
    best_age_top numeric,
    best_age_bottom numeric,
    color character varying(20),
    lith_types text[],
    lith_classes text[],
    concept_ids integer[],
    strat_name_children integer[],
    legend_id integer
);

CREATE TABLE public.lookup_tiny (
    map_id integer,
    unit_ids integer[],
    strat_name_ids integer[],
    lith_ids integer[],
    best_age_top numeric,
    best_age_bottom numeric,
    color character varying(20),
    lith_types text[],
    lith_classes text[],
    concept_ids integer[],
    strat_name_children integer[],
    legend_id integer
);
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.lookup_tiny TO rockd;


CREATE TABLE public.macrostrat_union (
    id integer NOT NULL,
    geom public.geometry
);

CREATE SEQUENCE public.macrostrat_union_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.macrostrat_union_id_seq OWNED BY public.macrostrat_union.id;

CREATE TABLE public.ref_boundaries (
    ref_id integer,
    ref text,
    geom public.geometry
);

CREATE TABLE public.units (
    mapunit text,
    description text
);

ALTER TABLE ONLY geologic_boundaries.boundaries ALTER COLUMN boundary_id SET DEFAULT nextval('geologic_boundaries.boundaries_boundary_id_seq'::regclass);

ALTER TABLE ONLY hexgrids.r10 ALTER COLUMN hex_id SET DEFAULT nextval('hexgrids.r10_ogc_fid_seq'::regclass);

ALTER TABLE ONLY hexgrids.r11 ALTER COLUMN hex_id SET DEFAULT nextval('hexgrids.r11_ogc_fid_seq'::regclass);

ALTER TABLE ONLY hexgrids.r12 ALTER COLUMN hex_id SET DEFAULT nextval('hexgrids.r12_ogc_fid_seq'::regclass);

ALTER TABLE ONLY hexgrids.r5 ALTER COLUMN hex_id SET DEFAULT nextval('hexgrids.r5_ogc_fid_seq'::regclass);

ALTER TABLE ONLY hexgrids.r6 ALTER COLUMN hex_id SET DEFAULT nextval('hexgrids.r6_ogc_fid_seq'::regclass);

ALTER TABLE ONLY hexgrids.r7 ALTER COLUMN hex_id SET DEFAULT nextval('hexgrids.r7_ogc_fid_seq'::regclass);

ALTER TABLE ONLY hexgrids.r8 ALTER COLUMN hex_id SET DEFAULT nextval('hexgrids.r8_ogc_fid_seq'::regclass);

ALTER TABLE ONLY hexgrids.r9 ALTER COLUMN hex_id SET DEFAULT nextval('hexgrids.r9_ogc_fid_seq'::regclass);

ALTER TABLE ONLY macrostrat.intervals ALTER COLUMN id SET DEFAULT nextval('macrostrat.intervals_new_id_seq1'::regclass);

ALTER TABLE ONLY macrostrat.measurements ALTER COLUMN id SET DEFAULT nextval('macrostrat.measurements_new_id_seq'::regclass);

ALTER TABLE ONLY macrostrat.measuremeta ALTER COLUMN id SET DEFAULT nextval('macrostrat.measuremeta_new_id_seq1'::regclass);

ALTER TABLE ONLY macrostrat.measures ALTER COLUMN id SET DEFAULT nextval('macrostrat.measures_new_id_seq1'::regclass);

ALTER TABLE ONLY macrostrat.strat_names ALTER COLUMN id SET DEFAULT nextval('macrostrat.strat_names_new_id_seq'::regclass);

ALTER TABLE ONLY macrostrat.unit_measures ALTER COLUMN id SET DEFAULT nextval('macrostrat.unit_measures_new_id_seq'::regclass);

ALTER TABLE ONLY macrostrat.unit_strat_names ALTER COLUMN id SET DEFAULT nextval('macrostrat.unit_strat_names_new_id_seq1'::regclass);

ALTER TABLE ONLY macrostrat.units_sections ALTER COLUMN id SET DEFAULT nextval('macrostrat.units_sections_new_id_seq'::regclass);

ALTER TABLE ONLY maps.legend ALTER COLUMN legend_id SET DEFAULT nextval('maps.legend_legend_id_seq'::regclass);

ALTER TABLE ONLY maps.manual_matches ALTER COLUMN match_id SET DEFAULT nextval('maps.manual_matches_match_id_seq'::regclass);

ALTER TABLE ONLY maps.sources ALTER COLUMN source_id SET DEFAULT nextval('maps.sources_source_id_seq'::regclass);

ALTER TABLE ONLY points.points ALTER COLUMN point_id SET DEFAULT nextval('points.points_point_id_seq'::regclass);

ALTER TABLE ONLY public.impervious ALTER COLUMN rid SET DEFAULT nextval('public.impervious_rid_seq'::regclass);

ALTER TABLE ONLY public.land ALTER COLUMN gid SET DEFAULT nextval('public.land_gid_seq'::regclass);

ALTER TABLE ONLY public.macrostrat_union ALTER COLUMN id SET DEFAULT nextval('public.macrostrat_union_id_seq'::regclass);

ALTER TABLE ONLY geologic_boundaries.sources
    ADD CONSTRAINT sources_pkey PRIMARY KEY (source_id);

ALTER TABLE ONLY hexgrids.hexgrids
    ADD CONSTRAINT hexgrids_pkey PRIMARY KEY (hex_id);

ALTER TABLE ONLY hexgrids.r10
    ADD CONSTRAINT r10_pkey PRIMARY KEY (hex_id);

ALTER TABLE ONLY hexgrids.r11
    ADD CONSTRAINT r11_pkey PRIMARY KEY (hex_id);

ALTER TABLE ONLY hexgrids.r12
    ADD CONSTRAINT r12_pkey PRIMARY KEY (hex_id);

ALTER TABLE ONLY hexgrids.r5
    ADD CONSTRAINT r5_pkey PRIMARY KEY (hex_id);

ALTER TABLE ONLY hexgrids.r6
    ADD CONSTRAINT r6_pkey PRIMARY KEY (hex_id);

ALTER TABLE ONLY hexgrids.r7
    ADD CONSTRAINT r7_pkey PRIMARY KEY (hex_id);

ALTER TABLE ONLY hexgrids.r8
    ADD CONSTRAINT r8_pkey PRIMARY KEY (hex_id);

ALTER TABLE ONLY hexgrids.r9
    ADD CONSTRAINT r9_pkey PRIMARY KEY (hex_id);

ALTER TABLE ONLY lines.large
    ADD CONSTRAINT large_pkey PRIMARY KEY (line_id);

ALTER TABLE ONLY lines.medium
    ADD CONSTRAINT medium_pkey PRIMARY KEY (line_id);

ALTER TABLE ONLY lines.small
    ADD CONSTRAINT small_pkey PRIMARY KEY (line_id);

ALTER TABLE ONLY lines.tiny
    ADD CONSTRAINT tiny_pkey PRIMARY KEY (line_id);

ALTER TABLE ONLY macrostrat.col_areas
    ADD CONSTRAINT col_areas_new_pkey PRIMARY KEY (id);

ALTER TABLE ONLY macrostrat.col_groups
    ADD CONSTRAINT col_groups_new_pkey1 PRIMARY KEY (id);

ALTER TABLE ONLY macrostrat.col_refs
    ADD CONSTRAINT col_refs_new_pkey1 PRIMARY KEY (id);

ALTER TABLE ONLY macrostrat.cols
    ADD CONSTRAINT cols_new_pkey PRIMARY KEY (id);

ALTER TABLE ONLY macrostrat.econs
    ADD CONSTRAINT econs_new_pkey PRIMARY KEY (id);

ALTER TABLE ONLY macrostrat.environs
    ADD CONSTRAINT environs_new_pkey1 PRIMARY KEY (id);

ALTER TABLE ONLY macrostrat.grainsize
    ADD CONSTRAINT grainsize_pkey PRIMARY KEY (grain_id);

ALTER TABLE ONLY macrostrat.lith_atts
    ADD CONSTRAINT lith_atts_new_pkey1 PRIMARY KEY (id);

ALTER TABLE ONLY macrostrat.liths
    ADD CONSTRAINT liths_new_pkey1 PRIMARY KEY (id);

ALTER TABLE ONLY macrostrat.lookup_units
    ADD CONSTRAINT lookup_units_new_pkey1 PRIMARY KEY (unit_id);

ALTER TABLE ONLY macrostrat.measurements
    ADD CONSTRAINT measurements_new_pkey PRIMARY KEY (id);

ALTER TABLE ONLY macrostrat.measuremeta
    ADD CONSTRAINT measuremeta_new_pkey PRIMARY KEY (id);

ALTER TABLE ONLY macrostrat.places
    ADD CONSTRAINT places_new_pkey PRIMARY KEY (place_id);

ALTER TABLE ONLY macrostrat.refs
    ADD CONSTRAINT refs_new_pkey1 PRIMARY KEY (id);

ALTER TABLE ONLY macrostrat.strat_names_meta
    ADD CONSTRAINT strat_names_meta_new_pkey1 PRIMARY KEY (concept_id);

ALTER TABLE ONLY macrostrat.strat_names
    ADD CONSTRAINT strat_names_new_pkey PRIMARY KEY (id);

ALTER TABLE ONLY macrostrat.timescales
    ADD CONSTRAINT timescales_new_pkey1 PRIMARY KEY (id);

ALTER TABLE ONLY macrostrat.unit_econs
    ADD CONSTRAINT unit_econs_new_pkey1 PRIMARY KEY (id);

ALTER TABLE ONLY macrostrat.unit_environs
    ADD CONSTRAINT unit_environs_new_pkey1 PRIMARY KEY (id);

ALTER TABLE ONLY macrostrat.unit_lith_atts
    ADD CONSTRAINT unit_lith_atts_new_pkey1 PRIMARY KEY (id);

ALTER TABLE ONLY macrostrat.unit_liths
    ADD CONSTRAINT unit_liths_new_pkey1 PRIMARY KEY (id);

ALTER TABLE ONLY macrostrat.unit_measures
    ADD CONSTRAINT unit_measures_new_pkey PRIMARY KEY (id);

ALTER TABLE ONLY macrostrat.unit_strat_names
    ADD CONSTRAINT unit_strat_names_new_pkey1 PRIMARY KEY (id);

ALTER TABLE ONLY macrostrat.units
    ADD CONSTRAINT units_new_pkey PRIMARY KEY (id);

ALTER TABLE ONLY macrostrat.units_sections
    ADD CONSTRAINT units_sections_new_pkey PRIMARY KEY (id);

ALTER TABLE ONLY maps.large
    ADD CONSTRAINT large_pkey PRIMARY KEY (map_id);

ALTER TABLE ONLY maps.legend_liths
    ADD CONSTRAINT legend_liths_legend_id_lith_id_basis_col_key UNIQUE (legend_id, lith_id, basis_col);

ALTER TABLE ONLY maps.legend
    ADD CONSTRAINT legend_pkey PRIMARY KEY (legend_id);

ALTER TABLE ONLY maps.map_legend
    ADD CONSTRAINT map_legend_legend_id_map_id_key UNIQUE (legend_id, map_id);

ALTER TABLE ONLY maps.medium
    ADD CONSTRAINT medium_pkey PRIMARY KEY (map_id);

ALTER TABLE ONLY maps.small
    ADD CONSTRAINT small_pkey PRIMARY KEY (map_id);

ALTER TABLE ONLY maps.sources
    ADD CONSTRAINT sources_source_id_key UNIQUE (source_id);

ALTER TABLE ONLY maps.tiny
    ADD CONSTRAINT tiny_pkey PRIMARY KEY (map_id);

ALTER TABLE ONLY public.impervious
    ADD CONSTRAINT impervious_pkey PRIMARY KEY (rid);

ALTER TABLE ONLY public.land
    ADD CONSTRAINT land_pkey PRIMARY KEY (gid);

ALTER TABLE ONLY public.macrostrat_union
    ADD CONSTRAINT macrostrat_union_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.test_rgeom
    ADD CONSTRAINT test_rgeom_pkey PRIMARY KEY (gid);

CREATE INDEX flat_large_geom_idx ON carto.flat_large USING gist (geom);

CREATE INDEX flat_large_map_id_idx ON carto.flat_large USING btree (map_id);

CREATE INDEX large_new_geom_idx ON carto.large USING gist (geom);

CREATE INDEX large_new_map_id_idx ON carto.large USING btree (map_id);

CREATE INDEX lines_large_new_geom_idx1 ON carto.lines_large USING gist (geom);

CREATE INDEX lines_large_new_line_id_idx1 ON carto.lines_large USING btree (line_id);

CREATE INDEX lines_medium_new_geom_idx1 ON carto.lines_medium USING gist (geom);

CREATE INDEX lines_medium_new_line_id_idx1 ON carto.lines_medium USING btree (line_id);

CREATE INDEX lines_small_new_geom_idx1 ON carto.lines_small USING gist (geom);

CREATE INDEX lines_small_new_line_id_idx1 ON carto.lines_small USING btree (line_id);

CREATE INDEX lines_tiny_new_geom_idx1 ON carto.lines_tiny USING gist (geom);

CREATE INDEX lines_tiny_new_line_id_idx1 ON carto.lines_tiny USING btree (line_id);

CREATE INDEX medium_new_geom_idx ON carto.medium USING gist (geom);

CREATE INDEX medium_new_map_id_idx ON carto.medium USING btree (map_id);

CREATE INDEX small_new_geom_idx ON carto.small USING gist (geom);

CREATE INDEX small_new_map_id_idx ON carto.small USING btree (map_id);

CREATE INDEX tiny_new_geom_idx ON carto.tiny USING gist (geom);

CREATE INDEX tiny_new_map_id_idx ON carto.tiny USING btree (map_id);

CREATE INDEX hex_index_hex_id_idx ON carto_new.hex_index USING btree (hex_id);

CREATE INDEX hex_index_map_id_idx ON carto_new.hex_index USING btree (map_id);

CREATE INDEX hex_index_scale_idx ON carto_new.hex_index USING btree (scale);

CREATE INDEX large_geom_idx ON carto_new.large USING gist (geom);

CREATE INDEX large_map_id_idx ON carto_new.large USING btree (map_id);

CREATE INDEX lines_large_geom_idx ON carto_new.lines_large USING gist (geom);

CREATE INDEX lines_large_line_id_idx ON carto_new.lines_large USING btree (line_id);

CREATE INDEX lines_medium_geom_idx ON carto_new.lines_medium USING gist (geom);

CREATE INDEX lines_medium_line_id_idx ON carto_new.lines_medium USING btree (line_id);

CREATE INDEX lines_small_geom_idx ON carto_new.lines_small USING gist (geom);

CREATE INDEX lines_small_line_id_idx ON carto_new.lines_small USING btree (line_id);

CREATE INDEX lines_tiny_geom_idx ON carto_new.lines_tiny USING gist (geom);

CREATE INDEX lines_tiny_line_id_idx ON carto_new.lines_tiny USING btree (line_id);

CREATE INDEX medium_geom_idx ON carto_new.medium USING gist (geom);

CREATE INDEX medium_map_id_idx ON carto_new.medium USING btree (map_id);

CREATE INDEX pbdb_hex_index_collection_no_idx ON carto_new.pbdb_hex_index USING btree (collection_no);

CREATE INDEX pbdb_hex_index_hex_id_idx ON carto_new.pbdb_hex_index USING btree (hex_id);

CREATE INDEX pbdb_hex_index_scale_idx ON carto_new.pbdb_hex_index USING btree (scale);

CREATE INDEX small_geom_idx ON carto_new.small USING gist (geom);

CREATE INDEX small_map_id_idx ON carto_new.small USING btree (map_id);

CREATE INDEX tiny_geom_idx ON carto_new.tiny USING gist (geom);

CREATE INDEX tiny_map_id_idx ON carto_new.tiny USING btree (map_id);

CREATE INDEX boundaries_boundary_class_idx ON geologic_boundaries.boundaries USING btree (boundary_class);

CREATE INDEX boundaries_boundary_id_idx ON geologic_boundaries.boundaries USING btree (boundary_id);

CREATE INDEX boundaries_geom_idx ON geologic_boundaries.boundaries USING gist (geom);

CREATE INDEX boundaries_orig_id_idx ON geologic_boundaries.boundaries USING btree (orig_id);

CREATE INDEX boundaries_source_id_idx ON geologic_boundaries.boundaries USING btree (source_id);

CREATE INDEX bedrock_index_hex_id_idx ON hexgrids.bedrock_index USING btree (hex_id);

CREATE UNIQUE INDEX bedrock_index_legend_id_hex_id_idx ON hexgrids.bedrock_index USING btree (legend_id, hex_id);

CREATE INDEX bedrock_index_legend_id_idx ON hexgrids.bedrock_index USING btree (legend_id);

CREATE INDEX hexgrids_geom_idx ON hexgrids.hexgrids USING gist (geom);

CREATE INDEX hexgrids_res_idx ON hexgrids.hexgrids USING btree (res);

CREATE UNIQUE INDEX pbdb_index_collection_no_hex_id_idx ON hexgrids.pbdb_index USING btree (collection_no, hex_id);

CREATE INDEX pbdb_index_collection_no_idx ON hexgrids.pbdb_index USING btree (collection_no);

CREATE INDEX pbdb_index_hex_id_idx ON hexgrids.pbdb_index USING btree (hex_id);

CREATE INDEX r10_geom_geom_idx ON hexgrids.r10 USING gist (geom);

CREATE INDEX r10_geom_idx ON hexgrids.r10 USING gist (geom);

CREATE INDEX r10_web_geom_idx ON hexgrids.r10 USING gist (web_geom);

CREATE INDEX r11_geom_geom_idx ON hexgrids.r11 USING gist (geom);

CREATE INDEX r11_web_geom_idx ON hexgrids.r11 USING gist (web_geom);

CREATE INDEX r12_geom_geom_idx ON hexgrids.r12 USING gist (geom);

CREATE INDEX r12_web_geom_idx ON hexgrids.r12 USING gist (web_geom);

CREATE INDEX r5_geom_idx ON hexgrids.r5 USING gist (geom);

CREATE INDEX r5_web_geom_idx ON hexgrids.r5 USING gist (web_geom);

CREATE INDEX r6_geom_idx ON hexgrids.r6 USING gist (geom);

CREATE INDEX r6_web_geom_idx ON hexgrids.r6 USING gist (web_geom);

CREATE INDEX r7_geom_idx ON hexgrids.r7 USING gist (geom);

CREATE INDEX r7_geom_idx1 ON hexgrids.r7 USING gist (geom);

CREATE INDEX r7_geom_idx2 ON hexgrids.r7 USING gist (geom);

CREATE INDEX r7_web_geom_idx ON hexgrids.r7 USING gist (web_geom);

CREATE INDEX r8_geom_idx ON hexgrids.r8 USING gist (geom);

CREATE INDEX r8_geom_idx1 ON hexgrids.r8 USING gist (geom);

CREATE INDEX r8_geom_idx2 ON hexgrids.r8 USING gist (geom);

CREATE INDEX r8_web_geom_idx ON hexgrids.r8 USING gist (web_geom);

CREATE INDEX r9_geom_idx ON hexgrids.r9 USING gist (geom);

CREATE INDEX r9_geom_idx1 ON hexgrids.r9 USING gist (geom);

CREATE INDEX r9_web_geom_idx ON hexgrids.r9 USING gist (web_geom);

CREATE INDEX large_geom_idx ON lines.large USING gist (geom);

CREATE INDEX large_line_id_idx ON lines.large USING btree (line_id);

CREATE INDEX large_orig_id_idx ON lines.large USING btree (orig_id);

CREATE INDEX large_source_id_idx ON lines.large USING btree (source_id);

CREATE INDEX medium_geom_idx ON lines.medium USING gist (geom);

CREATE INDEX medium_line_id_idx ON lines.medium USING btree (line_id);

CREATE INDEX medium_orig_id_idx ON lines.medium USING btree (orig_id);

CREATE INDEX medium_source_id_idx ON lines.medium USING btree (source_id);

CREATE INDEX small_geom_idx ON lines.small USING gist (geom);

CREATE INDEX small_source_id_idx ON lines.small USING btree (source_id);

CREATE INDEX tiny_geom_idx ON lines.tiny USING gist (geom);

CREATE INDEX tiny_source_id_idx ON lines.tiny USING btree (source_id);

CREATE INDEX autocomplete_new_category_idx1 ON macrostrat.autocomplete USING btree (category);

CREATE INDEX autocomplete_new_id_idx1 ON macrostrat.autocomplete USING btree (id);

CREATE INDEX autocomplete_new_name_idx1 ON macrostrat.autocomplete USING btree (name);

CREATE INDEX autocomplete_new_type_idx1 ON macrostrat.autocomplete USING btree (type);

CREATE INDEX col_areas_new_col_area_idx ON macrostrat.col_areas USING gist (col_area);

CREATE INDEX col_areas_new_col_id_idx ON macrostrat.col_areas USING btree (col_id);

CREATE INDEX col_groups_new_id_idx1 ON macrostrat.col_groups USING btree (id);

CREATE INDEX col_refs_new_col_id_idx1 ON macrostrat.col_refs USING btree (col_id);

CREATE INDEX col_refs_new_ref_id_idx1 ON macrostrat.col_refs USING btree (ref_id);

CREATE INDEX cols_new_col_group_id_idx ON macrostrat.cols USING btree (col_group_id);

CREATE INDEX cols_new_coordinate_idx ON macrostrat.cols USING gist (coordinate);

CREATE INDEX cols_new_poly_geom_idx ON macrostrat.cols USING gist (poly_geom);

CREATE INDEX cols_new_project_id_idx ON macrostrat.cols USING btree (project_id);

CREATE INDEX cols_new_status_code_idx ON macrostrat.cols USING btree (status_code);

CREATE INDEX concepts_places_new_concept_id_idx ON macrostrat.concepts_places USING btree (concept_id);

CREATE INDEX concepts_places_new_place_id_idx ON macrostrat.concepts_places USING btree (place_id);

CREATE INDEX intervals_new_age_bottom_idx1 ON macrostrat.intervals USING btree (age_bottom);

CREATE INDEX intervals_new_age_top_idx1 ON macrostrat.intervals USING btree (age_top);

CREATE INDEX intervals_new_id_idx1 ON macrostrat.intervals USING btree (id);

CREATE INDEX intervals_new_interval_name_idx1 ON macrostrat.intervals USING btree (interval_name);

CREATE INDEX intervals_new_interval_type_idx1 ON macrostrat.intervals USING btree (interval_type);

CREATE INDEX lith_atts_new_att_type_idx1 ON macrostrat.lith_atts USING btree (att_type);

CREATE INDEX lith_atts_new_lith_att_idx1 ON macrostrat.lith_atts USING btree (lith_att);

CREATE INDEX liths_new_lith_class_idx1 ON macrostrat.liths USING btree (lith_class);

CREATE INDEX liths_new_lith_idx1 ON macrostrat.liths USING btree (lith);

CREATE INDEX liths_new_lith_type_idx1 ON macrostrat.liths USING btree (lith_type);

CREATE INDEX lookup_strat_names_new_bed_id_idx ON macrostrat.lookup_strat_names USING btree (bed_id);

CREATE INDEX lookup_strat_names_new_concept_id_idx ON macrostrat.lookup_strat_names USING btree (concept_id);

CREATE INDEX lookup_strat_names_new_fm_id_idx ON macrostrat.lookup_strat_names USING btree (fm_id);

CREATE INDEX lookup_strat_names_new_gp_id_idx ON macrostrat.lookup_strat_names USING btree (gp_id);

CREATE INDEX lookup_strat_names_new_mbr_id_idx ON macrostrat.lookup_strat_names USING btree (mbr_id);

CREATE INDEX lookup_strat_names_new_sgp_id_idx ON macrostrat.lookup_strat_names USING btree (sgp_id);

CREATE INDEX lookup_strat_names_new_strat_name_id_idx ON macrostrat.lookup_strat_names USING btree (strat_name_id);

CREATE INDEX lookup_strat_names_new_strat_name_idx ON macrostrat.lookup_strat_names USING btree (strat_name);

CREATE INDEX lookup_unit_attrs_api_new_unit_id_idx1 ON macrostrat.lookup_unit_attrs_api USING btree (unit_id);

CREATE INDEX lookup_unit_intervals_new_best_interval_id_idx ON macrostrat.lookup_unit_intervals USING btree (best_interval_id);

CREATE INDEX lookup_unit_intervals_new_unit_id_idx ON macrostrat.lookup_unit_intervals USING btree (unit_id);

CREATE INDEX lookup_unit_liths_new_unit_id_idx ON macrostrat.lookup_unit_liths USING btree (unit_id);

CREATE INDEX lookup_units_new_b_int_idx1 ON macrostrat.lookup_units USING btree (b_int);

CREATE INDEX lookup_units_new_project_id_idx1 ON macrostrat.lookup_units USING btree (project_id);

CREATE INDEX lookup_units_new_t_int_idx1 ON macrostrat.lookup_units USING btree (t_int);

CREATE INDEX measurements_new_id_idx ON macrostrat.measurements USING btree (id);

CREATE INDEX measurements_new_measurement_class_idx ON macrostrat.measurements USING btree (measurement_class);

CREATE INDEX measurements_new_measurement_type_idx ON macrostrat.measurements USING btree (measurement_type);

CREATE INDEX measuremeta_new_lith_att_id_idx1 ON macrostrat.measuremeta USING btree (lith_att_id);

CREATE INDEX measuremeta_new_lith_id_idx1 ON macrostrat.measuremeta USING btree (lith_id);

CREATE INDEX measuremeta_new_ref_id_idx1 ON macrostrat.measuremeta USING btree (ref_id);

CREATE INDEX measures_new_measurement_id_idx1 ON macrostrat.measures USING btree (measurement_id);

CREATE INDEX measures_new_measuremeta_id_idx1 ON macrostrat.measures USING btree (measuremeta_id);

CREATE INDEX pbdb_collections_new_collection_no_idx1 ON macrostrat.pbdb_collections USING btree (collection_no);

CREATE INDEX pbdb_collections_new_early_age_idx1 ON macrostrat.pbdb_collections USING btree (early_age);

CREATE INDEX pbdb_collections_new_geom_idx1 ON macrostrat.pbdb_collections USING gist (geom);

CREATE INDEX pbdb_collections_new_late_age_idx1 ON macrostrat.pbdb_collections USING btree (late_age);

CREATE INDEX places_new_geom_idx ON macrostrat.places USING gist (geom);

CREATE INDEX refs_new_rgeom_idx1 ON macrostrat.refs USING gist (rgeom);

CREATE INDEX strat_name_footprints_new_geom_idx ON macrostrat.strat_name_footprints USING gist (geom);

CREATE INDEX strat_name_footprints_new_strat_name_id_idx ON macrostrat.strat_name_footprints USING btree (strat_name_id);

CREATE INDEX strat_names_meta_new_b_int_idx1 ON macrostrat.strat_names_meta USING btree (b_int);

CREATE INDEX strat_names_meta_new_interval_id_idx1 ON macrostrat.strat_names_meta USING btree (interval_id);

CREATE INDEX strat_names_meta_new_ref_id_idx1 ON macrostrat.strat_names_meta USING btree (ref_id);

CREATE INDEX strat_names_meta_new_t_int_idx1 ON macrostrat.strat_names_meta USING btree (t_int);

CREATE INDEX strat_names_new_concept_id_idx ON macrostrat.strat_names USING btree (concept_id);

CREATE INDEX strat_names_new_rank_idx ON macrostrat.strat_names USING btree (rank);

CREATE INDEX strat_names_new_ref_id_idx ON macrostrat.strat_names USING btree (ref_id);

CREATE INDEX strat_names_new_strat_name_idx ON macrostrat.strat_names USING btree (strat_name);

CREATE INDEX strat_names_places_new_place_id_idx1 ON macrostrat.strat_names_places USING btree (place_id);

CREATE INDEX strat_names_places_new_strat_name_id_idx1 ON macrostrat.strat_names_places USING btree (strat_name_id);

CREATE INDEX timescales_intervals_new_interval_id_idx1 ON macrostrat.timescales_intervals USING btree (interval_id);

CREATE INDEX timescales_intervals_new_timescale_id_idx1 ON macrostrat.timescales_intervals USING btree (timescale_id);

CREATE INDEX timescales_new_ref_id_idx1 ON macrostrat.timescales USING btree (ref_id);

CREATE INDEX timescales_new_timescale_idx1 ON macrostrat.timescales USING btree (timescale);

CREATE INDEX unit_econs_new_econ_id_idx1 ON macrostrat.unit_econs USING btree (econ_id);

CREATE INDEX unit_econs_new_ref_id_idx1 ON macrostrat.unit_econs USING btree (ref_id);

CREATE INDEX unit_econs_new_unit_id_idx1 ON macrostrat.unit_econs USING btree (unit_id);

CREATE INDEX unit_environs_new_environ_id_idx1 ON macrostrat.unit_environs USING btree (environ_id);

CREATE INDEX unit_environs_new_ref_id_idx1 ON macrostrat.unit_environs USING btree (ref_id);

CREATE INDEX unit_environs_new_unit_id_idx1 ON macrostrat.unit_environs USING btree (unit_id);

CREATE INDEX unit_lith_atts_new_lith_att_id_idx1 ON macrostrat.unit_lith_atts USING btree (lith_att_id);

CREATE INDEX unit_lith_atts_new_ref_id_idx1 ON macrostrat.unit_lith_atts USING btree (ref_id);

CREATE INDEX unit_lith_atts_new_unit_lith_id_idx1 ON macrostrat.unit_lith_atts USING btree (unit_lith_id);

CREATE INDEX unit_liths_new_lith_id_idx1 ON macrostrat.unit_liths USING btree (lith_id);

CREATE INDEX unit_liths_new_ref_id_idx1 ON macrostrat.unit_liths USING btree (ref_id);

CREATE INDEX unit_liths_new_unit_id_idx1 ON macrostrat.unit_liths USING btree (unit_id);

CREATE INDEX unit_measures_new_measuremeta_id_idx ON macrostrat.unit_measures USING btree (measuremeta_id);

CREATE INDEX unit_measures_new_strat_name_id_idx ON macrostrat.unit_measures USING btree (strat_name_id);

CREATE INDEX unit_measures_new_unit_id_idx ON macrostrat.unit_measures USING btree (unit_id);

CREATE INDEX unit_strat_names_new_strat_name_id_idx1 ON macrostrat.unit_strat_names USING btree (strat_name_id);

CREATE INDEX unit_strat_names_new_unit_id_idx1 ON macrostrat.unit_strat_names USING btree (unit_id);

CREATE INDEX units_new_col_id_idx ON macrostrat.units USING btree (col_id);

CREATE INDEX units_new_color_idx ON macrostrat.units USING btree (color);

CREATE INDEX units_new_section_id_idx ON macrostrat.units USING btree (section_id);

CREATE INDEX units_new_strat_name_idx ON macrostrat.units USING btree (strat_name);

CREATE INDEX units_sections_new_col_id_idx ON macrostrat.units_sections USING btree (col_id);

CREATE INDEX units_sections_new_section_id_idx ON macrostrat.units_sections USING btree (section_id);

CREATE INDEX units_sections_new_unit_id_idx ON macrostrat.units_sections USING btree (unit_id);

CREATE INDEX large_b_interval_idx ON maps.large USING btree (b_interval);

CREATE INDEX large_geom_idx ON maps.large USING gist (geom);

CREATE INDEX large_name_idx ON maps.large USING btree (name);

CREATE INDEX large_orig_id_idx ON maps.large USING btree (orig_id);

CREATE INDEX large_source_id_idx ON maps.large USING btree (source_id);

CREATE INDEX large_t_interval_idx ON maps.large USING btree (t_interval);

CREATE INDEX legend_liths_legend_id_idx ON maps.legend_liths USING btree (legend_id);

CREATE INDEX legend_liths_lith_id_idx ON maps.legend_liths USING btree (lith_id);

CREATE INDEX legend_source_id_idx ON maps.legend USING btree (source_id);

CREATE INDEX manual_matches_map_id_idx ON maps.manual_matches USING btree (map_id);

CREATE INDEX manual_matches_strat_name_id_idx ON maps.manual_matches USING btree (strat_name_id);

CREATE INDEX manual_matches_unit_id_idx ON maps.manual_matches USING btree (unit_id);

CREATE INDEX map_legend_legend_id_idx ON maps.map_legend USING btree (legend_id);

CREATE INDEX map_legend_map_id_idx ON maps.map_legend USING btree (map_id);

CREATE INDEX map_liths_lith_id_idx ON maps.map_liths USING btree (lith_id);

CREATE INDEX map_liths_map_id_idx ON maps.map_liths USING btree (map_id);

CREATE INDEX map_strat_names_map_id_idx ON maps.map_strat_names USING btree (map_id);

CREATE INDEX map_strat_names_strat_name_id_idx ON maps.map_strat_names USING btree (strat_name_id);

CREATE INDEX map_units_map_id_idx ON maps.map_units USING btree (map_id);

CREATE INDEX map_units_unit_id_idx ON maps.map_units USING btree (unit_id);

CREATE INDEX medium_b_interval_idx ON maps.medium USING btree (b_interval);

CREATE INDEX medium_geom_idx ON maps.medium USING gist (geom);

CREATE INDEX medium_orig_id_idx ON maps.medium USING btree (orig_id);

CREATE INDEX medium_source_id_idx ON maps.medium USING btree (source_id);

CREATE INDEX medium_t_interval_idx ON maps.medium USING btree (t_interval);

CREATE INDEX small_b_interval_idx ON maps.small USING btree (b_interval);

CREATE INDEX small_geom_idx ON maps.small USING gist (geom);

CREATE INDEX small_orig_id_idx ON maps.small USING btree (orig_id);

CREATE INDEX small_source_id_idx ON maps.small USING btree (source_id);

CREATE INDEX small_t_interval_idx ON maps.small USING btree (t_interval);

CREATE INDEX sources_rgeom_idx ON maps.sources USING gist (rgeom);

CREATE INDEX sources_web_geom_idx ON maps.sources USING gist (web_geom);

CREATE INDEX tiny_b_interval_idx ON maps.tiny USING btree (b_interval);

CREATE INDEX tiny_geom_idx ON maps.tiny USING gist (geom);

CREATE INDEX tiny_orig_id_idx ON maps.tiny USING btree (orig_id);

CREATE INDEX tiny_source_id_idx ON maps.tiny USING btree (source_id);

CREATE INDEX tiny_t_interval_idx ON maps.tiny USING btree (t_interval);

CREATE INDEX points_geom_idx ON points.points USING gist (geom);

CREATE INDEX points_source_id_idx ON points.points USING btree (source_id);

CREATE INDEX impervious_st_convexhull_idx ON public.impervious USING gist (public.st_convexhull(rast));

CREATE INDEX land_geom_idx ON public.land USING gist (geom);

CREATE INDEX lookup_large_concept_ids_idx ON public.lookup_large USING gin (concept_ids);

CREATE INDEX lookup_large_legend_id_idx ON public.lookup_large USING btree (legend_id);

CREATE INDEX lookup_large_lith_ids_idx ON public.lookup_large USING gin (lith_ids);

CREATE INDEX lookup_large_map_id_idx ON public.lookup_large USING btree (map_id);

CREATE INDEX lookup_large_strat_name_children_idx ON public.lookup_large USING gin (strat_name_children);

CREATE INDEX lookup_medium_concept_ids_idx ON public.lookup_medium USING gin (concept_ids);

CREATE INDEX lookup_medium_legend_id_idx ON public.lookup_medium USING btree (legend_id);

CREATE INDEX lookup_medium_lith_ids_idx ON public.lookup_medium USING gin (lith_ids);

CREATE INDEX lookup_medium_map_id_idx ON public.lookup_medium USING btree (map_id);

CREATE INDEX lookup_medium_strat_name_children_idx ON public.lookup_medium USING gin (strat_name_children);

CREATE INDEX lookup_small_concept_ids_idx ON public.lookup_small USING gin (concept_ids);

CREATE INDEX lookup_small_legend_id_idx ON public.lookup_small USING btree (legend_id);

CREATE INDEX lookup_small_lith_ids_idx ON public.lookup_small USING gin (lith_ids);

CREATE INDEX lookup_small_map_id_idx ON public.lookup_small USING btree (map_id);

CREATE INDEX lookup_small_strat_name_children_idx ON public.lookup_small USING gin (strat_name_children);

CREATE INDEX lookup_tiny_concept_ids_idx ON public.lookup_tiny USING gin (concept_ids);

CREATE INDEX lookup_tiny_legend_id_idx ON public.lookup_tiny USING btree (legend_id);

CREATE INDEX lookup_tiny_lith_ids_idx ON public.lookup_tiny USING gin (lith_ids);

CREATE INDEX lookup_tiny_map_id_idx ON public.lookup_tiny USING btree (map_id);

CREATE INDEX lookup_tiny_strat_name_children_idx ON public.lookup_tiny USING gin (strat_name_children);

