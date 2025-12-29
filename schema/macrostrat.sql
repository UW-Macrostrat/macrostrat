--
-- pgschema database dump
--

-- Dumped from database version PostgreSQL 15.15
-- Dumped by pgschema version 1.5.1


--
-- Name: colors_color; Type: TYPE; Schema: -; Owner: -
--

CREATE TYPE colors_color AS ENUM (
    '',
    'blue',
    'blue dark',
    'blue green',
    'black',
    'yellow',
    'orange',
    'brown dark',
    'brown light',
    'tan',
    'green dark',
    'green light',
    'gray dark',
    'gray light',
    'pink',
    'purple',
    'red',
    'gray',
    'green',
    'brown',
    'steel blue',
    'white'
);

--
-- Name: cols_col_position; Type: TYPE; Schema: -; Owner: -
--

CREATE TYPE cols_col_position AS ENUM (
    '',
    'onshore',
    'offshore'
);

--
-- Name: cols_col_type; Type: TYPE; Schema: -; Owner: -
--

CREATE TYPE cols_col_type AS ENUM (
    'column',
    'section'
);

--
-- Name: cols_status_code; Type: TYPE; Schema: -; Owner: -
--

CREATE TYPE cols_status_code AS ENUM (
    '',
    'active',
    'in process',
    'obsolete'
);

--
-- Name: econs_econ_class; Type: TYPE; Schema: -; Owner: -
--

CREATE TYPE econs_econ_class AS ENUM (
    '',
    'energy',
    'material',
    'precious commodity',
    'water'
);

--
-- Name: econs_econ_type; Type: TYPE; Schema: -; Owner: -
--

CREATE TYPE econs_econ_type AS ENUM (
    '',
    'mineral',
    'hydrocarbon',
    'construction',
    'nuclear',
    'coal',
    'aquifer'
);

--
-- Name: environs_environ_class; Type: TYPE; Schema: -; Owner: -
--

CREATE TYPE environs_environ_class AS ENUM (
    '',
    'marine',
    'non-marine'
);

--
-- Name: environs_environ_type; Type: TYPE; Schema: -; Owner: -
--

CREATE TYPE environs_environ_type AS ENUM (
    '',
    'carbonate',
    'siliciclastic',
    'fluvial',
    'lacustrine',
    'landscape',
    'glacial',
    'eolian'
);

--
-- Name: interval_boundaries_boundary_status; Type: TYPE; Schema: -; Owner: -
--

CREATE TYPE interval_boundaries_boundary_status AS ENUM (
    '',
    'modeled',
    'relative',
    'absolute',
    'spike'
);

--
-- Name: interval_boundaries_scratch_boundary_status; Type: TYPE; Schema: -; Owner: -
--

CREATE TYPE interval_boundaries_scratch_boundary_status AS ENUM (
    '',
    'modeled',
    'relative',
    'absolute',
    'spike'
);

--
-- Name: intervals_interval_type; Type: TYPE; Schema: -; Owner: -
--

CREATE TYPE intervals_interval_type AS ENUM (
    'supereon',
    'eon',
    'era',
    'period',
    'superepoch',
    'epoch',
    'sub-epoch',
    'age',
    'chron',
    'zone',
    'bin',
    'sub-age',
    'subchron',
    'subzone'
);

--
-- Name: lith_atts_att_type; Type: TYPE; Schema: -; Owner: -
--

CREATE TYPE lith_atts_att_type AS ENUM (
    '',
    'bedform',
    'sed structure',
    'grains',
    'color',
    'lithology',
    'structure'
);

--
-- Name: liths_lith_class; Type: TYPE; Schema: -; Owner: -
--

CREATE TYPE liths_lith_class AS ENUM (
    '',
    'sedimentary',
    'igneous',
    'metamorphic'
);

--
-- Name: liths_lith_group; Type: TYPE; Schema: -; Owner: -
--

CREATE TYPE liths_lith_group AS ENUM (
    'sandstones',
    'mudrocks',
    'conglomerates',
    'unconsolidated',
    'Folk',
    'Dunham',
    'felsic',
    'mafic',
    'ultramafic'
);

--
-- Name: liths_lith_type; Type: TYPE; Schema: -; Owner: -
--

CREATE TYPE liths_lith_type AS ENUM (
    '',
    'carbonate',
    'siliciclastic',
    'evaporite',
    'organic',
    'chemical',
    'volcanic',
    'plutonic',
    'metamorphic',
    'sedimentary',
    'igneous',
    'metasedimentary',
    'metaigneous',
    'metavolcanic',
    'regolith',
    'cataclastic'
);

--
-- Name: lookup_measurements_measurement_class; Type: TYPE; Schema: -; Owner: -
--

CREATE TYPE lookup_measurements_measurement_class AS ENUM (
    '',
    'geophysical',
    'geochemical',
    'sedimentological'
);

--
-- Name: lookup_measurements_measurement_type; Type: TYPE; Schema: -; Owner: -
--

CREATE TYPE lookup_measurements_measurement_type AS ENUM (
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

--
-- Name: lookup_strat_names_rank; Type: TYPE; Schema: -; Owner: -
--

CREATE TYPE lookup_strat_names_rank AS ENUM (
    '',
    'SGp',
    'Gp',
    'SubGp',
    'Fm',
    'Mbr',
    'Bed'
);

--
-- Name: map_scale; Type: TYPE; Schema: -; Owner: -
--

CREATE TYPE map_scale AS ENUM (
    'tiny',
    'small',
    'medium',
    'large'
);

--
-- Name: measurements_measurement_class; Type: TYPE; Schema: -; Owner: -
--

CREATE TYPE measurements_measurement_class AS ENUM (
    '',
    'geophysical',
    'geochemical',
    'sedimentological'
);

--
-- Name: measurements_measurement_type; Type: TYPE; Schema: -; Owner: -
--

CREATE TYPE measurements_measurement_type AS ENUM (
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

--
-- Name: pbdb_intervals_interval_type; Type: TYPE; Schema: -; Owner: -
--

CREATE TYPE pbdb_intervals_interval_type AS ENUM (
    'supereon',
    'eon',
    'era',
    'period',
    'superepoch',
    'epoch',
    'sub-epoch',
    'age',
    'chron',
    'zone',
    'bin',
    'sub-age',
    'subchron',
    'subzone'
);

--
-- Name: refs_compilation_code; Type: TYPE; Schema: -; Owner: -
--

CREATE TYPE refs_compilation_code AS ENUM (
    '',
    'COSUNA',
    'COSUNA II',
    'Canada',
    'GNS Folio Series 1'
);

--
-- Name: rockd_features_feature_class; Type: TYPE; Schema: -; Owner: -
--

CREATE TYPE rockd_features_feature_class AS ENUM (
    '',
    'structure',
    'geomorphology'
);

--
-- Name: rockd_features_feature_type; Type: TYPE; Schema: -; Owner: -
--

CREATE TYPE rockd_features_feature_type AS ENUM (
    '',
    'fault',
    'glacial',
    'deformation'
);

--
-- Name: stats_project; Type: TYPE; Schema: -; Owner: -
--

CREATE TYPE stats_project AS ENUM (
    '',
    'North America',
    'New Zealand',
    'Deep Sea',
    'Australia',
    'Caribbean',
    'South America',
    'Africa',
    'North American Ediacaran',
    'North American Cretaceous',
    'Indonesia',
    'eODP',
    'Northern Eurasia'
);

--
-- Name: strat_names_lookup_rank; Type: TYPE; Schema: -; Owner: -
--

CREATE TYPE strat_names_lookup_rank AS ENUM (
    '',
    'SGp',
    'Gp',
    'Fm',
    'Mbr',
    'Bed'
);

--
-- Name: strat_names_rank; Type: TYPE; Schema: -; Owner: -
--

CREATE TYPE strat_names_rank AS ENUM (
    '',
    'SGp',
    'Gp',
    'SubGp',
    'Fm',
    'Mbr',
    'Bed'
);

--
-- Name: strat_tree_rel; Type: TYPE; Schema: -; Owner: -
--

CREATE TYPE strat_tree_rel AS ENUM (
    '',
    'parent',
    'synonym'
);

--
-- Name: structure_atts_att_class; Type: TYPE; Schema: -; Owner: -
--

CREATE TYPE structure_atts_att_class AS ENUM ();

--
-- Name: structure_atts_att_type; Type: TYPE; Schema: -; Owner: -
--

CREATE TYPE structure_atts_att_type AS ENUM ();

--
-- Name: structures_structure_class; Type: TYPE; Schema: -; Owner: -
--

CREATE TYPE structures_structure_class AS ENUM (
    '',
    'fracture',
    'structure',
    'fabric',
    'sedimentology',
    'igneous'
);

--
-- Name: structures_structure_group; Type: TYPE; Schema: -; Owner: -
--

CREATE TYPE structures_structure_group AS ENUM ();

--
-- Name: structures_structure_type; Type: TYPE; Schema: -; Owner: -
--

CREATE TYPE structures_structure_type AS ENUM (
    '',
    'fault',
    'fold',
    'foliation',
    'lineation',
    'paleocurrent',
    'fracture',
    'bedding',
    'contact',
    'intrusion'
);

--
-- Name: tectonics_basin_setting; Type: TYPE; Schema: -; Owner: -
--

CREATE TYPE tectonics_basin_setting AS ENUM (
    '',
    'divergent',
    'intraplate',
    'convergent',
    'transform',
    'hybrid'
);

--
-- Name: unit_boundaries_backup_boundary_status; Type: TYPE; Schema: -; Owner: -
--

CREATE TYPE unit_boundaries_backup_boundary_status AS ENUM (
    '',
    'modeled',
    'relative',
    'absolute',
    'spike'
);

--
-- Name: unit_boundaries_backup_boundary_type; Type: TYPE; Schema: -; Owner: -
--

CREATE TYPE unit_boundaries_backup_boundary_type AS ENUM (
    '',
    'unconformity',
    'conformity',
    'fault',
    'disconformity',
    'non-conformity',
    'angular unconformity'
);

--
-- Name: unit_boundaries_boundary_status; Type: TYPE; Schema: -; Owner: -
--

CREATE TYPE unit_boundaries_boundary_status AS ENUM (
    '',
    'modeled',
    'relative',
    'absolute',
    'spike'
);

--
-- Name: unit_boundaries_boundary_type; Type: TYPE; Schema: -; Owner: -
--

CREATE TYPE unit_boundaries_boundary_type AS ENUM (
    '',
    'unconformity',
    'conformity',
    'fault',
    'disconformity',
    'non-conformity',
    'angular unconformity'
);

--
-- Name: unit_boundaries_scratch_boundary_status; Type: TYPE; Schema: -; Owner: -
--

CREATE TYPE unit_boundaries_scratch_boundary_status AS ENUM (
    '',
    'modeled',
    'relative',
    'absolute',
    'spike'
);

--
-- Name: unit_boundaries_scratch_boundary_type; Type: TYPE; Schema: -; Owner: -
--

CREATE TYPE unit_boundaries_scratch_boundary_type AS ENUM (
    '',
    'unconformity',
    'conformity',
    'fault',
    'disconformity',
    'non-conformity',
    'angular unconformity'
);

--
-- Name: unit_boundaries_scratch_old_boundary_status; Type: TYPE; Schema: -; Owner: -
--

CREATE TYPE unit_boundaries_scratch_old_boundary_status AS ENUM (
    '',
    'modeled',
    'relative',
    'absolute',
    'spike'
);

--
-- Name: unit_boundaries_scratch_old_boundary_type; Type: TYPE; Schema: -; Owner: -
--

CREATE TYPE unit_boundaries_scratch_old_boundary_type AS ENUM (
    '',
    'unconformity',
    'conformity',
    'fault',
    'disconformity',
    'non-conformity',
    'angular unconformity'
);

--
-- Name: unit_contacts_contact; Type: TYPE; Schema: -; Owner: -
--

CREATE TYPE unit_contacts_contact AS ENUM (
    'above',
    'below',
    'lateral',
    'lateral-bottom',
    'lateral-top',
    'within'
);

--
-- Name: unit_contacts_old_contact; Type: TYPE; Schema: -; Owner: -
--

CREATE TYPE unit_contacts_old_contact AS ENUM (
    'above',
    'below',
    'lateral',
    'lateral-bottom',
    'lateral-top',
    'within'
);

--
-- Name: unit_dates_system; Type: TYPE; Schema: -; Owner: -
--

CREATE TYPE unit_dates_system AS ENUM (
    '',
    'U/Pb',
    'Rb/Sr',
    'Ar/Ar',
    'C14',
    'Re/Os',
    'K/Ar',
    'Pb/Pb',
    'Fission Track',
    'Amino Acid',
    'Ur-Series'
);

--
-- Name: unit_liths_dom; Type: TYPE; Schema: -; Owner: -
--

CREATE TYPE unit_liths_dom AS ENUM (
    '',
    'dom',
    'sub'
);

--
-- Name: unit_seq_strat_seq_order; Type: TYPE; Schema: -; Owner: -
--

CREATE TYPE unit_seq_strat_seq_order AS ENUM (
    '',
    '2nd',
    '3rd',
    '4th',
    '5th',
    '6th'
);

--
-- Name: unit_seq_strat_seq_strat; Type: TYPE; Schema: -; Owner: -
--

CREATE TYPE unit_seq_strat_seq_strat AS ENUM (
    '',
    'TST',
    'HST',
    'FSST',
    'LST',
    'SQ'
);

--
-- Name: units_color; Type: TYPE; Schema: -; Owner: -
--

CREATE TYPE units_color AS ENUM (
    '',
    'blue',
    'blue dark',
    'blue green',
    'black',
    'yellow',
    'orange',
    'brown dark',
    'brown light',
    'tan',
    'green dark',
    'green light',
    'gray dark',
    'gray light',
    'pink',
    'purple',
    'red',
    'gray',
    'green',
    'brown',
    'steel blue',
    'white'
);

--
-- Name: units_outcrop; Type: TYPE; Schema: -; Owner: -
--

CREATE TYPE units_outcrop AS ENUM (
    '',
    'surface',
    'subsurface',
    'both'
);

--
-- Name: autocomplete; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS autocomplete (
    id integer DEFAULT 0 NOT NULL,
    name varchar(255) DEFAULT NULL,
    type varchar(20) DEFAULT '' NOT NULL,
    category varchar(10) DEFAULT '' NOT NULL
);


COMMENT ON TABLE autocomplete IS 'Last updated from MariaDB - 2022-06-28 15:08';

--
-- Name: autocomplete_old; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS autocomplete_old (
    id integer DEFAULT 0 NOT NULL,
    name varchar(255) DEFAULT NULL,
    type varchar(20) DEFAULT '' NOT NULL,
    category varchar(10) DEFAULT '' NOT NULL
);

--
-- Name: canada_lexicon_dump; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS canada_lexicon_dump (
    strat_unit_id varchar(6),
    id integer NOT NULL,
    concept_id integer NOT NULL,
    unit varchar(255) NOT NULL,
    strat_name varchar(255) NOT NULL,
    strat_name_id integer NOT NULL,
    web_id varchar(20) NOT NULL,
    upper_age_e varchar(50) NOT NULL,
    upper_interval_id integer NOT NULL,
    lower_age_e varchar(50) NOT NULL,
    lower_interval_id integer NOT NULL,
    containing_interval integer NOT NULL,
    containing_interval_name varchar(150) NOT NULL,
    ptype varchar(50) NOT NULL,
    rank varchar(30) NOT NULL,
    type varchar(30) NOT NULL,
    status varchar(30) NOT NULL,
    usage_cs varchar(50) NOT NULL,
    lex varchar(30) NOT NULL,
    moreinfo varchar(2) NOT NULL,
    province_en varchar(255) NOT NULL,
    lastdate varchar(10) NOT NULL,
    url varchar(255) NOT NULL,
    descrip text NOT NULL,
    CONSTRAINT idx_44157002_primary PRIMARY KEY (strat_unit_id)
);

--
-- Name: idx_44157002_concept_id; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157002_concept_id ON canada_lexicon_dump (concept_id);

--
-- Name: idx_44157002_lower_interval_id; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157002_lower_interval_id ON canada_lexicon_dump (lower_interval_id);

--
-- Name: idx_44157002_strat_name_id; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157002_strat_name_id ON canada_lexicon_dump (strat_name_id);

--
-- Name: idx_44157002_upper_interval_id; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157002_upper_interval_id ON canada_lexicon_dump (upper_interval_id);

--
-- Name: col_areas_6april2016; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS col_areas_6april2016 (
    id integer DEFAULT 0 NOT NULL,
    col_id integer NOT NULL,
    gmap text NOT NULL,
    col_area public.geometry
);

--
-- Name: col_equiv; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS col_equiv (
    id SERIAL,
    col_1 integer NOT NULL,
    col_2 integer NOT NULL,
    CONSTRAINT idx_44157034_primary PRIMARY KEY (id)
);

--
-- Name: idx_44157034_col_1; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157034_col_1 ON col_equiv (col_1);

--
-- Name: idx_44157034_col_2; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157034_col_2 ON col_equiv (col_2);

--
-- Name: col_groups; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS col_groups (
    id SERIAL,
    col_group varchar(100) NOT NULL,
    col_group_long varchar(100) NOT NULL,
    project_id integer NOT NULL,
    CONSTRAINT idx_44157039_primary PRIMARY KEY (id)
);

--
-- Name: col_groups_new_id_idx1; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS col_groups_new_id_idx1 ON col_groups (id);

--
-- Name: idx_44157039_project_id; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157039_project_id ON col_groups (project_id);

--
-- Name: col_notes; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS col_notes (
    id SERIAL,
    col_id integer NOT NULL,
    notes text NOT NULL,
    CONSTRAINT idx_44157044_primary PRIMARY KEY (id)
);

--
-- Name: idx_44157044_col_id; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157044_col_id ON col_notes (col_id);

--
-- Name: colors; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS colors (
    color colors_color NOT NULL,
    unit_hex varchar(9) DEFAULT '#FFFFFF' NOT NULL,
    text_hex varchar(9) DEFAULT '#000000' NOT NULL,
    unit_class varchar(4) DEFAULT NULL
);

--
-- Name: idx_44157007_color; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157007_color ON colors (color);

--
-- Name: idx_44157007_unit_hex; Type: INDEX; Schema: -; Owner: -
--

CREATE UNIQUE INDEX IF NOT EXISTS idx_44157007_unit_hex ON colors (unit_hex);

--
-- Name: econs; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS econs (
    id SERIAL,
    econ varchar(100) NOT NULL,
    econ_type econs_econ_type NOT NULL,
    econ_class econs_econ_class NOT NULL,
    econ_color varchar(7) NOT NULL,
    CONSTRAINT idx_44157059_primary PRIMARY KEY (id)
);

--
-- Name: environs; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS environs (
    id SERIAL,
    environ varchar(50) NOT NULL,
    environ_type environs_environ_type NOT NULL,
    environ_class environs_environ_class NOT NULL,
    environ_fill integer NOT NULL,
    environ_color varchar(7) NOT NULL,
    CONSTRAINT idx_44157064_primary PRIMARY KEY (id)
);

--
-- Name: idx_44157064_environ; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157064_environ ON environs (environ);

--
-- Name: idx_44157064_environ_class; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157064_environ_class ON environs (environ_class);

--
-- Name: idx_44157064_environ_type; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157064_environ_type ON environs (environ_type);

--
-- Name: grainsize; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS grainsize (
    grain_id integer,
    grain_symbol text,
    grain_name text,
    grain_group text,
    soil_group text,
    min_size numeric,
    max_size numeric,
    classification text,
    CONSTRAINT grainsize_pkey PRIMARY KEY (grain_id)
);

--
-- Name: interval_boundaries; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS interval_boundaries (
    id integer NOT NULL,
    t1 integer NOT NULL,
    t1_prop numeric(6,5) NOT NULL,
    t1_prop_error numeric(6,5) DEFAULT NULL,
    t1_age numeric(8,4) NOT NULL,
    t1_age_error numeric(8,4) DEFAULT NULL,
    interval_id integer NOT NULL,
    interval_id_2 integer NOT NULL,
    timescale_id integer NOT NULL,
    boundary_status interval_boundaries_boundary_status DEFAULT '' NOT NULL
);

--
-- Name: interval_boundaries_scratch; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS interval_boundaries_scratch (
    id integer NOT NULL,
    t1 integer NOT NULL,
    t1_prop numeric(6,5) NOT NULL,
    t1_prop_error numeric(6,5) DEFAULT NULL,
    t1_age numeric(8,4) NOT NULL,
    t1_age_error numeric(8,4) DEFAULT NULL,
    interval_id integer NOT NULL,
    interval_id_2 integer NOT NULL,
    timescale_id integer NOT NULL,
    boundary_status interval_boundaries_scratch_boundary_status DEFAULT '' NOT NULL
);

--
-- Name: intervals; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS intervals (
    id SERIAL,
    age_bottom numeric(8,4) DEFAULT NULL,
    age_top numeric(8,4) DEFAULT NULL,
    interval_name varchar(255) DEFAULT NULL,
    interval_abbrev varchar(40) DEFAULT NULL,
    interval_type intervals_interval_type DEFAULT 'supereon',
    interval_color varchar(7) NOT NULL,
    orig_color varchar(7) NOT NULL,
    rank integer,
    CONSTRAINT idx_44157069_primary PRIMARY KEY (id)
);

--
-- Name: idx_44157069__intervals_age_bottom; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157069__intervals_age_bottom ON intervals (age_bottom);

--
-- Name: idx_44157069__intervals_age_top; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157069__intervals_age_top ON intervals (age_top);

--
-- Name: idx_44157069__intervals_interval_type; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157069__intervals_interval_type ON intervals (interval_type);

--
-- Name: idx_44157069_interval_name; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157069_interval_name ON intervals (interval_name);

--
-- Name: intervals_new_age_bottom_idx1; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS intervals_new_age_bottom_idx1 ON intervals (age_bottom);

--
-- Name: intervals_new_age_top_idx1; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS intervals_new_age_top_idx1 ON intervals (age_top);

--
-- Name: intervals_new_id_idx1; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS intervals_new_id_idx1 ON intervals (id);

--
-- Name: intervals_new_interval_name_idx1; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS intervals_new_interval_name_idx1 ON intervals (interval_name);

--
-- Name: intervals_new_interval_type_idx1; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS intervals_new_interval_type_idx1 ON intervals (interval_type);

--
-- Name: lith_atts; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS lith_atts (
    id SERIAL,
    lith_att varchar(50) NOT NULL,
    equiv integer NOT NULL,
    att_type lith_atts_att_type NOT NULL,
    lith_att_fill integer NOT NULL,
    CONSTRAINT idx_44157097_primary PRIMARY KEY (id)
);


COMMENT ON TABLE lith_atts IS 'Last updated from MariaDB - 2022-06-28 15:09';

--
-- Name: idx_44157097_att_type; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157097_att_type ON lith_atts (att_type);

--
-- Name: idx_44157097_equiv; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157097_equiv ON lith_atts (equiv);

--
-- Name: idx_44157097_lith_att; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157097_lith_att ON lith_atts (lith_att);

--
-- Name: lith_atts_new_att_type_idx1; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS lith_atts_new_att_type_idx1 ON lith_atts (att_type);

--
-- Name: lith_atts_new_lith_att_idx1; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS lith_atts_new_lith_att_idx1 ON lith_atts (lith_att);

--
-- Name: liths; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS liths (
    id SERIAL,
    lith varchar(50) NOT NULL,
    lith_group liths_lith_group,
    lith_type liths_lith_type NOT NULL,
    lith_class liths_lith_class NOT NULL,
    lith_equiv integer NOT NULL,
    lith_fill integer NOT NULL,
    comp_coef numeric(3,2) NOT NULL,
    initial_porosity numeric(3,2) NOT NULL,
    bulk_density numeric(3,2) NOT NULL,
    lith_color varchar(7) DEFAULT NULL,
    CONSTRAINT idx_44157091_primary PRIMARY KEY (id)
);

--
-- Name: idx_44157091_lith; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157091_lith ON liths (lith);

--
-- Name: idx_44157091_lith_class; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157091_lith_class ON liths (lith_class);

--
-- Name: idx_44157091_lith_type; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157091_lith_type ON liths (lith_type);

--
-- Name: liths_new_lith_class_idx1; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS liths_new_lith_class_idx1 ON liths (lith_class);

--
-- Name: liths_new_lith_idx1; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS liths_new_lith_idx1 ON liths (lith);

--
-- Name: liths_new_lith_type_idx1; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS liths_new_lith_type_idx1 ON liths (lith_type);

--
-- Name: lookup_measurements; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS lookup_measurements (
    measure_id integer,
    measuremeta_id integer NOT NULL,
    measurement_id integer NOT NULL,
    measurement varchar(100) NOT NULL,
    measurement_class lookup_measurements_measurement_class NOT NULL,
    measurement_type lookup_measurements_measurement_type NOT NULL,
    measure_phase varchar(100) NOT NULL,
    method varchar(100) NOT NULL,
    measure_units varchar(25) NOT NULL,
    measure_value numeric(10,5) DEFAULT NULL,
    v_error numeric(10,5) DEFAULT NULL,
    v_error_units varchar(25) DEFAULT NULL,
    v_type varchar(100) NOT NULL,
    v_n integer,
    lat numeric(8,5) DEFAULT NULL,
    lng numeric(8,5) DEFAULT NULL,
    sample_geo_unit varchar(255) NOT NULL,
    sample_lith varchar(255) NOT NULL,
    lith_id integer NOT NULL,
    sample_descrip text NOT NULL,
    ref_id integer NOT NULL,
    ref varchar(255) NOT NULL,
    units varchar(255) NOT NULL,
    CONSTRAINT idx_44157101_primary PRIMARY KEY (measure_id)
);

--
-- Name: idx_44157101_lith_id; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157101_lith_id ON lookup_measurements (lith_id);

--
-- Name: idx_44157101_measure_phase; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157101_measure_phase ON lookup_measurements (measure_phase);

--
-- Name: idx_44157101_measurement_class; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157101_measurement_class ON lookup_measurements (measurement_class);

--
-- Name: idx_44157101_measurement_id; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157101_measurement_id ON lookup_measurements (measurement_id);

--
-- Name: idx_44157101_measurement_type; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157101_measurement_type ON lookup_measurements (measurement_type);

--
-- Name: idx_44157101_measuremeta_id; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157101_measuremeta_id ON lookup_measurements (measuremeta_id);

--
-- Name: idx_44157101_ref_id; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157101_ref_id ON lookup_measurements (ref_id);

--
-- Name: lookup_strat_names; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS lookup_strat_names (
    strat_name_id integer,
    strat_name varchar(100) NOT NULL,
    rank lookup_strat_names_rank,
    concept_id integer NOT NULL,
    rank_name varchar(100) NOT NULL,
    bed_id integer NOT NULL,
    bed_name varchar(100) DEFAULT NULL,
    mbr_id integer NOT NULL,
    mbr_name varchar(100) DEFAULT NULL,
    fm_id integer NOT NULL,
    fm_name varchar(100) DEFAULT NULL,
    subgp_id integer NOT NULL,
    subgp_name varchar(100) DEFAULT NULL,
    gp_id integer NOT NULL,
    gp_name varchar(100) DEFAULT NULL,
    sgp_id integer NOT NULL,
    sgp_name varchar(100) DEFAULT NULL,
    early_age numeric(8,4) DEFAULT NULL,
    late_age numeric(8,4) DEFAULT NULL,
    gsc_lexicon character(15) DEFAULT NULL,
    parent integer NOT NULL,
    tree integer NOT NULL,
    t_units integer NOT NULL,
    b_period varchar(100) DEFAULT NULL,
    t_period varchar(100) DEFAULT NULL,
    name_no_lith varchar(100) DEFAULT NULL,
    ref_id integer NOT NULL,
    c_interval varchar(100) DEFAULT NULL,
    CONSTRAINT idx_44157111_primary PRIMARY KEY (strat_name_id)
);

--
-- Name: idx_44157111_bed_id; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157111_bed_id ON lookup_strat_names (bed_id);

--
-- Name: idx_44157111_concept_id; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157111_concept_id ON lookup_strat_names (concept_id);

--
-- Name: idx_44157111_fm_id; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157111_fm_id ON lookup_strat_names (fm_id);

--
-- Name: idx_44157111_gp_id; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157111_gp_id ON lookup_strat_names (gp_id);

--
-- Name: idx_44157111_mbr_id; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157111_mbr_id ON lookup_strat_names (mbr_id);

--
-- Name: idx_44157111_parent; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157111_parent ON lookup_strat_names (parent);

--
-- Name: idx_44157111_rank; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157111_rank ON lookup_strat_names (rank);

--
-- Name: idx_44157111_ref_id; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157111_ref_id ON lookup_strat_names (ref_id);

--
-- Name: idx_44157111_sgp_id; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157111_sgp_id ON lookup_strat_names (sgp_id);

--
-- Name: idx_44157111_strat_name; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157111_strat_name ON lookup_strat_names (strat_name);

--
-- Name: idx_44157111_subgp_id; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157111_subgp_id ON lookup_strat_names (subgp_id);

--
-- Name: idx_44157111_tree; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157111_tree ON lookup_strat_names (tree);

--
-- Name: lookup_strat_names_new_bed_id_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS lookup_strat_names_new_bed_id_idx ON lookup_strat_names (bed_id);

--
-- Name: lookup_strat_names_new_concept_id_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS lookup_strat_names_new_concept_id_idx ON lookup_strat_names (concept_id);

--
-- Name: lookup_strat_names_new_fm_id_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS lookup_strat_names_new_fm_id_idx ON lookup_strat_names (fm_id);

--
-- Name: lookup_strat_names_new_gp_id_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS lookup_strat_names_new_gp_id_idx ON lookup_strat_names (gp_id);

--
-- Name: lookup_strat_names_new_mbr_id_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS lookup_strat_names_new_mbr_id_idx ON lookup_strat_names (mbr_id);

--
-- Name: lookup_strat_names_new_sgp_id_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS lookup_strat_names_new_sgp_id_idx ON lookup_strat_names (sgp_id);

--
-- Name: lookup_strat_names_new_strat_name_id_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS lookup_strat_names_new_strat_name_id_idx ON lookup_strat_names (strat_name_id);

--
-- Name: lookup_strat_names_new_strat_name_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS lookup_strat_names_new_strat_name_idx ON lookup_strat_names (strat_name);

--
-- Name: lookup_strat_names_new; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS lookup_strat_names_new (
    strat_name_id integer,
    strat_name varchar(100),
    rank lookup_strat_names_rank,
    concept_id integer,
    rank_name varchar(100),
    bed_id integer,
    bed_name varchar(100),
    mbr_id integer,
    mbr_name varchar(100),
    fm_id integer,
    fm_name varchar(100),
    subgp_id integer,
    subgp_name varchar(100),
    gp_id integer,
    gp_name varchar(100),
    sgp_id integer,
    sgp_name varchar(100),
    early_age numeric(8,4),
    late_age numeric(8,4),
    gsc_lexicon character(15),
    parent integer,
    tree integer,
    t_units integer,
    b_period varchar(100),
    t_period varchar(100),
    name_no_lith varchar(100),
    ref_id integer,
    c_interval varchar(100)
);

--
-- Name: lookup_unit_attrs_api; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS lookup_unit_attrs_api (
    unit_id integer,
    lith bytea,
    environ bytea,
    econ bytea,
    measure_short bytea,
    measure_long bytea
);


COMMENT ON TABLE lookup_unit_attrs_api IS 'Last updated from MariaDB - 2022-06-28 15:07';

--
-- Name: idx_44157155_unit_id_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157155_unit_id_idx ON lookup_unit_attrs_api (unit_id);

--
-- Name: lookup_unit_attrs_api_new_unit_id_idx1; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS lookup_unit_attrs_api_new_unit_id_idx1 ON lookup_unit_attrs_api (unit_id);

--
-- Name: lookup_unit_intervals; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS lookup_unit_intervals (
    unit_id integer,
    fo_age numeric(8,4) NOT NULL,
    b_age numeric(8,4) DEFAULT NULL,
    fo_interval varchar(50) NOT NULL,
    fo_period varchar(50) NOT NULL,
    lo_age numeric(8,4) NOT NULL,
    t_age numeric(8,4) DEFAULT NULL,
    lo_interval varchar(50) NOT NULL,
    lo_period varchar(50) NOT NULL,
    age varchar(50) NOT NULL,
    age_id integer NOT NULL,
    epoch varchar(50) NOT NULL,
    epoch_id integer NOT NULL,
    period varchar(50) NOT NULL,
    period_id integer NOT NULL,
    era varchar(50) NOT NULL,
    era_id integer NOT NULL,
    eon varchar(50) NOT NULL,
    eon_id integer NOT NULL,
    best_interval_id integer,
    CONSTRAINT idx_44157160_primary PRIMARY KEY (unit_id)
);

--
-- Name: lookup_unit_intervals_new_best_interval_id_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS lookup_unit_intervals_new_best_interval_id_idx ON lookup_unit_intervals (best_interval_id);

--
-- Name: lookup_unit_intervals_new_unit_id_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS lookup_unit_intervals_new_unit_id_idx ON lookup_unit_intervals (unit_id);

--
-- Name: lookup_unit_liths; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS lookup_unit_liths (
    unit_id integer,
    lith_class varchar(100) NOT NULL,
    lith_type varchar(100) NOT NULL,
    lith_short text NOT NULL,
    lith_long text NOT NULL,
    environ_class varchar(100) NOT NULL,
    environ_type varchar(100) NOT NULL,
    environ varchar(255) NOT NULL,
    CONSTRAINT idx_44157165_primary PRIMARY KEY (unit_id)
);

--
-- Name: lookup_unit_liths_new_unit_id_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS lookup_unit_liths_new_unit_id_idx ON lookup_unit_liths (unit_id);

--
-- Name: lookup_units; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS lookup_units (
    unit_id integer DEFAULT 0,
    col_area double precision NOT NULL,
    project_id integer NOT NULL,
    t_int integer,
    t_int_name varchar(255) DEFAULT NULL,
    t_int_age numeric(8,4) DEFAULT NULL,
    t_age numeric(8,4) DEFAULT NULL,
    t_prop numeric(6,5) DEFAULT NULL,
    t_plat numeric(7,3) DEFAULT NULL,
    t_plng numeric(7,3) DEFAULT NULL,
    b_int integer,
    b_int_name varchar(255) DEFAULT NULL,
    b_int_age numeric(8,4) DEFAULT NULL,
    b_age numeric(8,4) DEFAULT NULL,
    b_prop numeric(6,5) DEFAULT NULL,
    b_plat numeric(7,3) DEFAULT NULL,
    b_plng numeric(7,3) DEFAULT NULL,
    clat numeric(7,4) NOT NULL,
    clng numeric(7,4) NOT NULL,
    color varchar(9) DEFAULT '#FFFFFF' NOT NULL,
    text_color varchar(9) DEFAULT '#000000' NOT NULL,
    units_above text,
    units_below text,
    pbdb_collections integer DEFAULT 0 NOT NULL,
    pbdb_occurrences integer NOT NULL,
    age varchar(200) DEFAULT NULL,
    age_id integer,
    epoch varchar(200) DEFAULT NULL,
    epoch_id integer,
    period varchar(200) DEFAULT NULL,
    period_id integer,
    era varchar(200) DEFAULT NULL,
    era_id integer,
    eon varchar(200) DEFAULT NULL,
    eon_id integer,
    CONSTRAINT idx_44157129_primary PRIMARY KEY (unit_id)
);

--
-- Name: idx_44157129_b_int; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157129_b_int ON lookup_units (b_int);

--
-- Name: idx_44157129_project_id; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157129_project_id ON lookup_units (project_id);

--
-- Name: idx_44157129_t_int; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157129_t_int ON lookup_units (t_int);

--
-- Name: lookup_units_new_b_int_idx1; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS lookup_units_new_b_int_idx1 ON lookup_units (b_int);

--
-- Name: lookup_units_new_project_id_idx1; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS lookup_units_new_project_id_idx1 ON lookup_units (project_id);

--
-- Name: lookup_units_new_t_int_idx1; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS lookup_units_new_t_int_idx1 ON lookup_units (t_int);

--
-- Name: measurements; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS measurements (
    id SERIAL,
    measurement_class measurements_measurement_class NOT NULL,
    measurement_type measurements_measurement_type NOT NULL,
    measurement varchar(150) NOT NULL,
    CONSTRAINT idx_44157171_primary PRIMARY KEY (id)
);

--
-- Name: idx_44157171_measurement_class; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157171_measurement_class ON measurements (measurement_class);

--
-- Name: idx_44157171_measurement_type; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157171_measurement_type ON measurements (measurement_type);

--
-- Name: measurements_new_id_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS measurements_new_id_idx ON measurements (id);

--
-- Name: measurements_new_measurement_class_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS measurements_new_measurement_class_idx ON measurements (measurement_class);

--
-- Name: measurements_new_measurement_type_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS measurements_new_measurement_type_idx ON measurements (measurement_type);

--
-- Name: measuremeta; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS measuremeta (
    id SERIAL,
    sample_name varchar(255) NOT NULL,
    lat numeric(8,5) DEFAULT NULL,
    lng numeric(8,5) DEFAULT NULL,
    sample_geo_unit varchar(255) NOT NULL,
    sample_lith varchar(255) DEFAULT NULL,
    lith_id integer NOT NULL,
    lith_att_id integer NOT NULL,
    age varchar(100) NOT NULL,
    early_id integer NOT NULL,
    late_id integer NOT NULL,
    sample_descrip text,
    ref varchar(255) NOT NULL,
    ref_id integer NOT NULL,
    geometry public.geometry,
    CONSTRAINT idx_44157176_primary PRIMARY KEY (id)
);

--
-- Name: idx_44157176_lith_att_id; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157176_lith_att_id ON measuremeta (lith_att_id);

--
-- Name: idx_44157176_lith_id; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157176_lith_id ON measuremeta (lith_id);

--
-- Name: idx_44157176_ref_id; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157176_ref_id ON measuremeta (ref_id);

--
-- Name: measuremeta_new_lith_att_id_idx1; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS measuremeta_new_lith_att_id_idx1 ON measuremeta (lith_att_id);

--
-- Name: measuremeta_new_lith_id_idx1; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS measuremeta_new_lith_id_idx1 ON measuremeta (lith_id);

--
-- Name: measuremeta_new_ref_id_idx1; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS measuremeta_new_ref_id_idx1 ON measuremeta (ref_id);

--
-- Name: measuremeta_cols; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS measuremeta_cols (
    id SERIAL,
    col_id integer NOT NULL,
    measuremeta_id integer NOT NULL,
    CONSTRAINT idx_44157186_primary PRIMARY KEY (id)
);

--
-- Name: idx_44157186_col_id; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157186_col_id ON measuremeta_cols (col_id);

--
-- Name: idx_44157186_measuremeta_id; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157186_measuremeta_id ON measuremeta_cols (measuremeta_id);

--
-- Name: measures; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS measures (
    id SERIAL,
    measuremeta_id integer NOT NULL,
    measurement_id integer NOT NULL,
    sample_no varchar(50) DEFAULT NULL,
    samp_pos numeric(7,3) DEFAULT NULL,
    measure_phase varchar(100) NOT NULL,
    method varchar(100) NOT NULL,
    units varchar(25) NOT NULL,
    measure_value numeric(10,5) DEFAULT NULL,
    v_error numeric(10,5) DEFAULT NULL,
    v_error_units varchar(25) DEFAULT NULL,
    v_type varchar(100) NOT NULL,
    v_n integer,
    CONSTRAINT idx_44157191_primary PRIMARY KEY (id)
);


COMMENT ON TABLE measures IS 'Last updated from MariaDB - 2022-06-28 15:06';

--
-- Name: idx_44157191_measure_phase; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157191_measure_phase ON measures (measure_phase);

--
-- Name: idx_44157191_measurement_id; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157191_measurement_id ON measures (measurement_id);

--
-- Name: idx_44157191_measuremeta_id; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157191_measuremeta_id ON measures (measuremeta_id);

--
-- Name: idx_44157191_method; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157191_method ON measures (method);

--
-- Name: measures_new_measurement_id_idx1; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS measures_new_measurement_id_idx1 ON measures (measurement_id);

--
-- Name: measures_new_measuremeta_id_idx1; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS measures_new_measuremeta_id_idx1 ON measures (measuremeta_id);

--
-- Name: minerals; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS minerals (
    id integer,
    mineral varchar(100) NOT NULL,
    mineral_type varchar(155) DEFAULT NULL,
    min_type varchar(100) NOT NULL,
    hardness_min numeric(3,1) DEFAULT NULL,
    hardness_max numeric(3,1) DEFAULT NULL,
    crystal_form varchar(100) DEFAULT NULL,
    color varchar(255) DEFAULT NULL,
    lustre varchar(255) DEFAULT NULL,
    formula varchar(155) NOT NULL,
    formula_tags text NOT NULL,
    url varchar(155) NOT NULL,
    paragenesis varchar(150) DEFAULT NULL,
    CONSTRAINT idx_44157200_primary PRIMARY KEY (id)
);

--
-- Name: offshore_baggage; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS offshore_baggage (
    id bigint,
    section_id integer NOT NULL,
    name varchar(150) NOT NULL,
    site_hole varchar(20) NOT NULL,
    col_id integer NOT NULL,
    top numeric(7,3) NOT NULL,
    bottom numeric(7,3) NOT NULL,
    top_depth numeric(7,3) NOT NULL,
    bottom_depth numeric(7,3) NOT NULL,
    principal_lithology_prefix varchar(100) NOT NULL,
    principal_lith_prefix_cleaned varchar(125) NOT NULL,
    principal_prefix_lith_att_id integer NOT NULL,
    principal_lithology_name varchar(150) NOT NULL,
    cleaned_lith varchar(100) NOT NULL,
    lith varchar(50) NOT NULL,
    lith_id integer NOT NULL,
    lith_att varchar(50) NOT NULL,
    lith_att_id integer NOT NULL,
    principal_lithology_suffix varchar(100) NOT NULL,
    principal_lith_suffix_cleaned varchar(150) NOT NULL,
    minor_lithology_prefix varchar(100) NOT NULL,
    minor_lith_prefix_cleaned varchar(100) NOT NULL,
    minor_lith_prefix_att_id integer NOT NULL,
    minor_lithology_name varchar(100) NOT NULL,
    cleaned_minor varchar(50) NOT NULL,
    minor_lith varchar(50) NOT NULL,
    minor_lith_id integer NOT NULL,
    minor_lith_att_id integer NOT NULL,
    minor_lithology_suffix varchar(100) NOT NULL,
    standard_minor_lith varchar(150) DEFAULT NULL,
    raw_data text NOT NULL,
    data_source_notes varchar(100) NOT NULL,
    created_at timestamptz,
    data_source_type varchar(100) NOT NULL,
    drop_row smallint DEFAULT 0 NOT NULL,
    unit_id_secondary integer NOT NULL,
    unit_id integer NOT NULL,
    neptune_bin integer NOT NULL,
    CONSTRAINT idx_44157212_primary PRIMARY KEY (id)
);

--
-- Name: idx_44157212_bottom_depth; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157212_bottom_depth ON offshore_baggage (bottom_depth);

--
-- Name: idx_44157212_cleaned_lith; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157212_cleaned_lith ON offshore_baggage (cleaned_lith);

--
-- Name: idx_44157212_cleaned_minor; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157212_cleaned_minor ON offshore_baggage (cleaned_minor);

--
-- Name: idx_44157212_col_id; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157212_col_id ON offshore_baggage (col_id);

--
-- Name: idx_44157212_principal_lith_prefix_cleaned; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157212_principal_lith_prefix_cleaned ON offshore_baggage (principal_lith_prefix_cleaned);

--
-- Name: idx_44157212_principal_lithology_name; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157212_principal_lithology_name ON offshore_baggage (principal_lithology_name);

--
-- Name: idx_44157212_principal_lithology_prefix; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157212_principal_lithology_prefix ON offshore_baggage (principal_lithology_prefix);

--
-- Name: idx_44157212_principal_lithology_suffix; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157212_principal_lithology_suffix ON offshore_baggage (principal_lithology_suffix);

--
-- Name: idx_44157212_section_id; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157212_section_id ON offshore_baggage (section_id);

--
-- Name: idx_44157212_top_depth; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157212_top_depth ON offshore_baggage (top_depth);

--
-- Name: offshore_baggage_units; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS offshore_baggage_units (
    offshore_baggage_id integer,
    unit_id integer NOT NULL,
    unit_lith_id integer NOT NULL,
    unit_lith_sub_id integer NOT NULL,
    col_id integer NOT NULL,
    CONSTRAINT idx_44157219_primary PRIMARY KEY (offshore_baggage_id)
);

--
-- Name: offshore_fossils; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS offshore_fossils (
    id bigint,
    section_id integer NOT NULL,
    name varchar(150) NOT NULL,
    col_id integer NOT NULL,
    top numeric(7,3) NOT NULL,
    bottom numeric(7,3) NOT NULL,
    top_depth numeric(7,3) NOT NULL,
    bottom_depth numeric(7,3) NOT NULL,
    mid_depth numeric(7,3) NOT NULL,
    data_source_notes varchar(100) NOT NULL,
    taxa varchar(100) NOT NULL,
    created_at timestamptz,
    site_hole varchar(100) NOT NULL,
    pbdb_pres varchar(15) DEFAULT NULL,
    pbdb_frag varchar(15) DEFAULT NULL,
    taxa_count integer NOT NULL,
    unit_id integer NOT NULL,
    ma varchar(8) NOT NULL,
    pbdb_interval_no integer NOT NULL,
    collection_no integer NOT NULL,
    CONSTRAINT idx_44157222_primary PRIMARY KEY (id)
);

--
-- Name: idx_44157222_col_id; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157222_col_id ON offshore_fossils (col_id);

--
-- Name: idx_44157222_section_id; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157222_section_id ON offshore_fossils (section_id);

--
-- Name: idx_44157222_taxa; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157222_taxa ON offshore_fossils (taxa);

--
-- Name: idx_44157222_unit_id; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157222_unit_id ON offshore_fossils (unit_id);

--
-- Name: offshore_hole_ages; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS offshore_hole_ages (
    id SERIAL,
    col_id integer NOT NULL,
    top_depth numeric(7,3) NOT NULL,
    top_core integer,
    bottom_depth numeric(7,3) NOT NULL,
    bottom_core integer,
    interval_id integer NOT NULL,
    CONSTRAINT idx_44157230_primary PRIMARY KEY (id)
);

--
-- Name: idx_44157230_col_id; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157230_col_id ON offshore_hole_ages (col_id);

--
-- Name: idx_44157230_interval_id; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157230_interval_id ON offshore_hole_ages (interval_id);

--
-- Name: offshore_sections; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS offshore_sections (
    exp integer NOT NULL,
    site varchar(6) NOT NULL,
    hole varchar(2) NOT NULL,
    col_id integer NOT NULL,
    core integer NOT NULL,
    core_type varchar(1) NOT NULL,
    sect varchar(2) NOT NULL,
    recovered_length numeric(2,1) NOT NULL,
    curated_length numeric(2,1) NOT NULL,
    top_mbsf numeric(6,2) NOT NULL,
    bottom_mbsf numeric(6,2) NOT NULL
);

--
-- Name: idx_44157234_col_id; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157234_col_id ON offshore_sections (col_id);

--
-- Name: offshore_sites; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS offshore_sites (
    id integer,
    epoch varchar(4) NOT NULL,
    leg varchar(5) NOT NULL,
    site varchar(6) NOT NULL,
    hole varchar(1) NOT NULL,
    col_id integer NOT NULL,
    col_group_id integer NOT NULL,
    lat_deg integer NOT NULL,
    lat_min numeric(7,4) NOT NULL,
    lat_dir varchar(1) NOT NULL,
    lat numeric(8,5) NOT NULL,
    lng_deg integer NOT NULL,
    lng_min numeric(7,4) NOT NULL,
    lng_dir varchar(1) NOT NULL,
    lng numeric(8,5) NOT NULL,
    penetration numeric(5,1) NOT NULL,
    cored numeric(5,1) NOT NULL,
    recovered numeric(5,1) NOT NULL,
    recovery numeric(5,2) NOT NULL,
    drilled_interval numeric(5,1) NOT NULL,
    drilled_intervals smallint NOT NULL,
    cores smallint NOT NULL,
    apc_cores smallint NOT NULL,
    hlapc_cores smallint NOT NULL,
    xcb_cores smallint NOT NULL,
    rcb_cores smallint NOT NULL,
    other_cores smallint NOT NULL,
    date_started varchar(25) NOT NULL,
    date_finished varchar(25) NOT NULL,
    time_on_hole numeric(5,2) NOT NULL,
    comments varchar(255) NOT NULL,
    ref_id integer NOT NULL,
    CONSTRAINT idx_44157237_primary PRIMARY KEY (id)
);

--
-- Name: idx_44157237_col_group_id; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157237_col_group_id ON offshore_sites (col_group_id);

--
-- Name: idx_44157237_col_id; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157237_col_id ON offshore_sites (col_id);

--
-- Name: idx_44157237_leg; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157237_leg ON offshore_sites (leg);

--
-- Name: idx_44157237_ref_id; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157237_ref_id ON offshore_sites (ref_id);

--
-- Name: idx_44157237_site; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157237_site ON offshore_sites (site);

--
-- Name: pbdb_collections; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS pbdb_collections (
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

--
-- Name: pbdb_collections_collection_no_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS pbdb_collections_collection_no_idx ON pbdb_collections (collection_no);

--
-- Name: pbdb_collections_collection_no_idx1; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS pbdb_collections_collection_no_idx1 ON pbdb_collections (collection_no);

--
-- Name: pbdb_collections_early_age_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS pbdb_collections_early_age_idx ON pbdb_collections (early_age);

--
-- Name: pbdb_collections_early_age_idx1; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS pbdb_collections_early_age_idx1 ON pbdb_collections (early_age);

--
-- Name: pbdb_collections_geom_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS pbdb_collections_geom_idx ON pbdb_collections USING gist (geom);

--
-- Name: pbdb_collections_geom_idx1; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS pbdb_collections_geom_idx1 ON pbdb_collections USING gist (geom);

--
-- Name: pbdb_collections_late_age_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS pbdb_collections_late_age_idx ON pbdb_collections (late_age);

--
-- Name: pbdb_collections_late_age_idx1; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS pbdb_collections_late_age_idx1 ON pbdb_collections (late_age);

--
-- Name: pbdb_collections_new_collection_no_idx1; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS pbdb_collections_new_collection_no_idx1 ON pbdb_collections (collection_no);

--
-- Name: pbdb_collections_new_early_age_idx1; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS pbdb_collections_new_early_age_idx1 ON pbdb_collections (early_age);

--
-- Name: pbdb_collections_new_geom_idx1; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS pbdb_collections_new_geom_idx1 ON pbdb_collections USING gist (geom);

--
-- Name: pbdb_collections_new_late_age_idx1; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS pbdb_collections_new_late_age_idx1 ON pbdb_collections (late_age);

--
-- Name: pbdb_collections_strat_names; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS pbdb_collections_strat_names (
    collection_no integer NOT NULL,
    strat_name_id integer NOT NULL,
    basis_col text
);

--
-- Name: pbdb_intervals; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS pbdb_intervals (
    id SERIAL,
    age_bottom numeric(8,4) DEFAULT NULL,
    age_top numeric(8,4) DEFAULT NULL,
    interval_name varchar(255) DEFAULT NULL,
    interval_abbrev varchar(40) DEFAULT NULL,
    interval_type pbdb_intervals_interval_type DEFAULT 'supereon',
    interval_color varchar(7) NOT NULL,
    orig_color varchar(7) NOT NULL,
    pbdb_interval_no integer NOT NULL,
    CONSTRAINT idx_44157241_primary PRIMARY KEY (id)
);

--
-- Name: idx_44157241__intervals_age_bottom; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157241__intervals_age_bottom ON pbdb_intervals (age_bottom);

--
-- Name: idx_44157241__intervals_age_top; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157241__intervals_age_top ON pbdb_intervals (age_top);

--
-- Name: idx_44157241__intervals_interval_type; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157241__intervals_interval_type ON pbdb_intervals (interval_type);

--
-- Name: idx_44157241_interval_name; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157241_interval_name ON pbdb_intervals (interval_name);

--
-- Name: pbdb_liths; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS pbdb_liths (
    lith_id integer,
    lith varchar(100) NOT NULL,
    pbdb_lith varchar(100) NOT NULL,
    CONSTRAINT idx_44157250_primary PRIMARY KEY (lith_id)
);

--
-- Name: pbdb_matches; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS pbdb_matches (
    id SERIAL,
    collection_no integer NOT NULL,
    collection_name varchar(255) NOT NULL,
    occs integer NOT NULL,
    lat numeric(7,4) NOT NULL,
    lng numeric(7,4) NOT NULL,
    unit_id integer NOT NULL,
    verified boolean DEFAULT false NOT NULL,
    modified timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
    release_date timestamptz NOT NULL,
    ref_id integer NOT NULL,
    coordinate public.geometry,
    CONSTRAINT idx_44157254_primary PRIMARY KEY (id)
);

--
-- Name: idx_44157254_collection_no; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157254_collection_no ON pbdb_matches (collection_no);

--
-- Name: idx_44157254_ref_id; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157254_ref_id ON pbdb_matches (ref_id);

--
-- Name: idx_44157254_unit_id; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157254_unit_id ON pbdb_matches (unit_id);

--
-- Name: places; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS places (
    place_id BIGSERIAL,
    name text,
    abbrev text,
    postal text,
    country text,
    country_abbrev text,
    geom public.geometry,
    CONSTRAINT idx_44157263_primary PRIMARY KEY (place_id)
);


COMMENT ON TABLE places IS 'Last updated from MariaDB - 2022-06-28 15:07';

--
-- Name: places_new_geom_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS places_new_geom_idx ON places USING gist (geom);

--
-- Name: concepts_places; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS concepts_places (
    concept_id integer NOT NULL,
    place_id bigint NOT NULL,
    CONSTRAINT concepts_places_places_fk FOREIGN KEY (place_id) REFERENCES places (place_id) ON DELETE CASCADE
);

--
-- Name: concepts_places_new_concept_id_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS concepts_places_new_concept_id_idx ON concepts_places (concept_id);

--
-- Name: concepts_places_new_place_id_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS concepts_places_new_place_id_idx ON concepts_places (place_id);

--
-- Name: idx_44157055_concept_id; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157055_concept_id ON concepts_places (concept_id);

--
-- Name: idx_44157055_concept_id_2; Type: INDEX; Schema: -; Owner: -
--

CREATE UNIQUE INDEX IF NOT EXISTS idx_44157055_concept_id_2 ON concepts_places (concept_id, place_id);

--
-- Name: idx_44157055_place_id; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157055_place_id ON concepts_places (place_id);

--
-- Name: refs; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS refs (
    id SERIAL,
    pub_year integer NOT NULL,
    author varchar(255) NOT NULL,
    ref text NOT NULL,
    doi varchar(40) DEFAULT NULL,
    compilation_code refs_compilation_code NOT NULL,
    url varchar(255) DEFAULT NULL,
    rgeom public.geometry,
    CONSTRAINT idx_44157277_primary PRIMARY KEY (id)
);

--
-- Name: refs_new_rgeom_idx1; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS refs_new_rgeom_idx1 ON refs USING gist (rgeom);

--
-- Name: rockd_features; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS rockd_features (
    id SERIAL,
    feature varchar(100) NOT NULL,
    feature_type rockd_features_feature_type NOT NULL,
    feature_class rockd_features_feature_class NOT NULL,
    CONSTRAINT idx_44157286_primary PRIMARY KEY (id)
);

--
-- Name: idx_44157286_feature_class; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157286_feature_class ON rockd_features (feature_class);

--
-- Name: idx_44157286_feature_type; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157286_feature_type ON rockd_features (feature_type);

--
-- Name: ronov_sediment; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS ronov_sediment (
    interval_name varchar(25) NOT NULL,
    interval_id integer NOT NULL,
    platforms numeric(4,2) NOT NULL,
    geosynclines numeric(4,2) NOT NULL,
    platform_flooding integer NOT NULL,
    geosyncline_flooding integer NOT NULL,
    cont_flooding integer NOT NULL,
    carbonate numeric(3,1) NOT NULL,
    carbonate_clastic numeric(3,1) NOT NULL,
    marine_clastic numeric(3,1) NOT NULL,
    coal_bearing numeric(3,1) NOT NULL,
    evaporite numeric(3,1) NOT NULL,
    terrestrial_clastic numeric(3,1) NOT NULL,
    geosync_submarine_volc numeric(3,1) NOT NULL,
    terrestrial_volc numeric(3,1) NOT NULL,
    platform_terrest_trap numeric(3,1) NOT NULL,
    glacial numeric(3,1) NOT NULL,
    cherty numeric(3,1) NOT NULL
);

--
-- Name: idx_44157290_interval_id; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157290_interval_id ON ronov_sediment (interval_id);

--
-- Name: stats; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS stats (
    project_id integer DEFAULT 0 NOT NULL,
    project stats_project NOT NULL,
    columns bigint DEFAULT 0 NOT NULL,
    packages bigint DEFAULT 0 NOT NULL,
    units bigint DEFAULT 0 NOT NULL,
    pbdb_collections bigint DEFAULT 0 NOT NULL,
    measurements bigint DEFAULT 0 NOT NULL,
    burwell_polygons bigint DEFAULT 0
);

--
-- Name: strat_name_footprints; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS strat_name_footprints (
    strat_name_id integer,
    name_no_lith varchar(100),
    rank_name varchar(200),
    concept_id integer,
    concept_names integer[],
    geom public.geometry,
    best_t_age numeric,
    best_b_age numeric
);

--
-- Name: strat_name_footprints_geom_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS strat_name_footprints_geom_idx ON strat_name_footprints USING gist (geom);

--
-- Name: strat_name_footprints_geom_idx1; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS strat_name_footprints_geom_idx1 ON strat_name_footprints USING gist (geom);

--
-- Name: strat_name_footprints_new_geom_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS strat_name_footprints_new_geom_idx ON strat_name_footprints USING gist (geom);

--
-- Name: strat_name_footprints_new_strat_name_id_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS strat_name_footprints_new_strat_name_id_idx ON strat_name_footprints (strat_name_id);

--
-- Name: strat_name_footprints_strat_name_id_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS strat_name_footprints_strat_name_id_idx ON strat_name_footprints (strat_name_id);

--
-- Name: strat_name_footprints_strat_name_id_idx1; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS strat_name_footprints_strat_name_id_idx1 ON strat_name_footprints (strat_name_id);

--
-- Name: strat_names_lookup; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS strat_names_lookup (
    strat_name_id integer,
    strat_name varchar(100) NOT NULL,
    rank strat_names_lookup_rank NOT NULL,
    bed_id integer NOT NULL,
    bed_name varchar(100) NOT NULL,
    mbr_id integer NOT NULL,
    mbr_name varchar(100) NOT NULL,
    fm_id integer NOT NULL,
    fm_name varchar(100) NOT NULL,
    gp_id integer NOT NULL,
    gp_name varchar(100) NOT NULL,
    sgp_id integer NOT NULL,
    sgp_name varchar(100) NOT NULL,
    CONSTRAINT idx_44157318_primary PRIMARY KEY (strat_name_id)
);

--
-- Name: idx_44157318_bed_id; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157318_bed_id ON strat_names_lookup (bed_id);

--
-- Name: idx_44157318_fm_id; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157318_fm_id ON strat_names_lookup (fm_id);

--
-- Name: idx_44157318_gp_id; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157318_gp_id ON strat_names_lookup (gp_id);

--
-- Name: idx_44157318_mbr_id; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157318_mbr_id ON strat_names_lookup (mbr_id);

--
-- Name: idx_44157318_sgp_id; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157318_sgp_id ON strat_names_lookup (sgp_id);

--
-- Name: strat_names_meta; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS strat_names_meta (
    concept_id SERIAL,
    orig_id integer NOT NULL,
    name varchar(40) DEFAULT NULL,
    geologic_age text,
    interval_id integer,
    b_int integer NOT NULL,
    t_int integer NOT NULL,
    usage_notes text,
    other text,
    province text,
    url varchar(150) NOT NULL,
    ref_id integer NOT NULL,
    CONSTRAINT idx_44157324_primary PRIMARY KEY (concept_id),
    CONSTRAINT strat_names_meta_intervals_fk FOREIGN KEY (interval_id) REFERENCES intervals (id) ON DELETE CASCADE,
    CONSTRAINT strat_names_meta_refs_fk FOREIGN KEY (ref_id) REFERENCES refs (id) ON DELETE CASCADE
);

--
-- Name: idx_44157324_b_int; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157324_b_int ON strat_names_meta (b_int);

--
-- Name: idx_44157324_interval_id; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157324_interval_id ON strat_names_meta (interval_id);

--
-- Name: idx_44157324_ref_id; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157324_ref_id ON strat_names_meta (ref_id);

--
-- Name: idx_44157324_t_int; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157324_t_int ON strat_names_meta (t_int);

--
-- Name: strat_names_meta_new_b_int_idx1; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS strat_names_meta_new_b_int_idx1 ON strat_names_meta (b_int);

--
-- Name: strat_names_meta_new_interval_id_idx1; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS strat_names_meta_new_interval_id_idx1 ON strat_names_meta (interval_id);

--
-- Name: strat_names_meta_new_ref_id_idx1; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS strat_names_meta_new_ref_id_idx1 ON strat_names_meta (ref_id);

--
-- Name: strat_names_meta_new_t_int_idx1; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS strat_names_meta_new_t_int_idx1 ON strat_names_meta (t_int);

--
-- Name: strat_names; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS strat_names (
    id SERIAL,
    old_id integer NOT NULL,
    concept_id integer,
    strat_name varchar(75) DEFAULT NULL,
    rank strat_names_rank,
    old_strat_name_id integer NOT NULL,
    ref_id integer,
    places text,
    orig_id integer NOT NULL,
    CONSTRAINT idx_44157311_primary PRIMARY KEY (id),
    CONSTRAINT strat_names_strat_names_meta_fk FOREIGN KEY (concept_id) REFERENCES strat_names_meta (concept_id) ON DELETE CASCADE
);


COMMENT ON TABLE strat_names IS 'Last updated from MariaDB - 2022-06-28 15:10';

--
-- Name: idx_44157311_concept_id; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157311_concept_id ON strat_names (concept_id);

--
-- Name: idx_44157311_rank; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157311_rank ON strat_names (rank);

--
-- Name: idx_44157311_ref_id; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157311_ref_id ON strat_names (ref_id);

--
-- Name: idx_44157311_strat_name; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157311_strat_name ON strat_names (strat_name);

--
-- Name: strat_names_new_concept_id_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS strat_names_new_concept_id_idx ON strat_names (concept_id);

--
-- Name: strat_names_new_rank_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS strat_names_new_rank_idx ON strat_names (rank);

--
-- Name: strat_names_new_ref_id_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS strat_names_new_ref_id_idx ON strat_names (ref_id);

--
-- Name: strat_names_new_strat_name_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS strat_names_new_strat_name_idx ON strat_names (strat_name);

--
-- Name: strat_names_places; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS strat_names_places (
    strat_name_id integer NOT NULL,
    place_id integer NOT NULL,
    CONSTRAINT strat_names_places_places_fk FOREIGN KEY (place_id) REFERENCES places (place_id) ON DELETE CASCADE,
    CONSTRAINT strat_names_places_strat_names_fk FOREIGN KEY (strat_name_id) REFERENCES strat_names (id) ON DELETE CASCADE
);

--
-- Name: idx_44157331_strat_name_id; Type: INDEX; Schema: -; Owner: -
--

CREATE UNIQUE INDEX IF NOT EXISTS idx_44157331_strat_name_id ON strat_names_places (strat_name_id, place_id);

--
-- Name: strat_names_places_new_place_id_idx1; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS strat_names_places_new_place_id_idx1 ON strat_names_places (place_id);

--
-- Name: strat_names_places_new_strat_name_id_idx1; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS strat_names_places_new_strat_name_id_idx1 ON strat_names_places (strat_name_id);

--
-- Name: strat_tree; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS strat_tree (
    id integer,
    parent integer,
    rel macrostratbak2.strat_tree_rel,
    child integer,
    ref_id integer,
    check_me smallint
);


COMMENT ON TABLE strat_tree IS 'Last updated from MariaDB - 2023-07-28 18:06';

--
-- Name: structure_atts; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS structure_atts (
    id BIGSERIAL,
    structure_att varchar(100) NOT NULL,
    att_type structure_atts_att_type,
    att_class structure_atts_att_class,
    CONSTRAINT idx_44157345_primary PRIMARY KEY (id)
);

--
-- Name: structures; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS structures (
    id SERIAL,
    structure varchar(100) NOT NULL,
    structure_group structures_structure_group,
    structure_type structures_structure_type NOT NULL,
    structure_class structures_structure_class NOT NULL,
    CONSTRAINT idx_44157340_primary PRIMARY KEY (id)
);

--
-- Name: tectonics; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS tectonics (
    id SERIAL,
    basin_type varchar(100) NOT NULL,
    basin_setting tectonics_basin_setting NOT NULL,
    CONSTRAINT idx_44157350_primary PRIMARY KEY (id)
);

--
-- Name: temp_areas; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS temp_areas (
    areas double precision NOT NULL,
    col_id integer NOT NULL
);

--
-- Name: idx_44157354_col_id; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157354_col_id ON temp_areas (col_id);

--
-- Name: idx_44157354_col_id_2; Type: INDEX; Schema: -; Owner: -
--

CREATE UNIQUE INDEX IF NOT EXISTS idx_44157354_col_id_2 ON temp_areas (col_id);

--
-- Name: timescales; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS timescales (
    id SERIAL,
    timescale varchar(255) DEFAULT NULL,
    ref_id integer NOT NULL,
    CONSTRAINT idx_44157358_primary PRIMARY KEY (id)
);

--
-- Name: idx_44157358_ref_id; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157358_ref_id ON timescales (ref_id);

--
-- Name: idx_44157358_timescale; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157358_timescale ON timescales (timescale);

--
-- Name: timescales_new_ref_id_idx1; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS timescales_new_ref_id_idx1 ON timescales (ref_id);

--
-- Name: timescales_new_timescale_idx1; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS timescales_new_timescale_idx1 ON timescales (timescale);

--
-- Name: projects; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS projects (
    id SERIAL,
    project text NOT NULL,
    descrip text NOT NULL,
    timescale_id integer NOT NULL,
    is_composite boolean DEFAULT false,
    slug text NOT NULL,
    CONSTRAINT idx_44157270_primary PRIMARY KEY (id),
    CONSTRAINT projects_slug_key UNIQUE (slug),
    CONSTRAINT projects_timescale_fk FOREIGN KEY (timescale_id) REFERENCES timescales (id) ON DELETE CASCADE
);

--
-- Name: idx_44157270_project; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157270_project ON projects (project);

--
-- Name: idx_44157270_timescale_id; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157270_timescale_id ON projects (timescale_id);

--
-- Name: idx_projects_slug; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_projects_slug ON projects (slug);

--
-- Name: projects_new_timescale_id_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS projects_new_timescale_id_idx ON projects (timescale_id);

--
-- Name: cols; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS cols (
    id SERIAL,
    col_group_id integer NOT NULL,
    project_id integer NOT NULL,
    status_code cols_status_code NOT NULL,
    col_type cols_col_type NOT NULL,
    col_position cols_col_position NOT NULL,
    col numeric(6,2) NOT NULL,
    col_name varchar(75) NOT NULL,
    lat numeric(8,5) NOT NULL,
    lng numeric(8,5) NOT NULL,
    col_area double precision NOT NULL,
    created timestamptz NOT NULL,
    coordinate public.geometry,
    wkt text,
    poly_geom public.geometry,
    CONSTRAINT idx_44157014_primary PRIMARY KEY (id),
    CONSTRAINT cols_col_groups_fk FOREIGN KEY (col_group_id) REFERENCES col_groups (id) ON DELETE CASCADE,
    CONSTRAINT cols_project_fk FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE
);


COMMENT ON TABLE cols IS 'Last updated from MariaDB - 2022-06-28 15:06';

--
-- Name: cols_new_col_group_id_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS cols_new_col_group_id_idx ON cols (col_group_id);

--
-- Name: cols_new_coordinate_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS cols_new_coordinate_idx ON cols USING gist (coordinate);

--
-- Name: cols_new_poly_geom_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS cols_new_poly_geom_idx ON cols USING gist (poly_geom);

--
-- Name: cols_new_project_id_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS cols_new_project_id_idx ON cols (project_id);

--
-- Name: cols_new_status_code_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS cols_new_status_code_idx ON cols (status_code);

--
-- Name: idx_44157014_col_group_id; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157014_col_group_id ON cols (col_group_id);

--
-- Name: idx_44157014_col_type; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157014_col_type ON cols (col_type);

--
-- Name: idx_44157014_project_id; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157014_project_id ON cols (project_id);

--
-- Name: idx_44157014_status_code; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157014_status_code ON cols (status_code);

--
-- Name: col_areas; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS col_areas (
    id SERIAL,
    col_id integer NOT NULL,
    gmap text NOT NULL,
    col_area public.geometry,
    wkt text,
    CONSTRAINT idx_44157021_primary PRIMARY KEY (id),
    CONSTRAINT col_areas_cols_fk FOREIGN KEY (col_id) REFERENCES cols (id) ON DELETE CASCADE
);


COMMENT ON TABLE col_areas IS 'Last updated from MariaDB - 2022-06-28 15:08';

--
-- Name: col_areas_new_col_area_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS col_areas_new_col_area_idx ON col_areas USING gist (col_area);

--
-- Name: col_areas_new_col_id_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS col_areas_new_col_id_idx ON col_areas (col_id);

--
-- Name: idx_44157021_col_id; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157021_col_id ON col_areas (col_id);

--
-- Name: col_refs; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS col_refs (
    id SERIAL,
    col_id integer NOT NULL,
    ref_id integer NOT NULL,
    CONSTRAINT idx_44157051_primary PRIMARY KEY (id),
    CONSTRAINT col_refs_col_fk FOREIGN KEY (col_id) REFERENCES cols (id) ON DELETE CASCADE,
    CONSTRAINT col_refs_ref_fk FOREIGN KEY (ref_id) REFERENCES refs (id) ON DELETE CASCADE
);

--
-- Name: col_refs_new_col_id_idx1; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS col_refs_new_col_id_idx1 ON col_refs (col_id);

--
-- Name: col_refs_new_ref_id_idx1; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS col_refs_new_ref_id_idx1 ON col_refs (ref_id);

--
-- Name: idx_44157051_col_id; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157051_col_id ON col_refs (col_id);

--
-- Name: idx_44157051_ref_id; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157051_ref_id ON col_refs (ref_id);

--
-- Name: projects_tree; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS projects_tree (
    id integer GENERATED ALWAYS AS IDENTITY,
    parent_id integer NOT NULL,
    child_id integer NOT NULL,
    CONSTRAINT projects_tree_pkey PRIMARY KEY (id),
    CONSTRAINT projects_tree_parent_id_child_id_key UNIQUE (parent_id, child_id),
    CONSTRAINT projects_tree_child_id_fkey FOREIGN KEY (child_id) REFERENCES projects (id) ON UPDATE CASCADE ON DELETE CASCADE,
    CONSTRAINT projects_tree_parent_id_fkey FOREIGN KEY (parent_id) REFERENCES projects (id) ON UPDATE CASCADE ON DELETE CASCADE
);

--
-- Name: sections; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS sections (
    id BIGSERIAL,
    col_id integer NOT NULL,
    fo integer DEFAULT 0 NOT NULL,
    fo_h smallint NOT NULL,
    lo integer DEFAULT 0 NOT NULL,
    lo_h smallint NOT NULL,
    CONSTRAINT idx_44157294_primary PRIMARY KEY (id),
    CONSTRAINT sections_cols_fk FOREIGN KEY (col_id) REFERENCES cols (id) ON DELETE CASCADE
);

--
-- Name: idx_44157294_col_id; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157294_col_id ON sections (col_id);

--
-- Name: idx_44157294_fo; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157294_fo ON sections (fo);

--
-- Name: idx_44157294_lo; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157294_lo ON sections (lo);

--
-- Name: sections_new_col_id_idx1; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS sections_new_col_id_idx1 ON sections (col_id);

--
-- Name: sections_new_id_idx1; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS sections_new_id_idx1 ON sections (id);

--
-- Name: timescales_intervals; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS timescales_intervals (
    timescale_id integer,
    interval_id integer,
    CONSTRAINT idx_44157363_primary PRIMARY KEY (timescale_id, interval_id),
    CONSTRAINT timescales_intervals_intervals_fk FOREIGN KEY (interval_id) REFERENCES intervals (id) ON DELETE CASCADE,
    CONSTRAINT timescales_intervals_timescales_fk FOREIGN KEY (timescale_id) REFERENCES timescales (id) ON DELETE CASCADE
);


COMMENT ON TABLE timescales_intervals IS 'Last updated from MariaDB - 2022-06-28 15:08';

--
-- Name: idx_44157363__timescale_intervals_interval_id; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157363__timescale_intervals_interval_id ON timescales_intervals (interval_id);

--
-- Name: idx_44157363__timescale_intervals_timescale_id; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157363__timescale_intervals_timescale_id ON timescales_intervals (timescale_id);

--
-- Name: timescales_intervals_new_interval_id_idx1; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS timescales_intervals_new_interval_id_idx1 ON timescales_intervals (interval_id);

--
-- Name: timescales_intervals_new_timescale_id_idx1; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS timescales_intervals_new_timescale_id_idx1 ON timescales_intervals (timescale_id);

--
-- Name: uniquedatafiles2; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS uniquedatafiles2 (
    id SERIAL,
    comp smallint NOT NULL,
    data smallint NOT NULL,
    ref1 integer NOT NULL,
    ref2 integer NOT NULL,
    colrnge varchar(60) NOT NULL,
    loc varchar(10) NOT NULL,
    lat varchar(20) NOT NULL,
    lon varchar(20) NOT NULL,
    state varchar(100) NOT NULL,
    stapi varchar(10) NOT NULL,
    county1 varchar(200) NOT NULL,
    county varchar(200) NOT NULL,
    coscode varchar(100) NOT NULL,
    provnme varchar(100) NOT NULL,
    colname varchar(100) NOT NULL,
    chart varchar(5) NOT NULL,
    chartnm varchar(5) NOT NULL,
    chartc varchar(5) NOT NULL,
    col varchar(7) NOT NULL,
    colc varchar(7) NOT NULL,
    strunit varchar(255) NOT NULL,
    grp smallint NOT NULL,
    formtn smallint NOT NULL,
    member smallint NOT NULL,
    bed smallint NOT NULL,
    rankdes varchar(200) NOT NULL,
    formal smallint NOT NULL,
    informl smallint NOT NULL,
    system varchar(255) NOT NULL,
    series varchar(255) NOT NULL,
    stage varchar(255) NOT NULL,
    surface smallint NOT NULL,
    subsurf smallint NOT NULL,
    bth smallint NOT NULL,
    above varchar(255) NOT NULL,
    below varchar(255) NOT NULL,
    domlith varchar(255) NOT NULL,
    dompct varchar(8) NOT NULL,
    sublith varchar(200) NOT NULL,
    subpct varchar(5) NOT NULL,
    thick1 varchar(8) NOT NULL,
    thick2 varchar(8) NOT NULL,
    abvnone smallint NOT NULL,
    abvdis smallint NOT NULL,
    abvang smallint NOT NULL,
    winone smallint NOT NULL,
    widis smallint NOT NULL,
    woamg smallint NOT NULL,
    blwnone smallint NOT NULL,
    blwdis smallint NOT NULL,
    blwang smallint NOT NULL,
    fossil text NOT NULL,
    rad text NOT NULL,
    econ text NOT NULL,
    other text NOT NULL,
    origref text NOT NULL,
    sigref text NOT NULL,
    author varchar(255) NOT NULL,
    date varchar(100) NOT NULL,
    added_unit bytea DEFAULT '\x7827333127' NOT NULL,
    CONSTRAINT idx_44157367_primary PRIMARY KEY (id)
);

--
-- Name: unit_boundaries; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS unit_boundaries (
    id SERIAL,
    t1 integer NOT NULL,
    t1_prop numeric(6,5) NOT NULL,
    t1_age numeric(8,4) NOT NULL,
    unit_id integer NOT NULL,
    unit_id_2 integer NOT NULL,
    section_id integer NOT NULL,
    boundary_position numeric(7,3) DEFAULT NULL,
    boundary_type unit_boundaries_boundary_type DEFAULT '' NOT NULL,
    boundary_status unit_boundaries_boundary_status DEFAULT 'modeled' NOT NULL,
    paleo_lat numeric(7,3) DEFAULT NULL,
    paleo_lng numeric(7,3) DEFAULT NULL,
    ref_id integer DEFAULT 217 NOT NULL,
    CONSTRAINT idx_44157393_primary PRIMARY KEY (id)
);

--
-- Name: idx_44157393_section_id; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157393_section_id ON unit_boundaries (section_id);

--
-- Name: idx_44157393_t1; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157393_t1 ON unit_boundaries (t1);

--
-- Name: idx_44157393_unit_id; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157393_unit_id ON unit_boundaries (unit_id);

--
-- Name: idx_44157393_unit_id_2; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157393_unit_id_2 ON unit_boundaries (unit_id_2);

--
-- Name: unit_boundaries_section_id_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS unit_boundaries_section_id_idx ON unit_boundaries (section_id);

--
-- Name: unit_boundaries_t1_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS unit_boundaries_t1_idx ON unit_boundaries (t1);

--
-- Name: unit_boundaries_unit_id_2_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS unit_boundaries_unit_id_2_idx ON unit_boundaries (unit_id_2);

--
-- Name: unit_boundaries_unit_id_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS unit_boundaries_unit_id_idx ON unit_boundaries (unit_id);

--
-- Name: unit_boundaries_backup; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS unit_boundaries_backup (
    id SERIAL,
    t1 integer NOT NULL,
    t1_prop numeric(6,5) NOT NULL,
    t1_age numeric(8,4) NOT NULL,
    unit_id integer NOT NULL,
    unit_id_2 integer NOT NULL,
    section_id integer NOT NULL,
    boundary_position numeric(6,2) DEFAULT NULL,
    boundary_type unit_boundaries_backup_boundary_type DEFAULT '' NOT NULL,
    boundary_status unit_boundaries_backup_boundary_status DEFAULT 'modeled' NOT NULL,
    paleo_lat numeric(7,3) DEFAULT NULL,
    paleo_lng numeric(7,3) DEFAULT NULL,
    ref_id integer DEFAULT 217 NOT NULL,
    CONSTRAINT idx_44157404_primary PRIMARY KEY (id)
);

--
-- Name: idx_44157404_section_id; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157404_section_id ON unit_boundaries_backup (section_id);

--
-- Name: idx_44157404_t1; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157404_t1 ON unit_boundaries_backup (t1);

--
-- Name: idx_44157404_unit_id; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157404_unit_id ON unit_boundaries_backup (unit_id);

--
-- Name: idx_44157404_unit_id_2; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157404_unit_id_2 ON unit_boundaries_backup (unit_id_2);

--
-- Name: unit_boundaries_scratch; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS unit_boundaries_scratch (
    id SERIAL,
    t1 integer NOT NULL,
    t1_prop numeric(6,5) NOT NULL,
    t1_age numeric(8,4) NOT NULL,
    unit_id integer NOT NULL,
    unit_id_2 integer NOT NULL,
    section_id integer NOT NULL,
    boundary_position numeric(6,2) DEFAULT NULL,
    boundary_type unit_boundaries_scratch_boundary_type DEFAULT '' NOT NULL,
    boundary_status unit_boundaries_scratch_boundary_status DEFAULT 'modeled' NOT NULL,
    paleo_lat numeric(7,3) DEFAULT NULL,
    paleo_lng numeric(7,3) DEFAULT NULL,
    ref_id integer DEFAULT 217 NOT NULL,
    CONSTRAINT idx_44157415_primary PRIMARY KEY (id)
);

--
-- Name: idx_44157415_section_id; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157415_section_id ON unit_boundaries_scratch (section_id);

--
-- Name: idx_44157415_t1; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157415_t1 ON unit_boundaries_scratch (t1);

--
-- Name: idx_44157415_unit_id; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157415_unit_id ON unit_boundaries_scratch (unit_id);

--
-- Name: idx_44157415_unit_id_2; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157415_unit_id_2 ON unit_boundaries_scratch (unit_id_2);

--
-- Name: unit_boundaries_scratch_old; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS unit_boundaries_scratch_old (
    id SERIAL,
    t1 integer NOT NULL,
    t1_prop numeric(6,5) NOT NULL,
    t1_age numeric(8,4) NOT NULL,
    unit_id integer NOT NULL,
    unit_id_2 integer NOT NULL,
    section_id integer NOT NULL,
    boundary_type unit_boundaries_scratch_old_boundary_type DEFAULT '' NOT NULL,
    boundary_status unit_boundaries_scratch_old_boundary_status DEFAULT 'modeled' NOT NULL,
    paleo_lat numeric(7,3) DEFAULT NULL,
    paleo_lng numeric(7,3) DEFAULT NULL,
    CONSTRAINT idx_44157426_primary PRIMARY KEY (id)
);

--
-- Name: idx_44157426_section_id; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157426_section_id ON unit_boundaries_scratch_old (section_id);

--
-- Name: idx_44157426_t1; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157426_t1 ON unit_boundaries_scratch_old (t1);

--
-- Name: idx_44157426_unit_id; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157426_unit_id ON unit_boundaries_scratch_old (unit_id);

--
-- Name: idx_44157426_unit_id_2; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157426_unit_id_2 ON unit_boundaries_scratch_old (unit_id_2);

--
-- Name: unit_contacts; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS unit_contacts (
    id SERIAL,
    unit_id integer NOT NULL,
    old_contact unit_contacts_old_contact NOT NULL,
    contact unit_contacts_contact NOT NULL,
    old_with_unit integer NOT NULL,
    with_unit integer NOT NULL,
    CONSTRAINT idx_44157435_primary PRIMARY KEY (id)
);

--
-- Name: idx_44157435_unit_id; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157435_unit_id ON unit_contacts (unit_id);

--
-- Name: idx_44157435_with_unit; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157435_with_unit ON unit_contacts (with_unit);

--
-- Name: unit_dates; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS unit_dates (
    id SERIAL,
    unit_id integer NOT NULL,
    age numeric(7,3) NOT NULL,
    error numeric(7,3) DEFAULT NULL,
    system unit_dates_system NOT NULL,
    source varchar(255) DEFAULT NULL,
    ref_id integer NOT NULL,
    date_mod timestamptz,
    CONSTRAINT idx_44157440_primary PRIMARY KEY (id)
);

--
-- Name: idx_44157440_ref_id; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157440_ref_id ON unit_dates (ref_id);

--
-- Name: idx_44157440_unit_id; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157440_unit_id ON unit_dates (unit_id);

--
-- Name: unit_equiv; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS unit_equiv (
    id SERIAL,
    unit_id integer NOT NULL,
    new_unit_id integer NOT NULL,
    CONSTRAINT idx_44157458_primary PRIMARY KEY (id)
);

--
-- Name: idx_44157458_new_unit_id; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157458_new_unit_id ON unit_equiv (new_unit_id);

--
-- Name: idx_44157458_unit_id; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157458_unit_id ON unit_equiv (unit_id);

--
-- Name: unit_lith_atts; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS unit_lith_atts (
    id integer,
    unit_lith_id integer,
    lith_att_id integer,
    ref_id integer,
    date_mod text,
    CONSTRAINT unit_lith_atts_new_pkey1 PRIMARY KEY (id)
);


COMMENT ON TABLE unit_lith_atts IS 'Last updated from MariaDB - 2022-06-28 15:10';

--
-- Name: unit_lith_atts_new_lith_att_id_idx1; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS unit_lith_atts_new_lith_att_id_idx1 ON unit_lith_atts (lith_att_id);

--
-- Name: unit_lith_atts_new_ref_id_idx1; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS unit_lith_atts_new_ref_id_idx1 ON unit_lith_atts (ref_id);

--
-- Name: unit_lith_atts_new_unit_lith_id_idx1; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS unit_lith_atts_new_unit_lith_id_idx1 ON unit_lith_atts (unit_lith_id);

--
-- Name: unit_measures; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS unit_measures (
    id SERIAL,
    measuremeta_id integer NOT NULL,
    unit_id integer NOT NULL,
    strat_name_id integer NOT NULL,
    match_basis varchar(10) NOT NULL,
    rel_position numeric(6,5) DEFAULT NULL,
    CONSTRAINT idx_44157474_primary PRIMARY KEY (id)
);


COMMENT ON TABLE unit_measures IS 'Last updated from MariaDB - 2018-09-25 10:40';

--
-- Name: idx_44157474_measuremeta_id; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157474_measuremeta_id ON unit_measures (measuremeta_id);

--
-- Name: idx_44157474_strat_name_id; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157474_strat_name_id ON unit_measures (strat_name_id);

--
-- Name: idx_44157474_unit_id; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157474_unit_id ON unit_measures (unit_id);

--
-- Name: unit_measures_new_measuremeta_id_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS unit_measures_new_measuremeta_id_idx ON unit_measures (measuremeta_id);

--
-- Name: unit_measures_new_strat_name_id_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS unit_measures_new_strat_name_id_idx ON unit_measures (strat_name_id);

--
-- Name: unit_measures_new_unit_id_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS unit_measures_new_unit_id_idx ON unit_measures (unit_id);

--
-- Name: unit_measures_pbdb; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS unit_measures_pbdb (
    collection_no integer NOT NULL,
    geo_name text NOT NULL,
    sample_col integer NOT NULL,
    unit_id integer NOT NULL,
    strat_name_id integer NOT NULL,
    strat_name text NOT NULL,
    b_age numeric(9,5) NOT NULL,
    t_age numeric(9,5) NOT NULL,
    strat_match text NOT NULL
);

--
-- Name: idx_44157479_collection_no; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157479_collection_no ON unit_measures_pbdb (collection_no);

--
-- Name: unit_notes; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS unit_notes (
    id SERIAL,
    notes text NOT NULL,
    unit_id integer NOT NULL,
    date_mod timestamptz,
    CONSTRAINT idx_44157485_primary PRIMARY KEY (id)
);

--
-- Name: idx_44157485_unit_id; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157485_unit_id ON unit_notes (unit_id);

--
-- Name: unit_seq_strat; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS unit_seq_strat (
    id SERIAL,
    unit_id integer NOT NULL,
    seq_strat unit_seq_strat_seq_strat NOT NULL,
    seq_order unit_seq_strat_seq_order NOT NULL,
    CONSTRAINT idx_44157492_primary PRIMARY KEY (id)
);

--
-- Name: idx_44157492_unit_id; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157492_unit_id ON unit_seq_strat (unit_id);

--
-- Name: unit_tectonics; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS unit_tectonics (
    id SERIAL,
    unit_id integer NOT NULL,
    tectonic_id integer NOT NULL,
    CONSTRAINT idx_44157502_primary PRIMARY KEY (id)
);

--
-- Name: idx_44157502_tectonic_id; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157502_tectonic_id ON unit_tectonics (tectonic_id);

--
-- Name: idx_44157502_unit_id; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157502_unit_id ON unit_tectonics (unit_id);

--
-- Name: units; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS units (
    id SERIAL,
    strat_name varchar(150) NOT NULL,
    color units_color NOT NULL,
    outcrop units_outcrop NOT NULL,
    fo integer DEFAULT 0 NOT NULL,
    fo_h smallint DEFAULT 0 NOT NULL,
    lo integer DEFAULT 0 NOT NULL,
    lo_h smallint DEFAULT 0 NOT NULL,
    position_bottom numeric(7,3) NOT NULL,
    position_top numeric(7,3) NOT NULL,
    max_thick numeric(7,2) NOT NULL,
    min_thick numeric(7,2) NOT NULL,
    section_id integer DEFAULT 0 NOT NULL,
    col_id integer NOT NULL,
    date_mod timestamptz,
    CONSTRAINT idx_44157375_primary PRIMARY KEY (id),
    CONSTRAINT units_cols_fk FOREIGN KEY (col_id) REFERENCES cols (id) ON DELETE CASCADE,
    CONSTRAINT units_intervals_fo_fk FOREIGN KEY (fo) REFERENCES intervals (id) ON DELETE RESTRICT,
    CONSTRAINT units_intervals_lo_fk FOREIGN KEY (lo) REFERENCES intervals (id) ON DELETE RESTRICT,
    CONSTRAINT units_sections_fk FOREIGN KEY (section_id) REFERENCES sections (id) ON DELETE CASCADE
);

--
-- Name: idx_44157375_col_id; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157375_col_id ON units (col_id);

--
-- Name: idx_44157375_color; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157375_color ON units (color);

--
-- Name: idx_44157375_fo; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157375_fo ON units (fo);

--
-- Name: idx_44157375_lo; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157375_lo ON units (lo);

--
-- Name: idx_44157375_section_id; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157375_section_id ON units (section_id);

--
-- Name: idx_44157375_strat_name; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157375_strat_name ON units (strat_name);

--
-- Name: units_new_col_id_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS units_new_col_id_idx ON units (col_id);

--
-- Name: units_new_color_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS units_new_color_idx ON units (color);

--
-- Name: units_new_section_id_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS units_new_section_id_idx ON units (section_id);

--
-- Name: units_new_strat_name_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS units_new_strat_name_idx ON units (strat_name);

--
-- Name: unit_econs; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS unit_econs (
    id SERIAL,
    unit_id integer NOT NULL,
    econ_id integer NOT NULL,
    ref_id integer NOT NULL,
    date_mod timestamptz,
    CONSTRAINT idx_44157447_primary PRIMARY KEY (id),
    CONSTRAINT unit_econs_econs_fk FOREIGN KEY (econ_id) REFERENCES econs (id) ON DELETE CASCADE,
    CONSTRAINT unit_econs_refs_fk FOREIGN KEY (ref_id) REFERENCES refs (id) ON DELETE CASCADE,
    CONSTRAINT unit_econs_units_fk FOREIGN KEY (unit_id) REFERENCES units (id) ON DELETE CASCADE
);


COMMENT ON TABLE unit_econs IS 'Last updated from MariaDB - 2022-06-28 15:06';

--
-- Name: idx_44157447_econ_id; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157447_econ_id ON unit_econs (econ_id);

--
-- Name: idx_44157447_ref_id; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157447_ref_id ON unit_econs (ref_id);

--
-- Name: idx_44157447_unit_id; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157447_unit_id ON unit_econs (unit_id);

--
-- Name: unit_econs_new_econ_id_idx1; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS unit_econs_new_econ_id_idx1 ON unit_econs (econ_id);

--
-- Name: unit_econs_new_ref_id_idx1; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS unit_econs_new_ref_id_idx1 ON unit_econs (ref_id);

--
-- Name: unit_econs_new_unit_id_idx1; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS unit_econs_new_unit_id_idx1 ON unit_econs (unit_id);

--
-- Name: unit_environs; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS unit_environs (
    id SERIAL,
    unit_id integer NOT NULL,
    environ_id integer NOT NULL,
    f integer,
    l integer,
    ref_id integer DEFAULT 1,
    date_mod timestamptz,
    CONSTRAINT idx_44157452_primary PRIMARY KEY (id),
    CONSTRAINT unit_environs_environs_fk FOREIGN KEY (environ_id) REFERENCES environs (id) ON DELETE CASCADE,
    CONSTRAINT unit_environs_refs_fk FOREIGN KEY (ref_id) REFERENCES refs (id) ON DELETE CASCADE,
    CONSTRAINT unit_environs_units_fk FOREIGN KEY (unit_id) REFERENCES units (id) ON DELETE CASCADE
);

--
-- Name: idx_44157452_environ_id; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157452_environ_id ON unit_environs (environ_id);

--
-- Name: idx_44157452_ref_id; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157452_ref_id ON unit_environs (ref_id);

--
-- Name: idx_44157452_unit_id; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157452_unit_id ON unit_environs (unit_id);

--
-- Name: unit_environs_new_environ_id_idx1; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS unit_environs_new_environ_id_idx1 ON unit_environs (environ_id);

--
-- Name: unit_environs_new_ref_id_idx1; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS unit_environs_new_ref_id_idx1 ON unit_environs (ref_id);

--
-- Name: unit_environs_new_unit_id_idx1; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS unit_environs_new_unit_id_idx1 ON unit_environs (unit_id);

--
-- Name: unit_liths; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS unit_liths (
    id SERIAL,
    lith_id integer NOT NULL,
    unit_id integer NOT NULL,
    prop varchar(7) DEFAULT NULL,
    dom unit_liths_dom NOT NULL,
    comp_prop numeric(5,4) NOT NULL,
    mod_prop numeric(5,4) NOT NULL,
    toc numeric(6,5) NOT NULL,
    ref_id integer NOT NULL,
    date_mod timestamptz,
    CONSTRAINT idx_44157463_primary PRIMARY KEY (id),
    CONSTRAINT unit_liths_liths_fk FOREIGN KEY (lith_id) REFERENCES liths (id) ON DELETE CASCADE,
    CONSTRAINT unit_liths_units_fk FOREIGN KEY (unit_id) REFERENCES units (id) ON DELETE CASCADE
);

--
-- Name: idx_44157463_lith_id; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157463_lith_id ON unit_liths (lith_id);

--
-- Name: idx_44157463_ref_id; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157463_ref_id ON unit_liths (ref_id);

--
-- Name: idx_44157463_unit_id; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157463_unit_id ON unit_liths (unit_id);

--
-- Name: unit_liths_new_lith_id_idx1; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS unit_liths_new_lith_id_idx1 ON unit_liths (lith_id);

--
-- Name: unit_liths_new_ref_id_idx1; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS unit_liths_new_ref_id_idx1 ON unit_liths (ref_id);

--
-- Name: unit_liths_new_unit_id_idx1; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS unit_liths_new_unit_id_idx1 ON unit_liths (unit_id);

--
-- Name: unit_liths_atts; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS unit_liths_atts (
    id SERIAL,
    unit_lith_id integer NOT NULL,
    lith_att_id integer NOT NULL,
    ref_id integer NOT NULL,
    date_mod timestamptz,
    CONSTRAINT idx_44157469_primary PRIMARY KEY (id),
    CONSTRAINT unit_liths_atts_lith_atts_fk FOREIGN KEY (lith_att_id) REFERENCES lith_atts (id) ON DELETE CASCADE,
    CONSTRAINT unit_liths_atts_unit_liths_fk FOREIGN KEY (unit_lith_id) REFERENCES unit_liths (id) ON DELETE CASCADE
);

--
-- Name: idx_44157469_lith_att_id; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157469_lith_att_id ON unit_liths_atts (lith_att_id);

--
-- Name: idx_44157469_ref_id; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157469_ref_id ON unit_liths_atts (ref_id);

--
-- Name: idx_44157469_unit_lith_id; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157469_unit_lith_id ON unit_liths_atts (unit_lith_id);

--
-- Name: unit_strat_names; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS unit_strat_names (
    id SERIAL,
    unit_id integer NOT NULL,
    strat_name_id integer NOT NULL,
    old_strat_name_id integer NOT NULL,
    CONSTRAINT idx_44157497_primary PRIMARY KEY (id),
    CONSTRAINT unit_strat_names_strat_names_fk FOREIGN KEY (strat_name_id) REFERENCES strat_names (id) ON DELETE CASCADE,
    CONSTRAINT unit_strat_names_units_fk FOREIGN KEY (unit_id) REFERENCES units (id) ON DELETE CASCADE
);

--
-- Name: idx_44157497_strat_name_id; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157497_strat_name_id ON unit_strat_names (strat_name_id);

--
-- Name: idx_44157497_unit_id; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157497_unit_id ON unit_strat_names (unit_id);

--
-- Name: unit_strat_names_new_strat_name_id_idx1; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS unit_strat_names_new_strat_name_id_idx1 ON unit_strat_names (strat_name_id);

--
-- Name: unit_strat_names_new_unit_id_idx1; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS unit_strat_names_new_unit_id_idx1 ON unit_strat_names (unit_id);

--
-- Name: units_datafiles; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS units_datafiles (
    unit_id integer,
    datafile_id integer NOT NULL,
    CONSTRAINT idx_44157384_primary PRIMARY KEY (unit_id)
);

--
-- Name: idx_44157384_datafile_id; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157384_datafile_id ON units_datafiles (datafile_id);

--
-- Name: units_sections; Type: TABLE; Schema: -; Owner: -
--

CREATE TABLE IF NOT EXISTS units_sections (
    id SERIAL,
    unit_id integer NOT NULL,
    section_id integer NOT NULL,
    col_id integer NOT NULL,
    CONSTRAINT idx_44157388_primary PRIMARY KEY (id),
    CONSTRAINT units_sections_sections_fk FOREIGN KEY (section_id) REFERENCES sections (id) ON DELETE CASCADE,
    CONSTRAINT units_sections_units_fk FOREIGN KEY (unit_id) REFERENCES units (id) ON DELETE CASCADE
);

--
-- Name: idx_44157388_col_id; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157388_col_id ON units_sections (col_id);

--
-- Name: idx_44157388_section_id; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157388_section_id ON units_sections (section_id);

--
-- Name: idx_44157388_unit_id; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_44157388_unit_id ON units_sections (unit_id);

--
-- Name: units_sections_new_col_id_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS units_sections_new_col_id_idx ON units_sections (col_id);

--
-- Name: units_sections_new_section_id_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS units_sections_new_section_id_idx ON units_sections (section_id);

--
-- Name: units_sections_new_unit_id_idx; Type: INDEX; Schema: -; Owner: -
--

CREATE INDEX IF NOT EXISTS units_sections_new_unit_id_idx ON units_sections (unit_id);

--
-- Name: check_column_project_non_composite(); Type: FUNCTION; Schema: -; Owner: -
--

CREATE OR REPLACE FUNCTION check_column_project_non_composite()
RETURNS trigger
LANGUAGE plpgsql
VOLATILE
AS $$
BEGIN
  IF (SELECT is_composite FROM macrostrat.projects WHERE id = NEW.project_id)
  THEN
    RAISE EXCEPTION 'A composite project cannot itself contain columns. We may relax this restriction in the future.';
  END IF;
  RETURN NEW;
END;
$$;

--
-- Name: check_composite_parent(); Type: FUNCTION; Schema: -; Owner: -
--

CREATE OR REPLACE FUNCTION check_composite_parent()
RETURNS trigger
LANGUAGE plpgsql
VOLATILE
AS $$
BEGIN
  IF NOT (SELECT is_composite FROM macrostrat.projects WHERE id = NEW.parent_id) THEN
    RAISE EXCEPTION 'Parent project must be a composite project';
  END IF;
  RETURN NEW;
END;
$$;

--
-- Name: core_project_ids(); Type: FUNCTION; Schema: -; Owner: -
--

CREATE OR REPLACE FUNCTION core_project_ids()
RETURNS integer[]
LANGUAGE sql
STABLE
AS $$
SELECT macrostrat.flattened_project_ids(ARRAY[id]) FROM macrostrat.projects WHERE slug = 'core';
$$;

--
-- Name: flattened_project_ids(integer[]); Type: FUNCTION; Schema: -; Owner: -
--

CREATE OR REPLACE FUNCTION flattened_project_ids(
    project_ids integer[]
)
RETURNS integer[]
LANGUAGE plpgsql
STABLE
AS $$
DECLARE
  result_ids integer[] := ARRAY[]::integer[];
  current_ids integer[] := project_ids;
  child_ids integer[];
BEGIN
  LOOP
    EXIT WHEN array_length(current_ids, 1) IS NULL;
    result_ids := result_ids || current_ids;
    SELECT array_agg(pt.child_id)
    INTO child_ids
    FROM macrostrat.projects_tree pt
    WHERE pt.parent_id = ANY(current_ids);
    current_ids := child_ids;
  END LOOP;
  RETURN ARRAY(SELECT DISTINCT unnest(result_ids));
END;
$$;

--
-- Name: generate_project_slug(projects); Type: FUNCTION; Schema: -; Owner: -
--

CREATE OR REPLACE FUNCTION generate_project_slug(
    _project projects
)
RETURNS text
LANGUAGE plpgsql
VOLATILE
AS $$
DECLARE
  base_slug TEXT;
  unique_slug TEXT;
  suffix INT;
BEGIN
  base_slug := lower(regexp_replace(_project.project, '[^a-zA-Z0-9]+', '-', 'g'));
  unique_slug := base_slug;
  suffix := 1;
  WHILE EXISTS (SELECT 1 FROM macrostrat.projects p WHERE p.slug = unique_slug AND p.id != _project.id) LOOP
    suffix := suffix + 1;
    unique_slug := base_slug || '-' || suffix;
  END LOOP;
  RETURN unique_slug;
END;
$$;

--
-- Name: generate_project_slug(text); Type: FUNCTION; Schema: -; Owner: -
--

CREATE OR REPLACE FUNCTION generate_project_slug(
    project_name text
)
RETURNS text
LANGUAGE plpgsql
VOLATILE
AS $$
DECLARE
  base_slug TEXT;
  unique_slug TEXT;
  suffix INT;
BEGIN
  base_slug := lower(regexp_replace(project_name, '[^a-zA-Z0-9]+', '-', 'g'));
  unique_slug := base_slug;
  suffix := 1;
  WHILE EXISTS (SELECT 1 FROM macrostrat.projects WHERE slug = unique_slug) LOOP
    suffix := suffix + 1;
    unique_slug := base_slug || '-' || suffix;
  END LOOP;
  RETURN unique_slug;
END;
$$;

--
-- Name: get_lith_comp_prop(integer); Type: FUNCTION; Schema: -; Owner: -
--

CREATE OR REPLACE FUNCTION get_lith_comp_prop(
    _unit_id integer
)
RETURNS TABLE(dom_prop numeric, sub_prop numeric)
LANGUAGE plpgsql
VOLATILE
AS $$
BEGIN
  RETURN QUERY
    WITH dom as (
        SELECT
            unit_id,
            count(id) count,
            'dom' AS dom
        FROM macrostrat.unit_liths
        WHERE dom = 'dom' and unit_id = _unit_id
        GROUP BY unit_id
      ), sub as(
        SELECT
          unit_id,
          count(id) count,
          'sub' AS dom
        FROM macrostrat.unit_liths
        WHERE dom = 'sub' and unit_id = _unit_id
        GROUP BY unit_id
      )
    SELECT
      -- need at least one float to prevent truncating to 0
      ROUND((5.0 / (COALESCE(sub.count, 0) + (dom.count * 5))),4) AS dom_prop,
      ROUND((1.0 / (COALESCE(sub.count, 0) + (dom.count * 5))),4) AS sub_prop
    FROM sub
    JOIN dom
    ON dom.unit_id = sub.unit_id;
END
$$;

--
-- Name: lng_lat_insert_trigger(); Type: FUNCTION; Schema: -; Owner: -
--

CREATE OR REPLACE FUNCTION lng_lat_insert_trigger()
RETURNS trigger
LANGUAGE plpgsql
VOLATILE
AS $$
DECLARE
BEGIN
  IF tg_op = 'INSERT' OR new.lat <> old.lat OR new.lng <> old.lng THEN
    new.wkt := ST_AsText(ST_MakePoint(new.lng, new.lat));
    new.coordinate := ST_SetSrid(new.wkt, 4326);
  END IF;
  RETURN new;
END;
$$;

--
-- Name: on_update_current_timestamp_offshore_baggage(); Type: FUNCTION; Schema: -; Owner: -
--

CREATE OR REPLACE FUNCTION on_update_current_timestamp_offshore_baggage()
RETURNS trigger
LANGUAGE plpgsql
VOLATILE
AS $$
BEGIN
   NEW.created_at = now();
   RETURN NEW;
END;
$$;

--
-- Name: on_update_current_timestamp_offshore_fossils(); Type: FUNCTION; Schema: -; Owner: -
--

CREATE OR REPLACE FUNCTION on_update_current_timestamp_offshore_fossils()
RETURNS trigger
LANGUAGE plpgsql
VOLATILE
AS $$
BEGIN
   NEW.created_at = now();
   RETURN NEW;
END;
$$;

--
-- Name: on_update_current_timestamp_unit_dates(); Type: FUNCTION; Schema: -; Owner: -
--

CREATE OR REPLACE FUNCTION on_update_current_timestamp_unit_dates()
RETURNS trigger
LANGUAGE plpgsql
VOLATILE
AS $$
BEGIN
   NEW.date_mod = now();
   RETURN NEW;
END;
$$;

--
-- Name: on_update_current_timestamp_unit_econs(); Type: FUNCTION; Schema: -; Owner: -
--

CREATE OR REPLACE FUNCTION on_update_current_timestamp_unit_econs()
RETURNS trigger
LANGUAGE plpgsql
VOLATILE
AS $$
BEGIN
   NEW.date_mod = now();
   RETURN NEW;
END;
$$;

--
-- Name: on_update_current_timestamp_unit_environs(); Type: FUNCTION; Schema: -; Owner: -
--

CREATE OR REPLACE FUNCTION on_update_current_timestamp_unit_environs()
RETURNS trigger
LANGUAGE plpgsql
VOLATILE
AS $$
BEGIN
   NEW.date_mod = now();
   RETURN NEW;
END;
$$;

--
-- Name: on_update_current_timestamp_unit_liths(); Type: FUNCTION; Schema: -; Owner: -
--

CREATE OR REPLACE FUNCTION on_update_current_timestamp_unit_liths()
RETURNS trigger
LANGUAGE plpgsql
VOLATILE
AS $$
BEGIN
   NEW.date_mod = now();
   RETURN NEW;
END;
$$;

--
-- Name: on_update_current_timestamp_unit_liths_atts(); Type: FUNCTION; Schema: -; Owner: -
--

CREATE OR REPLACE FUNCTION on_update_current_timestamp_unit_liths_atts()
RETURNS trigger
LANGUAGE plpgsql
VOLATILE
AS $$
BEGIN
   NEW.date_mod = now();
   RETURN NEW;
END;
$$;

--
-- Name: on_update_current_timestamp_unit_notes(); Type: FUNCTION; Schema: -; Owner: -
--

CREATE OR REPLACE FUNCTION on_update_current_timestamp_unit_notes()
RETURNS trigger
LANGUAGE plpgsql
VOLATILE
AS $$
BEGIN
   NEW.date_mod = now();
   RETURN NEW;
END;
$$;

--
-- Name: on_update_current_timestamp_units(); Type: FUNCTION; Schema: -; Owner: -
--

CREATE OR REPLACE FUNCTION on_update_current_timestamp_units()
RETURNS trigger
LANGUAGE plpgsql
VOLATILE
AS $$
BEGIN
   NEW.date_mod = now();
   RETURN NEW;
END;
$$;

--
-- Name: update_unit_lith_comp_props(integer); Type: FUNCTION; Schema: -; Owner: -
--

CREATE OR REPLACE FUNCTION update_unit_lith_comp_props(
    _unit_id integer
)
RETURNS void
LANGUAGE plpgsql
VOLATILE
AS $$
BEGIN
  UPDATE macrostrat.unit_liths ul
  SET
    comp_prop = (CASE WHEN ul.dom = 'sub' THEN prop.sub_prop ELSE prop.dom_prop END)
  FROM (SELECT * FROM macrostrat.get_lith_comp_prop(_unit_id)) as prop
  WHERE ul.unit_id = _unit_id;
END
$$;

--
-- Name: lng_lat_insert_trigger; Type: TRIGGER; Schema: -; Owner: -
--

CREATE OR REPLACE TRIGGER lng_lat_insert_trigger
    BEFORE INSERT OR UPDATE ON cols
    FOR EACH ROW
    EXECUTE FUNCTION lng_lat_insert_trigger();

--
-- Name: on_update_current_timestamp; Type: TRIGGER; Schema: -; Owner: -
--

CREATE OR REPLACE TRIGGER on_update_current_timestamp
    BEFORE UPDATE ON offshore_baggage
    FOR EACH ROW
    EXECUTE FUNCTION on_update_current_timestamp_offshore_baggage();

--
-- Name: on_update_current_timestamp; Type: TRIGGER; Schema: -; Owner: -
--

CREATE OR REPLACE TRIGGER on_update_current_timestamp
    BEFORE UPDATE ON offshore_fossils
    FOR EACH ROW
    EXECUTE FUNCTION on_update_current_timestamp_offshore_fossils();

--
-- Name: on_update_current_timestamp; Type: TRIGGER; Schema: -; Owner: -
--

CREATE OR REPLACE TRIGGER on_update_current_timestamp
    BEFORE UPDATE ON unit_dates
    FOR EACH ROW
    EXECUTE FUNCTION on_update_current_timestamp_unit_dates();

--
-- Name: on_update_current_timestamp; Type: TRIGGER; Schema: -; Owner: -
--

CREATE OR REPLACE TRIGGER on_update_current_timestamp
    BEFORE UPDATE ON unit_notes
    FOR EACH ROW
    EXECUTE FUNCTION on_update_current_timestamp_unit_notes();

--
-- Name: on_update_current_timestamp; Type: TRIGGER; Schema: -; Owner: -
--

CREATE OR REPLACE TRIGGER on_update_current_timestamp
    BEFORE UPDATE ON units
    FOR EACH ROW
    EXECUTE FUNCTION on_update_current_timestamp_units();

--
-- Name: on_update_current_timestamp; Type: TRIGGER; Schema: -; Owner: -
--

CREATE OR REPLACE TRIGGER on_update_current_timestamp
    BEFORE UPDATE ON unit_econs
    FOR EACH ROW
    EXECUTE FUNCTION on_update_current_timestamp_unit_econs();

--
-- Name: on_update_current_timestamp; Type: TRIGGER; Schema: -; Owner: -
--

CREATE OR REPLACE TRIGGER on_update_current_timestamp
    BEFORE UPDATE ON unit_environs
    FOR EACH ROW
    EXECUTE FUNCTION on_update_current_timestamp_unit_environs();

--
-- Name: on_update_current_timestamp; Type: TRIGGER; Schema: -; Owner: -
--

CREATE OR REPLACE TRIGGER on_update_current_timestamp
    BEFORE UPDATE ON unit_liths
    FOR EACH ROW
    EXECUTE FUNCTION on_update_current_timestamp_unit_liths();

--
-- Name: on_update_current_timestamp; Type: TRIGGER; Schema: -; Owner: -
--

CREATE OR REPLACE TRIGGER on_update_current_timestamp
    BEFORE UPDATE ON unit_liths_atts
    FOR EACH ROW
    EXECUTE FUNCTION on_update_current_timestamp_unit_liths_atts();

--
-- Name: trg_check_column_project_non_composite; Type: TRIGGER; Schema: -; Owner: -
--

CREATE OR REPLACE TRIGGER trg_check_column_project_non_composite
    BEFORE INSERT OR UPDATE ON cols
    FOR EACH ROW
    EXECUTE FUNCTION check_column_project_non_composite();

--
-- Name: trg_check_composite_parent; Type: TRIGGER; Schema: -; Owner: -
--

CREATE OR REPLACE TRIGGER trg_check_composite_parent
    BEFORE INSERT OR UPDATE ON projects_tree
    FOR EACH ROW
    EXECUTE FUNCTION check_composite_parent();

