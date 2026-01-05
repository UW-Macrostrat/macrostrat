
CREATE SCHEMA macrostrat;
ALTER SCHEMA macrostrat OWNER TO macrostrat;

CREATE TYPE macrostrat.colors_color AS ENUM (
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
ALTER TYPE macrostrat.colors_color OWNER TO macrostrat_admin;

CREATE TYPE macrostrat.cols_col_position AS ENUM (
    '',
    'onshore',
    'offshore'
);
ALTER TYPE macrostrat.cols_col_position OWNER TO macrostrat_admin;

CREATE TYPE macrostrat.cols_col_type AS ENUM (
    'column',
    'section'
);
ALTER TYPE macrostrat.cols_col_type OWNER TO macrostrat_admin;

CREATE TYPE macrostrat.cols_status_code AS ENUM (
    '',
    'active',
    'in process',
    'obsolete'
);
ALTER TYPE macrostrat.cols_status_code OWNER TO macrostrat_admin;

CREATE TYPE macrostrat.econs_econ_class AS ENUM (
    '',
    'energy',
    'material',
    'precious commodity',
    'water'
);
ALTER TYPE macrostrat.econs_econ_class OWNER TO macrostrat_admin;

CREATE TYPE macrostrat.econs_econ_type AS ENUM (
    '',
    'mineral',
    'hydrocarbon',
    'construction',
    'nuclear',
    'coal',
    'aquifer'
);
ALTER TYPE macrostrat.econs_econ_type OWNER TO macrostrat_admin;

CREATE TYPE macrostrat.environs_environ_class AS ENUM (
    '',
    'marine',
    'non-marine'
);
ALTER TYPE macrostrat.environs_environ_class OWNER TO macrostrat_admin;

CREATE TYPE macrostrat.environs_environ_type AS ENUM (
    '',
    'carbonate',
    'siliciclastic',
    'fluvial',
    'lacustrine',
    'landscape',
    'glacial',
    'eolian'
);
ALTER TYPE macrostrat.environs_environ_type OWNER TO macrostrat_admin;
CREATE TYPE macrostrat.boundary_status AS ENUM (
    '',
    'modeled',
    'relative',
    'absolute',
    'spike'
);
ALTER TYPE macrostrat.boundary_status OWNER TO macrostrat_admin;

CREATE TYPE macrostrat.intervals_interval_type AS ENUM (
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
ALTER TYPE macrostrat.intervals_interval_type OWNER TO macrostrat_admin;

CREATE TYPE macrostrat.lith_atts_att_type AS ENUM (
    '',
    'bedform',
    'sed structure',
    'grains',
    'color',
    'lithology',
    'structure'
);
ALTER TYPE macrostrat.lith_atts_att_type OWNER TO macrostrat_admin;

CREATE TYPE macrostrat.liths_lith_class AS ENUM (
    '',
    'sedimentary',
    'igneous',
    'metamorphic'
);
ALTER TYPE macrostrat.liths_lith_class OWNER TO macrostrat_admin;

CREATE TYPE macrostrat.liths_lith_group AS ENUM (
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
ALTER TYPE macrostrat.liths_lith_group OWNER TO macrostrat_admin;

CREATE TYPE macrostrat.liths_lith_type AS ENUM (
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
ALTER TYPE macrostrat.liths_lith_type OWNER TO macrostrat_admin;

CREATE TYPE macrostrat.measurement_class AS ENUM (
    '',
    'geophysical',
    'geochemical',
    'sedimentological'
);
ALTER TYPE macrostrat.measurement_class OWNER TO macrostrat_admin;
CREATE TYPE macrostrat.measurement_type AS ENUM (
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
ALTER TYPE macrostrat.measurement_type OWNER TO macrostrat_admin;

CREATE TYPE macrostrat.lookup_strat_names_rank AS ENUM (
    '',
    'SGp',
    'Gp',
    'SubGp',
    'Fm',
    'Mbr',
    'Bed'
);
ALTER TYPE macrostrat.lookup_strat_names_rank OWNER TO macrostrat_admin;

CREATE TYPE macrostrat.map_scale AS ENUM (
    'tiny',
    'small',
    'medium',
    'large'
);
ALTER TYPE macrostrat.map_scale OWNER TO macrostrat_admin;

CREATE TYPE macrostrat.pbdb_intervals_interval_type AS ENUM (
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
ALTER TYPE macrostrat.pbdb_intervals_interval_type OWNER TO macrostrat_admin;

CREATE TYPE macrostrat.refs_compilation_code AS ENUM (
    '',
    'COSUNA',
    'COSUNA II',
    'Canada',
    'GNS Folio Series 1'
);
ALTER TYPE macrostrat.refs_compilation_code OWNER TO macrostrat_admin;

CREATE TYPE macrostrat.rockd_features_feature_class AS ENUM (
    '',
    'structure',
    'geomorphology'
);
ALTER TYPE macrostrat.rockd_features_feature_class OWNER TO macrostrat_admin;

CREATE TYPE macrostrat.rockd_features_feature_type AS ENUM (
    '',
    'fault',
    'glacial',
    'deformation'
);
ALTER TYPE macrostrat.rockd_features_feature_type OWNER TO macrostrat_admin;

CREATE TYPE macrostrat.stats_project AS ENUM (
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
ALTER TYPE macrostrat.stats_project OWNER TO macrostrat_admin;

CREATE TYPE macrostrat.strat_names_lookup_rank AS ENUM (
    '',
    'SGp',
    'Gp',
    'Fm',
    'Mbr',
    'Bed'
);
ALTER TYPE macrostrat.strat_names_lookup_rank OWNER TO macrostrat_admin;

CREATE TYPE macrostrat.strat_names_rank AS ENUM (
    '',
    'SGp',
    'Gp',
    'SubGp',
    'Fm',
    'Mbr',
    'Bed'
);
ALTER TYPE macrostrat.strat_names_rank OWNER TO macrostrat_admin;

CREATE TYPE macrostrat.strat_tree_rel AS ENUM (
    '',
    'parent',
    'synonym'
);
ALTER TYPE macrostrat.strat_tree_rel OWNER TO macrostrat_admin;

CREATE TYPE macrostrat.structure_atts_att_class AS ENUM (
);
ALTER TYPE macrostrat.structure_atts_att_class OWNER TO macrostrat_admin;

CREATE TYPE macrostrat.structure_atts_att_type AS ENUM (
);
ALTER TYPE macrostrat.structure_atts_att_type OWNER TO macrostrat_admin;

CREATE TYPE macrostrat.structures_structure_class AS ENUM (
    '',
    'fracture',
    'structure',
    'fabric',
    'sedimentology',
    'igneous'
);
ALTER TYPE macrostrat.structures_structure_class OWNER TO macrostrat_admin;

CREATE TYPE macrostrat.structures_structure_group AS ENUM (
);
ALTER TYPE macrostrat.structures_structure_group OWNER TO macrostrat_admin;

CREATE TYPE macrostrat.structures_structure_type AS ENUM (
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
ALTER TYPE macrostrat.structures_structure_type OWNER TO macrostrat_admin;

CREATE TYPE macrostrat.tectonics_basin_setting AS ENUM (
    '',
    'divergent',
    'intraplate',
    'convergent',
    'transform',
    'hybrid'
);
ALTER TYPE macrostrat.tectonics_basin_setting OWNER TO macrostrat_admin;
CREATE TYPE macrostrat.boundary_type AS ENUM (
    '',
    'unconformity',
    'conformity',
    'fault',
    'disconformity',
    'non-conformity',
    'angular unconformity'
);
ALTER TYPE macrostrat.boundary_type OWNER TO macrostrat_admin;

CREATE TYPE macrostrat.unit_contacts_contact AS ENUM (
    'above',
    'below',
    'lateral',
    'lateral-bottom',
    'lateral-top',
    'within'
);
ALTER TYPE macrostrat.unit_contacts_contact OWNER TO macrostrat_admin;

CREATE TYPE macrostrat.unit_contacts_old_contact AS ENUM (
    'above',
    'below',
    'lateral',
    'lateral-bottom',
    'lateral-top',
    'within'
);
ALTER TYPE macrostrat.unit_contacts_old_contact OWNER TO macrostrat_admin;

CREATE TYPE macrostrat.unit_dates_system AS ENUM (
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
ALTER TYPE macrostrat.unit_dates_system OWNER TO macrostrat_admin;

CREATE TYPE macrostrat.unit_liths_dom AS ENUM (
    '',
    'dom',
    'sub'
);
ALTER TYPE macrostrat.unit_liths_dom OWNER TO macrostrat_admin;

CREATE TYPE macrostrat.unit_seq_strat_seq_order AS ENUM (
    '',
    '2nd',
    '3rd',
    '4th',
    '5th',
    '6th'
);
ALTER TYPE macrostrat.unit_seq_strat_seq_order OWNER TO macrostrat_admin;

CREATE TYPE macrostrat.unit_seq_strat_seq_strat AS ENUM (
    '',
    'TST',
    'HST',
    'FSST',
    'LST',
    'SQ'
);
ALTER TYPE macrostrat.unit_seq_strat_seq_strat OWNER TO macrostrat_admin;

CREATE TYPE macrostrat.units_color AS ENUM (
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
ALTER TYPE macrostrat.units_color OWNER TO macrostrat_admin;

CREATE TYPE macrostrat.units_outcrop AS ENUM (
    '',
    'surface',
    'subsurface',
    'both'
);
ALTER TYPE macrostrat.units_outcrop OWNER TO macrostrat_admin;

CREATE FUNCTION macrostrat.check_column_project_non_composite() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
  IF (SELECT is_composite FROM macrostrat.projects WHERE id = NEW.project_id)
  THEN
    RAISE EXCEPTION 'A composite project cannot itself contain columns. We may relax this restriction in the future.';
  END IF;
  RETURN NEW;
END;
$$;
ALTER FUNCTION macrostrat.check_column_project_non_composite() OWNER TO macrostrat_admin;

CREATE FUNCTION macrostrat.check_composite_parent() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
  IF NOT (SELECT is_composite FROM macrostrat.projects WHERE id = NEW.parent_id) THEN
    RAISE EXCEPTION 'Parent project must be a composite project';
  END IF;
  RETURN NEW;
END;
$$;
ALTER FUNCTION macrostrat.check_composite_parent() OWNER TO macrostrat_admin;

CREATE FUNCTION macrostrat.core_project_ids() RETURNS integer[]
    LANGUAGE sql STABLE
    AS $$
SELECT macrostrat.flattened_project_ids(ARRAY[id]) FROM macrostrat.projects WHERE slug = 'core';
$$;
ALTER FUNCTION macrostrat.core_project_ids() OWNER TO macrostrat_admin;

CREATE FUNCTION macrostrat.flattened_project_ids(project_ids integer[]) RETURNS integer[]
    LANGUAGE plpgsql STABLE
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
ALTER FUNCTION macrostrat.flattened_project_ids(project_ids integer[]) OWNER TO macrostrat_admin;
SET default_tablespace = '';
SET default_table_access_method = heap;

CREATE TABLE macrostrat.projects (
    id integer NOT NULL,
    project text NOT NULL,
    descrip text NOT NULL,
    timescale_id integer NOT NULL,
    is_composite boolean DEFAULT false,
    slug text NOT NULL
);
ALTER TABLE macrostrat.projects OWNER TO macrostrat;

COMMENT ON TABLE macrostrat.projects IS 'Last updated from MariaDB - 2023-07-28 16:57';

CREATE FUNCTION macrostrat.generate_project_slug(_project macrostrat.projects) RETURNS text
    LANGUAGE plpgsql
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
ALTER FUNCTION macrostrat.generate_project_slug(_project macrostrat.projects) OWNER TO macrostrat_admin;

CREATE FUNCTION macrostrat.generate_project_slug(project_name text) RETURNS text
    LANGUAGE plpgsql
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
ALTER FUNCTION macrostrat.generate_project_slug(project_name text) OWNER TO macrostrat_admin;

CREATE FUNCTION macrostrat.get_lith_comp_prop(_unit_id integer) RETURNS TABLE(dom_prop numeric, sub_prop numeric)
    LANGUAGE plpgsql
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
ALTER FUNCTION macrostrat.get_lith_comp_prop(_unit_id integer) OWNER TO macrostrat_admin;

CREATE FUNCTION macrostrat.lng_lat_insert_trigger() RETURNS trigger
    LANGUAGE plpgsql
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
ALTER FUNCTION macrostrat.lng_lat_insert_trigger() OWNER TO macrostrat_admin;

CREATE FUNCTION macrostrat.on_update_current_timestamp_offshore_baggage() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
   NEW.created_at = now();
   RETURN NEW;
END;
$$;
ALTER FUNCTION macrostrat.on_update_current_timestamp_offshore_baggage() OWNER TO macrostrat_admin;

CREATE FUNCTION macrostrat.on_update_current_timestamp_offshore_fossils() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
   NEW.created_at = now();
   RETURN NEW;
END;
$$;
ALTER FUNCTION macrostrat.on_update_current_timestamp_offshore_fossils() OWNER TO macrostrat_admin;

CREATE FUNCTION macrostrat.on_update_current_timestamp_unit_dates() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
   NEW.date_mod = now();
   RETURN NEW;
END;
$$;
ALTER FUNCTION macrostrat.on_update_current_timestamp_unit_dates() OWNER TO macrostrat_admin;

CREATE FUNCTION macrostrat.on_update_current_timestamp_unit_econs() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
   NEW.date_mod = now();
   RETURN NEW;
END;
$$;
ALTER FUNCTION macrostrat.on_update_current_timestamp_unit_econs() OWNER TO macrostrat_admin;

CREATE FUNCTION macrostrat.on_update_current_timestamp_unit_environs() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
   NEW.date_mod = now();
   RETURN NEW;
END;
$$;
ALTER FUNCTION macrostrat.on_update_current_timestamp_unit_environs() OWNER TO macrostrat_admin;

CREATE FUNCTION macrostrat.on_update_current_timestamp_unit_liths() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
   NEW.date_mod = now();
   RETURN NEW;
END;
$$;
ALTER FUNCTION macrostrat.on_update_current_timestamp_unit_liths() OWNER TO macrostrat_admin;

CREATE FUNCTION macrostrat.on_update_current_timestamp_unit_liths_atts() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
   NEW.date_mod = now();
   RETURN NEW;
END;
$$;
ALTER FUNCTION macrostrat.on_update_current_timestamp_unit_liths_atts() OWNER TO macrostrat_admin;

CREATE FUNCTION macrostrat.on_update_current_timestamp_unit_notes() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
   NEW.date_mod = now();
   RETURN NEW;
END;
$$;
ALTER FUNCTION macrostrat.on_update_current_timestamp_unit_notes() OWNER TO macrostrat_admin;

CREATE FUNCTION macrostrat.on_update_current_timestamp_units() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
   NEW.date_mod = now();
   RETURN NEW;
END;
$$;
ALTER FUNCTION macrostrat.on_update_current_timestamp_units() OWNER TO macrostrat_admin;

CREATE FUNCTION macrostrat.update_unit_lith_comp_props(_unit_id integer) RETURNS void
    LANGUAGE plpgsql
    AS $$
BEGIN
  UPDATE macrostrat.unit_liths ul
  SET
    comp_prop = (CASE WHEN ul.dom = 'sub' THEN prop.sub_prop ELSE prop.dom_prop END)
  FROM (SELECT * FROM macrostrat.get_lith_comp_prop(_unit_id)) as prop
  WHERE ul.unit_id = _unit_id;
END
$$;
ALTER FUNCTION macrostrat.update_unit_lith_comp_props(_unit_id integer) OWNER TO macrostrat_admin;

CREATE TABLE macrostrat.autocomplete (
    id integer DEFAULT 0 NOT NULL,
    name character varying(255) DEFAULT NULL::character varying,
    type character varying(20) DEFAULT ''::character varying NOT NULL,
    category character varying(10) DEFAULT ''::character varying NOT NULL
);
ALTER TABLE macrostrat.autocomplete OWNER TO macrostrat_admin;

CREATE TABLE macrostrat.autocomplete_old (
    id integer DEFAULT 0 NOT NULL,
    name character varying(255) DEFAULT NULL::character varying,
    type character varying(20) DEFAULT ''::character varying NOT NULL,
    category character varying(10) DEFAULT ''::character varying NOT NULL
);
ALTER TABLE macrostrat.autocomplete_old OWNER TO macrostrat_admin;

CREATE TABLE macrostrat.canada_lexicon_dump (
    strat_unit_id character varying(6) NOT NULL,
    id integer NOT NULL,
    concept_id integer NOT NULL,
    unit character varying(255) NOT NULL,
    strat_name character varying(255) NOT NULL,
    strat_name_id integer NOT NULL,
    web_id character varying(20) NOT NULL,
    upper_age_e character varying(50) NOT NULL,
    upper_interval_id integer NOT NULL,
    lower_age_e character varying(50) NOT NULL,
    lower_interval_id integer NOT NULL,
    containing_interval integer NOT NULL,
    containing_interval_name character varying(150) NOT NULL,
    ptype character varying(50) NOT NULL,
    rank character varying(30) NOT NULL,
    type character varying(30) NOT NULL,
    status character varying(30) NOT NULL,
    usage_cs character varying(50) NOT NULL,
    lex character varying(30) NOT NULL,
    moreinfo character varying(2) NOT NULL,
    province_en character varying(255) NOT NULL,
    lastdate character varying(10) NOT NULL,
    url character varying(255) NOT NULL,
    descrip text NOT NULL
);
ALTER TABLE macrostrat.canada_lexicon_dump OWNER TO macrostrat_admin;

CREATE TABLE macrostrat.col_areas (
    id integer NOT NULL,
    col_id integer NOT NULL,
    gmap text NOT NULL,
    col_area public.geometry,
    wkt text
);
ALTER TABLE macrostrat.col_areas OWNER TO macrostrat_admin;

CREATE TABLE macrostrat.col_areas_6april2016 (
    id integer DEFAULT 0 NOT NULL,
    col_id integer NOT NULL,
    gmap text NOT NULL,
    col_area public.geometry
);
ALTER TABLE macrostrat.col_areas_6april2016 OWNER TO macrostrat_admin;

CREATE SEQUENCE macrostrat.col_areas_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
ALTER TABLE macrostrat.col_areas_id_seq OWNER TO macrostrat_admin;

ALTER SEQUENCE macrostrat.col_areas_id_seq OWNED BY macrostrat.col_areas.id;

CREATE TABLE macrostrat.col_equiv (
    id integer NOT NULL,
    col_1 integer NOT NULL,
    col_2 integer NOT NULL
);
ALTER TABLE macrostrat.col_equiv OWNER TO macrostrat_admin;

CREATE SEQUENCE macrostrat.col_equiv_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
ALTER TABLE macrostrat.col_equiv_id_seq OWNER TO macrostrat_admin;

ALTER SEQUENCE macrostrat.col_equiv_id_seq OWNED BY macrostrat.col_equiv.id;

CREATE TABLE macrostrat.col_groups (
    id integer NOT NULL,
    col_group character varying(100) NOT NULL,
    col_group_long character varying(100) NOT NULL,
    project_id integer NOT NULL
);
ALTER TABLE macrostrat.col_groups OWNER TO macrostrat_admin;

CREATE SEQUENCE macrostrat.col_groups_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
ALTER TABLE macrostrat.col_groups_id_seq OWNER TO macrostrat_admin;

ALTER SEQUENCE macrostrat.col_groups_id_seq OWNED BY macrostrat.col_groups.id;

CREATE TABLE macrostrat.col_notes (
    id integer NOT NULL,
    col_id integer NOT NULL,
    notes text NOT NULL
);
ALTER TABLE macrostrat.col_notes OWNER TO macrostrat_admin;

CREATE SEQUENCE macrostrat.col_notes_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
ALTER TABLE macrostrat.col_notes_id_seq OWNER TO macrostrat_admin;

ALTER SEQUENCE macrostrat.col_notes_id_seq OWNED BY macrostrat.col_notes.id;

CREATE TABLE macrostrat.col_refs (
    id integer NOT NULL,
    col_id integer NOT NULL,
    ref_id integer NOT NULL
);
ALTER TABLE macrostrat.col_refs OWNER TO macrostrat_admin;

CREATE SEQUENCE macrostrat.col_refs_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
ALTER TABLE macrostrat.col_refs_id_seq OWNER TO macrostrat_admin;

ALTER SEQUENCE macrostrat.col_refs_id_seq OWNED BY macrostrat.col_refs.id;

CREATE TABLE macrostrat.colors (
    color macrostrat.colors_color NOT NULL,
    unit_hex character varying(9) DEFAULT '#FFFFFF'::character varying NOT NULL,
    text_hex character varying(9) DEFAULT '#000000'::character varying NOT NULL,
    unit_class character varying(4) DEFAULT NULL::character varying
);
ALTER TABLE macrostrat.colors OWNER TO macrostrat_admin;

CREATE TABLE macrostrat.cols (
    id integer NOT NULL,
    col_group_id integer NOT NULL,
    project_id integer NOT NULL,
    status_code macrostrat.cols_status_code NOT NULL,
    col_type macrostrat.cols_col_type NOT NULL,
    col_position macrostrat.cols_col_position NOT NULL,
    col numeric(6,2) NOT NULL,
    col_name character varying(75) NOT NULL,
    lat numeric(8,5) NOT NULL,
    lng numeric(8,5) NOT NULL,
    col_area double precision NOT NULL,
    created timestamp with time zone NOT NULL,
    coordinate public.geometry,
    wkt text,
    poly_geom public.geometry
);
ALTER TABLE macrostrat.cols OWNER TO macrostrat_admin;

CREATE SEQUENCE macrostrat.cols_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
ALTER TABLE macrostrat.cols_id_seq OWNER TO macrostrat_admin;

ALTER SEQUENCE macrostrat.cols_id_seq OWNED BY macrostrat.cols.id;

CREATE TABLE macrostrat.concepts_places (
    concept_id integer NOT NULL,
    place_id bigint NOT NULL
);
ALTER TABLE macrostrat.concepts_places OWNER TO macrostrat_admin;

CREATE TABLE macrostrat.econs (
    id integer NOT NULL,
    econ character varying(100) NOT NULL,
    econ_type macrostrat.econs_econ_type NOT NULL,
    econ_class macrostrat.econs_econ_class NOT NULL,
    econ_color character varying(7) NOT NULL
);
ALTER TABLE macrostrat.econs OWNER TO macrostrat_admin;

CREATE SEQUENCE macrostrat.econs_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
ALTER TABLE macrostrat.econs_id_seq OWNER TO macrostrat_admin;

ALTER SEQUENCE macrostrat.econs_id_seq OWNED BY macrostrat.econs.id;

CREATE TABLE macrostrat.environs (
    id integer NOT NULL,
    environ character varying(50) NOT NULL,
    environ_type macrostrat.environs_environ_type NOT NULL,
    environ_class macrostrat.environs_environ_class NOT NULL,
    environ_fill integer NOT NULL,
    environ_color character varying(7) NOT NULL
);
ALTER TABLE macrostrat.environs OWNER TO macrostrat_admin;

CREATE SEQUENCE macrostrat.environs_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
ALTER TABLE macrostrat.environs_id_seq OWNER TO macrostrat_admin;

ALTER SEQUENCE macrostrat.environs_id_seq OWNED BY macrostrat.environs.id;

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
ALTER TABLE macrostrat.grainsize OWNER TO macrostrat_admin;

CREATE TABLE macrostrat.interval_boundaries (
    id integer NOT NULL,
    t1 integer NOT NULL,
    t1_prop numeric(6,5) NOT NULL,
    t1_prop_error numeric(6,5) DEFAULT NULL::numeric,
    t1_age numeric(8,4) NOT NULL,
    t1_age_error numeric(8,4) DEFAULT NULL::numeric,
    interval_id integer NOT NULL,
    interval_id_2 integer NOT NULL,
    timescale_id integer NOT NULL,
    boundary_status macrostrat.boundary_status DEFAULT ''::macrostrat.boundary_status NOT NULL
);
ALTER TABLE macrostrat.interval_boundaries OWNER TO macrostrat_admin;

CREATE TABLE macrostrat.interval_boundaries_scratch (
    id integer NOT NULL,
    t1 integer NOT NULL,
    t1_prop numeric(6,5) NOT NULL,
    t1_prop_error numeric(6,5) DEFAULT NULL::numeric,
    t1_age numeric(8,4) NOT NULL,
    t1_age_error numeric(8,4) DEFAULT NULL::numeric,
    interval_id integer NOT NULL,
    interval_id_2 integer NOT NULL,
    timescale_id integer NOT NULL,
    boundary_status macrostrat.boundary_status DEFAULT ''::macrostrat.boundary_status NOT NULL
);
ALTER TABLE macrostrat.interval_boundaries_scratch OWNER TO macrostrat_admin;

CREATE TABLE macrostrat.intervals (
    id integer NOT NULL,
    age_bottom numeric(8,4) DEFAULT NULL::numeric,
    age_top numeric(8,4) DEFAULT NULL::numeric,
    interval_name character varying(255) DEFAULT NULL::character varying,
    interval_abbrev character varying(40) DEFAULT NULL::character varying,
    interval_type macrostrat.intervals_interval_type DEFAULT 'supereon'::macrostrat.intervals_interval_type,
    interval_color character varying(7) NOT NULL,
    orig_color character varying(7) NOT NULL,
    rank integer
);
ALTER TABLE macrostrat.intervals OWNER TO macrostrat_admin;

CREATE SEQUENCE macrostrat.intervals_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
ALTER TABLE macrostrat.intervals_id_seq OWNER TO macrostrat_admin;

ALTER SEQUENCE macrostrat.intervals_id_seq OWNED BY macrostrat.intervals.id;

CREATE SEQUENCE macrostrat.intervals_new_id_seq1
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
ALTER TABLE macrostrat.intervals_new_id_seq1 OWNER TO macrostrat_admin;

ALTER SEQUENCE macrostrat.intervals_new_id_seq1 OWNED BY macrostrat.intervals.id;

CREATE TABLE macrostrat.lith_atts (
    id integer NOT NULL,
    lith_att character varying(50) NOT NULL,
    equiv integer NOT NULL,
    att_type macrostrat.lith_atts_att_type NOT NULL,
    lith_att_fill integer NOT NULL
);
ALTER TABLE macrostrat.lith_atts OWNER TO macrostrat_admin;

CREATE SEQUENCE macrostrat.lith_atts_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
ALTER TABLE macrostrat.lith_atts_id_seq OWNER TO macrostrat_admin;

ALTER SEQUENCE macrostrat.lith_atts_id_seq OWNED BY macrostrat.lith_atts.id;

CREATE TABLE macrostrat.liths (
    id integer NOT NULL,
    lith character varying(50) NOT NULL,
    lith_group macrostrat.liths_lith_group,
    lith_type macrostrat.liths_lith_type NOT NULL,
    lith_class macrostrat.liths_lith_class NOT NULL,
    lith_equiv integer NOT NULL,
    lith_fill integer NOT NULL,
    comp_coef numeric(3,2) NOT NULL,
    initial_porosity numeric(3,2) NOT NULL,
    bulk_density numeric(3,2) NOT NULL,
    lith_color character varying(7) DEFAULT NULL::character varying
);
ALTER TABLE macrostrat.liths OWNER TO macrostrat_admin;

CREATE SEQUENCE macrostrat.liths_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
ALTER TABLE macrostrat.liths_id_seq OWNER TO macrostrat_admin;

ALTER SEQUENCE macrostrat.liths_id_seq OWNED BY macrostrat.liths.id;

CREATE TABLE macrostrat.lookup_measurements (
    measure_id integer NOT NULL,
    measuremeta_id integer NOT NULL,
    measurement_id integer NOT NULL,
    measurement character varying(100) NOT NULL,
    measurement_class macrostrat.measurement_class NOT NULL,
    measurement_type macrostrat.measurement_type NOT NULL,
    measure_phase character varying(100) NOT NULL,
    method character varying(100) NOT NULL,
    measure_units character varying(25) NOT NULL,
    measure_value numeric(10,5) DEFAULT NULL::numeric,
    v_error numeric(10,5) DEFAULT NULL::numeric,
    v_error_units character varying(25) DEFAULT NULL::character varying,
    v_type character varying(100) NOT NULL,
    v_n integer,
    lat numeric(8,5) DEFAULT NULL::numeric,
    lng numeric(8,5) DEFAULT NULL::numeric,
    sample_geo_unit character varying(255) NOT NULL,
    sample_lith character varying(255) NOT NULL,
    lith_id integer NOT NULL,
    sample_descrip text NOT NULL,
    ref_id integer NOT NULL,
    ref character varying(255) NOT NULL,
    units character varying(255) NOT NULL
);
ALTER TABLE macrostrat.lookup_measurements OWNER TO macrostrat_admin;

CREATE TABLE macrostrat.lookup_strat_names (
    strat_name_id integer NOT NULL,
    strat_name character varying(100) NOT NULL,
    rank macrostrat.lookup_strat_names_rank,
    concept_id integer NOT NULL,
    rank_name character varying(100) NOT NULL,
    bed_id integer NOT NULL,
    bed_name character varying(100) DEFAULT NULL::character varying,
    mbr_id integer NOT NULL,
    mbr_name character varying(100) DEFAULT NULL::character varying,
    fm_id integer NOT NULL,
    fm_name character varying(100) DEFAULT NULL::character varying,
    subgp_id integer NOT NULL,
    subgp_name character varying(100) DEFAULT NULL::character varying,
    gp_id integer NOT NULL,
    gp_name character varying(100) DEFAULT NULL::character varying,
    sgp_id integer NOT NULL,
    sgp_name character varying(100) DEFAULT NULL::character varying,
    early_age numeric(8,4) DEFAULT NULL::numeric,
    late_age numeric(8,4) DEFAULT NULL::numeric,
    gsc_lexicon character(15) DEFAULT NULL::bpchar,
    parent integer NOT NULL,
    tree integer NOT NULL,
    t_units integer NOT NULL,
    b_period character varying(100) DEFAULT NULL::character varying,
    t_period character varying(100) DEFAULT NULL::character varying,
    name_no_lith character varying(100) DEFAULT NULL::character varying,
    ref_id integer NOT NULL,
    c_interval character varying(100) DEFAULT NULL::character varying
);
ALTER TABLE macrostrat.lookup_strat_names OWNER TO macrostrat_admin;

CREATE TABLE macrostrat.lookup_strat_names_new (
    strat_name_id integer,
    strat_name character varying(100),
    rank macrostrat.lookup_strat_names_rank,
    concept_id integer,
    rank_name character varying(100),
    bed_id integer,
    bed_name character varying(100),
    mbr_id integer,
    mbr_name character varying(100),
    fm_id integer,
    fm_name character varying(100),
    subgp_id integer,
    subgp_name character varying(100),
    gp_id integer,
    gp_name character varying(100),
    sgp_id integer,
    sgp_name character varying(100),
    early_age numeric(8,4),
    late_age numeric(8,4),
    gsc_lexicon character(15),
    parent integer,
    tree integer,
    t_units integer,
    b_period character varying(100),
    t_period character varying(100),
    name_no_lith character varying(100),
    ref_id integer,
    c_interval character varying(100)
);
ALTER TABLE macrostrat.lookup_strat_names_new OWNER TO macrostrat_admin;

CREATE TABLE macrostrat.lookup_unit_attrs_api (
    unit_id integer,
    lith bytea,
    environ bytea,
    econ bytea,
    measure_short bytea,
    measure_long bytea
);
ALTER TABLE macrostrat.lookup_unit_attrs_api OWNER TO macrostrat_admin;

CREATE TABLE macrostrat.lookup_unit_intervals (
    unit_id integer NOT NULL,
    fo_age numeric(8,4) NOT NULL,
    b_age numeric(8,4) DEFAULT NULL::numeric,
    fo_interval character varying(50) NOT NULL,
    fo_period character varying(50) NOT NULL,
    lo_age numeric(8,4) NOT NULL,
    t_age numeric(8,4) DEFAULT NULL::numeric,
    lo_interval character varying(50) NOT NULL,
    lo_period character varying(50) NOT NULL,
    age character varying(50) NOT NULL,
    age_id integer NOT NULL,
    epoch character varying(50) NOT NULL,
    epoch_id integer NOT NULL,
    period character varying(50) NOT NULL,
    period_id integer NOT NULL,
    era character varying(50) NOT NULL,
    era_id integer NOT NULL,
    eon character varying(50) NOT NULL,
    eon_id integer NOT NULL,
    best_interval_id integer
);
ALTER TABLE macrostrat.lookup_unit_intervals OWNER TO macrostrat_admin;

CREATE TABLE macrostrat.lookup_unit_liths (
    unit_id integer NOT NULL,
    lith_class character varying(100) NOT NULL,
    lith_type character varying(100) NOT NULL,
    lith_short text NOT NULL,
    lith_long text NOT NULL,
    environ_class character varying(100) NOT NULL,
    environ_type character varying(100) NOT NULL,
    environ character varying(255) NOT NULL
);
ALTER TABLE macrostrat.lookup_unit_liths OWNER TO macrostrat_admin;

CREATE TABLE macrostrat.lookup_units (
    unit_id integer DEFAULT 0 NOT NULL,
    col_area double precision NOT NULL,
    project_id integer NOT NULL,
    t_int integer,
    t_int_name character varying(255) DEFAULT NULL::character varying,
    t_int_age numeric(8,4) DEFAULT NULL::numeric,
    t_age numeric(8,4) DEFAULT NULL::numeric,
    t_prop numeric(6,5) DEFAULT NULL::numeric,
    t_plat numeric(7,3) DEFAULT NULL::numeric,
    t_plng numeric(7,3) DEFAULT NULL::numeric,
    b_int integer,
    b_int_name character varying(255) DEFAULT NULL::character varying,
    b_int_age numeric(8,4) DEFAULT NULL::numeric,
    b_age numeric(8,4) DEFAULT NULL::numeric,
    b_prop numeric(6,5) DEFAULT NULL::numeric,
    b_plat numeric(7,3) DEFAULT NULL::numeric,
    b_plng numeric(7,3) DEFAULT NULL::numeric,
    clat numeric(7,4) NOT NULL,
    clng numeric(7,4) NOT NULL,
    color character varying(9) DEFAULT '#FFFFFF'::character varying NOT NULL,
    text_color character varying(9) DEFAULT '#000000'::character varying NOT NULL,
    units_above text,
    units_below text,
    pbdb_collections integer DEFAULT 0 NOT NULL,
    pbdb_occurrences integer NOT NULL,
    age character varying(200) DEFAULT NULL::character varying,
    age_id integer,
    epoch character varying(200) DEFAULT NULL::character varying,
    epoch_id integer,
    period character varying(200) DEFAULT NULL::character varying,
    period_id integer,
    era character varying(200) DEFAULT NULL::character varying,
    era_id integer,
    eon character varying(200) DEFAULT NULL::character varying,
    eon_id integer
);
ALTER TABLE macrostrat.lookup_units OWNER TO macrostrat_admin;

CREATE TABLE macrostrat.measurements (
    id integer NOT NULL,
    measurement_class macrostrat.measurement_class NOT NULL,
    measurement_type macrostrat.measurement_type NOT NULL,
    measurement character varying(150) NOT NULL
);
ALTER TABLE macrostrat.measurements OWNER TO macrostrat_admin;

CREATE SEQUENCE macrostrat.measurements_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
ALTER TABLE macrostrat.measurements_id_seq OWNER TO macrostrat_admin;

ALTER SEQUENCE macrostrat.measurements_id_seq OWNED BY macrostrat.measurements.id;

CREATE SEQUENCE macrostrat.measurements_new_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
ALTER TABLE macrostrat.measurements_new_id_seq OWNER TO macrostrat_admin;

ALTER SEQUENCE macrostrat.measurements_new_id_seq OWNED BY macrostrat.measurements.id;

CREATE TABLE macrostrat.measuremeta (
    id integer NOT NULL,
    sample_name character varying(255) NOT NULL,
    lat numeric(8,5) DEFAULT NULL::numeric,
    lng numeric(8,5) DEFAULT NULL::numeric,
    sample_geo_unit character varying(255) NOT NULL,
    sample_lith character varying(255) DEFAULT NULL::character varying,
    lith_id integer NOT NULL,
    lith_att_id integer NOT NULL,
    age character varying(100) NOT NULL,
    early_id integer NOT NULL,
    late_id integer NOT NULL,
    sample_descrip text,
    ref character varying(255) NOT NULL,
    ref_id integer NOT NULL,
    geometry public.geometry(Point,4326)
);
ALTER TABLE macrostrat.measuremeta OWNER TO macrostrat_admin;

CREATE TABLE macrostrat.measuremeta_cols (
    id integer NOT NULL,
    col_id integer NOT NULL,
    measuremeta_id integer NOT NULL
);
ALTER TABLE macrostrat.measuremeta_cols OWNER TO macrostrat_admin;

CREATE SEQUENCE macrostrat.measuremeta_cols_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
ALTER TABLE macrostrat.measuremeta_cols_id_seq OWNER TO macrostrat_admin;

ALTER SEQUENCE macrostrat.measuremeta_cols_id_seq OWNED BY macrostrat.measuremeta_cols.id;

CREATE SEQUENCE macrostrat.measuremeta_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
ALTER TABLE macrostrat.measuremeta_id_seq OWNER TO macrostrat_admin;

ALTER SEQUENCE macrostrat.measuremeta_id_seq OWNED BY macrostrat.measuremeta.id;

CREATE SEQUENCE macrostrat.measuremeta_new_id_seq1
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
ALTER TABLE macrostrat.measuremeta_new_id_seq1 OWNER TO macrostrat_admin;

ALTER SEQUENCE macrostrat.measuremeta_new_id_seq1 OWNED BY macrostrat.measuremeta.id;

CREATE TABLE macrostrat.measures (
    id integer NOT NULL,
    measuremeta_id integer NOT NULL,
    measurement_id integer NOT NULL,
    sample_no character varying(50) DEFAULT NULL::character varying,
    samp_pos numeric(7,3) DEFAULT NULL::numeric,
    measure_phase character varying(100) NOT NULL,
    method character varying(100) NOT NULL,
    units character varying(25) NOT NULL,
    measure_value numeric(10,5) DEFAULT NULL::numeric,
    v_error numeric(10,5) DEFAULT NULL::numeric,
    v_error_units character varying(25) DEFAULT NULL::character varying,
    v_type character varying(100) NOT NULL,
    v_n integer
);
ALTER TABLE macrostrat.measures OWNER TO macrostrat_admin;

CREATE SEQUENCE macrostrat.measures_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
ALTER TABLE macrostrat.measures_id_seq OWNER TO macrostrat_admin;

ALTER SEQUENCE macrostrat.measures_id_seq OWNED BY macrostrat.measures.id;

CREATE SEQUENCE macrostrat.measures_new_id_seq1
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
ALTER TABLE macrostrat.measures_new_id_seq1 OWNER TO macrostrat_admin;

ALTER SEQUENCE macrostrat.measures_new_id_seq1 OWNED BY macrostrat.measures.id;

CREATE TABLE macrostrat.minerals (
    id integer NOT NULL,
    mineral character varying(100) NOT NULL,
    mineral_type character varying(155) DEFAULT NULL::character varying,
    min_type character varying(100) NOT NULL,
    hardness_min numeric(3,1) DEFAULT NULL::numeric,
    hardness_max numeric(3,1) DEFAULT NULL::numeric,
    crystal_form character varying(100) DEFAULT NULL::character varying,
    color character varying(255) DEFAULT NULL::character varying,
    lustre character varying(255) DEFAULT NULL::character varying,
    formula character varying(155) NOT NULL,
    formula_tags text NOT NULL,
    url character varying(155) NOT NULL,
    paragenesis character varying(150) DEFAULT NULL::character varying
);
ALTER TABLE macrostrat.minerals OWNER TO macrostrat_admin;

CREATE TABLE macrostrat.offshore_baggage (
    id bigint NOT NULL,
    section_id integer NOT NULL,
    name character varying(150) NOT NULL,
    site_hole character varying(20) NOT NULL,
    col_id integer NOT NULL,
    top numeric(7,3) NOT NULL,
    bottom numeric(7,3) NOT NULL,
    top_depth numeric(7,3) NOT NULL,
    bottom_depth numeric(7,3) NOT NULL,
    principal_lithology_prefix character varying(100) NOT NULL,
    principal_lith_prefix_cleaned character varying(125) NOT NULL,
    principal_prefix_lith_att_id integer NOT NULL,
    principal_lithology_name character varying(150) NOT NULL,
    cleaned_lith character varying(100) NOT NULL,
    lith character varying(50) NOT NULL,
    lith_id integer NOT NULL,
    lith_att character varying(50) NOT NULL,
    lith_att_id integer NOT NULL,
    principal_lithology_suffix character varying(100) NOT NULL,
    principal_lith_suffix_cleaned character varying(150) NOT NULL,
    minor_lithology_prefix character varying(100) NOT NULL,
    minor_lith_prefix_cleaned character varying(100) NOT NULL,
    minor_lith_prefix_att_id integer NOT NULL,
    minor_lithology_name character varying(100) NOT NULL,
    cleaned_minor character varying(50) NOT NULL,
    minor_lith character varying(50) NOT NULL,
    minor_lith_id integer NOT NULL,
    minor_lith_att_id integer NOT NULL,
    minor_lithology_suffix character varying(100) NOT NULL,
    standard_minor_lith character varying(150) DEFAULT NULL::character varying,
    raw_data text NOT NULL,
    data_source_notes character varying(100) NOT NULL,
    created_at timestamp with time zone,
    data_source_type character varying(100) NOT NULL,
    drop_row smallint DEFAULT '0'::smallint NOT NULL,
    unit_id_secondary integer NOT NULL,
    unit_id integer NOT NULL,
    neptune_bin integer NOT NULL
);
ALTER TABLE macrostrat.offshore_baggage OWNER TO macrostrat_admin;

CREATE TABLE macrostrat.offshore_baggage_units (
    offshore_baggage_id integer NOT NULL,
    unit_id integer NOT NULL,
    unit_lith_id integer NOT NULL,
    unit_lith_sub_id integer NOT NULL,
    col_id integer NOT NULL
);
ALTER TABLE macrostrat.offshore_baggage_units OWNER TO macrostrat_admin;

CREATE TABLE macrostrat.offshore_fossils (
    id bigint NOT NULL,
    section_id integer NOT NULL,
    name character varying(150) NOT NULL,
    col_id integer NOT NULL,
    top numeric(7,3) NOT NULL,
    bottom numeric(7,3) NOT NULL,
    top_depth numeric(7,3) NOT NULL,
    bottom_depth numeric(7,3) NOT NULL,
    mid_depth numeric(7,3) NOT NULL,
    data_source_notes character varying(100) NOT NULL,
    taxa character varying(100) NOT NULL,
    created_at timestamp with time zone,
    site_hole character varying(100) NOT NULL,
    pbdb_pres character varying(15) DEFAULT NULL::character varying,
    pbdb_frag character varying(15) DEFAULT NULL::character varying,
    taxa_count integer NOT NULL,
    unit_id integer NOT NULL,
    ma character varying(8) NOT NULL,
    pbdb_interval_no integer NOT NULL,
    collection_no integer NOT NULL
);
ALTER TABLE macrostrat.offshore_fossils OWNER TO macrostrat_admin;

CREATE TABLE macrostrat.offshore_hole_ages (
    id integer NOT NULL,
    col_id integer NOT NULL,
    top_depth numeric(7,3) NOT NULL,
    top_core integer,
    bottom_depth numeric(7,3) NOT NULL,
    bottom_core integer,
    interval_id integer NOT NULL
);
ALTER TABLE macrostrat.offshore_hole_ages OWNER TO macrostrat_admin;

CREATE SEQUENCE macrostrat.offshore_hole_ages_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
ALTER TABLE macrostrat.offshore_hole_ages_id_seq OWNER TO macrostrat_admin;

ALTER SEQUENCE macrostrat.offshore_hole_ages_id_seq OWNED BY macrostrat.offshore_hole_ages.id;

CREATE TABLE macrostrat.offshore_sections (
    exp integer NOT NULL,
    site character varying(6) NOT NULL,
    hole character varying(2) NOT NULL,
    col_id integer NOT NULL,
    core integer NOT NULL,
    core_type character varying(1) NOT NULL,
    sect character varying(2) NOT NULL,
    recovered_length numeric(2,1) NOT NULL,
    curated_length numeric(2,1) NOT NULL,
    top_mbsf numeric(6,2) NOT NULL,
    bottom_mbsf numeric(6,2) NOT NULL
);
ALTER TABLE macrostrat.offshore_sections OWNER TO macrostrat_admin;

CREATE TABLE macrostrat.offshore_sites (
    id integer NOT NULL,
    epoch character varying(4) NOT NULL,
    leg character varying(5) NOT NULL,
    site character varying(6) NOT NULL,
    hole character varying(1) NOT NULL,
    col_id integer NOT NULL,
    col_group_id integer NOT NULL,
    lat_deg integer NOT NULL,
    lat_min numeric(7,4) NOT NULL,
    lat_dir character varying(1) NOT NULL,
    lat numeric(8,5) NOT NULL,
    lng_deg integer NOT NULL,
    lng_min numeric(7,4) NOT NULL,
    lng_dir character varying(1) NOT NULL,
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
    date_started character varying(25) NOT NULL,
    date_finished character varying(25) NOT NULL,
    time_on_hole numeric(5,2) NOT NULL,
    comments character varying(255) NOT NULL,
    ref_id integer NOT NULL
);
ALTER TABLE macrostrat.offshore_sites OWNER TO macrostrat_admin;

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
ALTER TABLE macrostrat.pbdb_collections OWNER TO macrostrat_admin;

CREATE TABLE macrostrat.pbdb_collections_strat_names (
    collection_no integer NOT NULL,
    strat_name_id integer NOT NULL,
    basis_col text
);
ALTER TABLE macrostrat.pbdb_collections_strat_names OWNER TO macrostrat_admin;

CREATE TABLE macrostrat.pbdb_intervals (
    id integer NOT NULL,
    age_bottom numeric(8,4) DEFAULT NULL::numeric,
    age_top numeric(8,4) DEFAULT NULL::numeric,
    interval_name character varying(255) DEFAULT NULL::character varying,
    interval_abbrev character varying(40) DEFAULT NULL::character varying,
    interval_type macrostrat.pbdb_intervals_interval_type DEFAULT 'supereon'::macrostrat.pbdb_intervals_interval_type,
    interval_color character varying(7) NOT NULL,
    orig_color character varying(7) NOT NULL,
    pbdb_interval_no integer NOT NULL
);
ALTER TABLE macrostrat.pbdb_intervals OWNER TO macrostrat_admin;

CREATE SEQUENCE macrostrat.pbdb_intervals_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
ALTER TABLE macrostrat.pbdb_intervals_id_seq OWNER TO macrostrat_admin;

ALTER SEQUENCE macrostrat.pbdb_intervals_id_seq OWNED BY macrostrat.pbdb_intervals.id;

CREATE TABLE macrostrat.pbdb_liths (
    lith_id integer NOT NULL,
    lith character varying(100) NOT NULL,
    pbdb_lith character varying(100) NOT NULL
);
ALTER TABLE macrostrat.pbdb_liths OWNER TO macrostrat_admin;

CREATE TABLE macrostrat.pbdb_matches (
    id integer NOT NULL,
    collection_no integer NOT NULL,
    collection_name character varying(255) NOT NULL,
    occs integer NOT NULL,
    lat numeric(7,4) NOT NULL,
    lng numeric(7,4) NOT NULL,
    unit_id integer NOT NULL,
    verified boolean DEFAULT false NOT NULL,
    modified timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    release_date timestamp with time zone NOT NULL,
    ref_id integer NOT NULL,
    coordinate public.geometry(Point,4326)
);
ALTER TABLE macrostrat.pbdb_matches OWNER TO macrostrat_admin;

CREATE SEQUENCE macrostrat.pbdb_matches_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
ALTER TABLE macrostrat.pbdb_matches_id_seq OWNER TO macrostrat_admin;

ALTER SEQUENCE macrostrat.pbdb_matches_id_seq OWNED BY macrostrat.pbdb_matches.id;

CREATE TABLE macrostrat.places (
    place_id bigint NOT NULL,
    name text,
    abbrev text,
    postal text,
    country text,
    country_abbrev text,
    geom public.geometry
);
ALTER TABLE macrostrat.places OWNER TO macrostrat_admin;

CREATE SEQUENCE macrostrat.places_place_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
ALTER TABLE macrostrat.places_place_id_seq OWNER TO macrostrat_admin;

ALTER SEQUENCE macrostrat.places_place_id_seq OWNED BY macrostrat.places.place_id;

CREATE SEQUENCE macrostrat.projects_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
ALTER TABLE macrostrat.projects_id_seq OWNER TO macrostrat;

ALTER SEQUENCE macrostrat.projects_id_seq OWNED BY macrostrat.projects.id;

CREATE TABLE macrostrat.projects_tree (
    id integer PRIMARY KEY GENERATED ALWAYS AS IDENTITY (
        SEQUENCE NAME macrostrat.projects_tree_id_seq
        START WITH 1
        INCREMENT BY 1
        NO MINVALUE
        NO MAXVALUE
        CACHE 1
    ),
    parent_id integer NOT NULL,
    child_id integer NOT NULL
);
ALTER TABLE macrostrat.projects_tree OWNER TO macrostrat;

CREATE TABLE macrostrat.refs (
    id integer NOT NULL,
    pub_year integer NOT NULL,
    author character varying(255) NOT NULL,
    ref text NOT NULL,
    doi character varying(40) DEFAULT NULL::character varying,
    compilation_code macrostrat.refs_compilation_code NOT NULL,
    url character varying(255) DEFAULT NULL::character varying,
    rgeom public.geometry
);
ALTER TABLE macrostrat.refs OWNER TO macrostrat_admin;

CREATE SEQUENCE macrostrat.refs_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
ALTER TABLE macrostrat.refs_id_seq OWNER TO macrostrat_admin;

ALTER SEQUENCE macrostrat.refs_id_seq OWNED BY macrostrat.refs.id;

CREATE TABLE macrostrat.rockd_features (
    id integer NOT NULL,
    feature character varying(100) NOT NULL,
    feature_type macrostrat.rockd_features_feature_type NOT NULL,
    feature_class macrostrat.rockd_features_feature_class NOT NULL
);
ALTER TABLE macrostrat.rockd_features OWNER TO macrostrat_admin;

CREATE SEQUENCE macrostrat.rockd_features_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
ALTER TABLE macrostrat.rockd_features_id_seq OWNER TO macrostrat_admin;

ALTER SEQUENCE macrostrat.rockd_features_id_seq OWNED BY macrostrat.rockd_features.id;

CREATE TABLE macrostrat.ronov_sediment (
    interval_name character varying(25) NOT NULL,
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
ALTER TABLE macrostrat.ronov_sediment OWNER TO macrostrat_admin;

CREATE TABLE macrostrat.sections (
    id bigint NOT NULL,
    col_id integer NOT NULL,
    fo integer DEFAULT 0 NOT NULL,
    fo_h smallint NOT NULL,
    lo integer DEFAULT 0 NOT NULL,
    lo_h smallint NOT NULL
);
ALTER TABLE macrostrat.sections OWNER TO macrostrat;

COMMENT ON TABLE macrostrat.sections IS 'Last updated from MariaDB - 2023-07-28 18:11';

CREATE SEQUENCE macrostrat.sections_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
ALTER TABLE macrostrat.sections_id_seq OWNER TO macrostrat;

ALTER SEQUENCE macrostrat.sections_id_seq OWNED BY macrostrat.sections.id;

CREATE TABLE macrostrat.stats (
    project_id integer DEFAULT 0 NOT NULL,
    project macrostrat.stats_project NOT NULL,
    columns bigint DEFAULT '0'::bigint NOT NULL,
    packages bigint DEFAULT '0'::bigint NOT NULL,
    units bigint DEFAULT '0'::bigint NOT NULL,
    pbdb_collections bigint DEFAULT '0'::bigint NOT NULL,
    measurements bigint DEFAULT '0'::bigint NOT NULL,
    burwell_polygons bigint DEFAULT '0'::bigint
);
ALTER TABLE macrostrat.stats OWNER TO macrostrat_admin;

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
ALTER TABLE macrostrat.strat_name_footprints OWNER TO macrostrat_admin;

CREATE TABLE macrostrat.strat_names (
    id integer NOT NULL,
    old_id integer NOT NULL,
    concept_id integer,
    strat_name character varying(75) DEFAULT NULL::character varying,
    rank macrostrat.strat_names_rank,
    old_strat_name_id integer NOT NULL,
    ref_id integer,
    places text,
    orig_id integer NOT NULL,
    CONSTRAINT idx_44157311_primary PRIMARY KEY (id)
);
ALTER TABLE macrostrat.strat_names OWNER TO macrostrat_admin;

CREATE SEQUENCE macrostrat.strat_names_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
ALTER TABLE macrostrat.strat_names_id_seq OWNER TO macrostrat_admin;

ALTER SEQUENCE macrostrat.strat_names_id_seq OWNED BY macrostrat.strat_names.id;

CREATE TABLE macrostrat.strat_names_lookup (
    strat_name_id integer NOT NULL,
    strat_name character varying(100) NOT NULL,
    rank macrostrat.strat_names_lookup_rank NOT NULL,
    bed_id integer NOT NULL,
    bed_name character varying(100) NOT NULL,
    mbr_id integer NOT NULL,
    mbr_name character varying(100) NOT NULL,
    fm_id integer NOT NULL,
    fm_name character varying(100) NOT NULL,
    gp_id integer NOT NULL,
    gp_name character varying(100) NOT NULL,
    sgp_id integer NOT NULL,
    sgp_name character varying(100) NOT NULL
);
ALTER TABLE macrostrat.strat_names_lookup OWNER TO macrostrat_admin;

CREATE TABLE macrostrat.strat_names_meta (
    concept_id integer NOT NULL,
    orig_id integer NOT NULL,
    name character varying(40) DEFAULT NULL::character varying,
    geologic_age text,
    interval_id integer,
    b_int integer NOT NULL,
    t_int integer NOT NULL,
    usage_notes text,
    other text,
    province text,
    url character varying(150) NOT NULL,
    ref_id integer NOT NULL,
    CONSTRAINT idx_44157324_primary PRIMARY KEY (concept_id)
);
ALTER TABLE macrostrat.strat_names_meta OWNER TO macrostrat_admin;

CREATE SEQUENCE macrostrat.strat_names_meta_concept_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
ALTER TABLE macrostrat.strat_names_meta_concept_id_seq OWNER TO macrostrat_admin;

ALTER SEQUENCE macrostrat.strat_names_meta_concept_id_seq OWNED BY macrostrat.strat_names_meta.concept_id;

CREATE SEQUENCE macrostrat.strat_names_new_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
ALTER TABLE macrostrat.strat_names_new_id_seq OWNER TO macrostrat_admin;

ALTER SEQUENCE macrostrat.strat_names_new_id_seq OWNED BY macrostrat.strat_names.id;

CREATE TABLE macrostrat.strat_names_places (
    strat_name_id integer NOT NULL,
    place_id integer NOT NULL
);
ALTER TABLE macrostrat.strat_names_places OWNER TO macrostrat_admin;

CREATE TABLE macrostrat.strat_tree (
    id integer,
    parent integer,
    rel macrostrat.strat_tree_rel,
    child integer,
    ref_id integer,
    check_me smallint
);
ALTER TABLE macrostrat.strat_tree OWNER TO macrostrat_admin;

CREATE TABLE macrostrat.structure_atts (
    id bigint NOT NULL,
    structure_att character varying(100) NOT NULL,
    att_type macrostrat.structure_atts_att_type,
    att_class macrostrat.structure_atts_att_class
);
ALTER TABLE macrostrat.structure_atts OWNER TO macrostrat_admin;

CREATE SEQUENCE macrostrat.structure_atts_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
ALTER TABLE macrostrat.structure_atts_id_seq OWNER TO macrostrat_admin;

ALTER SEQUENCE macrostrat.structure_atts_id_seq OWNED BY macrostrat.structure_atts.id;

CREATE TABLE macrostrat.structures (
    id integer NOT NULL,
    structure character varying(100) NOT NULL,
    structure_group macrostrat.structures_structure_group,
    structure_type macrostrat.structures_structure_type NOT NULL,
    structure_class macrostrat.structures_structure_class NOT NULL
);
ALTER TABLE macrostrat.structures OWNER TO macrostrat_admin;

CREATE SEQUENCE macrostrat.structures_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
ALTER TABLE macrostrat.structures_id_seq OWNER TO macrostrat_admin;

ALTER SEQUENCE macrostrat.structures_id_seq OWNED BY macrostrat.structures.id;

CREATE TABLE macrostrat.tectonics (
    id integer NOT NULL,
    basin_type character varying(100) NOT NULL,
    basin_setting macrostrat.tectonics_basin_setting NOT NULL
);
ALTER TABLE macrostrat.tectonics OWNER TO macrostrat_admin;

CREATE SEQUENCE macrostrat.tectonics_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
ALTER TABLE macrostrat.tectonics_id_seq OWNER TO macrostrat_admin;

ALTER SEQUENCE macrostrat.tectonics_id_seq OWNED BY macrostrat.tectonics.id;

CREATE TABLE macrostrat.temp_areas (
    areas double precision NOT NULL,
    col_id integer NOT NULL
);
ALTER TABLE macrostrat.temp_areas OWNER TO macrostrat_admin;

CREATE TABLE macrostrat.timescales (
    id integer NOT NULL,
    timescale character varying(255) DEFAULT NULL::character varying,
    ref_id integer NOT NULL
);
ALTER TABLE macrostrat.timescales OWNER TO macrostrat_admin;

CREATE SEQUENCE macrostrat.timescales_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
ALTER TABLE macrostrat.timescales_id_seq OWNER TO macrostrat_admin;

ALTER SEQUENCE macrostrat.timescales_id_seq OWNED BY macrostrat.timescales.id;

CREATE TABLE macrostrat.timescales_intervals (
    timescale_id integer NOT NULL,
    interval_id integer NOT NULL
);
ALTER TABLE macrostrat.timescales_intervals OWNER TO macrostrat_admin;

CREATE TABLE macrostrat.uniquedatafiles2 (
    id integer NOT NULL,
    comp smallint NOT NULL,
    data smallint NOT NULL,
    ref1 integer NOT NULL,
    ref2 integer NOT NULL,
    colrnge character varying(60) NOT NULL,
    loc character varying(10) NOT NULL,
    lat character varying(20) NOT NULL,
    lon character varying(20) NOT NULL,
    state character varying(100) NOT NULL,
    stapi character varying(10) NOT NULL,
    county1 character varying(200) NOT NULL,
    county character varying(200) NOT NULL,
    coscode character varying(100) NOT NULL,
    provnme character varying(100) NOT NULL,
    colname character varying(100) NOT NULL,
    chart character varying(5) NOT NULL,
    chartnm character varying(5) NOT NULL,
    chartc character varying(5) NOT NULL,
    col character varying(7) NOT NULL,
    colc character varying(7) NOT NULL,
    strunit character varying(255) NOT NULL,
    grp smallint NOT NULL,
    formtn smallint NOT NULL,
    member smallint NOT NULL,
    bed smallint NOT NULL,
    rankdes character varying(200) NOT NULL,
    formal smallint NOT NULL,
    informl smallint NOT NULL,
    system character varying(255) NOT NULL,
    series character varying(255) NOT NULL,
    stage character varying(255) NOT NULL,
    surface smallint NOT NULL,
    subsurf smallint NOT NULL,
    bth smallint NOT NULL,
    above character varying(255) NOT NULL,
    below character varying(255) NOT NULL,
    domlith character varying(255) NOT NULL,
    dompct character varying(8) NOT NULL,
    sublith character varying(200) NOT NULL,
    subpct character varying(5) NOT NULL,
    thick1 character varying(8) NOT NULL,
    thick2 character varying(8) NOT NULL,
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
    author character varying(255) NOT NULL,
    date character varying(100) NOT NULL,
    added_unit bytea DEFAULT '\x7827333127'::bytea NOT NULL
);
ALTER TABLE macrostrat.uniquedatafiles2 OWNER TO macrostrat_admin;

CREATE SEQUENCE macrostrat.uniquedatafiles2_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
ALTER TABLE macrostrat.uniquedatafiles2_id_seq OWNER TO macrostrat_admin;

ALTER SEQUENCE macrostrat.uniquedatafiles2_id_seq OWNED BY macrostrat.uniquedatafiles2.id;

CREATE TABLE macrostrat.unit_boundaries (
    id integer NOT NULL,
    t1 integer NOT NULL,
    t1_prop numeric(6,5) NOT NULL,
    t1_age numeric(8,4) NOT NULL,
    unit_id integer NOT NULL,
    unit_id_2 integer NOT NULL,
    section_id integer NOT NULL,
    boundary_position numeric(7,3) DEFAULT NULL::numeric,
    boundary_type macrostrat.boundary_type DEFAULT ''::macrostrat.boundary_type NOT NULL,
    boundary_status macrostrat.boundary_status DEFAULT 'modeled'::macrostrat.boundary_status NOT NULL,
    paleo_lat numeric(7,3) DEFAULT NULL::numeric,
    paleo_lng numeric(7,3) DEFAULT NULL::numeric,
    ref_id integer DEFAULT 217 NOT NULL
);
ALTER TABLE macrostrat.unit_boundaries OWNER TO macrostrat;

CREATE TABLE macrostrat.unit_boundaries_backup (
    id integer NOT NULL,
    t1 integer NOT NULL,
    t1_prop numeric(6,5) NOT NULL,
    t1_age numeric(8,4) NOT NULL,
    unit_id integer NOT NULL,
    unit_id_2 integer NOT NULL,
    section_id integer NOT NULL,
    boundary_position numeric(6,2) DEFAULT NULL::numeric,
    boundary_type macrostrat.boundary_type DEFAULT ''::macrostrat.boundary_type NOT NULL,
    boundary_status macrostrat.boundary_status DEFAULT 'modeled'::macrostrat.boundary_status NOT NULL,
    paleo_lat numeric(7,3) DEFAULT NULL::numeric,
    paleo_lng numeric(7,3) DEFAULT NULL::numeric,
    ref_id integer DEFAULT 217 NOT NULL
);
ALTER TABLE macrostrat.unit_boundaries_backup OWNER TO macrostrat_admin;

CREATE SEQUENCE macrostrat.unit_boundaries_backup_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
ALTER TABLE macrostrat.unit_boundaries_backup_id_seq OWNER TO macrostrat_admin;

ALTER SEQUENCE macrostrat.unit_boundaries_backup_id_seq OWNED BY macrostrat.unit_boundaries_backup.id;

CREATE SEQUENCE macrostrat.unit_boundaries_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
ALTER TABLE macrostrat.unit_boundaries_id_seq OWNER TO macrostrat;

ALTER SEQUENCE macrostrat.unit_boundaries_id_seq OWNED BY macrostrat.unit_boundaries.id;

CREATE TABLE macrostrat.unit_boundaries_scratch (
    id integer NOT NULL,
    t1 integer NOT NULL,
    t1_prop numeric(6,5) NOT NULL,
    t1_age numeric(8,4) NOT NULL,
    unit_id integer NOT NULL,
    unit_id_2 integer NOT NULL,
    section_id integer NOT NULL,
    boundary_position numeric(6,2) DEFAULT NULL::numeric,
    boundary_type macrostrat.boundary_type DEFAULT ''::macrostrat.boundary_type NOT NULL,
    boundary_status macrostrat.boundary_status DEFAULT 'modeled'::macrostrat.boundary_status NOT NULL,
    paleo_lat numeric(7,3) DEFAULT NULL::numeric,
    paleo_lng numeric(7,3) DEFAULT NULL::numeric,
    ref_id integer DEFAULT 217 NOT NULL
);
ALTER TABLE macrostrat.unit_boundaries_scratch OWNER TO macrostrat_admin;

CREATE SEQUENCE macrostrat.unit_boundaries_scratch_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
ALTER TABLE macrostrat.unit_boundaries_scratch_id_seq OWNER TO macrostrat_admin;

ALTER SEQUENCE macrostrat.unit_boundaries_scratch_id_seq OWNED BY macrostrat.unit_boundaries_scratch.id;

CREATE TABLE macrostrat.unit_boundaries_scratch_old (
    id integer NOT NULL,
    t1 integer NOT NULL,
    t1_prop numeric(6,5) NOT NULL,
    t1_age numeric(8,4) NOT NULL,
    unit_id integer NOT NULL,
    unit_id_2 integer NOT NULL,
    section_id integer NOT NULL,
    boundary_type macrostrat.boundary_type DEFAULT ''::macrostrat.boundary_type NOT NULL,
    boundary_status macrostrat.boundary_status DEFAULT 'modeled'::macrostrat.boundary_status NOT NULL,
    paleo_lat numeric(7,3) DEFAULT NULL::numeric,
    paleo_lng numeric(7,3) DEFAULT NULL::numeric
);
ALTER TABLE macrostrat.unit_boundaries_scratch_old OWNER TO macrostrat_admin;

CREATE SEQUENCE macrostrat.unit_boundaries_scratch_old_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
ALTER TABLE macrostrat.unit_boundaries_scratch_old_id_seq OWNER TO macrostrat_admin;

ALTER SEQUENCE macrostrat.unit_boundaries_scratch_old_id_seq OWNED BY macrostrat.unit_boundaries_scratch_old.id;

CREATE TABLE macrostrat.unit_contacts (
  id integer NOT NULL,
  unit_id integer NOT NULL,
  old_contact macrostrat.unit_contacts_old_contact NOT NULL,
  contact macrostrat.unit_contacts_contact NOT NULL,
  old_with_unit integer NOT NULL,
  with_unit integer NOT NULL
);
ALTER TABLE macrostrat.unit_contacts OWNER TO macrostrat_admin;

CREATE SEQUENCE macrostrat.unit_contacts_id_seq
  AS integer
  START WITH 1
  INCREMENT BY 1
  NO MINVALUE
  NO MAXVALUE
  CACHE 1;
ALTER TABLE macrostrat.unit_contacts_id_seq OWNER TO macrostrat_admin;

ALTER SEQUENCE macrostrat.unit_contacts_id_seq OWNED BY macrostrat.unit_contacts.id;

CREATE TABLE macrostrat.unit_dates (
  id integer NOT NULL,
  unit_id integer NOT NULL,
  age numeric(7,3) NOT NULL,
  error numeric(7,3) DEFAULT NULL::numeric,
  system macrostrat.unit_dates_system NOT NULL,
  source character varying(255) DEFAULT NULL::character varying,
  ref_id integer NOT NULL,
  date_mod timestamp with time zone
);
ALTER TABLE macrostrat.unit_dates OWNER TO macrostrat_admin;

CREATE SEQUENCE macrostrat.unit_dates_id_seq
  AS integer
  START WITH 1
  INCREMENT BY 1
  NO MINVALUE
  NO MAXVALUE
  CACHE 1;
ALTER TABLE macrostrat.unit_dates_id_seq OWNER TO macrostrat_admin;

ALTER SEQUENCE macrostrat.unit_dates_id_seq OWNED BY macrostrat.unit_dates.id;

CREATE TABLE macrostrat.unit_econs (
  id integer NOT NULL,
  unit_id integer NOT NULL,
  econ_id integer NOT NULL,
  ref_id integer NOT NULL,
  date_mod timestamp with time zone
);
ALTER TABLE macrostrat.unit_econs OWNER TO macrostrat_admin;

CREATE SEQUENCE macrostrat.unit_econs_id_seq
  AS integer
  START WITH 1
  INCREMENT BY 1
  NO MINVALUE
  NO MAXVALUE
  CACHE 1;
ALTER TABLE macrostrat.unit_econs_id_seq OWNER TO macrostrat_admin;

ALTER SEQUENCE macrostrat.unit_econs_id_seq OWNED BY macrostrat.unit_econs.id;

CREATE TABLE macrostrat.unit_environs (
  id integer NOT NULL,
  unit_id integer NOT NULL,
  environ_id integer NOT NULL,
  f integer,
  l integer,
  ref_id integer DEFAULT 1,
  date_mod timestamp with time zone
);
ALTER TABLE macrostrat.unit_environs OWNER TO macrostrat_admin;

CREATE SEQUENCE macrostrat.unit_environs_id_seq
  AS integer
  START WITH 1
  INCREMENT BY 1
  NO MINVALUE
  NO MAXVALUE
  CACHE 1;
ALTER TABLE macrostrat.unit_environs_id_seq OWNER TO macrostrat_admin;

ALTER SEQUENCE macrostrat.unit_environs_id_seq OWNED BY macrostrat.unit_environs.id;

CREATE TABLE macrostrat.unit_equiv (
  id integer NOT NULL,
  unit_id integer NOT NULL,
  new_unit_id integer NOT NULL
);
ALTER TABLE macrostrat.unit_equiv OWNER TO macrostrat_admin;

CREATE SEQUENCE macrostrat.unit_equiv_id_seq
  AS integer
  START WITH 1
  INCREMENT BY 1
  NO MINVALUE
  NO MAXVALUE
  CACHE 1;
ALTER TABLE macrostrat.unit_equiv_id_seq OWNER TO macrostrat_admin;

ALTER SEQUENCE macrostrat.unit_equiv_id_seq OWNED BY macrostrat.unit_equiv.id;

CREATE TABLE macrostrat.unit_lith_atts (
  id integer NOT NULL,
  unit_lith_id integer,
  lith_att_id integer,
  ref_id integer,
  date_mod text
);
ALTER TABLE macrostrat.unit_lith_atts OWNER TO macrostrat_admin;

CREATE TABLE macrostrat.unit_liths (
  id integer NOT NULL,
  lith_id integer NOT NULL,
  unit_id integer NOT NULL,
  prop character varying(7) DEFAULT NULL::character varying,
  dom macrostrat.unit_liths_dom NOT NULL,
  comp_prop numeric(5,4) NOT NULL,
  mod_prop numeric(5,4) NOT NULL,
  toc numeric(6,5) NOT NULL,
  ref_id integer NOT NULL,
  date_mod timestamp with time zone
);
ALTER TABLE macrostrat.unit_liths OWNER TO macrostrat_admin;

CREATE TABLE macrostrat.unit_liths_atts (
  id integer NOT NULL,
  unit_lith_id integer NOT NULL,
  lith_att_id integer NOT NULL,
  ref_id integer NOT NULL,
  date_mod timestamp with time zone
);
ALTER TABLE macrostrat.unit_liths_atts OWNER TO macrostrat_admin;

CREATE SEQUENCE macrostrat.unit_liths_atts_id_seq
  AS integer
  START WITH 1
  INCREMENT BY 1
  NO MINVALUE
  NO MAXVALUE
  CACHE 1;
ALTER TABLE macrostrat.unit_liths_atts_id_seq OWNER TO macrostrat_admin;

ALTER SEQUENCE macrostrat.unit_liths_atts_id_seq OWNED BY macrostrat.unit_liths_atts.id;

CREATE SEQUENCE macrostrat.unit_liths_id_seq
  AS integer
  START WITH 1
  INCREMENT BY 1
  NO MINVALUE
  NO MAXVALUE
  CACHE 1;
ALTER TABLE macrostrat.unit_liths_id_seq OWNER TO macrostrat_admin;

ALTER SEQUENCE macrostrat.unit_liths_id_seq OWNED BY macrostrat.unit_liths.id;

CREATE TABLE macrostrat.unit_measures (
  id integer NOT NULL,
  measuremeta_id integer NOT NULL,
  unit_id integer NOT NULL,
  strat_name_id integer NOT NULL,
  match_basis character varying(10) NOT NULL,
  rel_position numeric(6,5) DEFAULT NULL::numeric
);
ALTER TABLE macrostrat.unit_measures OWNER TO macrostrat_admin;

CREATE SEQUENCE macrostrat.unit_measures_id_seq
  AS integer
  START WITH 1
  INCREMENT BY 1
  NO MINVALUE
  NO MAXVALUE
  CACHE 1;
ALTER TABLE macrostrat.unit_measures_id_seq OWNER TO macrostrat_admin;

ALTER SEQUENCE macrostrat.unit_measures_id_seq OWNED BY macrostrat.unit_measures.id;

CREATE SEQUENCE macrostrat.unit_measures_new_id_seq
  AS integer
  START WITH 1
  INCREMENT BY 1
  NO MINVALUE
  NO MAXVALUE
  CACHE 1;
ALTER TABLE macrostrat.unit_measures_new_id_seq OWNER TO macrostrat_admin;

ALTER SEQUENCE macrostrat.unit_measures_new_id_seq OWNED BY macrostrat.unit_measures.id;

CREATE TABLE macrostrat.unit_measures_pbdb (
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
ALTER TABLE macrostrat.unit_measures_pbdb OWNER TO macrostrat_admin;

CREATE TABLE macrostrat.unit_notes (
  id integer NOT NULL,
  notes text NOT NULL,
  unit_id integer NOT NULL,
  date_mod timestamp with time zone
);
ALTER TABLE macrostrat.unit_notes OWNER TO macrostrat_admin;

CREATE SEQUENCE macrostrat.unit_notes_id_seq
  AS integer
  START WITH 1
  INCREMENT BY 1
  NO MINVALUE
  NO MAXVALUE
  CACHE 1;
ALTER TABLE macrostrat.unit_notes_id_seq OWNER TO macrostrat_admin;

ALTER SEQUENCE macrostrat.unit_notes_id_seq OWNED BY macrostrat.unit_notes.id;

CREATE TABLE macrostrat.unit_seq_strat (
  id integer NOT NULL,
  unit_id integer NOT NULL,
  seq_strat macrostrat.unit_seq_strat_seq_strat NOT NULL,
  seq_order macrostrat.unit_seq_strat_seq_order NOT NULL
);
ALTER TABLE macrostrat.unit_seq_strat OWNER TO macrostrat_admin;

CREATE SEQUENCE macrostrat.unit_seq_strat_id_seq
  AS integer
  START WITH 1
  INCREMENT BY 1
  NO MINVALUE
  NO MAXVALUE
  CACHE 1;
ALTER TABLE macrostrat.unit_seq_strat_id_seq OWNER TO macrostrat_admin;

ALTER SEQUENCE macrostrat.unit_seq_strat_id_seq OWNED BY macrostrat.unit_seq_strat.id;

CREATE TABLE macrostrat.unit_strat_names (
  id integer NOT NULL,
  unit_id integer NOT NULL,
  strat_name_id integer NOT NULL,
  old_strat_name_id integer NOT NULL
);
ALTER TABLE macrostrat.unit_strat_names OWNER TO macrostrat_admin;

CREATE SEQUENCE macrostrat.unit_strat_names_id_seq
  AS integer
  START WITH 1
  INCREMENT BY 1
  NO MINVALUE
  NO MAXVALUE
  CACHE 1;
ALTER TABLE macrostrat.unit_strat_names_id_seq OWNER TO macrostrat_admin;

ALTER SEQUENCE macrostrat.unit_strat_names_id_seq OWNED BY macrostrat.unit_strat_names.id;

CREATE SEQUENCE macrostrat.unit_strat_names_new_id_seq1
  AS integer
  START WITH 1
  INCREMENT BY 1
  NO MINVALUE
  NO MAXVALUE
  CACHE 1;
ALTER TABLE macrostrat.unit_strat_names_new_id_seq1 OWNER TO macrostrat_admin;

ALTER SEQUENCE macrostrat.unit_strat_names_new_id_seq1 OWNED BY macrostrat.unit_strat_names.id;

CREATE TABLE macrostrat.unit_tectonics (
  id integer NOT NULL,
  unit_id integer NOT NULL,
  tectonic_id integer NOT NULL
);
ALTER TABLE macrostrat.unit_tectonics OWNER TO macrostrat_admin;

CREATE SEQUENCE macrostrat.unit_tectonics_id_seq
  AS integer
  START WITH 1
  INCREMENT BY 1
  NO MINVALUE
  NO MAXVALUE
  CACHE 1;
ALTER TABLE macrostrat.unit_tectonics_id_seq OWNER TO macrostrat_admin;

ALTER SEQUENCE macrostrat.unit_tectonics_id_seq OWNED BY macrostrat.unit_tectonics.id;

CREATE TABLE macrostrat.units (
  id integer NOT NULL,
  strat_name character varying(150) NOT NULL,
  color macrostrat.units_color NOT NULL,
  outcrop macrostrat.units_outcrop NOT NULL,
  fo integer DEFAULT 0 NOT NULL,
  fo_h smallint DEFAULT '0'::smallint NOT NULL,
  lo integer DEFAULT 0 NOT NULL,
  lo_h smallint DEFAULT '0'::smallint NOT NULL,
  position_bottom numeric(7,3) NOT NULL,
  position_top numeric(7,3) NOT NULL,
  max_thick numeric(7,2) NOT NULL,
  min_thick numeric(7,2) NOT NULL,
  section_id integer DEFAULT 0 NOT NULL,
  col_id integer NOT NULL,
  date_mod timestamp with time zone
);
ALTER TABLE macrostrat.units OWNER TO macrostrat_admin;

CREATE TABLE macrostrat.units_datafiles (
  unit_id integer NOT NULL,
  datafile_id integer NOT NULL
);
ALTER TABLE macrostrat.units_datafiles OWNER TO macrostrat_admin;

CREATE SEQUENCE macrostrat.units_id_seq
  AS integer
  START WITH 1
  INCREMENT BY 1
  NO MINVALUE
  NO MAXVALUE
  CACHE 1;
ALTER TABLE macrostrat.units_id_seq OWNER TO macrostrat_admin;

ALTER SEQUENCE macrostrat.units_id_seq OWNED BY macrostrat.units.id;

CREATE TABLE macrostrat.units_sections (
  id integer NOT NULL,
  unit_id integer NOT NULL,
  section_id integer NOT NULL,
  col_id integer NOT NULL
);
ALTER TABLE macrostrat.units_sections OWNER TO macrostrat_admin;

CREATE SEQUENCE macrostrat.units_sections_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
ALTER TABLE macrostrat.units_sections_id_seq OWNER TO macrostrat_admin;

ALTER SEQUENCE macrostrat.units_sections_id_seq OWNED BY macrostrat.units_sections.id;

CREATE SEQUENCE macrostrat.units_sections_new_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
ALTER TABLE macrostrat.units_sections_new_id_seq OWNER TO macrostrat_admin;

ALTER SEQUENCE macrostrat.units_sections_new_id_seq OWNED BY macrostrat.units_sections.id;


