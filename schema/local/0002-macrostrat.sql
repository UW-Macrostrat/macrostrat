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
-- Name: macrostrat; Type: SCHEMA; Schema: -; Owner: macrostrat
--

CREATE SCHEMA macrostrat;


ALTER SCHEMA macrostrat OWNER TO macrostrat;

--
-- Name: colors_color; Type: TYPE; Schema: macrostrat; Owner: macrostrat-admin
--

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


ALTER TYPE macrostrat.colors_color OWNER TO "macrostrat-admin";

--
-- Name: cols_col_position; Type: TYPE; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE TYPE macrostrat.cols_col_position AS ENUM (
    '',
    'onshore',
    'offshore'
);


ALTER TYPE macrostrat.cols_col_position OWNER TO "macrostrat-admin";

--
-- Name: cols_col_type; Type: TYPE; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE TYPE macrostrat.cols_col_type AS ENUM (
    'column',
    'section'
);


ALTER TYPE macrostrat.cols_col_type OWNER TO "macrostrat-admin";

--
-- Name: cols_status_code; Type: TYPE; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE TYPE macrostrat.cols_status_code AS ENUM (
    '',
    'active',
    'in process',
    'obsolete'
);


ALTER TYPE macrostrat.cols_status_code OWNER TO "macrostrat-admin";

--
-- Name: econs_econ_class; Type: TYPE; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE TYPE macrostrat.econs_econ_class AS ENUM (
    '',
    'energy',
    'material',
    'precious commodity',
    'water'
);


ALTER TYPE macrostrat.econs_econ_class OWNER TO "macrostrat-admin";

--
-- Name: econs_econ_type; Type: TYPE; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE TYPE macrostrat.econs_econ_type AS ENUM (
    '',
    'mineral',
    'hydrocarbon',
    'construction',
    'nuclear',
    'coal',
    'aquifer'
);


ALTER TYPE macrostrat.econs_econ_type OWNER TO "macrostrat-admin";

--
-- Name: environs_environ_class; Type: TYPE; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE TYPE macrostrat.environs_environ_class AS ENUM (
    '',
    'marine',
    'non-marine'
);


ALTER TYPE macrostrat.environs_environ_class OWNER TO "macrostrat-admin";

--
-- Name: environs_environ_type; Type: TYPE; Schema: macrostrat; Owner: macrostrat-admin
--

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


ALTER TYPE macrostrat.environs_environ_type OWNER TO "macrostrat-admin";


CREATE TYPE macrostrat.boundary_status AS ENUM (
    '',
    'modeled',
    'relative',
    'absolute',
    'spike'
);


ALTER TYPE macrostrat.boundary_status OWNER TO "macrostrat-admin";


--
-- Name: intervals_interval_type; Type: TYPE; Schema: macrostrat; Owner: macrostrat-admin
--

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


ALTER TYPE macrostrat.intervals_interval_type OWNER TO "macrostrat-admin";

--
-- Name: lith_atts_att_type; Type: TYPE; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE TYPE macrostrat.lith_atts_att_type AS ENUM (
    '',
    'bedform',
    'sed structure',
    'grains',
    'color',
    'lithology',
    'structure'
);


ALTER TYPE macrostrat.lith_atts_att_type OWNER TO "macrostrat-admin";

--
-- Name: liths_lith_class; Type: TYPE; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE TYPE macrostrat.liths_lith_class AS ENUM (
    '',
    'sedimentary',
    'igneous',
    'metamorphic'
);


ALTER TYPE macrostrat.liths_lith_class OWNER TO "macrostrat-admin";

--
-- Name: liths_lith_group; Type: TYPE; Schema: macrostrat; Owner: macrostrat-admin
--

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


ALTER TYPE macrostrat.liths_lith_group OWNER TO "macrostrat-admin";

--
-- Name: liths_lith_type; Type: TYPE; Schema: macrostrat; Owner: macrostrat-admin
--

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


ALTER TYPE macrostrat.liths_lith_type OWNER TO "macrostrat-admin";

--
-- Name: lookup_measurements_measurement_class; Type: TYPE; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE TYPE macrostrat.lookup_measurements_measurement_class AS ENUM (
    '',
    'geophysical',
    'geochemical',
    'sedimentological'
);


ALTER TYPE macrostrat.lookup_measurements_measurement_class OWNER TO "macrostrat-admin";

--
-- Name: lookup_measurements_measurement_type; Type: TYPE; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE TYPE macrostrat.lookup_measurements_measurement_type AS ENUM (
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


ALTER TYPE macrostrat.lookup_measurements_measurement_type OWNER TO "macrostrat-admin";

--
-- Name: lookup_strat_names_rank; Type: TYPE; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE TYPE macrostrat.lookup_strat_names_rank AS ENUM (
    '',
    'SGp',
    'Gp',
    'SubGp',
    'Fm',
    'Mbr',
    'Bed'
);


ALTER TYPE macrostrat.lookup_strat_names_rank OWNER TO "macrostrat-admin";

--
-- Name: map_scale; Type: TYPE; Schema: macrostrat; Owner: macrostrat_admin
--

CREATE TYPE macrostrat.map_scale AS ENUM (
    'tiny',
    'small',
    'medium',
    'large'
);


ALTER TYPE macrostrat.map_scale OWNER TO macrostrat_admin;

--
-- Name: measurements_measurement_class; Type: TYPE; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE TYPE macrostrat.measurements_measurement_class AS ENUM (
    '',
    'geophysical',
    'geochemical',
    'sedimentological'
);


ALTER TYPE macrostrat.measurements_measurement_class OWNER TO "macrostrat-admin";

--
-- Name: measurements_measurement_type; Type: TYPE; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE TYPE macrostrat.measurements_measurement_type AS ENUM (
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


ALTER TYPE macrostrat.measurements_measurement_type OWNER TO "macrostrat-admin";

--
-- Name: pbdb_intervals_interval_type; Type: TYPE; Schema: macrostrat; Owner: macrostrat-admin
--

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


ALTER TYPE macrostrat.pbdb_intervals_interval_type OWNER TO "macrostrat-admin";

--
-- Name: refs_compilation_code; Type: TYPE; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE TYPE macrostrat.refs_compilation_code AS ENUM (
    '',
    'COSUNA',
    'COSUNA II',
    'Canada',
    'GNS Folio Series 1'
);


ALTER TYPE macrostrat.refs_compilation_code OWNER TO "macrostrat-admin";

--
-- Name: rockd_features_feature_class; Type: TYPE; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE TYPE macrostrat.rockd_features_feature_class AS ENUM (
    '',
    'structure',
    'geomorphology'
);


ALTER TYPE macrostrat.rockd_features_feature_class OWNER TO "macrostrat-admin";

--
-- Name: rockd_features_feature_type; Type: TYPE; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE TYPE macrostrat.rockd_features_feature_type AS ENUM (
    '',
    'fault',
    'glacial',
    'deformation'
);


ALTER TYPE macrostrat.rockd_features_feature_type OWNER TO "macrostrat-admin";

--
-- Name: stats_project; Type: TYPE; Schema: macrostrat; Owner: macrostrat-admin
--

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


ALTER TYPE macrostrat.stats_project OWNER TO "macrostrat-admin";

--
-- Name: strat_names_lookup_rank; Type: TYPE; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE TYPE macrostrat.strat_names_lookup_rank AS ENUM (
    '',
    'SGp',
    'Gp',
    'Fm',
    'Mbr',
    'Bed'
);


ALTER TYPE macrostrat.strat_names_lookup_rank OWNER TO "macrostrat-admin";

--
-- Name: strat_names_rank; Type: TYPE; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE TYPE macrostrat.strat_names_rank AS ENUM (
    '',
    'SGp',
    'Gp',
    'SubGp',
    'Fm',
    'Mbr',
    'Bed'
);


ALTER TYPE macrostrat.strat_names_rank OWNER TO "macrostrat-admin";

--
-- Name: strat_tree_rel; Type: TYPE; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE TYPE macrostrat.strat_tree_rel AS ENUM (
    '',
    'parent',
    'synonym'
);


ALTER TYPE macrostrat.strat_tree_rel OWNER TO "macrostrat-admin";

--
-- Name: structure_atts_att_class; Type: TYPE; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE TYPE macrostrat.structure_atts_att_class AS ENUM (
);


ALTER TYPE macrostrat.structure_atts_att_class OWNER TO "macrostrat-admin";

--
-- Name: structure_atts_att_type; Type: TYPE; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE TYPE macrostrat.structure_atts_att_type AS ENUM (
);


ALTER TYPE macrostrat.structure_atts_att_type OWNER TO "macrostrat-admin";

--
-- Name: structures_structure_class; Type: TYPE; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE TYPE macrostrat.structures_structure_class AS ENUM (
    '',
    'fracture',
    'structure',
    'fabric',
    'sedimentology',
    'igneous'
);


ALTER TYPE macrostrat.structures_structure_class OWNER TO "macrostrat-admin";

--
-- Name: structures_structure_group; Type: TYPE; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE TYPE macrostrat.structures_structure_group AS ENUM (
);


ALTER TYPE macrostrat.structures_structure_group OWNER TO "macrostrat-admin";

--
-- Name: structures_structure_type; Type: TYPE; Schema: macrostrat; Owner: macrostrat-admin
--

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


ALTER TYPE macrostrat.structures_structure_type OWNER TO "macrostrat-admin";

--
-- Name: tectonics_basin_setting; Type: TYPE; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE TYPE macrostrat.tectonics_basin_setting AS ENUM (
    '',
    'divergent',
    'intraplate',
    'convergent',
    'transform',
    'hybrid'
);


ALTER TYPE macrostrat.tectonics_basin_setting OWNER TO "macrostrat-admin";


CREATE TYPE macrostrat.boundary_type AS ENUM (
    '',
    'unconformity',
    'conformity',
    'fault',
    'disconformity',
    'non-conformity',
    'angular unconformity'
);


ALTER TYPE macrostrat.boundary_type OWNER TO "macrostrat-admin";

--
-- Name: unit_contacts_contact; Type: TYPE; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE TYPE macrostrat.unit_contacts_contact AS ENUM (
    'above',
    'below',
    'lateral',
    'lateral-bottom',
    'lateral-top',
    'within'
);


ALTER TYPE macrostrat.unit_contacts_contact OWNER TO "macrostrat-admin";

--
-- Name: unit_contacts_old_contact; Type: TYPE; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE TYPE macrostrat.unit_contacts_old_contact AS ENUM (
    'above',
    'below',
    'lateral',
    'lateral-bottom',
    'lateral-top',
    'within'
);


ALTER TYPE macrostrat.unit_contacts_old_contact OWNER TO "macrostrat-admin";

--
-- Name: unit_dates_system; Type: TYPE; Schema: macrostrat; Owner: macrostrat-admin
--

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


ALTER TYPE macrostrat.unit_dates_system OWNER TO "macrostrat-admin";

--
-- Name: unit_liths_dom; Type: TYPE; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE TYPE macrostrat.unit_liths_dom AS ENUM (
    '',
    'dom',
    'sub'
);


ALTER TYPE macrostrat.unit_liths_dom OWNER TO "macrostrat-admin";

--
-- Name: unit_seq_strat_seq_order; Type: TYPE; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE TYPE macrostrat.unit_seq_strat_seq_order AS ENUM (
    '',
    '2nd',
    '3rd',
    '4th',
    '5th',
    '6th'
);


ALTER TYPE macrostrat.unit_seq_strat_seq_order OWNER TO "macrostrat-admin";

--
-- Name: unit_seq_strat_seq_strat; Type: TYPE; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE TYPE macrostrat.unit_seq_strat_seq_strat AS ENUM (
    '',
    'TST',
    'HST',
    'FSST',
    'LST',
    'SQ'
);


ALTER TYPE macrostrat.unit_seq_strat_seq_strat OWNER TO "macrostrat-admin";

--
-- Name: units_color; Type: TYPE; Schema: macrostrat; Owner: macrostrat-admin
--

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


ALTER TYPE macrostrat.units_color OWNER TO "macrostrat-admin";

--
-- Name: units_outcrop; Type: TYPE; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE TYPE macrostrat.units_outcrop AS ENUM (
    '',
    'surface',
    'subsurface',
    'both'
);


ALTER TYPE macrostrat.units_outcrop OWNER TO "macrostrat-admin";

--
-- Name: check_column_project_non_composite(); Type: FUNCTION; Schema: macrostrat; Owner: macrostrat_admin
--

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

--
-- Name: check_composite_parent(); Type: FUNCTION; Schema: macrostrat; Owner: macrostrat_admin
--

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

--
-- Name: core_project_ids(); Type: FUNCTION; Schema: macrostrat; Owner: macrostrat_admin
--

CREATE FUNCTION macrostrat.core_project_ids() RETURNS integer[]
    LANGUAGE sql STABLE
    AS $$
SELECT macrostrat.flattened_project_ids(ARRAY[id]) FROM macrostrat.projects WHERE slug = 'core';
$$;


ALTER FUNCTION macrostrat.core_project_ids() OWNER TO macrostrat_admin;

--
-- Name: flattened_project_ids(integer[]); Type: FUNCTION; Schema: macrostrat; Owner: macrostrat_admin
--

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

--
-- Name: projects; Type: TABLE; Schema: macrostrat; Owner: macrostrat
--

CREATE TABLE macrostrat.projects (
    id integer NOT NULL,
    project text NOT NULL,
    descrip text NOT NULL,
    timescale_id integer NOT NULL,
    is_composite boolean DEFAULT false,
    slug text NOT NULL
);


ALTER TABLE macrostrat.projects OWNER TO macrostrat;

--
-- Name: TABLE projects; Type: COMMENT; Schema: macrostrat; Owner: macrostrat
--

COMMENT ON TABLE macrostrat.projects IS 'Last updated from MariaDB - 2023-07-28 16:57';


--
-- Name: generate_project_slug(macrostrat.projects); Type: FUNCTION; Schema: macrostrat; Owner: macrostrat_admin
--

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

--
-- Name: generate_project_slug(text); Type: FUNCTION; Schema: macrostrat; Owner: macrostrat_admin
--

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

--
-- Name: get_lith_comp_prop(integer); Type: FUNCTION; Schema: macrostrat; Owner: macrostrat-admin
--

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


ALTER FUNCTION macrostrat.get_lith_comp_prop(_unit_id integer) OWNER TO "macrostrat-admin";

--
-- Name: lng_lat_insert_trigger(); Type: FUNCTION; Schema: macrostrat; Owner: macrostrat-admin
--

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


ALTER FUNCTION macrostrat.lng_lat_insert_trigger() OWNER TO "macrostrat-admin";

--
-- Name: on_update_current_timestamp_offshore_baggage(); Type: FUNCTION; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE FUNCTION macrostrat.on_update_current_timestamp_offshore_baggage() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
   NEW.created_at = now();
   RETURN NEW;
END;
$$;


ALTER FUNCTION macrostrat.on_update_current_timestamp_offshore_baggage() OWNER TO "macrostrat-admin";

--
-- Name: on_update_current_timestamp_offshore_fossils(); Type: FUNCTION; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE FUNCTION macrostrat.on_update_current_timestamp_offshore_fossils() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
   NEW.created_at = now();
   RETURN NEW;
END;
$$;


ALTER FUNCTION macrostrat.on_update_current_timestamp_offshore_fossils() OWNER TO "macrostrat-admin";

--
-- Name: on_update_current_timestamp_unit_dates(); Type: FUNCTION; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE FUNCTION macrostrat.on_update_current_timestamp_unit_dates() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
   NEW.date_mod = now();
   RETURN NEW;
END;
$$;


ALTER FUNCTION macrostrat.on_update_current_timestamp_unit_dates() OWNER TO "macrostrat-admin";

--
-- Name: on_update_current_timestamp_unit_econs(); Type: FUNCTION; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE FUNCTION macrostrat.on_update_current_timestamp_unit_econs() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
   NEW.date_mod = now();
   RETURN NEW;
END;
$$;


ALTER FUNCTION macrostrat.on_update_current_timestamp_unit_econs() OWNER TO "macrostrat-admin";

--
-- Name: on_update_current_timestamp_unit_environs(); Type: FUNCTION; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE FUNCTION macrostrat.on_update_current_timestamp_unit_environs() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
   NEW.date_mod = now();
   RETURN NEW;
END;
$$;


ALTER FUNCTION macrostrat.on_update_current_timestamp_unit_environs() OWNER TO "macrostrat-admin";

--
-- Name: on_update_current_timestamp_unit_liths(); Type: FUNCTION; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE FUNCTION macrostrat.on_update_current_timestamp_unit_liths() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
   NEW.date_mod = now();
   RETURN NEW;
END;
$$;


ALTER FUNCTION macrostrat.on_update_current_timestamp_unit_liths() OWNER TO "macrostrat-admin";

--
-- Name: on_update_current_timestamp_unit_liths_atts(); Type: FUNCTION; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE FUNCTION macrostrat.on_update_current_timestamp_unit_liths_atts() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
   NEW.date_mod = now();
   RETURN NEW;
END;
$$;


ALTER FUNCTION macrostrat.on_update_current_timestamp_unit_liths_atts() OWNER TO "macrostrat-admin";

--
-- Name: on_update_current_timestamp_unit_notes(); Type: FUNCTION; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE FUNCTION macrostrat.on_update_current_timestamp_unit_notes() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
   NEW.date_mod = now();
   RETURN NEW;
END;
$$;


ALTER FUNCTION macrostrat.on_update_current_timestamp_unit_notes() OWNER TO "macrostrat-admin";

--
-- Name: on_update_current_timestamp_units(); Type: FUNCTION; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE FUNCTION macrostrat.on_update_current_timestamp_units() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
   NEW.date_mod = now();
   RETURN NEW;
END;
$$;


ALTER FUNCTION macrostrat.on_update_current_timestamp_units() OWNER TO "macrostrat-admin";

--
-- Name: update_unit_lith_comp_props(integer); Type: FUNCTION; Schema: macrostrat; Owner: macrostrat-admin
--

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


ALTER FUNCTION macrostrat.update_unit_lith_comp_props(_unit_id integer) OWNER TO "macrostrat-admin";

--
-- Name: autocomplete; Type: TABLE; Schema: macrostrat; Owner: macrostrat_admin
--

CREATE TABLE macrostrat.autocomplete (
    id integer DEFAULT 0 NOT NULL,
    name character varying(255) DEFAULT NULL::character varying,
    type character varying(20) DEFAULT ''::character varying NOT NULL,
    category character varying(10) DEFAULT ''::character varying NOT NULL
);


ALTER TABLE macrostrat.autocomplete OWNER TO macrostrat_admin;

--
-- Name: autocomplete_old; Type: TABLE; Schema: macrostrat; Owner: macrostrat_admin
--

CREATE TABLE macrostrat.autocomplete_old (
    id integer DEFAULT 0 NOT NULL,
    name character varying(255) DEFAULT NULL::character varying,
    type character varying(20) DEFAULT ''::character varying NOT NULL,
    category character varying(10) DEFAULT ''::character varying NOT NULL
);


ALTER TABLE macrostrat.autocomplete_old OWNER TO macrostrat_admin;

--
-- Name: canada_lexicon_dump; Type: TABLE; Schema: macrostrat; Owner: macrostrat-admin
--

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


ALTER TABLE macrostrat.canada_lexicon_dump OWNER TO "macrostrat-admin";

--
-- Name: col_areas; Type: TABLE; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE TABLE macrostrat.col_areas (
    id integer NOT NULL,
    col_id integer NOT NULL,
    gmap text NOT NULL,
    col_area public.geometry,
    wkt text
);


ALTER TABLE macrostrat.col_areas OWNER TO "macrostrat-admin";

--
-- Name: col_areas_6april2016; Type: TABLE; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE TABLE macrostrat.col_areas_6april2016 (
    id integer DEFAULT 0 NOT NULL,
    col_id integer NOT NULL,
    gmap text NOT NULL,
    col_area public.geometry
);


ALTER TABLE macrostrat.col_areas_6april2016 OWNER TO "macrostrat-admin";

--
-- Name: col_areas_id_seq; Type: SEQUENCE; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE SEQUENCE macrostrat.col_areas_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE macrostrat.col_areas_id_seq OWNER TO "macrostrat-admin";

--
-- Name: col_areas_id_seq; Type: SEQUENCE OWNED BY; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER SEQUENCE macrostrat.col_areas_id_seq OWNED BY macrostrat.col_areas.id;


--
-- Name: col_equiv; Type: TABLE; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE TABLE macrostrat.col_equiv (
    id integer NOT NULL,
    col_1 integer NOT NULL,
    col_2 integer NOT NULL
);


ALTER TABLE macrostrat.col_equiv OWNER TO "macrostrat-admin";

--
-- Name: col_equiv_id_seq; Type: SEQUENCE; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE SEQUENCE macrostrat.col_equiv_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE macrostrat.col_equiv_id_seq OWNER TO "macrostrat-admin";

--
-- Name: col_equiv_id_seq; Type: SEQUENCE OWNED BY; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER SEQUENCE macrostrat.col_equiv_id_seq OWNED BY macrostrat.col_equiv.id;


--
-- Name: col_groups; Type: TABLE; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE TABLE macrostrat.col_groups (
    id integer NOT NULL,
    col_group character varying(100) NOT NULL,
    col_group_long character varying(100) NOT NULL,
    project_id integer NOT NULL
);


ALTER TABLE macrostrat.col_groups OWNER TO "macrostrat-admin";

--
-- Name: col_groups_id_seq; Type: SEQUENCE; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE SEQUENCE macrostrat.col_groups_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE macrostrat.col_groups_id_seq OWNER TO "macrostrat-admin";

--
-- Name: col_groups_id_seq; Type: SEQUENCE OWNED BY; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER SEQUENCE macrostrat.col_groups_id_seq OWNED BY macrostrat.col_groups.id;


--
-- Name: col_notes; Type: TABLE; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE TABLE macrostrat.col_notes (
    id integer NOT NULL,
    col_id integer NOT NULL,
    notes text NOT NULL
);


ALTER TABLE macrostrat.col_notes OWNER TO "macrostrat-admin";

--
-- Name: col_notes_id_seq; Type: SEQUENCE; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE SEQUENCE macrostrat.col_notes_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE macrostrat.col_notes_id_seq OWNER TO "macrostrat-admin";

--
-- Name: col_notes_id_seq; Type: SEQUENCE OWNED BY; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER SEQUENCE macrostrat.col_notes_id_seq OWNED BY macrostrat.col_notes.id;


--
-- Name: col_refs; Type: TABLE; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE TABLE macrostrat.col_refs (
    id integer NOT NULL,
    col_id integer NOT NULL,
    ref_id integer NOT NULL
);


ALTER TABLE macrostrat.col_refs OWNER TO "macrostrat-admin";

--
-- Name: col_refs_id_seq; Type: SEQUENCE; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE SEQUENCE macrostrat.col_refs_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE macrostrat.col_refs_id_seq OWNER TO "macrostrat-admin";

--
-- Name: col_refs_id_seq; Type: SEQUENCE OWNED BY; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER SEQUENCE macrostrat.col_refs_id_seq OWNED BY macrostrat.col_refs.id;


--
-- Name: colors; Type: TABLE; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE TABLE macrostrat.colors (
    color macrostrat.colors_color NOT NULL,
    unit_hex character varying(9) DEFAULT '#FFFFFF'::character varying NOT NULL,
    text_hex character varying(9) DEFAULT '#000000'::character varying NOT NULL,
    unit_class character varying(4) DEFAULT NULL::character varying
);


ALTER TABLE macrostrat.colors OWNER TO "macrostrat-admin";

--
-- Name: cols; Type: TABLE; Schema: macrostrat; Owner: macrostrat-admin
--

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


ALTER TABLE macrostrat.cols OWNER TO "macrostrat-admin";

--
-- Name: cols_id_seq; Type: SEQUENCE; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE SEQUENCE macrostrat.cols_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE macrostrat.cols_id_seq OWNER TO "macrostrat-admin";

--
-- Name: cols_id_seq; Type: SEQUENCE OWNED BY; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER SEQUENCE macrostrat.cols_id_seq OWNED BY macrostrat.cols.id;


--
-- Name: concepts_places; Type: TABLE; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE TABLE macrostrat.concepts_places (
    concept_id integer NOT NULL,
    place_id bigint NOT NULL
);


ALTER TABLE macrostrat.concepts_places OWNER TO "macrostrat-admin";

--
-- Name: econs; Type: TABLE; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE TABLE macrostrat.econs (
    id integer NOT NULL,
    econ character varying(100) NOT NULL,
    econ_type macrostrat.econs_econ_type NOT NULL,
    econ_class macrostrat.econs_econ_class NOT NULL,
    econ_color character varying(7) NOT NULL
);


ALTER TABLE macrostrat.econs OWNER TO "macrostrat-admin";

--
-- Name: econs_id_seq; Type: SEQUENCE; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE SEQUENCE macrostrat.econs_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE macrostrat.econs_id_seq OWNER TO "macrostrat-admin";

--
-- Name: econs_id_seq; Type: SEQUENCE OWNED BY; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER SEQUENCE macrostrat.econs_id_seq OWNED BY macrostrat.econs.id;


--
-- Name: environs; Type: TABLE; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE TABLE macrostrat.environs (
    id integer NOT NULL,
    environ character varying(50) NOT NULL,
    environ_type macrostrat.environs_environ_type NOT NULL,
    environ_class macrostrat.environs_environ_class NOT NULL,
    environ_fill integer NOT NULL,
    environ_color character varying(7) NOT NULL
);


ALTER TABLE macrostrat.environs OWNER TO "macrostrat-admin";

--
-- Name: environs_id_seq; Type: SEQUENCE; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE SEQUENCE macrostrat.environs_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE macrostrat.environs_id_seq OWNER TO "macrostrat-admin";

--
-- Name: environs_id_seq; Type: SEQUENCE OWNED BY; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER SEQUENCE macrostrat.environs_id_seq OWNED BY macrostrat.environs.id;


--
-- Name: grainsize; Type: TABLE; Schema: macrostrat; Owner: macrostrat-admin
--

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


ALTER TABLE macrostrat.grainsize OWNER TO "macrostrat-admin";

--
-- Name: interval_boundaries; Type: TABLE; Schema: macrostrat; Owner: macrostrat-admin
--

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


ALTER TABLE macrostrat.interval_boundaries OWNER TO "macrostrat-admin";

--
-- Name: interval_boundaries_scratch; Type: TABLE; Schema: macrostrat; Owner: macrostrat-admin
--

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


ALTER TABLE macrostrat.interval_boundaries_scratch OWNER TO "macrostrat-admin";

--
-- Name: intervals; Type: TABLE; Schema: macrostrat; Owner: macrostrat-admin
--

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


ALTER TABLE macrostrat.intervals OWNER TO "macrostrat-admin";

--
-- Name: intervals_id_seq; Type: SEQUENCE; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE SEQUENCE macrostrat.intervals_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE macrostrat.intervals_id_seq OWNER TO "macrostrat-admin";

--
-- Name: intervals_id_seq; Type: SEQUENCE OWNED BY; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER SEQUENCE macrostrat.intervals_id_seq OWNED BY macrostrat.intervals.id;


--
-- Name: intervals_new_id_seq1; Type: SEQUENCE; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE SEQUENCE macrostrat.intervals_new_id_seq1
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE macrostrat.intervals_new_id_seq1 OWNER TO "macrostrat-admin";

--
-- Name: intervals_new_id_seq1; Type: SEQUENCE OWNED BY; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER SEQUENCE macrostrat.intervals_new_id_seq1 OWNED BY macrostrat.intervals.id;


--
-- Name: lith_atts; Type: TABLE; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE TABLE macrostrat.lith_atts (
    id integer NOT NULL,
    lith_att character varying(50) NOT NULL,
    equiv integer NOT NULL,
    att_type macrostrat.lith_atts_att_type NOT NULL,
    lith_att_fill integer NOT NULL
);


ALTER TABLE macrostrat.lith_atts OWNER TO "macrostrat-admin";

--
-- Name: lith_atts_id_seq; Type: SEQUENCE; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE SEQUENCE macrostrat.lith_atts_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE macrostrat.lith_atts_id_seq OWNER TO "macrostrat-admin";

--
-- Name: lith_atts_id_seq; Type: SEQUENCE OWNED BY; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER SEQUENCE macrostrat.lith_atts_id_seq OWNED BY macrostrat.lith_atts.id;


--
-- Name: liths; Type: TABLE; Schema: macrostrat; Owner: macrostrat-admin
--

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


ALTER TABLE macrostrat.liths OWNER TO "macrostrat-admin";

--
-- Name: liths_id_seq; Type: SEQUENCE; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE SEQUENCE macrostrat.liths_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE macrostrat.liths_id_seq OWNER TO "macrostrat-admin";

--
-- Name: liths_id_seq; Type: SEQUENCE OWNED BY; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER SEQUENCE macrostrat.liths_id_seq OWNED BY macrostrat.liths.id;


--
-- Name: lookup_measurements; Type: TABLE; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE TABLE macrostrat.lookup_measurements (
    measure_id integer NOT NULL,
    measuremeta_id integer NOT NULL,
    measurement_id integer NOT NULL,
    measurement character varying(100) NOT NULL,
    measurement_class macrostrat.lookup_measurements_measurement_class NOT NULL,
    measurement_type macrostrat.lookup_measurements_measurement_type NOT NULL,
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


ALTER TABLE macrostrat.lookup_measurements OWNER TO "macrostrat-admin";

--
-- Name: lookup_strat_names; Type: TABLE; Schema: macrostrat; Owner: macrostrat-admin
--

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


ALTER TABLE macrostrat.lookup_strat_names OWNER TO "macrostrat-admin";

--
-- Name: lookup_strat_names_new; Type: TABLE; Schema: macrostrat; Owner: macrostrat_admin
--

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

--
-- Name: lookup_unit_attrs_api; Type: TABLE; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE TABLE macrostrat.lookup_unit_attrs_api (
    unit_id integer,
    lith bytea,
    environ bytea,
    econ bytea,
    measure_short bytea,
    measure_long bytea
);


ALTER TABLE macrostrat.lookup_unit_attrs_api OWNER TO "macrostrat-admin";

--
-- Name: lookup_unit_intervals; Type: TABLE; Schema: macrostrat; Owner: macrostrat-admin
--

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


ALTER TABLE macrostrat.lookup_unit_intervals OWNER TO "macrostrat-admin";

--
-- Name: lookup_unit_liths; Type: TABLE; Schema: macrostrat; Owner: macrostrat-admin
--

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


ALTER TABLE macrostrat.lookup_unit_liths OWNER TO "macrostrat-admin";

--
-- Name: lookup_units; Type: TABLE; Schema: macrostrat; Owner: macrostrat-admin
--

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


ALTER TABLE macrostrat.lookup_units OWNER TO "macrostrat-admin";

--
-- Name: measurements; Type: TABLE; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE TABLE macrostrat.measurements (
    id integer NOT NULL,
    measurement_class macrostrat.measurements_measurement_class NOT NULL,
    measurement_type macrostrat.measurements_measurement_type NOT NULL,
    measurement character varying(150) NOT NULL
);


ALTER TABLE macrostrat.measurements OWNER TO "macrostrat-admin";

--
-- Name: measurements_id_seq; Type: SEQUENCE; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE SEQUENCE macrostrat.measurements_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE macrostrat.measurements_id_seq OWNER TO "macrostrat-admin";

--
-- Name: measurements_id_seq; Type: SEQUENCE OWNED BY; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER SEQUENCE macrostrat.measurements_id_seq OWNED BY macrostrat.measurements.id;


--
-- Name: measurements_new_id_seq; Type: SEQUENCE; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE SEQUENCE macrostrat.measurements_new_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE macrostrat.measurements_new_id_seq OWNER TO "macrostrat-admin";

--
-- Name: measurements_new_id_seq; Type: SEQUENCE OWNED BY; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER SEQUENCE macrostrat.measurements_new_id_seq OWNED BY macrostrat.measurements.id;


--
-- Name: measuremeta; Type: TABLE; Schema: macrostrat; Owner: macrostrat-admin
--

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


ALTER TABLE macrostrat.measuremeta OWNER TO "macrostrat-admin";

--
-- Name: measuremeta_cols; Type: TABLE; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE TABLE macrostrat.measuremeta_cols (
    id integer NOT NULL,
    col_id integer NOT NULL,
    measuremeta_id integer NOT NULL
);


ALTER TABLE macrostrat.measuremeta_cols OWNER TO "macrostrat-admin";

--
-- Name: measuremeta_cols_id_seq; Type: SEQUENCE; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE SEQUENCE macrostrat.measuremeta_cols_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE macrostrat.measuremeta_cols_id_seq OWNER TO "macrostrat-admin";

--
-- Name: measuremeta_cols_id_seq; Type: SEQUENCE OWNED BY; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER SEQUENCE macrostrat.measuremeta_cols_id_seq OWNED BY macrostrat.measuremeta_cols.id;


--
-- Name: measuremeta_id_seq; Type: SEQUENCE; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE SEQUENCE macrostrat.measuremeta_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE macrostrat.measuremeta_id_seq OWNER TO "macrostrat-admin";

--
-- Name: measuremeta_id_seq; Type: SEQUENCE OWNED BY; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER SEQUENCE macrostrat.measuremeta_id_seq OWNED BY macrostrat.measuremeta.id;


--
-- Name: measuremeta_new_id_seq1; Type: SEQUENCE; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE SEQUENCE macrostrat.measuremeta_new_id_seq1
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE macrostrat.measuremeta_new_id_seq1 OWNER TO "macrostrat-admin";

--
-- Name: measuremeta_new_id_seq1; Type: SEQUENCE OWNED BY; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER SEQUENCE macrostrat.measuremeta_new_id_seq1 OWNED BY macrostrat.measuremeta.id;


--
-- Name: measures; Type: TABLE; Schema: macrostrat; Owner: macrostrat-admin
--

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


ALTER TABLE macrostrat.measures OWNER TO "macrostrat-admin";

--
-- Name: measures_id_seq; Type: SEQUENCE; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE SEQUENCE macrostrat.measures_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE macrostrat.measures_id_seq OWNER TO "macrostrat-admin";

--
-- Name: measures_id_seq; Type: SEQUENCE OWNED BY; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER SEQUENCE macrostrat.measures_id_seq OWNED BY macrostrat.measures.id;


--
-- Name: measures_new_id_seq1; Type: SEQUENCE; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE SEQUENCE macrostrat.measures_new_id_seq1
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE macrostrat.measures_new_id_seq1 OWNER TO "macrostrat-admin";

--
-- Name: measures_new_id_seq1; Type: SEQUENCE OWNED BY; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER SEQUENCE macrostrat.measures_new_id_seq1 OWNED BY macrostrat.measures.id;


--
-- Name: minerals; Type: TABLE; Schema: macrostrat; Owner: macrostrat-admin
--

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


ALTER TABLE macrostrat.minerals OWNER TO "macrostrat-admin";

--
-- Name: offshore_baggage; Type: TABLE; Schema: macrostrat; Owner: macrostrat-admin
--

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


ALTER TABLE macrostrat.offshore_baggage OWNER TO "macrostrat-admin";

--
-- Name: offshore_baggage_units; Type: TABLE; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE TABLE macrostrat.offshore_baggage_units (
    offshore_baggage_id integer NOT NULL,
    unit_id integer NOT NULL,
    unit_lith_id integer NOT NULL,
    unit_lith_sub_id integer NOT NULL,
    col_id integer NOT NULL
);


ALTER TABLE macrostrat.offshore_baggage_units OWNER TO "macrostrat-admin";

--
-- Name: offshore_fossils; Type: TABLE; Schema: macrostrat; Owner: macrostrat-admin
--

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


ALTER TABLE macrostrat.offshore_fossils OWNER TO "macrostrat-admin";

--
-- Name: offshore_hole_ages; Type: TABLE; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE TABLE macrostrat.offshore_hole_ages (
    id integer NOT NULL,
    col_id integer NOT NULL,
    top_depth numeric(7,3) NOT NULL,
    top_core integer,
    bottom_depth numeric(7,3) NOT NULL,
    bottom_core integer,
    interval_id integer NOT NULL
);


ALTER TABLE macrostrat.offshore_hole_ages OWNER TO "macrostrat-admin";

--
-- Name: offshore_hole_ages_id_seq; Type: SEQUENCE; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE SEQUENCE macrostrat.offshore_hole_ages_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE macrostrat.offshore_hole_ages_id_seq OWNER TO "macrostrat-admin";

--
-- Name: offshore_hole_ages_id_seq; Type: SEQUENCE OWNED BY; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER SEQUENCE macrostrat.offshore_hole_ages_id_seq OWNED BY macrostrat.offshore_hole_ages.id;


--
-- Name: offshore_sections; Type: TABLE; Schema: macrostrat; Owner: macrostrat-admin
--

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


ALTER TABLE macrostrat.offshore_sections OWNER TO "macrostrat-admin";

--
-- Name: offshore_sites; Type: TABLE; Schema: macrostrat; Owner: macrostrat-admin
--

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


ALTER TABLE macrostrat.offshore_sites OWNER TO "macrostrat-admin";

--
-- Name: pbdb_collections; Type: TABLE; Schema: macrostrat; Owner: macrostrat-admin
--

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


ALTER TABLE macrostrat.pbdb_collections OWNER TO "macrostrat-admin";

--
-- Name: pbdb_collections_strat_names; Type: TABLE; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE TABLE macrostrat.pbdb_collections_strat_names (
    collection_no integer NOT NULL,
    strat_name_id integer NOT NULL,
    basis_col text
);


ALTER TABLE macrostrat.pbdb_collections_strat_names OWNER TO "macrostrat-admin";

--
-- Name: pbdb_intervals; Type: TABLE; Schema: macrostrat; Owner: macrostrat-admin
--

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


ALTER TABLE macrostrat.pbdb_intervals OWNER TO "macrostrat-admin";

--
-- Name: pbdb_intervals_id_seq; Type: SEQUENCE; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE SEQUENCE macrostrat.pbdb_intervals_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE macrostrat.pbdb_intervals_id_seq OWNER TO "macrostrat-admin";

--
-- Name: pbdb_intervals_id_seq; Type: SEQUENCE OWNED BY; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER SEQUENCE macrostrat.pbdb_intervals_id_seq OWNED BY macrostrat.pbdb_intervals.id;


--
-- Name: pbdb_liths; Type: TABLE; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE TABLE macrostrat.pbdb_liths (
    lith_id integer NOT NULL,
    lith character varying(100) NOT NULL,
    pbdb_lith character varying(100) NOT NULL
);


ALTER TABLE macrostrat.pbdb_liths OWNER TO "macrostrat-admin";

--
-- Name: pbdb_matches; Type: TABLE; Schema: macrostrat; Owner: macrostrat-admin
--

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


ALTER TABLE macrostrat.pbdb_matches OWNER TO "macrostrat-admin";

--
-- Name: pbdb_matches_id_seq; Type: SEQUENCE; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE SEQUENCE macrostrat.pbdb_matches_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE macrostrat.pbdb_matches_id_seq OWNER TO "macrostrat-admin";

--
-- Name: pbdb_matches_id_seq; Type: SEQUENCE OWNED BY; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER SEQUENCE macrostrat.pbdb_matches_id_seq OWNED BY macrostrat.pbdb_matches.id;


--
-- Name: places; Type: TABLE; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE TABLE macrostrat.places (
    place_id bigint NOT NULL,
    name text,
    abbrev text,
    postal text,
    country text,
    country_abbrev text,
    geom public.geometry
);


ALTER TABLE macrostrat.places OWNER TO "macrostrat-admin";

--
-- Name: places_place_id_seq; Type: SEQUENCE; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE SEQUENCE macrostrat.places_place_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE macrostrat.places_place_id_seq OWNER TO "macrostrat-admin";

--
-- Name: places_place_id_seq; Type: SEQUENCE OWNED BY; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER SEQUENCE macrostrat.places_place_id_seq OWNED BY macrostrat.places.place_id;


--
-- Name: projects_id_seq; Type: SEQUENCE; Schema: macrostrat; Owner: macrostrat
--

CREATE SEQUENCE macrostrat.projects_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE macrostrat.projects_id_seq OWNER TO macrostrat;

--
-- Name: projects_id_seq; Type: SEQUENCE OWNED BY; Schema: macrostrat; Owner: macrostrat
--

ALTER SEQUENCE macrostrat.projects_id_seq OWNED BY macrostrat.projects.id;


--
-- Name: projects_tree; Type: TABLE; Schema: macrostrat; Owner: macrostrat
--

CREATE TABLE macrostrat.projects_tree (
    id integer NOT NULL,
    parent_id integer NOT NULL,
    child_id integer NOT NULL
);


ALTER TABLE macrostrat.projects_tree OWNER TO macrostrat;

--
-- Name: projects_tree_id_seq; Type: SEQUENCE; Schema: macrostrat; Owner: macrostrat
--

ALTER TABLE macrostrat.projects_tree ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME macrostrat.projects_tree_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: refs; Type: TABLE; Schema: macrostrat; Owner: macrostrat-admin
--

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


ALTER TABLE macrostrat.refs OWNER TO "macrostrat-admin";

--
-- Name: refs_id_seq; Type: SEQUENCE; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE SEQUENCE macrostrat.refs_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE macrostrat.refs_id_seq OWNER TO "macrostrat-admin";

--
-- Name: refs_id_seq; Type: SEQUENCE OWNED BY; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER SEQUENCE macrostrat.refs_id_seq OWNED BY macrostrat.refs.id;


--
-- Name: rockd_features; Type: TABLE; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE TABLE macrostrat.rockd_features (
    id integer NOT NULL,
    feature character varying(100) NOT NULL,
    feature_type macrostrat.rockd_features_feature_type NOT NULL,
    feature_class macrostrat.rockd_features_feature_class NOT NULL
);


ALTER TABLE macrostrat.rockd_features OWNER TO "macrostrat-admin";

--
-- Name: rockd_features_id_seq; Type: SEQUENCE; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE SEQUENCE macrostrat.rockd_features_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE macrostrat.rockd_features_id_seq OWNER TO "macrostrat-admin";

--
-- Name: rockd_features_id_seq; Type: SEQUENCE OWNED BY; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER SEQUENCE macrostrat.rockd_features_id_seq OWNED BY macrostrat.rockd_features.id;


--
-- Name: ronov_sediment; Type: TABLE; Schema: macrostrat; Owner: macrostrat-admin
--

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


ALTER TABLE macrostrat.ronov_sediment OWNER TO "macrostrat-admin";

--
-- Name: sections; Type: TABLE; Schema: macrostrat; Owner: macrostrat
--

CREATE TABLE macrostrat.sections (
    id bigint NOT NULL,
    col_id integer NOT NULL,
    fo integer DEFAULT 0 NOT NULL,
    fo_h smallint NOT NULL,
    lo integer DEFAULT 0 NOT NULL,
    lo_h smallint NOT NULL
);


ALTER TABLE macrostrat.sections OWNER TO macrostrat;

--
-- Name: TABLE sections; Type: COMMENT; Schema: macrostrat; Owner: macrostrat
--

COMMENT ON TABLE macrostrat.sections IS 'Last updated from MariaDB - 2023-07-28 18:11';


--
-- Name: sections_id_seq; Type: SEQUENCE; Schema: macrostrat; Owner: macrostrat
--

CREATE SEQUENCE macrostrat.sections_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE macrostrat.sections_id_seq OWNER TO macrostrat;

--
-- Name: sections_id_seq; Type: SEQUENCE OWNED BY; Schema: macrostrat; Owner: macrostrat
--

ALTER SEQUENCE macrostrat.sections_id_seq OWNED BY macrostrat.sections.id;


--
-- Name: stats; Type: TABLE; Schema: macrostrat; Owner: macrostrat-admin
--

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


ALTER TABLE macrostrat.stats OWNER TO "macrostrat-admin";

--
-- Name: strat_name_footprints; Type: TABLE; Schema: macrostrat; Owner: macrostrat-admin
--

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


ALTER TABLE macrostrat.strat_name_footprints OWNER TO "macrostrat-admin";

--
-- Name: strat_names; Type: TABLE; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE TABLE macrostrat.strat_names (
    id integer NOT NULL,
    old_id integer NOT NULL,
    concept_id integer,
    strat_name character varying(75) DEFAULT NULL::character varying,
    rank macrostrat.strat_names_rank,
    old_strat_name_id integer NOT NULL,
    ref_id integer,
    places text,
    orig_id integer NOT NULL
);


ALTER TABLE macrostrat.strat_names OWNER TO "macrostrat-admin";

--
-- Name: strat_names_id_seq; Type: SEQUENCE; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE SEQUENCE macrostrat.strat_names_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE macrostrat.strat_names_id_seq OWNER TO "macrostrat-admin";

--
-- Name: strat_names_id_seq; Type: SEQUENCE OWNED BY; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER SEQUENCE macrostrat.strat_names_id_seq OWNED BY macrostrat.strat_names.id;


--
-- Name: strat_names_lookup; Type: TABLE; Schema: macrostrat; Owner: macrostrat-admin
--

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


ALTER TABLE macrostrat.strat_names_lookup OWNER TO "macrostrat-admin";

--
-- Name: strat_names_meta; Type: TABLE; Schema: macrostrat; Owner: macrostrat-admin
--

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
    ref_id integer NOT NULL
);


ALTER TABLE macrostrat.strat_names_meta OWNER TO "macrostrat-admin";

--
-- Name: strat_names_meta_concept_id_seq; Type: SEQUENCE; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE SEQUENCE macrostrat.strat_names_meta_concept_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE macrostrat.strat_names_meta_concept_id_seq OWNER TO "macrostrat-admin";

--
-- Name: strat_names_meta_concept_id_seq; Type: SEQUENCE OWNED BY; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER SEQUENCE macrostrat.strat_names_meta_concept_id_seq OWNED BY macrostrat.strat_names_meta.concept_id;


--
-- Name: strat_names_new_id_seq; Type: SEQUENCE; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE SEQUENCE macrostrat.strat_names_new_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE macrostrat.strat_names_new_id_seq OWNER TO "macrostrat-admin";

--
-- Name: strat_names_new_id_seq; Type: SEQUENCE OWNED BY; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER SEQUENCE macrostrat.strat_names_new_id_seq OWNED BY macrostrat.strat_names.id;


--
-- Name: strat_names_places; Type: TABLE; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE TABLE macrostrat.strat_names_places (
    strat_name_id integer NOT NULL,
    place_id integer NOT NULL
);


ALTER TABLE macrostrat.strat_names_places OWNER TO "macrostrat-admin";

--
-- Name: strat_tree; Type: TABLE; Schema: macrostrat; Owner: macrostrat_admin
--

CREATE TABLE macrostrat.strat_tree (
    id integer,
    parent integer,
    rel macrostrat.strat_tree_rel,
    child integer,
    ref_id integer,
    check_me smallint
);


ALTER TABLE macrostrat.strat_tree OWNER TO macrostrat_admin;

--
-- Name: structure_atts; Type: TABLE; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE TABLE macrostrat.structure_atts (
    id bigint NOT NULL,
    structure_att character varying(100) NOT NULL,
    att_type macrostrat.structure_atts_att_type,
    att_class macrostrat.structure_atts_att_class
);


ALTER TABLE macrostrat.structure_atts OWNER TO "macrostrat-admin";

--
-- Name: structure_atts_id_seq; Type: SEQUENCE; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE SEQUENCE macrostrat.structure_atts_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE macrostrat.structure_atts_id_seq OWNER TO "macrostrat-admin";

--
-- Name: structure_atts_id_seq; Type: SEQUENCE OWNED BY; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER SEQUENCE macrostrat.structure_atts_id_seq OWNED BY macrostrat.structure_atts.id;


--
-- Name: structures; Type: TABLE; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE TABLE macrostrat.structures (
    id integer NOT NULL,
    structure character varying(100) NOT NULL,
    structure_group macrostrat.structures_structure_group,
    structure_type macrostrat.structures_structure_type NOT NULL,
    structure_class macrostrat.structures_structure_class NOT NULL
);


ALTER TABLE macrostrat.structures OWNER TO "macrostrat-admin";

--
-- Name: structures_id_seq; Type: SEQUENCE; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE SEQUENCE macrostrat.structures_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE macrostrat.structures_id_seq OWNER TO "macrostrat-admin";

--
-- Name: structures_id_seq; Type: SEQUENCE OWNED BY; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER SEQUENCE macrostrat.structures_id_seq OWNED BY macrostrat.structures.id;


--
-- Name: tectonics; Type: TABLE; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE TABLE macrostrat.tectonics (
    id integer NOT NULL,
    basin_type character varying(100) NOT NULL,
    basin_setting macrostrat.tectonics_basin_setting NOT NULL
);


ALTER TABLE macrostrat.tectonics OWNER TO "macrostrat-admin";

--
-- Name: tectonics_id_seq; Type: SEQUENCE; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE SEQUENCE macrostrat.tectonics_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE macrostrat.tectonics_id_seq OWNER TO "macrostrat-admin";

--
-- Name: tectonics_id_seq; Type: SEQUENCE OWNED BY; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER SEQUENCE macrostrat.tectonics_id_seq OWNED BY macrostrat.tectonics.id;


--
-- Name: temp_areas; Type: TABLE; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE TABLE macrostrat.temp_areas (
    areas double precision NOT NULL,
    col_id integer NOT NULL
);


ALTER TABLE macrostrat.temp_areas OWNER TO "macrostrat-admin";

--
-- Name: timescales; Type: TABLE; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE TABLE macrostrat.timescales (
    id integer NOT NULL,
    timescale character varying(255) DEFAULT NULL::character varying,
    ref_id integer NOT NULL
);


ALTER TABLE macrostrat.timescales OWNER TO "macrostrat-admin";

--
-- Name: timescales_id_seq; Type: SEQUENCE; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE SEQUENCE macrostrat.timescales_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE macrostrat.timescales_id_seq OWNER TO "macrostrat-admin";

--
-- Name: timescales_id_seq; Type: SEQUENCE OWNED BY; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER SEQUENCE macrostrat.timescales_id_seq OWNED BY macrostrat.timescales.id;


--
-- Name: timescales_intervals; Type: TABLE; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE TABLE macrostrat.timescales_intervals (
    timescale_id integer NOT NULL,
    interval_id integer NOT NULL
);


ALTER TABLE macrostrat.timescales_intervals OWNER TO "macrostrat-admin";

--
-- Name: uniquedatafiles2; Type: TABLE; Schema: macrostrat; Owner: macrostrat-admin
--

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


ALTER TABLE macrostrat.uniquedatafiles2 OWNER TO "macrostrat-admin";

--
-- Name: uniquedatafiles2_id_seq; Type: SEQUENCE; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE SEQUENCE macrostrat.uniquedatafiles2_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE macrostrat.uniquedatafiles2_id_seq OWNER TO "macrostrat-admin";

--
-- Name: uniquedatafiles2_id_seq; Type: SEQUENCE OWNED BY; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER SEQUENCE macrostrat.uniquedatafiles2_id_seq OWNED BY macrostrat.uniquedatafiles2.id;


--
-- Name: unit_boundaries; Type: TABLE; Schema: macrostrat; Owner: macrostrat
--

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

--
-- Name: unit_boundaries_backup; Type: TABLE; Schema: macrostrat; Owner: macrostrat-admin
--

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


ALTER TABLE macrostrat.unit_boundaries_backup OWNER TO "macrostrat-admin";

--
-- Name: unit_boundaries_backup_id_seq; Type: SEQUENCE; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE SEQUENCE macrostrat.unit_boundaries_backup_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE macrostrat.unit_boundaries_backup_id_seq OWNER TO "macrostrat-admin";

--
-- Name: unit_boundaries_backup_id_seq; Type: SEQUENCE OWNED BY; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER SEQUENCE macrostrat.unit_boundaries_backup_id_seq OWNED BY macrostrat.unit_boundaries_backup.id;


--
-- Name: unit_boundaries_id_seq; Type: SEQUENCE; Schema: macrostrat; Owner: macrostrat
--

CREATE SEQUENCE macrostrat.unit_boundaries_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE macrostrat.unit_boundaries_id_seq OWNER TO macrostrat;

--
-- Name: unit_boundaries_id_seq; Type: SEQUENCE OWNED BY; Schema: macrostrat; Owner: macrostrat
--

ALTER SEQUENCE macrostrat.unit_boundaries_id_seq OWNED BY macrostrat.unit_boundaries.id;


--
-- Name: unit_boundaries_scratch; Type: TABLE; Schema: macrostrat; Owner: macrostrat-admin
--

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


ALTER TABLE macrostrat.unit_boundaries_scratch OWNER TO "macrostrat-admin";

--
-- Name: unit_boundaries_scratch_id_seq; Type: SEQUENCE; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE SEQUENCE macrostrat.unit_boundaries_scratch_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE macrostrat.unit_boundaries_scratch_id_seq OWNER TO "macrostrat-admin";

--
-- Name: unit_boundaries_scratch_id_seq; Type: SEQUENCE OWNED BY; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER SEQUENCE macrostrat.unit_boundaries_scratch_id_seq OWNED BY macrostrat.unit_boundaries_scratch.id;


--
-- Name: unit_boundaries_scratch_old; Type: TABLE; Schema: macrostrat; Owner: macrostrat-admin
--

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


ALTER TABLE macrostrat.unit_boundaries_scratch_old OWNER TO "macrostrat-admin";

--
-- Name: unit_boundaries_scratch_old_id_seq; Type: SEQUENCE; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE SEQUENCE macrostrat.unit_boundaries_scratch_old_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE macrostrat.unit_boundaries_scratch_old_id_seq OWNER TO "macrostrat-admin";

--
-- Name: unit_boundaries_scratch_old_id_seq; Type: SEQUENCE OWNED BY; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER SEQUENCE macrostrat.unit_boundaries_scratch_old_id_seq OWNED BY macrostrat.unit_boundaries_scratch_old.id;


--
-- Name: unit_contacts; Type: TABLE; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE TABLE macrostrat.unit_contacts (
    id integer NOT NULL,
    unit_id integer NOT NULL,
    old_contact macrostrat.unit_contacts_old_contact NOT NULL,
    contact macrostrat.unit_contacts_contact NOT NULL,
    old_with_unit integer NOT NULL,
    with_unit integer NOT NULL
);


ALTER TABLE macrostrat.unit_contacts OWNER TO "macrostrat-admin";

--
-- Name: unit_contacts_id_seq; Type: SEQUENCE; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE SEQUENCE macrostrat.unit_contacts_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE macrostrat.unit_contacts_id_seq OWNER TO "macrostrat-admin";

--
-- Name: unit_contacts_id_seq; Type: SEQUENCE OWNED BY; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER SEQUENCE macrostrat.unit_contacts_id_seq OWNED BY macrostrat.unit_contacts.id;


--
-- Name: unit_dates; Type: TABLE; Schema: macrostrat; Owner: macrostrat-admin
--

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


ALTER TABLE macrostrat.unit_dates OWNER TO "macrostrat-admin";

--
-- Name: unit_dates_id_seq; Type: SEQUENCE; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE SEQUENCE macrostrat.unit_dates_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE macrostrat.unit_dates_id_seq OWNER TO "macrostrat-admin";

--
-- Name: unit_dates_id_seq; Type: SEQUENCE OWNED BY; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER SEQUENCE macrostrat.unit_dates_id_seq OWNED BY macrostrat.unit_dates.id;


--
-- Name: unit_econs; Type: TABLE; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE TABLE macrostrat.unit_econs (
    id integer NOT NULL,
    unit_id integer NOT NULL,
    econ_id integer NOT NULL,
    ref_id integer NOT NULL,
    date_mod timestamp with time zone
);


ALTER TABLE macrostrat.unit_econs OWNER TO "macrostrat-admin";

--
-- Name: unit_econs_id_seq; Type: SEQUENCE; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE SEQUENCE macrostrat.unit_econs_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE macrostrat.unit_econs_id_seq OWNER TO "macrostrat-admin";

--
-- Name: unit_econs_id_seq; Type: SEQUENCE OWNED BY; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER SEQUENCE macrostrat.unit_econs_id_seq OWNED BY macrostrat.unit_econs.id;


--
-- Name: unit_environs; Type: TABLE; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE TABLE macrostrat.unit_environs (
    id integer NOT NULL,
    unit_id integer NOT NULL,
    environ_id integer NOT NULL,
    f integer,
    l integer,
    ref_id integer DEFAULT 1,
    date_mod timestamp with time zone
);


ALTER TABLE macrostrat.unit_environs OWNER TO "macrostrat-admin";

--
-- Name: unit_environs_id_seq; Type: SEQUENCE; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE SEQUENCE macrostrat.unit_environs_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE macrostrat.unit_environs_id_seq OWNER TO "macrostrat-admin";

--
-- Name: unit_environs_id_seq; Type: SEQUENCE OWNED BY; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER SEQUENCE macrostrat.unit_environs_id_seq OWNED BY macrostrat.unit_environs.id;


--
-- Name: unit_equiv; Type: TABLE; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE TABLE macrostrat.unit_equiv (
    id integer NOT NULL,
    unit_id integer NOT NULL,
    new_unit_id integer NOT NULL
);


ALTER TABLE macrostrat.unit_equiv OWNER TO "macrostrat-admin";

--
-- Name: unit_equiv_id_seq; Type: SEQUENCE; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE SEQUENCE macrostrat.unit_equiv_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE macrostrat.unit_equiv_id_seq OWNER TO "macrostrat-admin";

--
-- Name: unit_equiv_id_seq; Type: SEQUENCE OWNED BY; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER SEQUENCE macrostrat.unit_equiv_id_seq OWNED BY macrostrat.unit_equiv.id;


--
-- Name: unit_lith_atts; Type: TABLE; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE TABLE macrostrat.unit_lith_atts (
    id integer NOT NULL,
    unit_lith_id integer,
    lith_att_id integer,
    ref_id integer,
    date_mod text
);


ALTER TABLE macrostrat.unit_lith_atts OWNER TO "macrostrat-admin";

--
-- Name: unit_liths; Type: TABLE; Schema: macrostrat; Owner: macrostrat-admin
--

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


ALTER TABLE macrostrat.unit_liths OWNER TO "macrostrat-admin";

--
-- Name: unit_liths_atts; Type: TABLE; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE TABLE macrostrat.unit_liths_atts (
    id integer NOT NULL,
    unit_lith_id integer NOT NULL,
    lith_att_id integer NOT NULL,
    ref_id integer NOT NULL,
    date_mod timestamp with time zone
);


ALTER TABLE macrostrat.unit_liths_atts OWNER TO "macrostrat-admin";

--
-- Name: unit_liths_atts_id_seq; Type: SEQUENCE; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE SEQUENCE macrostrat.unit_liths_atts_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE macrostrat.unit_liths_atts_id_seq OWNER TO "macrostrat-admin";

--
-- Name: unit_liths_atts_id_seq; Type: SEQUENCE OWNED BY; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER SEQUENCE macrostrat.unit_liths_atts_id_seq OWNED BY macrostrat.unit_liths_atts.id;


--
-- Name: unit_liths_id_seq; Type: SEQUENCE; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE SEQUENCE macrostrat.unit_liths_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE macrostrat.unit_liths_id_seq OWNER TO "macrostrat-admin";

--
-- Name: unit_liths_id_seq; Type: SEQUENCE OWNED BY; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER SEQUENCE macrostrat.unit_liths_id_seq OWNED BY macrostrat.unit_liths.id;


--
-- Name: unit_measures; Type: TABLE; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE TABLE macrostrat.unit_measures (
    id integer NOT NULL,
    measuremeta_id integer NOT NULL,
    unit_id integer NOT NULL,
    strat_name_id integer NOT NULL,
    match_basis character varying(10) NOT NULL,
    rel_position numeric(6,5) DEFAULT NULL::numeric
);


ALTER TABLE macrostrat.unit_measures OWNER TO "macrostrat-admin";

--
-- Name: unit_measures_id_seq; Type: SEQUENCE; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE SEQUENCE macrostrat.unit_measures_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE macrostrat.unit_measures_id_seq OWNER TO "macrostrat-admin";

--
-- Name: unit_measures_id_seq; Type: SEQUENCE OWNED BY; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER SEQUENCE macrostrat.unit_measures_id_seq OWNED BY macrostrat.unit_measures.id;


--
-- Name: unit_measures_new_id_seq; Type: SEQUENCE; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE SEQUENCE macrostrat.unit_measures_new_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE macrostrat.unit_measures_new_id_seq OWNER TO "macrostrat-admin";

--
-- Name: unit_measures_new_id_seq; Type: SEQUENCE OWNED BY; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER SEQUENCE macrostrat.unit_measures_new_id_seq OWNED BY macrostrat.unit_measures.id;


--
-- Name: unit_measures_pbdb; Type: TABLE; Schema: macrostrat; Owner: macrostrat-admin
--

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


ALTER TABLE macrostrat.unit_measures_pbdb OWNER TO "macrostrat-admin";

--
-- Name: unit_notes; Type: TABLE; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE TABLE macrostrat.unit_notes (
    id integer NOT NULL,
    notes text NOT NULL,
    unit_id integer NOT NULL,
    date_mod timestamp with time zone
);


ALTER TABLE macrostrat.unit_notes OWNER TO "macrostrat-admin";

--
-- Name: unit_notes_id_seq; Type: SEQUENCE; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE SEQUENCE macrostrat.unit_notes_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE macrostrat.unit_notes_id_seq OWNER TO "macrostrat-admin";

--
-- Name: unit_notes_id_seq; Type: SEQUENCE OWNED BY; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER SEQUENCE macrostrat.unit_notes_id_seq OWNED BY macrostrat.unit_notes.id;


--
-- Name: unit_seq_strat; Type: TABLE; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE TABLE macrostrat.unit_seq_strat (
    id integer NOT NULL,
    unit_id integer NOT NULL,
    seq_strat macrostrat.unit_seq_strat_seq_strat NOT NULL,
    seq_order macrostrat.unit_seq_strat_seq_order NOT NULL
);


ALTER TABLE macrostrat.unit_seq_strat OWNER TO "macrostrat-admin";

--
-- Name: unit_seq_strat_id_seq; Type: SEQUENCE; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE SEQUENCE macrostrat.unit_seq_strat_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE macrostrat.unit_seq_strat_id_seq OWNER TO "macrostrat-admin";

--
-- Name: unit_seq_strat_id_seq; Type: SEQUENCE OWNED BY; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER SEQUENCE macrostrat.unit_seq_strat_id_seq OWNED BY macrostrat.unit_seq_strat.id;


--
-- Name: unit_strat_names; Type: TABLE; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE TABLE macrostrat.unit_strat_names (
    id integer NOT NULL,
    unit_id integer NOT NULL,
    strat_name_id integer NOT NULL,
    old_strat_name_id integer NOT NULL
);


ALTER TABLE macrostrat.unit_strat_names OWNER TO "macrostrat-admin";

--
-- Name: unit_strat_names_id_seq; Type: SEQUENCE; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE SEQUENCE macrostrat.unit_strat_names_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE macrostrat.unit_strat_names_id_seq OWNER TO "macrostrat-admin";

--
-- Name: unit_strat_names_id_seq; Type: SEQUENCE OWNED BY; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER SEQUENCE macrostrat.unit_strat_names_id_seq OWNED BY macrostrat.unit_strat_names.id;


--
-- Name: unit_strat_names_new_id_seq1; Type: SEQUENCE; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE SEQUENCE macrostrat.unit_strat_names_new_id_seq1
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE macrostrat.unit_strat_names_new_id_seq1 OWNER TO "macrostrat-admin";

--
-- Name: unit_strat_names_new_id_seq1; Type: SEQUENCE OWNED BY; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER SEQUENCE macrostrat.unit_strat_names_new_id_seq1 OWNED BY macrostrat.unit_strat_names.id;


--
-- Name: unit_tectonics; Type: TABLE; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE TABLE macrostrat.unit_tectonics (
    id integer NOT NULL,
    unit_id integer NOT NULL,
    tectonic_id integer NOT NULL
);


ALTER TABLE macrostrat.unit_tectonics OWNER TO "macrostrat-admin";

--
-- Name: unit_tectonics_id_seq; Type: SEQUENCE; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE SEQUENCE macrostrat.unit_tectonics_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE macrostrat.unit_tectonics_id_seq OWNER TO "macrostrat-admin";

--
-- Name: unit_tectonics_id_seq; Type: SEQUENCE OWNED BY; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER SEQUENCE macrostrat.unit_tectonics_id_seq OWNED BY macrostrat.unit_tectonics.id;


--
-- Name: units; Type: TABLE; Schema: macrostrat; Owner: macrostrat-admin
--

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


ALTER TABLE macrostrat.units OWNER TO "macrostrat-admin";

--
-- Name: units_datafiles; Type: TABLE; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE TABLE macrostrat.units_datafiles (
    unit_id integer NOT NULL,
    datafile_id integer NOT NULL
);


ALTER TABLE macrostrat.units_datafiles OWNER TO "macrostrat-admin";

--
-- Name: units_id_seq; Type: SEQUENCE; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE SEQUENCE macrostrat.units_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE macrostrat.units_id_seq OWNER TO "macrostrat-admin";

--
-- Name: units_id_seq; Type: SEQUENCE OWNED BY; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER SEQUENCE macrostrat.units_id_seq OWNED BY macrostrat.units.id;


--
-- Name: units_sections; Type: TABLE; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE TABLE macrostrat.units_sections (
    id integer NOT NULL,
    unit_id integer NOT NULL,
    section_id integer NOT NULL,
    col_id integer NOT NULL
);


ALTER TABLE macrostrat.units_sections OWNER TO "macrostrat-admin";

--
-- Name: units_sections_id_seq; Type: SEQUENCE; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE SEQUENCE macrostrat.units_sections_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE macrostrat.units_sections_id_seq OWNER TO "macrostrat-admin";

--
-- Name: units_sections_id_seq; Type: SEQUENCE OWNED BY; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER SEQUENCE macrostrat.units_sections_id_seq OWNED BY macrostrat.units_sections.id;


--
-- Name: units_sections_new_id_seq; Type: SEQUENCE; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE SEQUENCE macrostrat.units_sections_new_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE macrostrat.units_sections_new_id_seq OWNER TO "macrostrat-admin";

--
-- Name: units_sections_new_id_seq; Type: SEQUENCE OWNED BY; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER SEQUENCE macrostrat.units_sections_new_id_seq OWNED BY macrostrat.units_sections.id;


--
-- Name: col_areas id; Type: DEFAULT; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER TABLE ONLY macrostrat.col_areas ALTER COLUMN id SET DEFAULT nextval('macrostrat.col_areas_id_seq'::regclass);


--
-- Name: col_equiv id; Type: DEFAULT; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER TABLE ONLY macrostrat.col_equiv ALTER COLUMN id SET DEFAULT nextval('macrostrat.col_equiv_id_seq'::regclass);


--
-- Name: col_groups id; Type: DEFAULT; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER TABLE ONLY macrostrat.col_groups ALTER COLUMN id SET DEFAULT nextval('macrostrat.col_groups_id_seq'::regclass);


--
-- Name: col_notes id; Type: DEFAULT; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER TABLE ONLY macrostrat.col_notes ALTER COLUMN id SET DEFAULT nextval('macrostrat.col_notes_id_seq'::regclass);


--
-- Name: col_refs id; Type: DEFAULT; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER TABLE ONLY macrostrat.col_refs ALTER COLUMN id SET DEFAULT nextval('macrostrat.col_refs_id_seq'::regclass);


--
-- Name: cols id; Type: DEFAULT; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER TABLE ONLY macrostrat.cols ALTER COLUMN id SET DEFAULT nextval('macrostrat.cols_id_seq'::regclass);


--
-- Name: econs id; Type: DEFAULT; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER TABLE ONLY macrostrat.econs ALTER COLUMN id SET DEFAULT nextval('macrostrat.econs_id_seq'::regclass);


--
-- Name: environs id; Type: DEFAULT; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER TABLE ONLY macrostrat.environs ALTER COLUMN id SET DEFAULT nextval('macrostrat.environs_id_seq'::regclass);


--
-- Name: intervals id; Type: DEFAULT; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER TABLE ONLY macrostrat.intervals ALTER COLUMN id SET DEFAULT nextval('macrostrat.intervals_new_id_seq1'::regclass);


--
-- Name: lith_atts id; Type: DEFAULT; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER TABLE ONLY macrostrat.lith_atts ALTER COLUMN id SET DEFAULT nextval('macrostrat.lith_atts_id_seq'::regclass);


--
-- Name: liths id; Type: DEFAULT; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER TABLE ONLY macrostrat.liths ALTER COLUMN id SET DEFAULT nextval('macrostrat.liths_id_seq'::regclass);


--
-- Name: measurements id; Type: DEFAULT; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER TABLE ONLY macrostrat.measurements ALTER COLUMN id SET DEFAULT nextval('macrostrat.measurements_new_id_seq'::regclass);


--
-- Name: measuremeta id; Type: DEFAULT; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER TABLE ONLY macrostrat.measuremeta ALTER COLUMN id SET DEFAULT nextval('macrostrat.measuremeta_new_id_seq1'::regclass);


--
-- Name: measuremeta_cols id; Type: DEFAULT; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER TABLE ONLY macrostrat.measuremeta_cols ALTER COLUMN id SET DEFAULT nextval('macrostrat.measuremeta_cols_id_seq'::regclass);


--
-- Name: measures id; Type: DEFAULT; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER TABLE ONLY macrostrat.measures ALTER COLUMN id SET DEFAULT nextval('macrostrat.measures_new_id_seq1'::regclass);


--
-- Name: offshore_hole_ages id; Type: DEFAULT; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER TABLE ONLY macrostrat.offshore_hole_ages ALTER COLUMN id SET DEFAULT nextval('macrostrat.offshore_hole_ages_id_seq'::regclass);


--
-- Name: pbdb_intervals id; Type: DEFAULT; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER TABLE ONLY macrostrat.pbdb_intervals ALTER COLUMN id SET DEFAULT nextval('macrostrat.pbdb_intervals_id_seq'::regclass);


--
-- Name: pbdb_matches id; Type: DEFAULT; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER TABLE ONLY macrostrat.pbdb_matches ALTER COLUMN id SET DEFAULT nextval('macrostrat.pbdb_matches_id_seq'::regclass);


--
-- Name: places place_id; Type: DEFAULT; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER TABLE ONLY macrostrat.places ALTER COLUMN place_id SET DEFAULT nextval('macrostrat.places_place_id_seq'::regclass);


--
-- Name: projects id; Type: DEFAULT; Schema: macrostrat; Owner: macrostrat
--

ALTER TABLE ONLY macrostrat.projects ALTER COLUMN id SET DEFAULT nextval('macrostrat.projects_id_seq'::regclass);


--
-- Name: refs id; Type: DEFAULT; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER TABLE ONLY macrostrat.refs ALTER COLUMN id SET DEFAULT nextval('macrostrat.refs_id_seq'::regclass);


--
-- Name: rockd_features id; Type: DEFAULT; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER TABLE ONLY macrostrat.rockd_features ALTER COLUMN id SET DEFAULT nextval('macrostrat.rockd_features_id_seq'::regclass);


--
-- Name: sections id; Type: DEFAULT; Schema: macrostrat; Owner: macrostrat
--

ALTER TABLE ONLY macrostrat.sections ALTER COLUMN id SET DEFAULT nextval('macrostrat.sections_id_seq'::regclass);


--
-- Name: strat_names id; Type: DEFAULT; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER TABLE ONLY macrostrat.strat_names ALTER COLUMN id SET DEFAULT nextval('macrostrat.strat_names_new_id_seq'::regclass);


--
-- Name: strat_names_meta concept_id; Type: DEFAULT; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER TABLE ONLY macrostrat.strat_names_meta ALTER COLUMN concept_id SET DEFAULT nextval('macrostrat.strat_names_meta_concept_id_seq'::regclass);


--
-- Name: structure_atts id; Type: DEFAULT; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER TABLE ONLY macrostrat.structure_atts ALTER COLUMN id SET DEFAULT nextval('macrostrat.structure_atts_id_seq'::regclass);


--
-- Name: structures id; Type: DEFAULT; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER TABLE ONLY macrostrat.structures ALTER COLUMN id SET DEFAULT nextval('macrostrat.structures_id_seq'::regclass);


--
-- Name: tectonics id; Type: DEFAULT; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER TABLE ONLY macrostrat.tectonics ALTER COLUMN id SET DEFAULT nextval('macrostrat.tectonics_id_seq'::regclass);


--
-- Name: timescales id; Type: DEFAULT; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER TABLE ONLY macrostrat.timescales ALTER COLUMN id SET DEFAULT nextval('macrostrat.timescales_id_seq'::regclass);


--
-- Name: uniquedatafiles2 id; Type: DEFAULT; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER TABLE ONLY macrostrat.uniquedatafiles2 ALTER COLUMN id SET DEFAULT nextval('macrostrat.uniquedatafiles2_id_seq'::regclass);


--
-- Name: unit_boundaries id; Type: DEFAULT; Schema: macrostrat; Owner: macrostrat
--

ALTER TABLE ONLY macrostrat.unit_boundaries ALTER COLUMN id SET DEFAULT nextval('macrostrat.unit_boundaries_id_seq'::regclass);


--
-- Name: unit_boundaries_backup id; Type: DEFAULT; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER TABLE ONLY macrostrat.unit_boundaries_backup ALTER COLUMN id SET DEFAULT nextval('macrostrat.unit_boundaries_backup_id_seq'::regclass);


--
-- Name: unit_boundaries_scratch id; Type: DEFAULT; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER TABLE ONLY macrostrat.unit_boundaries_scratch ALTER COLUMN id SET DEFAULT nextval('macrostrat.unit_boundaries_scratch_id_seq'::regclass);


--
-- Name: unit_boundaries_scratch_old id; Type: DEFAULT; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER TABLE ONLY macrostrat.unit_boundaries_scratch_old ALTER COLUMN id SET DEFAULT nextval('macrostrat.unit_boundaries_scratch_old_id_seq'::regclass);


--
-- Name: unit_contacts id; Type: DEFAULT; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER TABLE ONLY macrostrat.unit_contacts ALTER COLUMN id SET DEFAULT nextval('macrostrat.unit_contacts_id_seq'::regclass);


--
-- Name: unit_dates id; Type: DEFAULT; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER TABLE ONLY macrostrat.unit_dates ALTER COLUMN id SET DEFAULT nextval('macrostrat.unit_dates_id_seq'::regclass);


--
-- Name: unit_econs id; Type: DEFAULT; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER TABLE ONLY macrostrat.unit_econs ALTER COLUMN id SET DEFAULT nextval('macrostrat.unit_econs_id_seq'::regclass);


--
-- Name: unit_environs id; Type: DEFAULT; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER TABLE ONLY macrostrat.unit_environs ALTER COLUMN id SET DEFAULT nextval('macrostrat.unit_environs_id_seq'::regclass);


--
-- Name: unit_equiv id; Type: DEFAULT; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER TABLE ONLY macrostrat.unit_equiv ALTER COLUMN id SET DEFAULT nextval('macrostrat.unit_equiv_id_seq'::regclass);


--
-- Name: unit_liths id; Type: DEFAULT; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER TABLE ONLY macrostrat.unit_liths ALTER COLUMN id SET DEFAULT nextval('macrostrat.unit_liths_id_seq'::regclass);


--
-- Name: unit_liths_atts id; Type: DEFAULT; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER TABLE ONLY macrostrat.unit_liths_atts ALTER COLUMN id SET DEFAULT nextval('macrostrat.unit_liths_atts_id_seq'::regclass);


--
-- Name: unit_measures id; Type: DEFAULT; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER TABLE ONLY macrostrat.unit_measures ALTER COLUMN id SET DEFAULT nextval('macrostrat.unit_measures_new_id_seq'::regclass);


--
-- Name: unit_notes id; Type: DEFAULT; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER TABLE ONLY macrostrat.unit_notes ALTER COLUMN id SET DEFAULT nextval('macrostrat.unit_notes_id_seq'::regclass);


--
-- Name: unit_seq_strat id; Type: DEFAULT; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER TABLE ONLY macrostrat.unit_seq_strat ALTER COLUMN id SET DEFAULT nextval('macrostrat.unit_seq_strat_id_seq'::regclass);


--
-- Name: unit_strat_names id; Type: DEFAULT; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER TABLE ONLY macrostrat.unit_strat_names ALTER COLUMN id SET DEFAULT nextval('macrostrat.unit_strat_names_new_id_seq1'::regclass);


--
-- Name: unit_tectonics id; Type: DEFAULT; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER TABLE ONLY macrostrat.unit_tectonics ALTER COLUMN id SET DEFAULT nextval('macrostrat.unit_tectonics_id_seq'::regclass);


--
-- Name: units id; Type: DEFAULT; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER TABLE ONLY macrostrat.units ALTER COLUMN id SET DEFAULT nextval('macrostrat.units_id_seq'::regclass);


--
-- Name: units_sections id; Type: DEFAULT; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER TABLE ONLY macrostrat.units_sections ALTER COLUMN id SET DEFAULT nextval('macrostrat.units_sections_new_id_seq'::regclass);


--
-- Name: grainsize grainsize_pkey; Type: CONSTRAINT; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER TABLE ONLY macrostrat.grainsize
    ADD CONSTRAINT grainsize_pkey PRIMARY KEY (grain_id);


--
-- Name: canada_lexicon_dump idx_44157002_primary; Type: CONSTRAINT; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER TABLE ONLY macrostrat.canada_lexicon_dump
    ADD CONSTRAINT idx_44157002_primary PRIMARY KEY (strat_unit_id);


--
-- Name: cols idx_44157014_primary; Type: CONSTRAINT; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER TABLE ONLY macrostrat.cols
    ADD CONSTRAINT idx_44157014_primary PRIMARY KEY (id);


--
-- Name: col_areas idx_44157021_primary; Type: CONSTRAINT; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER TABLE ONLY macrostrat.col_areas
    ADD CONSTRAINT idx_44157021_primary PRIMARY KEY (id);


--
-- Name: col_equiv idx_44157034_primary; Type: CONSTRAINT; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER TABLE ONLY macrostrat.col_equiv
    ADD CONSTRAINT idx_44157034_primary PRIMARY KEY (id);


--
-- Name: col_groups idx_44157039_primary; Type: CONSTRAINT; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER TABLE ONLY macrostrat.col_groups
    ADD CONSTRAINT idx_44157039_primary PRIMARY KEY (id);


--
-- Name: col_notes idx_44157044_primary; Type: CONSTRAINT; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER TABLE ONLY macrostrat.col_notes
    ADD CONSTRAINT idx_44157044_primary PRIMARY KEY (id);


--
-- Name: col_refs idx_44157051_primary; Type: CONSTRAINT; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER TABLE ONLY macrostrat.col_refs
    ADD CONSTRAINT idx_44157051_primary PRIMARY KEY (id);


--
-- Name: econs idx_44157059_primary; Type: CONSTRAINT; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER TABLE ONLY macrostrat.econs
    ADD CONSTRAINT idx_44157059_primary PRIMARY KEY (id);


--
-- Name: environs idx_44157064_primary; Type: CONSTRAINT; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER TABLE ONLY macrostrat.environs
    ADD CONSTRAINT idx_44157064_primary PRIMARY KEY (id);


--
-- Name: intervals idx_44157069_primary; Type: CONSTRAINT; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER TABLE ONLY macrostrat.intervals
    ADD CONSTRAINT idx_44157069_primary PRIMARY KEY (id);


--
-- Name: liths idx_44157091_primary; Type: CONSTRAINT; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER TABLE ONLY macrostrat.liths
    ADD CONSTRAINT idx_44157091_primary PRIMARY KEY (id);


--
-- Name: lith_atts idx_44157097_primary; Type: CONSTRAINT; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER TABLE ONLY macrostrat.lith_atts
    ADD CONSTRAINT idx_44157097_primary PRIMARY KEY (id);


--
-- Name: lookup_measurements idx_44157101_primary; Type: CONSTRAINT; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER TABLE ONLY macrostrat.lookup_measurements
    ADD CONSTRAINT idx_44157101_primary PRIMARY KEY (measure_id);


--
-- Name: lookup_strat_names idx_44157111_primary; Type: CONSTRAINT; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER TABLE ONLY macrostrat.lookup_strat_names
    ADD CONSTRAINT idx_44157111_primary PRIMARY KEY (strat_name_id);


--
-- Name: lookup_units idx_44157129_primary; Type: CONSTRAINT; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER TABLE ONLY macrostrat.lookup_units
    ADD CONSTRAINT idx_44157129_primary PRIMARY KEY (unit_id);


--
-- Name: lookup_unit_intervals idx_44157160_primary; Type: CONSTRAINT; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER TABLE ONLY macrostrat.lookup_unit_intervals
    ADD CONSTRAINT idx_44157160_primary PRIMARY KEY (unit_id);


--
-- Name: lookup_unit_liths idx_44157165_primary; Type: CONSTRAINT; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER TABLE ONLY macrostrat.lookup_unit_liths
    ADD CONSTRAINT idx_44157165_primary PRIMARY KEY (unit_id);


--
-- Name: measurements idx_44157171_primary; Type: CONSTRAINT; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER TABLE ONLY macrostrat.measurements
    ADD CONSTRAINT idx_44157171_primary PRIMARY KEY (id);


--
-- Name: measuremeta idx_44157176_primary; Type: CONSTRAINT; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER TABLE ONLY macrostrat.measuremeta
    ADD CONSTRAINT idx_44157176_primary PRIMARY KEY (id);


--
-- Name: measuremeta_cols idx_44157186_primary; Type: CONSTRAINT; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER TABLE ONLY macrostrat.measuremeta_cols
    ADD CONSTRAINT idx_44157186_primary PRIMARY KEY (id);


--
-- Name: measures idx_44157191_primary; Type: CONSTRAINT; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER TABLE ONLY macrostrat.measures
    ADD CONSTRAINT idx_44157191_primary PRIMARY KEY (id);


--
-- Name: minerals idx_44157200_primary; Type: CONSTRAINT; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER TABLE ONLY macrostrat.minerals
    ADD CONSTRAINT idx_44157200_primary PRIMARY KEY (id);


--
-- Name: offshore_baggage idx_44157212_primary; Type: CONSTRAINT; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER TABLE ONLY macrostrat.offshore_baggage
    ADD CONSTRAINT idx_44157212_primary PRIMARY KEY (id);


--
-- Name: offshore_baggage_units idx_44157219_primary; Type: CONSTRAINT; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER TABLE ONLY macrostrat.offshore_baggage_units
    ADD CONSTRAINT idx_44157219_primary PRIMARY KEY (offshore_baggage_id);


--
-- Name: offshore_fossils idx_44157222_primary; Type: CONSTRAINT; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER TABLE ONLY macrostrat.offshore_fossils
    ADD CONSTRAINT idx_44157222_primary PRIMARY KEY (id);


--
-- Name: offshore_hole_ages idx_44157230_primary; Type: CONSTRAINT; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER TABLE ONLY macrostrat.offshore_hole_ages
    ADD CONSTRAINT idx_44157230_primary PRIMARY KEY (id);


--
-- Name: offshore_sites idx_44157237_primary; Type: CONSTRAINT; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER TABLE ONLY macrostrat.offshore_sites
    ADD CONSTRAINT idx_44157237_primary PRIMARY KEY (id);


--
-- Name: pbdb_intervals idx_44157241_primary; Type: CONSTRAINT; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER TABLE ONLY macrostrat.pbdb_intervals
    ADD CONSTRAINT idx_44157241_primary PRIMARY KEY (id);


--
-- Name: pbdb_liths idx_44157250_primary; Type: CONSTRAINT; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER TABLE ONLY macrostrat.pbdb_liths
    ADD CONSTRAINT idx_44157250_primary PRIMARY KEY (lith_id);


--
-- Name: pbdb_matches idx_44157254_primary; Type: CONSTRAINT; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER TABLE ONLY macrostrat.pbdb_matches
    ADD CONSTRAINT idx_44157254_primary PRIMARY KEY (id);


--
-- Name: places idx_44157263_primary; Type: CONSTRAINT; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER TABLE ONLY macrostrat.places
    ADD CONSTRAINT idx_44157263_primary PRIMARY KEY (place_id);


--
-- Name: projects idx_44157270_primary; Type: CONSTRAINT; Schema: macrostrat; Owner: macrostrat
--

ALTER TABLE ONLY macrostrat.projects
    ADD CONSTRAINT idx_44157270_primary PRIMARY KEY (id);


--
-- Name: refs idx_44157277_primary; Type: CONSTRAINT; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER TABLE ONLY macrostrat.refs
    ADD CONSTRAINT idx_44157277_primary PRIMARY KEY (id);


--
-- Name: rockd_features idx_44157286_primary; Type: CONSTRAINT; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER TABLE ONLY macrostrat.rockd_features
    ADD CONSTRAINT idx_44157286_primary PRIMARY KEY (id);


--
-- Name: sections idx_44157294_primary; Type: CONSTRAINT; Schema: macrostrat; Owner: macrostrat
--

ALTER TABLE ONLY macrostrat.sections
    ADD CONSTRAINT idx_44157294_primary PRIMARY KEY (id);


--
-- Name: strat_names idx_44157311_primary; Type: CONSTRAINT; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER TABLE ONLY macrostrat.strat_names
    ADD CONSTRAINT idx_44157311_primary PRIMARY KEY (id);


--
-- Name: strat_names_lookup idx_44157318_primary; Type: CONSTRAINT; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER TABLE ONLY macrostrat.strat_names_lookup
    ADD CONSTRAINT idx_44157318_primary PRIMARY KEY (strat_name_id);


--
-- Name: strat_names_meta idx_44157324_primary; Type: CONSTRAINT; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER TABLE ONLY macrostrat.strat_names_meta
    ADD CONSTRAINT idx_44157324_primary PRIMARY KEY (concept_id);


--
-- Name: structures idx_44157340_primary; Type: CONSTRAINT; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER TABLE ONLY macrostrat.structures
    ADD CONSTRAINT idx_44157340_primary PRIMARY KEY (id);


--
-- Name: structure_atts idx_44157345_primary; Type: CONSTRAINT; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER TABLE ONLY macrostrat.structure_atts
    ADD CONSTRAINT idx_44157345_primary PRIMARY KEY (id);


--
-- Name: tectonics idx_44157350_primary; Type: CONSTRAINT; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER TABLE ONLY macrostrat.tectonics
    ADD CONSTRAINT idx_44157350_primary PRIMARY KEY (id);


--
-- Name: timescales idx_44157358_primary; Type: CONSTRAINT; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER TABLE ONLY macrostrat.timescales
    ADD CONSTRAINT idx_44157358_primary PRIMARY KEY (id);


--
-- Name: timescales_intervals idx_44157363_primary; Type: CONSTRAINT; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER TABLE ONLY macrostrat.timescales_intervals
    ADD CONSTRAINT idx_44157363_primary PRIMARY KEY (timescale_id, interval_id);


--
-- Name: uniquedatafiles2 idx_44157367_primary; Type: CONSTRAINT; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER TABLE ONLY macrostrat.uniquedatafiles2
    ADD CONSTRAINT idx_44157367_primary PRIMARY KEY (id);


--
-- Name: units idx_44157375_primary; Type: CONSTRAINT; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER TABLE ONLY macrostrat.units
    ADD CONSTRAINT idx_44157375_primary PRIMARY KEY (id);


--
-- Name: units_datafiles idx_44157384_primary; Type: CONSTRAINT; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER TABLE ONLY macrostrat.units_datafiles
    ADD CONSTRAINT idx_44157384_primary PRIMARY KEY (unit_id);


--
-- Name: units_sections idx_44157388_primary; Type: CONSTRAINT; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER TABLE ONLY macrostrat.units_sections
    ADD CONSTRAINT idx_44157388_primary PRIMARY KEY (id);


--
-- Name: unit_boundaries idx_44157393_primary; Type: CONSTRAINT; Schema: macrostrat; Owner: macrostrat
--

ALTER TABLE ONLY macrostrat.unit_boundaries
    ADD CONSTRAINT idx_44157393_primary PRIMARY KEY (id);


--
-- Name: unit_boundaries_backup idx_44157404_primary; Type: CONSTRAINT; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER TABLE ONLY macrostrat.unit_boundaries_backup
    ADD CONSTRAINT idx_44157404_primary PRIMARY KEY (id);


--
-- Name: unit_boundaries_scratch idx_44157415_primary; Type: CONSTRAINT; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER TABLE ONLY macrostrat.unit_boundaries_scratch
    ADD CONSTRAINT idx_44157415_primary PRIMARY KEY (id);


--
-- Name: unit_boundaries_scratch_old idx_44157426_primary; Type: CONSTRAINT; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER TABLE ONLY macrostrat.unit_boundaries_scratch_old
    ADD CONSTRAINT idx_44157426_primary PRIMARY KEY (id);


--
-- Name: unit_contacts idx_44157435_primary; Type: CONSTRAINT; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER TABLE ONLY macrostrat.unit_contacts
    ADD CONSTRAINT idx_44157435_primary PRIMARY KEY (id);


--
-- Name: unit_dates idx_44157440_primary; Type: CONSTRAINT; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER TABLE ONLY macrostrat.unit_dates
    ADD CONSTRAINT idx_44157440_primary PRIMARY KEY (id);


--
-- Name: unit_econs idx_44157447_primary; Type: CONSTRAINT; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER TABLE ONLY macrostrat.unit_econs
    ADD CONSTRAINT idx_44157447_primary PRIMARY KEY (id);


--
-- Name: unit_environs idx_44157452_primary; Type: CONSTRAINT; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER TABLE ONLY macrostrat.unit_environs
    ADD CONSTRAINT idx_44157452_primary PRIMARY KEY (id);


--
-- Name: unit_equiv idx_44157458_primary; Type: CONSTRAINT; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER TABLE ONLY macrostrat.unit_equiv
    ADD CONSTRAINT idx_44157458_primary PRIMARY KEY (id);


--
-- Name: unit_liths idx_44157463_primary; Type: CONSTRAINT; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER TABLE ONLY macrostrat.unit_liths
    ADD CONSTRAINT idx_44157463_primary PRIMARY KEY (id);


--
-- Name: unit_liths_atts idx_44157469_primary; Type: CONSTRAINT; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER TABLE ONLY macrostrat.unit_liths_atts
    ADD CONSTRAINT idx_44157469_primary PRIMARY KEY (id);


--
-- Name: unit_measures idx_44157474_primary; Type: CONSTRAINT; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER TABLE ONLY macrostrat.unit_measures
    ADD CONSTRAINT idx_44157474_primary PRIMARY KEY (id);


--
-- Name: unit_notes idx_44157485_primary; Type: CONSTRAINT; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER TABLE ONLY macrostrat.unit_notes
    ADD CONSTRAINT idx_44157485_primary PRIMARY KEY (id);


--
-- Name: unit_seq_strat idx_44157492_primary; Type: CONSTRAINT; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER TABLE ONLY macrostrat.unit_seq_strat
    ADD CONSTRAINT idx_44157492_primary PRIMARY KEY (id);


--
-- Name: unit_strat_names idx_44157497_primary; Type: CONSTRAINT; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER TABLE ONLY macrostrat.unit_strat_names
    ADD CONSTRAINT idx_44157497_primary PRIMARY KEY (id);


--
-- Name: unit_tectonics idx_44157502_primary; Type: CONSTRAINT; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER TABLE ONLY macrostrat.unit_tectonics
    ADD CONSTRAINT idx_44157502_primary PRIMARY KEY (id);


--
-- Name: projects projects_slug_key; Type: CONSTRAINT; Schema: macrostrat; Owner: macrostrat
--

ALTER TABLE ONLY macrostrat.projects
    ADD CONSTRAINT projects_slug_key UNIQUE (slug);


--
-- Name: projects_tree projects_tree_parent_id_child_id_key; Type: CONSTRAINT; Schema: macrostrat; Owner: macrostrat
--

ALTER TABLE ONLY macrostrat.projects_tree
    ADD CONSTRAINT projects_tree_parent_id_child_id_key UNIQUE (parent_id, child_id);


--
-- Name: projects_tree projects_tree_pkey; Type: CONSTRAINT; Schema: macrostrat; Owner: macrostrat
--

ALTER TABLE ONLY macrostrat.projects_tree
    ADD CONSTRAINT projects_tree_pkey PRIMARY KEY (id);


--
-- Name: unit_lith_atts unit_lith_atts_new_pkey1; Type: CONSTRAINT; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER TABLE ONLY macrostrat.unit_lith_atts
    ADD CONSTRAINT unit_lith_atts_new_pkey1 PRIMARY KEY (id);


--
-- Name: col_areas_new_col_area_idx; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX col_areas_new_col_area_idx ON macrostrat.col_areas USING gist (col_area);


--
-- Name: col_areas_new_col_id_idx; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX col_areas_new_col_id_idx ON macrostrat.col_areas USING btree (col_id);


--
-- Name: col_groups_new_id_idx1; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX col_groups_new_id_idx1 ON macrostrat.col_groups USING btree (id);


--
-- Name: col_refs_new_col_id_idx1; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX col_refs_new_col_id_idx1 ON macrostrat.col_refs USING btree (col_id);


--
-- Name: col_refs_new_ref_id_idx1; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX col_refs_new_ref_id_idx1 ON macrostrat.col_refs USING btree (ref_id);


--
-- Name: cols_new_col_group_id_idx; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX cols_new_col_group_id_idx ON macrostrat.cols USING btree (col_group_id);


--
-- Name: cols_new_coordinate_idx; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX cols_new_coordinate_idx ON macrostrat.cols USING gist (coordinate);


--
-- Name: cols_new_poly_geom_idx; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX cols_new_poly_geom_idx ON macrostrat.cols USING gist (poly_geom);


--
-- Name: cols_new_project_id_idx; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX cols_new_project_id_idx ON macrostrat.cols USING btree (project_id);


--
-- Name: cols_new_status_code_idx; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX cols_new_status_code_idx ON macrostrat.cols USING btree (status_code);


--
-- Name: concepts_places_new_concept_id_idx; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX concepts_places_new_concept_id_idx ON macrostrat.concepts_places USING btree (concept_id);


--
-- Name: concepts_places_new_place_id_idx; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX concepts_places_new_place_id_idx ON macrostrat.concepts_places USING btree (place_id);


--
-- Name: idx_44157002_concept_id; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157002_concept_id ON macrostrat.canada_lexicon_dump USING btree (concept_id);


--
-- Name: idx_44157002_lower_interval_id; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157002_lower_interval_id ON macrostrat.canada_lexicon_dump USING btree (lower_interval_id);


--
-- Name: idx_44157002_strat_name_id; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157002_strat_name_id ON macrostrat.canada_lexicon_dump USING btree (strat_name_id);


--
-- Name: idx_44157002_upper_interval_id; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157002_upper_interval_id ON macrostrat.canada_lexicon_dump USING btree (upper_interval_id);


--
-- Name: idx_44157007_color; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157007_color ON macrostrat.colors USING btree (color);


--
-- Name: idx_44157007_unit_hex; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE UNIQUE INDEX idx_44157007_unit_hex ON macrostrat.colors USING btree (unit_hex);


--
-- Name: idx_44157014_col_group_id; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157014_col_group_id ON macrostrat.cols USING btree (col_group_id);


--
-- Name: idx_44157014_col_type; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157014_col_type ON macrostrat.cols USING btree (col_type);


--
-- Name: idx_44157014_project_id; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157014_project_id ON macrostrat.cols USING btree (project_id);


--
-- Name: idx_44157014_status_code; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157014_status_code ON macrostrat.cols USING btree (status_code);


--
-- Name: idx_44157021_col_id; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157021_col_id ON macrostrat.col_areas USING btree (col_id);


--
-- Name: idx_44157034_col_1; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157034_col_1 ON macrostrat.col_equiv USING btree (col_1);


--
-- Name: idx_44157034_col_2; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157034_col_2 ON macrostrat.col_equiv USING btree (col_2);


--
-- Name: idx_44157039_project_id; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157039_project_id ON macrostrat.col_groups USING btree (project_id);


--
-- Name: idx_44157044_col_id; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157044_col_id ON macrostrat.col_notes USING btree (col_id);


--
-- Name: idx_44157051_col_id; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157051_col_id ON macrostrat.col_refs USING btree (col_id);


--
-- Name: idx_44157051_ref_id; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157051_ref_id ON macrostrat.col_refs USING btree (ref_id);


--
-- Name: idx_44157055_concept_id; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157055_concept_id ON macrostrat.concepts_places USING btree (concept_id);


--
-- Name: idx_44157055_concept_id_2; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE UNIQUE INDEX idx_44157055_concept_id_2 ON macrostrat.concepts_places USING btree (concept_id, place_id);


--
-- Name: idx_44157055_place_id; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157055_place_id ON macrostrat.concepts_places USING btree (place_id);


--
-- Name: idx_44157064_environ; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157064_environ ON macrostrat.environs USING btree (environ);


--
-- Name: idx_44157064_environ_class; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157064_environ_class ON macrostrat.environs USING btree (environ_class);


--
-- Name: idx_44157064_environ_type; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157064_environ_type ON macrostrat.environs USING btree (environ_type);


--
-- Name: idx_44157069__intervals_age_bottom; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157069__intervals_age_bottom ON macrostrat.intervals USING btree (age_bottom);


--
-- Name: idx_44157069__intervals_age_top; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157069__intervals_age_top ON macrostrat.intervals USING btree (age_top);


--
-- Name: idx_44157069__intervals_interval_type; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157069__intervals_interval_type ON macrostrat.intervals USING btree (interval_type);


--
-- Name: idx_44157069_interval_name; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157069_interval_name ON macrostrat.intervals USING btree (interval_name);


--
-- Name: idx_44157091_lith; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157091_lith ON macrostrat.liths USING btree (lith);


--
-- Name: idx_44157091_lith_class; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157091_lith_class ON macrostrat.liths USING btree (lith_class);


--
-- Name: idx_44157091_lith_type; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157091_lith_type ON macrostrat.liths USING btree (lith_type);


--
-- Name: idx_44157097_att_type; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157097_att_type ON macrostrat.lith_atts USING btree (att_type);


--
-- Name: idx_44157097_equiv; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157097_equiv ON macrostrat.lith_atts USING btree (equiv);


--
-- Name: idx_44157097_lith_att; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157097_lith_att ON macrostrat.lith_atts USING btree (lith_att);


--
-- Name: idx_44157101_lith_id; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157101_lith_id ON macrostrat.lookup_measurements USING btree (lith_id);


--
-- Name: idx_44157101_measure_phase; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157101_measure_phase ON macrostrat.lookup_measurements USING btree (measure_phase);


--
-- Name: idx_44157101_measurement_class; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157101_measurement_class ON macrostrat.lookup_measurements USING btree (measurement_class);


--
-- Name: idx_44157101_measurement_id; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157101_measurement_id ON macrostrat.lookup_measurements USING btree (measurement_id);


--
-- Name: idx_44157101_measurement_type; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157101_measurement_type ON macrostrat.lookup_measurements USING btree (measurement_type);


--
-- Name: idx_44157101_measuremeta_id; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157101_measuremeta_id ON macrostrat.lookup_measurements USING btree (measuremeta_id);


--
-- Name: idx_44157101_ref_id; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157101_ref_id ON macrostrat.lookup_measurements USING btree (ref_id);


--
-- Name: idx_44157111_bed_id; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157111_bed_id ON macrostrat.lookup_strat_names USING btree (bed_id);


--
-- Name: idx_44157111_concept_id; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157111_concept_id ON macrostrat.lookup_strat_names USING btree (concept_id);


--
-- Name: idx_44157111_fm_id; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157111_fm_id ON macrostrat.lookup_strat_names USING btree (fm_id);


--
-- Name: idx_44157111_gp_id; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157111_gp_id ON macrostrat.lookup_strat_names USING btree (gp_id);


--
-- Name: idx_44157111_mbr_id; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157111_mbr_id ON macrostrat.lookup_strat_names USING btree (mbr_id);


--
-- Name: idx_44157111_parent; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157111_parent ON macrostrat.lookup_strat_names USING btree (parent);


--
-- Name: idx_44157111_rank; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157111_rank ON macrostrat.lookup_strat_names USING btree (rank);


--
-- Name: idx_44157111_ref_id; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157111_ref_id ON macrostrat.lookup_strat_names USING btree (ref_id);


--
-- Name: idx_44157111_sgp_id; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157111_sgp_id ON macrostrat.lookup_strat_names USING btree (sgp_id);


--
-- Name: idx_44157111_strat_name; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157111_strat_name ON macrostrat.lookup_strat_names USING btree (strat_name);


--
-- Name: idx_44157111_subgp_id; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157111_subgp_id ON macrostrat.lookup_strat_names USING btree (subgp_id);


--
-- Name: idx_44157111_tree; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157111_tree ON macrostrat.lookup_strat_names USING btree (tree);


--
-- Name: idx_44157129_b_int; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157129_b_int ON macrostrat.lookup_units USING btree (b_int);


--
-- Name: idx_44157129_project_id; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157129_project_id ON macrostrat.lookup_units USING btree (project_id);


--
-- Name: idx_44157129_t_int; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157129_t_int ON macrostrat.lookup_units USING btree (t_int);


--
-- Name: idx_44157155_unit_id_idx; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157155_unit_id_idx ON macrostrat.lookup_unit_attrs_api USING btree (unit_id);


--
-- Name: idx_44157171_measurement_class; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157171_measurement_class ON macrostrat.measurements USING btree (measurement_class);


--
-- Name: idx_44157171_measurement_type; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157171_measurement_type ON macrostrat.measurements USING btree (measurement_type);


--
-- Name: idx_44157176_lith_att_id; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157176_lith_att_id ON macrostrat.measuremeta USING btree (lith_att_id);


--
-- Name: idx_44157176_lith_id; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157176_lith_id ON macrostrat.measuremeta USING btree (lith_id);


--
-- Name: idx_44157176_ref_id; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157176_ref_id ON macrostrat.measuremeta USING btree (ref_id);


--
-- Name: idx_44157186_col_id; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157186_col_id ON macrostrat.measuremeta_cols USING btree (col_id);


--
-- Name: idx_44157186_measuremeta_id; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157186_measuremeta_id ON macrostrat.measuremeta_cols USING btree (measuremeta_id);


--
-- Name: idx_44157191_measure_phase; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157191_measure_phase ON macrostrat.measures USING btree (measure_phase);


--
-- Name: idx_44157191_measurement_id; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157191_measurement_id ON macrostrat.measures USING btree (measurement_id);


--
-- Name: idx_44157191_measuremeta_id; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157191_measuremeta_id ON macrostrat.measures USING btree (measuremeta_id);


--
-- Name: idx_44157191_method; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157191_method ON macrostrat.measures USING btree (method);


--
-- Name: idx_44157212_bottom_depth; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157212_bottom_depth ON macrostrat.offshore_baggage USING btree (bottom_depth);


--
-- Name: idx_44157212_cleaned_lith; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157212_cleaned_lith ON macrostrat.offshore_baggage USING btree (cleaned_lith);


--
-- Name: idx_44157212_cleaned_minor; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157212_cleaned_minor ON macrostrat.offshore_baggage USING btree (cleaned_minor);


--
-- Name: idx_44157212_col_id; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157212_col_id ON macrostrat.offshore_baggage USING btree (col_id);


--
-- Name: idx_44157212_principal_lith_prefix_cleaned; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157212_principal_lith_prefix_cleaned ON macrostrat.offshore_baggage USING btree (principal_lith_prefix_cleaned);


--
-- Name: idx_44157212_principal_lithology_name; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157212_principal_lithology_name ON macrostrat.offshore_baggage USING btree (principal_lithology_name);


--
-- Name: idx_44157212_principal_lithology_prefix; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157212_principal_lithology_prefix ON macrostrat.offshore_baggage USING btree (principal_lithology_prefix);


--
-- Name: idx_44157212_principal_lithology_suffix; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157212_principal_lithology_suffix ON macrostrat.offshore_baggage USING btree (principal_lithology_suffix);


--
-- Name: idx_44157212_section_id; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157212_section_id ON macrostrat.offshore_baggage USING btree (section_id);


--
-- Name: idx_44157212_top_depth; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157212_top_depth ON macrostrat.offshore_baggage USING btree (top_depth);


--
-- Name: idx_44157222_col_id; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157222_col_id ON macrostrat.offshore_fossils USING btree (col_id);


--
-- Name: idx_44157222_section_id; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157222_section_id ON macrostrat.offshore_fossils USING btree (section_id);


--
-- Name: idx_44157222_taxa; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157222_taxa ON macrostrat.offshore_fossils USING btree (taxa);


--
-- Name: idx_44157222_unit_id; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157222_unit_id ON macrostrat.offshore_fossils USING btree (unit_id);


--
-- Name: idx_44157230_col_id; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157230_col_id ON macrostrat.offshore_hole_ages USING btree (col_id);


--
-- Name: idx_44157230_interval_id; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157230_interval_id ON macrostrat.offshore_hole_ages USING btree (interval_id);


--
-- Name: idx_44157234_col_id; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157234_col_id ON macrostrat.offshore_sections USING btree (col_id);


--
-- Name: idx_44157237_col_group_id; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157237_col_group_id ON macrostrat.offshore_sites USING btree (col_group_id);


--
-- Name: idx_44157237_col_id; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157237_col_id ON macrostrat.offshore_sites USING btree (col_id);


--
-- Name: idx_44157237_leg; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157237_leg ON macrostrat.offshore_sites USING btree (leg);


--
-- Name: idx_44157237_ref_id; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157237_ref_id ON macrostrat.offshore_sites USING btree (ref_id);


--
-- Name: idx_44157237_site; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157237_site ON macrostrat.offshore_sites USING btree (site);


--
-- Name: idx_44157241__intervals_age_bottom; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157241__intervals_age_bottom ON macrostrat.pbdb_intervals USING btree (age_bottom);


--
-- Name: idx_44157241__intervals_age_top; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157241__intervals_age_top ON macrostrat.pbdb_intervals USING btree (age_top);


--
-- Name: idx_44157241__intervals_interval_type; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157241__intervals_interval_type ON macrostrat.pbdb_intervals USING btree (interval_type);


--
-- Name: idx_44157241_interval_name; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157241_interval_name ON macrostrat.pbdb_intervals USING btree (interval_name);


--
-- Name: idx_44157254_collection_no; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157254_collection_no ON macrostrat.pbdb_matches USING btree (collection_no);


--
-- Name: idx_44157254_ref_id; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157254_ref_id ON macrostrat.pbdb_matches USING btree (ref_id);


--
-- Name: idx_44157254_unit_id; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157254_unit_id ON macrostrat.pbdb_matches USING btree (unit_id);


--
-- Name: idx_44157270_project; Type: INDEX; Schema: macrostrat; Owner: macrostrat
--

CREATE INDEX idx_44157270_project ON macrostrat.projects USING btree (project);


--
-- Name: idx_44157270_timescale_id; Type: INDEX; Schema: macrostrat; Owner: macrostrat
--

CREATE INDEX idx_44157270_timescale_id ON macrostrat.projects USING btree (timescale_id);


--
-- Name: idx_44157286_feature_class; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157286_feature_class ON macrostrat.rockd_features USING btree (feature_class);


--
-- Name: idx_44157286_feature_type; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157286_feature_type ON macrostrat.rockd_features USING btree (feature_type);


--
-- Name: idx_44157290_interval_id; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157290_interval_id ON macrostrat.ronov_sediment USING btree (interval_id);


--
-- Name: idx_44157294_col_id; Type: INDEX; Schema: macrostrat; Owner: macrostrat
--

CREATE INDEX idx_44157294_col_id ON macrostrat.sections USING btree (col_id);


--
-- Name: idx_44157294_fo; Type: INDEX; Schema: macrostrat; Owner: macrostrat
--

CREATE INDEX idx_44157294_fo ON macrostrat.sections USING btree (fo);


--
-- Name: idx_44157294_lo; Type: INDEX; Schema: macrostrat; Owner: macrostrat
--

CREATE INDEX idx_44157294_lo ON macrostrat.sections USING btree (lo);


--
-- Name: idx_44157311_concept_id; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157311_concept_id ON macrostrat.strat_names USING btree (concept_id);


--
-- Name: idx_44157311_rank; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157311_rank ON macrostrat.strat_names USING btree (rank);


--
-- Name: idx_44157311_ref_id; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157311_ref_id ON macrostrat.strat_names USING btree (ref_id);


--
-- Name: idx_44157311_strat_name; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157311_strat_name ON macrostrat.strat_names USING btree (strat_name);


--
-- Name: idx_44157318_bed_id; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157318_bed_id ON macrostrat.strat_names_lookup USING btree (bed_id);


--
-- Name: idx_44157318_fm_id; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157318_fm_id ON macrostrat.strat_names_lookup USING btree (fm_id);


--
-- Name: idx_44157318_gp_id; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157318_gp_id ON macrostrat.strat_names_lookup USING btree (gp_id);


--
-- Name: idx_44157318_mbr_id; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157318_mbr_id ON macrostrat.strat_names_lookup USING btree (mbr_id);


--
-- Name: idx_44157318_sgp_id; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157318_sgp_id ON macrostrat.strat_names_lookup USING btree (sgp_id);


--
-- Name: idx_44157324_b_int; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157324_b_int ON macrostrat.strat_names_meta USING btree (b_int);


--
-- Name: idx_44157324_interval_id; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157324_interval_id ON macrostrat.strat_names_meta USING btree (interval_id);


--
-- Name: idx_44157324_ref_id; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157324_ref_id ON macrostrat.strat_names_meta USING btree (ref_id);


--
-- Name: idx_44157324_t_int; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157324_t_int ON macrostrat.strat_names_meta USING btree (t_int);


--
-- Name: idx_44157331_strat_name_id; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE UNIQUE INDEX idx_44157331_strat_name_id ON macrostrat.strat_names_places USING btree (strat_name_id, place_id);


--
-- Name: idx_44157354_col_id; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157354_col_id ON macrostrat.temp_areas USING btree (col_id);


--
-- Name: idx_44157354_col_id_2; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE UNIQUE INDEX idx_44157354_col_id_2 ON macrostrat.temp_areas USING btree (col_id);


--
-- Name: idx_44157358_ref_id; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157358_ref_id ON macrostrat.timescales USING btree (ref_id);


--
-- Name: idx_44157358_timescale; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157358_timescale ON macrostrat.timescales USING btree (timescale);


--
-- Name: idx_44157363__timescale_intervals_interval_id; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157363__timescale_intervals_interval_id ON macrostrat.timescales_intervals USING btree (interval_id);


--
-- Name: idx_44157363__timescale_intervals_timescale_id; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157363__timescale_intervals_timescale_id ON macrostrat.timescales_intervals USING btree (timescale_id);


--
-- Name: idx_44157375_col_id; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157375_col_id ON macrostrat.units USING btree (col_id);


--
-- Name: idx_44157375_color; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157375_color ON macrostrat.units USING btree (color);


--
-- Name: idx_44157375_fo; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157375_fo ON macrostrat.units USING btree (fo);


--
-- Name: idx_44157375_lo; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157375_lo ON macrostrat.units USING btree (lo);


--
-- Name: idx_44157375_section_id; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157375_section_id ON macrostrat.units USING btree (section_id);


--
-- Name: idx_44157375_strat_name; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157375_strat_name ON macrostrat.units USING btree (strat_name);


--
-- Name: idx_44157384_datafile_id; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157384_datafile_id ON macrostrat.units_datafiles USING btree (datafile_id);


--
-- Name: idx_44157388_col_id; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157388_col_id ON macrostrat.units_sections USING btree (col_id);


--
-- Name: idx_44157388_section_id; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157388_section_id ON macrostrat.units_sections USING btree (section_id);


--
-- Name: idx_44157388_unit_id; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157388_unit_id ON macrostrat.units_sections USING btree (unit_id);


--
-- Name: idx_44157393_section_id; Type: INDEX; Schema: macrostrat; Owner: macrostrat
--

CREATE INDEX idx_44157393_section_id ON macrostrat.unit_boundaries USING btree (section_id);


--
-- Name: idx_44157393_t1; Type: INDEX; Schema: macrostrat; Owner: macrostrat
--

CREATE INDEX idx_44157393_t1 ON macrostrat.unit_boundaries USING btree (t1);


--
-- Name: idx_44157393_unit_id; Type: INDEX; Schema: macrostrat; Owner: macrostrat
--

CREATE INDEX idx_44157393_unit_id ON macrostrat.unit_boundaries USING btree (unit_id);


--
-- Name: idx_44157393_unit_id_2; Type: INDEX; Schema: macrostrat; Owner: macrostrat
--

CREATE INDEX idx_44157393_unit_id_2 ON macrostrat.unit_boundaries USING btree (unit_id_2);


--
-- Name: idx_44157404_section_id; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157404_section_id ON macrostrat.unit_boundaries_backup USING btree (section_id);


--
-- Name: idx_44157404_t1; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157404_t1 ON macrostrat.unit_boundaries_backup USING btree (t1);


--
-- Name: idx_44157404_unit_id; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157404_unit_id ON macrostrat.unit_boundaries_backup USING btree (unit_id);


--
-- Name: idx_44157404_unit_id_2; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157404_unit_id_2 ON macrostrat.unit_boundaries_backup USING btree (unit_id_2);


--
-- Name: idx_44157415_section_id; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157415_section_id ON macrostrat.unit_boundaries_scratch USING btree (section_id);


--
-- Name: idx_44157415_t1; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157415_t1 ON macrostrat.unit_boundaries_scratch USING btree (t1);


--
-- Name: idx_44157415_unit_id; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157415_unit_id ON macrostrat.unit_boundaries_scratch USING btree (unit_id);


--
-- Name: idx_44157415_unit_id_2; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157415_unit_id_2 ON macrostrat.unit_boundaries_scratch USING btree (unit_id_2);


--
-- Name: idx_44157426_section_id; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157426_section_id ON macrostrat.unit_boundaries_scratch_old USING btree (section_id);


--
-- Name: idx_44157426_t1; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157426_t1 ON macrostrat.unit_boundaries_scratch_old USING btree (t1);


--
-- Name: idx_44157426_unit_id; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157426_unit_id ON macrostrat.unit_boundaries_scratch_old USING btree (unit_id);


--
-- Name: idx_44157426_unit_id_2; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157426_unit_id_2 ON macrostrat.unit_boundaries_scratch_old USING btree (unit_id_2);


--
-- Name: idx_44157435_unit_id; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157435_unit_id ON macrostrat.unit_contacts USING btree (unit_id);


--
-- Name: idx_44157435_with_unit; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157435_with_unit ON macrostrat.unit_contacts USING btree (with_unit);


--
-- Name: idx_44157440_ref_id; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157440_ref_id ON macrostrat.unit_dates USING btree (ref_id);


--
-- Name: idx_44157440_unit_id; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157440_unit_id ON macrostrat.unit_dates USING btree (unit_id);


--
-- Name: idx_44157447_econ_id; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157447_econ_id ON macrostrat.unit_econs USING btree (econ_id);


--
-- Name: idx_44157447_ref_id; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157447_ref_id ON macrostrat.unit_econs USING btree (ref_id);


--
-- Name: idx_44157447_unit_id; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157447_unit_id ON macrostrat.unit_econs USING btree (unit_id);


--
-- Name: idx_44157452_environ_id; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157452_environ_id ON macrostrat.unit_environs USING btree (environ_id);


--
-- Name: idx_44157452_ref_id; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157452_ref_id ON macrostrat.unit_environs USING btree (ref_id);


--
-- Name: idx_44157452_unit_id; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157452_unit_id ON macrostrat.unit_environs USING btree (unit_id);


--
-- Name: idx_44157458_new_unit_id; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157458_new_unit_id ON macrostrat.unit_equiv USING btree (new_unit_id);


--
-- Name: idx_44157458_unit_id; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157458_unit_id ON macrostrat.unit_equiv USING btree (unit_id);


--
-- Name: idx_44157463_lith_id; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157463_lith_id ON macrostrat.unit_liths USING btree (lith_id);


--
-- Name: idx_44157463_ref_id; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157463_ref_id ON macrostrat.unit_liths USING btree (ref_id);


--
-- Name: idx_44157463_unit_id; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157463_unit_id ON macrostrat.unit_liths USING btree (unit_id);


--
-- Name: idx_44157469_lith_att_id; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157469_lith_att_id ON macrostrat.unit_liths_atts USING btree (lith_att_id);


--
-- Name: idx_44157469_ref_id; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157469_ref_id ON macrostrat.unit_liths_atts USING btree (ref_id);


--
-- Name: idx_44157469_unit_lith_id; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157469_unit_lith_id ON macrostrat.unit_liths_atts USING btree (unit_lith_id);


--
-- Name: idx_44157474_measuremeta_id; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157474_measuremeta_id ON macrostrat.unit_measures USING btree (measuremeta_id);


--
-- Name: idx_44157474_strat_name_id; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157474_strat_name_id ON macrostrat.unit_measures USING btree (strat_name_id);


--
-- Name: idx_44157474_unit_id; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157474_unit_id ON macrostrat.unit_measures USING btree (unit_id);


--
-- Name: idx_44157479_collection_no; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157479_collection_no ON macrostrat.unit_measures_pbdb USING btree (collection_no);


--
-- Name: idx_44157485_unit_id; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157485_unit_id ON macrostrat.unit_notes USING btree (unit_id);


--
-- Name: idx_44157492_unit_id; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157492_unit_id ON macrostrat.unit_seq_strat USING btree (unit_id);


--
-- Name: idx_44157497_strat_name_id; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157497_strat_name_id ON macrostrat.unit_strat_names USING btree (strat_name_id);


--
-- Name: idx_44157497_unit_id; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157497_unit_id ON macrostrat.unit_strat_names USING btree (unit_id);


--
-- Name: idx_44157502_tectonic_id; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157502_tectonic_id ON macrostrat.unit_tectonics USING btree (tectonic_id);


--
-- Name: idx_44157502_unit_id; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX idx_44157502_unit_id ON macrostrat.unit_tectonics USING btree (unit_id);


--
-- Name: idx_projects_slug; Type: INDEX; Schema: macrostrat; Owner: macrostrat
--

CREATE INDEX idx_projects_slug ON macrostrat.projects USING btree (slug);


--
-- Name: intervals_new_age_bottom_idx1; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX intervals_new_age_bottom_idx1 ON macrostrat.intervals USING btree (age_bottom);


--
-- Name: intervals_new_age_top_idx1; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX intervals_new_age_top_idx1 ON macrostrat.intervals USING btree (age_top);


--
-- Name: intervals_new_id_idx1; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX intervals_new_id_idx1 ON macrostrat.intervals USING btree (id);


--
-- Name: intervals_new_interval_name_idx1; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX intervals_new_interval_name_idx1 ON macrostrat.intervals USING btree (interval_name);


--
-- Name: intervals_new_interval_type_idx1; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX intervals_new_interval_type_idx1 ON macrostrat.intervals USING btree (interval_type);


--
-- Name: lith_atts_new_att_type_idx1; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX lith_atts_new_att_type_idx1 ON macrostrat.lith_atts USING btree (att_type);


--
-- Name: lith_atts_new_lith_att_idx1; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX lith_atts_new_lith_att_idx1 ON macrostrat.lith_atts USING btree (lith_att);


--
-- Name: liths_new_lith_class_idx1; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX liths_new_lith_class_idx1 ON macrostrat.liths USING btree (lith_class);


--
-- Name: liths_new_lith_idx1; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX liths_new_lith_idx1 ON macrostrat.liths USING btree (lith);


--
-- Name: liths_new_lith_type_idx1; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX liths_new_lith_type_idx1 ON macrostrat.liths USING btree (lith_type);


--
-- Name: lookup_strat_names_new_bed_id_idx; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX lookup_strat_names_new_bed_id_idx ON macrostrat.lookup_strat_names USING btree (bed_id);


--
-- Name: lookup_strat_names_new_concept_id_idx; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX lookup_strat_names_new_concept_id_idx ON macrostrat.lookup_strat_names USING btree (concept_id);


--
-- Name: lookup_strat_names_new_fm_id_idx; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX lookup_strat_names_new_fm_id_idx ON macrostrat.lookup_strat_names USING btree (fm_id);


--
-- Name: lookup_strat_names_new_gp_id_idx; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX lookup_strat_names_new_gp_id_idx ON macrostrat.lookup_strat_names USING btree (gp_id);


--
-- Name: lookup_strat_names_new_mbr_id_idx; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX lookup_strat_names_new_mbr_id_idx ON macrostrat.lookup_strat_names USING btree (mbr_id);


--
-- Name: lookup_strat_names_new_sgp_id_idx; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX lookup_strat_names_new_sgp_id_idx ON macrostrat.lookup_strat_names USING btree (sgp_id);


--
-- Name: lookup_strat_names_new_strat_name_id_idx; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX lookup_strat_names_new_strat_name_id_idx ON macrostrat.lookup_strat_names USING btree (strat_name_id);


--
-- Name: lookup_strat_names_new_strat_name_idx; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX lookup_strat_names_new_strat_name_idx ON macrostrat.lookup_strat_names USING btree (strat_name);


--
-- Name: lookup_unit_attrs_api_new_unit_id_idx1; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX lookup_unit_attrs_api_new_unit_id_idx1 ON macrostrat.lookup_unit_attrs_api USING btree (unit_id);


--
-- Name: lookup_unit_intervals_new_best_interval_id_idx; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX lookup_unit_intervals_new_best_interval_id_idx ON macrostrat.lookup_unit_intervals USING btree (best_interval_id);


--
-- Name: lookup_unit_intervals_new_unit_id_idx; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX lookup_unit_intervals_new_unit_id_idx ON macrostrat.lookup_unit_intervals USING btree (unit_id);


--
-- Name: lookup_unit_liths_new_unit_id_idx; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX lookup_unit_liths_new_unit_id_idx ON macrostrat.lookup_unit_liths USING btree (unit_id);


--
-- Name: lookup_units_new_b_int_idx1; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX lookup_units_new_b_int_idx1 ON macrostrat.lookup_units USING btree (b_int);


--
-- Name: lookup_units_new_project_id_idx1; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX lookup_units_new_project_id_idx1 ON macrostrat.lookup_units USING btree (project_id);


--
-- Name: lookup_units_new_t_int_idx1; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX lookup_units_new_t_int_idx1 ON macrostrat.lookup_units USING btree (t_int);


--
-- Name: measurements_new_id_idx; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX measurements_new_id_idx ON macrostrat.measurements USING btree (id);


--
-- Name: measurements_new_measurement_class_idx; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX measurements_new_measurement_class_idx ON macrostrat.measurements USING btree (measurement_class);


--
-- Name: measurements_new_measurement_type_idx; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX measurements_new_measurement_type_idx ON macrostrat.measurements USING btree (measurement_type);


--
-- Name: measuremeta_new_lith_att_id_idx1; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX measuremeta_new_lith_att_id_idx1 ON macrostrat.measuremeta USING btree (lith_att_id);


--
-- Name: measuremeta_new_lith_id_idx1; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX measuremeta_new_lith_id_idx1 ON macrostrat.measuremeta USING btree (lith_id);


--
-- Name: measuremeta_new_ref_id_idx1; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX measuremeta_new_ref_id_idx1 ON macrostrat.measuremeta USING btree (ref_id);


--
-- Name: measures_new_measurement_id_idx1; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX measures_new_measurement_id_idx1 ON macrostrat.measures USING btree (measurement_id);


--
-- Name: measures_new_measuremeta_id_idx1; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX measures_new_measuremeta_id_idx1 ON macrostrat.measures USING btree (measuremeta_id);


--
-- Name: pbdb_collections_collection_no_idx; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX pbdb_collections_collection_no_idx ON macrostrat.pbdb_collections USING btree (collection_no);


--
-- Name: pbdb_collections_collection_no_idx1; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX pbdb_collections_collection_no_idx1 ON macrostrat.pbdb_collections USING btree (collection_no);


--
-- Name: pbdb_collections_early_age_idx; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX pbdb_collections_early_age_idx ON macrostrat.pbdb_collections USING btree (early_age);


--
-- Name: pbdb_collections_early_age_idx1; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX pbdb_collections_early_age_idx1 ON macrostrat.pbdb_collections USING btree (early_age);


--
-- Name: pbdb_collections_geom_idx; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX pbdb_collections_geom_idx ON macrostrat.pbdb_collections USING gist (geom);


--
-- Name: pbdb_collections_geom_idx1; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX pbdb_collections_geom_idx1 ON macrostrat.pbdb_collections USING gist (geom);


--
-- Name: pbdb_collections_late_age_idx; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX pbdb_collections_late_age_idx ON macrostrat.pbdb_collections USING btree (late_age);


--
-- Name: pbdb_collections_late_age_idx1; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX pbdb_collections_late_age_idx1 ON macrostrat.pbdb_collections USING btree (late_age);


--
-- Name: pbdb_collections_new_collection_no_idx1; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX pbdb_collections_new_collection_no_idx1 ON macrostrat.pbdb_collections USING btree (collection_no);


--
-- Name: pbdb_collections_new_early_age_idx1; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX pbdb_collections_new_early_age_idx1 ON macrostrat.pbdb_collections USING btree (early_age);


--
-- Name: pbdb_collections_new_geom_idx1; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX pbdb_collections_new_geom_idx1 ON macrostrat.pbdb_collections USING gist (geom);


--
-- Name: pbdb_collections_new_late_age_idx1; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX pbdb_collections_new_late_age_idx1 ON macrostrat.pbdb_collections USING btree (late_age);


--
-- Name: places_new_geom_idx; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX places_new_geom_idx ON macrostrat.places USING gist (geom);


--
-- Name: projects_new_timescale_id_idx; Type: INDEX; Schema: macrostrat; Owner: macrostrat
--

CREATE INDEX projects_new_timescale_id_idx ON macrostrat.projects USING btree (timescale_id);


--
-- Name: refs_new_rgeom_idx1; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX refs_new_rgeom_idx1 ON macrostrat.refs USING gist (rgeom);


--
-- Name: sections_new_col_id_idx1; Type: INDEX; Schema: macrostrat; Owner: macrostrat
--

CREATE INDEX sections_new_col_id_idx1 ON macrostrat.sections USING btree (col_id);


--
-- Name: sections_new_id_idx1; Type: INDEX; Schema: macrostrat; Owner: macrostrat
--

CREATE INDEX sections_new_id_idx1 ON macrostrat.sections USING btree (id);


--
-- Name: strat_name_footprints_geom_idx; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX strat_name_footprints_geom_idx ON macrostrat.strat_name_footprints USING gist (geom);


--
-- Name: strat_name_footprints_geom_idx1; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX strat_name_footprints_geom_idx1 ON macrostrat.strat_name_footprints USING gist (geom);


--
-- Name: strat_name_footprints_new_geom_idx; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX strat_name_footprints_new_geom_idx ON macrostrat.strat_name_footprints USING gist (geom);


--
-- Name: strat_name_footprints_new_strat_name_id_idx; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX strat_name_footprints_new_strat_name_id_idx ON macrostrat.strat_name_footprints USING btree (strat_name_id);


--
-- Name: strat_name_footprints_strat_name_id_idx; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX strat_name_footprints_strat_name_id_idx ON macrostrat.strat_name_footprints USING btree (strat_name_id);


--
-- Name: strat_name_footprints_strat_name_id_idx1; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX strat_name_footprints_strat_name_id_idx1 ON macrostrat.strat_name_footprints USING btree (strat_name_id);


--
-- Name: strat_names_meta_new_b_int_idx1; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX strat_names_meta_new_b_int_idx1 ON macrostrat.strat_names_meta USING btree (b_int);


--
-- Name: strat_names_meta_new_interval_id_idx1; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX strat_names_meta_new_interval_id_idx1 ON macrostrat.strat_names_meta USING btree (interval_id);


--
-- Name: strat_names_meta_new_ref_id_idx1; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX strat_names_meta_new_ref_id_idx1 ON macrostrat.strat_names_meta USING btree (ref_id);


--
-- Name: strat_names_meta_new_t_int_idx1; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX strat_names_meta_new_t_int_idx1 ON macrostrat.strat_names_meta USING btree (t_int);


--
-- Name: strat_names_new_concept_id_idx; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX strat_names_new_concept_id_idx ON macrostrat.strat_names USING btree (concept_id);


--
-- Name: strat_names_new_rank_idx; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX strat_names_new_rank_idx ON macrostrat.strat_names USING btree (rank);


--
-- Name: strat_names_new_ref_id_idx; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX strat_names_new_ref_id_idx ON macrostrat.strat_names USING btree (ref_id);


--
-- Name: strat_names_new_strat_name_idx; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX strat_names_new_strat_name_idx ON macrostrat.strat_names USING btree (strat_name);


--
-- Name: strat_names_places_new_place_id_idx1; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX strat_names_places_new_place_id_idx1 ON macrostrat.strat_names_places USING btree (place_id);


--
-- Name: strat_names_places_new_strat_name_id_idx1; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX strat_names_places_new_strat_name_id_idx1 ON macrostrat.strat_names_places USING btree (strat_name_id);


--
-- Name: timescales_intervals_new_interval_id_idx1; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX timescales_intervals_new_interval_id_idx1 ON macrostrat.timescales_intervals USING btree (interval_id);


--
-- Name: timescales_intervals_new_timescale_id_idx1; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX timescales_intervals_new_timescale_id_idx1 ON macrostrat.timescales_intervals USING btree (timescale_id);


--
-- Name: timescales_new_ref_id_idx1; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX timescales_new_ref_id_idx1 ON macrostrat.timescales USING btree (ref_id);


--
-- Name: timescales_new_timescale_idx1; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX timescales_new_timescale_idx1 ON macrostrat.timescales USING btree (timescale);


--
-- Name: unit_boundaries_section_id_idx; Type: INDEX; Schema: macrostrat; Owner: macrostrat
--

CREATE INDEX unit_boundaries_section_id_idx ON macrostrat.unit_boundaries USING btree (section_id);


--
-- Name: unit_boundaries_t1_idx; Type: INDEX; Schema: macrostrat; Owner: macrostrat
--

CREATE INDEX unit_boundaries_t1_idx ON macrostrat.unit_boundaries USING btree (t1);


--
-- Name: unit_boundaries_unit_id_2_idx; Type: INDEX; Schema: macrostrat; Owner: macrostrat
--

CREATE INDEX unit_boundaries_unit_id_2_idx ON macrostrat.unit_boundaries USING btree (unit_id_2);


--
-- Name: unit_boundaries_unit_id_idx; Type: INDEX; Schema: macrostrat; Owner: macrostrat
--

CREATE INDEX unit_boundaries_unit_id_idx ON macrostrat.unit_boundaries USING btree (unit_id);


--
-- Name: unit_econs_new_econ_id_idx1; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX unit_econs_new_econ_id_idx1 ON macrostrat.unit_econs USING btree (econ_id);


--
-- Name: unit_econs_new_ref_id_idx1; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX unit_econs_new_ref_id_idx1 ON macrostrat.unit_econs USING btree (ref_id);


--
-- Name: unit_econs_new_unit_id_idx1; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX unit_econs_new_unit_id_idx1 ON macrostrat.unit_econs USING btree (unit_id);


--
-- Name: unit_environs_new_environ_id_idx1; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX unit_environs_new_environ_id_idx1 ON macrostrat.unit_environs USING btree (environ_id);


--
-- Name: unit_environs_new_ref_id_idx1; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX unit_environs_new_ref_id_idx1 ON macrostrat.unit_environs USING btree (ref_id);


--
-- Name: unit_environs_new_unit_id_idx1; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX unit_environs_new_unit_id_idx1 ON macrostrat.unit_environs USING btree (unit_id);


--
-- Name: unit_lith_atts_new_lith_att_id_idx1; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX unit_lith_atts_new_lith_att_id_idx1 ON macrostrat.unit_lith_atts USING btree (lith_att_id);


--
-- Name: unit_lith_atts_new_ref_id_idx1; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX unit_lith_atts_new_ref_id_idx1 ON macrostrat.unit_lith_atts USING btree (ref_id);


--
-- Name: unit_lith_atts_new_unit_lith_id_idx1; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX unit_lith_atts_new_unit_lith_id_idx1 ON macrostrat.unit_lith_atts USING btree (unit_lith_id);


--
-- Name: unit_liths_new_lith_id_idx1; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX unit_liths_new_lith_id_idx1 ON macrostrat.unit_liths USING btree (lith_id);


--
-- Name: unit_liths_new_ref_id_idx1; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX unit_liths_new_ref_id_idx1 ON macrostrat.unit_liths USING btree (ref_id);


--
-- Name: unit_liths_new_unit_id_idx1; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX unit_liths_new_unit_id_idx1 ON macrostrat.unit_liths USING btree (unit_id);


--
-- Name: unit_measures_new_measuremeta_id_idx; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX unit_measures_new_measuremeta_id_idx ON macrostrat.unit_measures USING btree (measuremeta_id);


--
-- Name: unit_measures_new_strat_name_id_idx; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX unit_measures_new_strat_name_id_idx ON macrostrat.unit_measures USING btree (strat_name_id);


--
-- Name: unit_measures_new_unit_id_idx; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX unit_measures_new_unit_id_idx ON macrostrat.unit_measures USING btree (unit_id);


--
-- Name: unit_strat_names_new_strat_name_id_idx1; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX unit_strat_names_new_strat_name_id_idx1 ON macrostrat.unit_strat_names USING btree (strat_name_id);


--
-- Name: unit_strat_names_new_unit_id_idx1; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX unit_strat_names_new_unit_id_idx1 ON macrostrat.unit_strat_names USING btree (unit_id);


--
-- Name: units_new_col_id_idx; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX units_new_col_id_idx ON macrostrat.units USING btree (col_id);


--
-- Name: units_new_color_idx; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX units_new_color_idx ON macrostrat.units USING btree (color);


--
-- Name: units_new_section_id_idx; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX units_new_section_id_idx ON macrostrat.units USING btree (section_id);


--
-- Name: units_new_strat_name_idx; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX units_new_strat_name_idx ON macrostrat.units USING btree (strat_name);


--
-- Name: units_sections_new_col_id_idx; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX units_sections_new_col_id_idx ON macrostrat.units_sections USING btree (col_id);


--
-- Name: units_sections_new_section_id_idx; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX units_sections_new_section_id_idx ON macrostrat.units_sections USING btree (section_id);


--
-- Name: units_sections_new_unit_id_idx; Type: INDEX; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE INDEX units_sections_new_unit_id_idx ON macrostrat.units_sections USING btree (unit_id);


--
-- Name: cols lng_lat_insert_trigger; Type: TRIGGER; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE TRIGGER lng_lat_insert_trigger BEFORE INSERT OR UPDATE ON macrostrat.cols FOR EACH ROW EXECUTE FUNCTION macrostrat.lng_lat_insert_trigger();


--
-- Name: offshore_baggage on_update_current_timestamp; Type: TRIGGER; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE TRIGGER on_update_current_timestamp BEFORE UPDATE ON macrostrat.offshore_baggage FOR EACH ROW EXECUTE FUNCTION macrostrat.on_update_current_timestamp_offshore_baggage();


--
-- Name: offshore_fossils on_update_current_timestamp; Type: TRIGGER; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE TRIGGER on_update_current_timestamp BEFORE UPDATE ON macrostrat.offshore_fossils FOR EACH ROW EXECUTE FUNCTION macrostrat.on_update_current_timestamp_offshore_fossils();


--
-- Name: unit_dates on_update_current_timestamp; Type: TRIGGER; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE TRIGGER on_update_current_timestamp BEFORE UPDATE ON macrostrat.unit_dates FOR EACH ROW EXECUTE FUNCTION macrostrat.on_update_current_timestamp_unit_dates();


--
-- Name: unit_econs on_update_current_timestamp; Type: TRIGGER; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE TRIGGER on_update_current_timestamp BEFORE UPDATE ON macrostrat.unit_econs FOR EACH ROW EXECUTE FUNCTION macrostrat.on_update_current_timestamp_unit_econs();


--
-- Name: unit_environs on_update_current_timestamp; Type: TRIGGER; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE TRIGGER on_update_current_timestamp BEFORE UPDATE ON macrostrat.unit_environs FOR EACH ROW EXECUTE FUNCTION macrostrat.on_update_current_timestamp_unit_environs();


--
-- Name: unit_liths on_update_current_timestamp; Type: TRIGGER; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE TRIGGER on_update_current_timestamp BEFORE UPDATE ON macrostrat.unit_liths FOR EACH ROW EXECUTE FUNCTION macrostrat.on_update_current_timestamp_unit_liths();


--
-- Name: unit_liths_atts on_update_current_timestamp; Type: TRIGGER; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE TRIGGER on_update_current_timestamp BEFORE UPDATE ON macrostrat.unit_liths_atts FOR EACH ROW EXECUTE FUNCTION macrostrat.on_update_current_timestamp_unit_liths_atts();


--
-- Name: unit_notes on_update_current_timestamp; Type: TRIGGER; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE TRIGGER on_update_current_timestamp BEFORE UPDATE ON macrostrat.unit_notes FOR EACH ROW EXECUTE FUNCTION macrostrat.on_update_current_timestamp_unit_notes();


--
-- Name: units on_update_current_timestamp; Type: TRIGGER; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE TRIGGER on_update_current_timestamp BEFORE UPDATE ON macrostrat.units FOR EACH ROW EXECUTE FUNCTION macrostrat.on_update_current_timestamp_units();


--
-- Name: cols trg_check_column_project_non_composite; Type: TRIGGER; Schema: macrostrat; Owner: macrostrat-admin
--

CREATE TRIGGER trg_check_column_project_non_composite BEFORE INSERT OR UPDATE ON macrostrat.cols FOR EACH ROW EXECUTE FUNCTION macrostrat.check_column_project_non_composite();


--
-- Name: projects_tree trg_check_composite_parent; Type: TRIGGER; Schema: macrostrat; Owner: macrostrat
--

CREATE TRIGGER trg_check_composite_parent BEFORE INSERT OR UPDATE ON macrostrat.projects_tree FOR EACH ROW EXECUTE FUNCTION macrostrat.check_composite_parent();


--
-- Name: col_areas col_areas_cols_fk; Type: FK CONSTRAINT; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER TABLE ONLY macrostrat.col_areas
    ADD CONSTRAINT col_areas_cols_fk FOREIGN KEY (col_id) REFERENCES macrostrat.cols(id) ON DELETE CASCADE;


--
-- Name: col_refs col_refs_col_fk; Type: FK CONSTRAINT; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER TABLE ONLY macrostrat.col_refs
    ADD CONSTRAINT col_refs_col_fk FOREIGN KEY (col_id) REFERENCES macrostrat.cols(id) ON DELETE CASCADE;


--
-- Name: col_refs col_refs_ref_fk; Type: FK CONSTRAINT; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER TABLE ONLY macrostrat.col_refs
    ADD CONSTRAINT col_refs_ref_fk FOREIGN KEY (ref_id) REFERENCES macrostrat.refs(id) ON DELETE CASCADE;


--
-- Name: cols cols_col_groups_fk; Type: FK CONSTRAINT; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER TABLE ONLY macrostrat.cols
    ADD CONSTRAINT cols_col_groups_fk FOREIGN KEY (col_group_id) REFERENCES macrostrat.col_groups(id) ON DELETE CASCADE;


--
-- Name: cols cols_project_fk; Type: FK CONSTRAINT; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER TABLE ONLY macrostrat.cols
    ADD CONSTRAINT cols_project_fk FOREIGN KEY (project_id) REFERENCES macrostrat.projects(id) ON DELETE CASCADE;


--
-- Name: concepts_places concepts_places_places_fk; Type: FK CONSTRAINT; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER TABLE ONLY macrostrat.concepts_places
    ADD CONSTRAINT concepts_places_places_fk FOREIGN KEY (place_id) REFERENCES macrostrat.places(place_id) ON DELETE CASCADE;


--
-- Name: projects projects_timescale_fk; Type: FK CONSTRAINT; Schema: macrostrat; Owner: macrostrat
--

ALTER TABLE ONLY macrostrat.projects
    ADD CONSTRAINT projects_timescale_fk FOREIGN KEY (timescale_id) REFERENCES macrostrat.timescales(id) ON DELETE CASCADE;


--
-- Name: projects_tree projects_tree_child_id_fkey; Type: FK CONSTRAINT; Schema: macrostrat; Owner: macrostrat
--

ALTER TABLE ONLY macrostrat.projects_tree
    ADD CONSTRAINT projects_tree_child_id_fkey FOREIGN KEY (child_id) REFERENCES macrostrat.projects(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: projects_tree projects_tree_parent_id_fkey; Type: FK CONSTRAINT; Schema: macrostrat; Owner: macrostrat
--

ALTER TABLE ONLY macrostrat.projects_tree
    ADD CONSTRAINT projects_tree_parent_id_fkey FOREIGN KEY (parent_id) REFERENCES macrostrat.projects(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: sections sections_cols_fk; Type: FK CONSTRAINT; Schema: macrostrat; Owner: macrostrat
--

ALTER TABLE ONLY macrostrat.sections
    ADD CONSTRAINT sections_cols_fk FOREIGN KEY (col_id) REFERENCES macrostrat.cols(id) ON DELETE CASCADE;


--
-- Name: strat_names_meta strat_names_meta_intervals_fk; Type: FK CONSTRAINT; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER TABLE ONLY macrostrat.strat_names_meta
    ADD CONSTRAINT strat_names_meta_intervals_fk FOREIGN KEY (interval_id) REFERENCES macrostrat.intervals(id) ON DELETE CASCADE;


--
-- Name: strat_names_meta strat_names_meta_refs_fk; Type: FK CONSTRAINT; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER TABLE ONLY macrostrat.strat_names_meta
    ADD CONSTRAINT strat_names_meta_refs_fk FOREIGN KEY (ref_id) REFERENCES macrostrat.refs(id) ON DELETE CASCADE;


--
-- Name: strat_names_places strat_names_places_places_fk; Type: FK CONSTRAINT; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER TABLE ONLY macrostrat.strat_names_places
    ADD CONSTRAINT strat_names_places_places_fk FOREIGN KEY (place_id) REFERENCES macrostrat.places(place_id) ON DELETE CASCADE;


--
-- Name: strat_names_places strat_names_places_strat_names_fk; Type: FK CONSTRAINT; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER TABLE ONLY macrostrat.strat_names_places
    ADD CONSTRAINT strat_names_places_strat_names_fk FOREIGN KEY (strat_name_id) REFERENCES macrostrat.strat_names(id) ON DELETE CASCADE;


--
-- Name: strat_names strat_names_strat_names_meta_fk; Type: FK CONSTRAINT; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER TABLE ONLY macrostrat.strat_names
    ADD CONSTRAINT strat_names_strat_names_meta_fk FOREIGN KEY (concept_id) REFERENCES macrostrat.strat_names_meta(concept_id) ON DELETE CASCADE;


--
-- Name: timescales_intervals timescales_intervals_intervals_fk; Type: FK CONSTRAINT; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER TABLE ONLY macrostrat.timescales_intervals
    ADD CONSTRAINT timescales_intervals_intervals_fk FOREIGN KEY (interval_id) REFERENCES macrostrat.intervals(id) ON DELETE CASCADE;


--
-- Name: timescales_intervals timescales_intervals_timescales_fk; Type: FK CONSTRAINT; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER TABLE ONLY macrostrat.timescales_intervals
    ADD CONSTRAINT timescales_intervals_timescales_fk FOREIGN KEY (timescale_id) REFERENCES macrostrat.timescales(id) ON DELETE CASCADE;


--
-- Name: unit_econs unit_econs_econs_fk; Type: FK CONSTRAINT; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER TABLE ONLY macrostrat.unit_econs
    ADD CONSTRAINT unit_econs_econs_fk FOREIGN KEY (econ_id) REFERENCES macrostrat.econs(id) ON DELETE CASCADE;


--
-- Name: unit_econs unit_econs_refs_fk; Type: FK CONSTRAINT; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER TABLE ONLY macrostrat.unit_econs
    ADD CONSTRAINT unit_econs_refs_fk FOREIGN KEY (ref_id) REFERENCES macrostrat.refs(id) ON DELETE CASCADE;


--
-- Name: unit_econs unit_econs_units_fk; Type: FK CONSTRAINT; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER TABLE ONLY macrostrat.unit_econs
    ADD CONSTRAINT unit_econs_units_fk FOREIGN KEY (unit_id) REFERENCES macrostrat.units(id) ON DELETE CASCADE;


--
-- Name: unit_environs unit_environs_environs_fk; Type: FK CONSTRAINT; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER TABLE ONLY macrostrat.unit_environs
    ADD CONSTRAINT unit_environs_environs_fk FOREIGN KEY (environ_id) REFERENCES macrostrat.environs(id) ON DELETE CASCADE;


--
-- Name: unit_environs unit_environs_refs_fk; Type: FK CONSTRAINT; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER TABLE ONLY macrostrat.unit_environs
    ADD CONSTRAINT unit_environs_refs_fk FOREIGN KEY (ref_id) REFERENCES macrostrat.refs(id) ON DELETE CASCADE;


--
-- Name: unit_environs unit_environs_units_fk; Type: FK CONSTRAINT; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER TABLE ONLY macrostrat.unit_environs
    ADD CONSTRAINT unit_environs_units_fk FOREIGN KEY (unit_id) REFERENCES macrostrat.units(id) ON DELETE CASCADE;


--
-- Name: unit_liths_atts unit_liths_atts_lith_atts_fk; Type: FK CONSTRAINT; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER TABLE ONLY macrostrat.unit_liths_atts
    ADD CONSTRAINT unit_liths_atts_lith_atts_fk FOREIGN KEY (lith_att_id) REFERENCES macrostrat.lith_atts(id) ON DELETE CASCADE;


--
-- Name: unit_liths_atts unit_liths_atts_unit_liths_fk; Type: FK CONSTRAINT; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER TABLE ONLY macrostrat.unit_liths_atts
    ADD CONSTRAINT unit_liths_atts_unit_liths_fk FOREIGN KEY (unit_lith_id) REFERENCES macrostrat.unit_liths(id) ON DELETE CASCADE;


--
-- Name: unit_liths unit_liths_liths_fk; Type: FK CONSTRAINT; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER TABLE ONLY macrostrat.unit_liths
    ADD CONSTRAINT unit_liths_liths_fk FOREIGN KEY (lith_id) REFERENCES macrostrat.liths(id) ON DELETE CASCADE;


--
-- Name: unit_liths unit_liths_units_fk; Type: FK CONSTRAINT; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER TABLE ONLY macrostrat.unit_liths
    ADD CONSTRAINT unit_liths_units_fk FOREIGN KEY (unit_id) REFERENCES macrostrat.units(id) ON DELETE CASCADE;


--
-- Name: unit_strat_names unit_strat_names_strat_names_fk; Type: FK CONSTRAINT; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER TABLE ONLY macrostrat.unit_strat_names
    ADD CONSTRAINT unit_strat_names_strat_names_fk FOREIGN KEY (strat_name_id) REFERENCES macrostrat.strat_names(id) ON DELETE CASCADE;


--
-- Name: unit_strat_names unit_strat_names_units_fk; Type: FK CONSTRAINT; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER TABLE ONLY macrostrat.unit_strat_names
    ADD CONSTRAINT unit_strat_names_units_fk FOREIGN KEY (unit_id) REFERENCES macrostrat.units(id) ON DELETE CASCADE;


--
-- Name: units units_cols_fk; Type: FK CONSTRAINT; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER TABLE ONLY macrostrat.units
    ADD CONSTRAINT units_cols_fk FOREIGN KEY (col_id) REFERENCES macrostrat.cols(id) ON DELETE CASCADE;


--
-- Name: units units_intervals_fo_fk; Type: FK CONSTRAINT; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER TABLE ONLY macrostrat.units
    ADD CONSTRAINT units_intervals_fo_fk FOREIGN KEY (fo) REFERENCES macrostrat.intervals(id) ON DELETE RESTRICT;


--
-- Name: units units_intervals_lo_fk; Type: FK CONSTRAINT; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER TABLE ONLY macrostrat.units
    ADD CONSTRAINT units_intervals_lo_fk FOREIGN KEY (lo) REFERENCES macrostrat.intervals(id) ON DELETE RESTRICT;


--
-- Name: units units_sections_fk; Type: FK CONSTRAINT; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER TABLE ONLY macrostrat.units
    ADD CONSTRAINT units_sections_fk FOREIGN KEY (section_id) REFERENCES macrostrat.sections(id) ON DELETE CASCADE;


--
-- Name: units_sections units_sections_sections_fk; Type: FK CONSTRAINT; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER TABLE ONLY macrostrat.units_sections
    ADD CONSTRAINT units_sections_sections_fk FOREIGN KEY (section_id) REFERENCES macrostrat.sections(id) ON DELETE CASCADE;


--
-- Name: units_sections units_sections_units_fk; Type: FK CONSTRAINT; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER TABLE ONLY macrostrat.units_sections
    ADD CONSTRAINT units_sections_units_fk FOREIGN KEY (unit_id) REFERENCES macrostrat.units(id) ON DELETE CASCADE;


--
-- Name: SEQUENCE col_areas_id_seq; Type: ACL; Schema: macrostrat; Owner: macrostrat-admin
--

GRANT SELECT,USAGE ON SEQUENCE macrostrat.col_areas_id_seq TO macrostrat;


--
-- Name: SEQUENCE col_equiv_id_seq; Type: ACL; Schema: macrostrat; Owner: macrostrat-admin
--

GRANT SELECT,USAGE ON SEQUENCE macrostrat.col_equiv_id_seq TO macrostrat;


--
-- Name: SEQUENCE col_groups_id_seq; Type: ACL; Schema: macrostrat; Owner: macrostrat-admin
--

GRANT SELECT,USAGE ON SEQUENCE macrostrat.col_groups_id_seq TO macrostrat;


--
-- Name: SEQUENCE col_notes_id_seq; Type: ACL; Schema: macrostrat; Owner: macrostrat-admin
--

GRANT SELECT,USAGE ON SEQUENCE macrostrat.col_notes_id_seq TO macrostrat;


--
-- Name: SEQUENCE col_refs_id_seq; Type: ACL; Schema: macrostrat; Owner: macrostrat-admin
--

GRANT SELECT,USAGE ON SEQUENCE macrostrat.col_refs_id_seq TO macrostrat;


--
-- Name: SEQUENCE cols_id_seq; Type: ACL; Schema: macrostrat; Owner: macrostrat-admin
--

GRANT SELECT,USAGE ON SEQUENCE macrostrat.cols_id_seq TO macrostrat;


--
-- Name: SEQUENCE econs_id_seq; Type: ACL; Schema: macrostrat; Owner: macrostrat-admin
--

GRANT SELECT,USAGE ON SEQUENCE macrostrat.econs_id_seq TO macrostrat;


--
-- Name: SEQUENCE environs_id_seq; Type: ACL; Schema: macrostrat; Owner: macrostrat-admin
--

GRANT SELECT,USAGE ON SEQUENCE macrostrat.environs_id_seq TO macrostrat;


--
-- Name: SEQUENCE intervals_id_seq; Type: ACL; Schema: macrostrat; Owner: macrostrat-admin
--

GRANT SELECT,USAGE ON SEQUENCE macrostrat.intervals_id_seq TO macrostrat;


--
-- Name: SEQUENCE intervals_new_id_seq1; Type: ACL; Schema: macrostrat; Owner: macrostrat-admin
--

GRANT SELECT,USAGE ON SEQUENCE macrostrat.intervals_new_id_seq1 TO macrostrat;


--
-- Name: SEQUENCE lith_atts_id_seq; Type: ACL; Schema: macrostrat; Owner: macrostrat-admin
--

GRANT SELECT,USAGE ON SEQUENCE macrostrat.lith_atts_id_seq TO macrostrat;


--
-- Name: SEQUENCE liths_id_seq; Type: ACL; Schema: macrostrat; Owner: macrostrat-admin
--

GRANT SELECT,USAGE ON SEQUENCE macrostrat.liths_id_seq TO macrostrat;


--
-- Name: SEQUENCE measurements_id_seq; Type: ACL; Schema: macrostrat; Owner: macrostrat-admin
--

GRANT SELECT,USAGE ON SEQUENCE macrostrat.measurements_id_seq TO macrostrat;


--
-- Name: SEQUENCE measurements_new_id_seq; Type: ACL; Schema: macrostrat; Owner: macrostrat-admin
--

GRANT SELECT,USAGE ON SEQUENCE macrostrat.measurements_new_id_seq TO macrostrat;


--
-- Name: SEQUENCE measuremeta_cols_id_seq; Type: ACL; Schema: macrostrat; Owner: macrostrat-admin
--

GRANT SELECT,USAGE ON SEQUENCE macrostrat.measuremeta_cols_id_seq TO macrostrat;


--
-- Name: SEQUENCE measuremeta_id_seq; Type: ACL; Schema: macrostrat; Owner: macrostrat-admin
--

GRANT SELECT,USAGE ON SEQUENCE macrostrat.measuremeta_id_seq TO macrostrat;


--
-- Name: SEQUENCE measuremeta_new_id_seq1; Type: ACL; Schema: macrostrat; Owner: macrostrat-admin
--

GRANT SELECT,USAGE ON SEQUENCE macrostrat.measuremeta_new_id_seq1 TO macrostrat;


--
-- Name: SEQUENCE measures_id_seq; Type: ACL; Schema: macrostrat; Owner: macrostrat-admin
--

GRANT SELECT,USAGE ON SEQUENCE macrostrat.measures_id_seq TO macrostrat;


--
-- Name: SEQUENCE measures_new_id_seq1; Type: ACL; Schema: macrostrat; Owner: macrostrat-admin
--

GRANT SELECT,USAGE ON SEQUENCE macrostrat.measures_new_id_seq1 TO macrostrat;


--
-- Name: SEQUENCE offshore_hole_ages_id_seq; Type: ACL; Schema: macrostrat; Owner: macrostrat-admin
--

GRANT SELECT,USAGE ON SEQUENCE macrostrat.offshore_hole_ages_id_seq TO macrostrat;


--
-- Name: SEQUENCE pbdb_intervals_id_seq; Type: ACL; Schema: macrostrat; Owner: macrostrat-admin
--

GRANT SELECT,USAGE ON SEQUENCE macrostrat.pbdb_intervals_id_seq TO macrostrat;


--
-- Name: SEQUENCE pbdb_matches_id_seq; Type: ACL; Schema: macrostrat; Owner: macrostrat-admin
--

GRANT SELECT,USAGE ON SEQUENCE macrostrat.pbdb_matches_id_seq TO macrostrat;


--
-- Name: SEQUENCE places_place_id_seq; Type: ACL; Schema: macrostrat; Owner: macrostrat-admin
--

GRANT SELECT,USAGE ON SEQUENCE macrostrat.places_place_id_seq TO macrostrat;


--
-- Name: SEQUENCE refs_id_seq; Type: ACL; Schema: macrostrat; Owner: macrostrat-admin
--

GRANT SELECT,USAGE ON SEQUENCE macrostrat.refs_id_seq TO macrostrat;


--
-- Name: SEQUENCE rockd_features_id_seq; Type: ACL; Schema: macrostrat; Owner: macrostrat-admin
--

GRANT SELECT,USAGE ON SEQUENCE macrostrat.rockd_features_id_seq TO macrostrat;


--
-- Name: SEQUENCE strat_names_id_seq; Type: ACL; Schema: macrostrat; Owner: macrostrat-admin
--

GRANT SELECT,USAGE ON SEQUENCE macrostrat.strat_names_id_seq TO macrostrat;


--
-- Name: SEQUENCE strat_names_meta_concept_id_seq; Type: ACL; Schema: macrostrat; Owner: macrostrat-admin
--

GRANT SELECT,USAGE ON SEQUENCE macrostrat.strat_names_meta_concept_id_seq TO macrostrat;


--
-- Name: SEQUENCE strat_names_new_id_seq; Type: ACL; Schema: macrostrat; Owner: macrostrat-admin
--

GRANT SELECT,USAGE ON SEQUENCE macrostrat.strat_names_new_id_seq TO macrostrat;


--
-- Name: SEQUENCE structure_atts_id_seq; Type: ACL; Schema: macrostrat; Owner: macrostrat-admin
--

GRANT SELECT,USAGE ON SEQUENCE macrostrat.structure_atts_id_seq TO macrostrat;


--
-- Name: SEQUENCE structures_id_seq; Type: ACL; Schema: macrostrat; Owner: macrostrat-admin
--

GRANT SELECT,USAGE ON SEQUENCE macrostrat.structures_id_seq TO macrostrat;


--
-- Name: SEQUENCE tectonics_id_seq; Type: ACL; Schema: macrostrat; Owner: macrostrat-admin
--

GRANT SELECT,USAGE ON SEQUENCE macrostrat.tectonics_id_seq TO macrostrat;


--
-- Name: SEQUENCE timescales_id_seq; Type: ACL; Schema: macrostrat; Owner: macrostrat-admin
--

GRANT SELECT,USAGE ON SEQUENCE macrostrat.timescales_id_seq TO macrostrat;


--
-- Name: SEQUENCE uniquedatafiles2_id_seq; Type: ACL; Schema: macrostrat; Owner: macrostrat-admin
--

GRANT SELECT,USAGE ON SEQUENCE macrostrat.uniquedatafiles2_id_seq TO macrostrat;


--
-- Name: SEQUENCE unit_boundaries_backup_id_seq; Type: ACL; Schema: macrostrat; Owner: macrostrat-admin
--

GRANT SELECT,USAGE ON SEQUENCE macrostrat.unit_boundaries_backup_id_seq TO macrostrat;


--
-- Name: SEQUENCE unit_boundaries_scratch_id_seq; Type: ACL; Schema: macrostrat; Owner: macrostrat-admin
--

GRANT SELECT,USAGE ON SEQUENCE macrostrat.unit_boundaries_scratch_id_seq TO macrostrat;


--
-- Name: SEQUENCE unit_boundaries_scratch_old_id_seq; Type: ACL; Schema: macrostrat; Owner: macrostrat-admin
--

GRANT SELECT,USAGE ON SEQUENCE macrostrat.unit_boundaries_scratch_old_id_seq TO macrostrat;


--
-- Name: SEQUENCE unit_contacts_id_seq; Type: ACL; Schema: macrostrat; Owner: macrostrat-admin
--

GRANT SELECT,USAGE ON SEQUENCE macrostrat.unit_contacts_id_seq TO macrostrat;


--
-- Name: SEQUENCE unit_dates_id_seq; Type: ACL; Schema: macrostrat; Owner: macrostrat-admin
--

GRANT SELECT,USAGE ON SEQUENCE macrostrat.unit_dates_id_seq TO macrostrat;


--
-- Name: SEQUENCE unit_econs_id_seq; Type: ACL; Schema: macrostrat; Owner: macrostrat-admin
--

GRANT SELECT,USAGE ON SEQUENCE macrostrat.unit_econs_id_seq TO macrostrat;


--
-- Name: SEQUENCE unit_environs_id_seq; Type: ACL; Schema: macrostrat; Owner: macrostrat-admin
--

GRANT SELECT,USAGE ON SEQUENCE macrostrat.unit_environs_id_seq TO macrostrat;


--
-- Name: SEQUENCE unit_equiv_id_seq; Type: ACL; Schema: macrostrat; Owner: macrostrat-admin
--

GRANT SELECT,USAGE ON SEQUENCE macrostrat.unit_equiv_id_seq TO macrostrat;


--
-- Name: SEQUENCE unit_liths_atts_id_seq; Type: ACL; Schema: macrostrat; Owner: macrostrat-admin
--

GRANT SELECT,USAGE ON SEQUENCE macrostrat.unit_liths_atts_id_seq TO macrostrat;


--
-- Name: SEQUENCE unit_liths_id_seq; Type: ACL; Schema: macrostrat; Owner: macrostrat-admin
--

GRANT SELECT,USAGE ON SEQUENCE macrostrat.unit_liths_id_seq TO macrostrat;


--
-- Name: SEQUENCE unit_measures_id_seq; Type: ACL; Schema: macrostrat; Owner: macrostrat-admin
--

GRANT SELECT,USAGE ON SEQUENCE macrostrat.unit_measures_id_seq TO macrostrat;


--
-- Name: SEQUENCE unit_measures_new_id_seq; Type: ACL; Schema: macrostrat; Owner: macrostrat-admin
--

GRANT SELECT,USAGE ON SEQUENCE macrostrat.unit_measures_new_id_seq TO macrostrat;


--
-- Name: SEQUENCE unit_notes_id_seq; Type: ACL; Schema: macrostrat; Owner: macrostrat-admin
--

GRANT SELECT,USAGE ON SEQUENCE macrostrat.unit_notes_id_seq TO macrostrat;


--
-- Name: SEQUENCE unit_seq_strat_id_seq; Type: ACL; Schema: macrostrat; Owner: macrostrat-admin
--

GRANT SELECT,USAGE ON SEQUENCE macrostrat.unit_seq_strat_id_seq TO macrostrat;


--
-- Name: SEQUENCE unit_strat_names_id_seq; Type: ACL; Schema: macrostrat; Owner: macrostrat-admin
--

GRANT SELECT,USAGE ON SEQUENCE macrostrat.unit_strat_names_id_seq TO macrostrat;


--
-- Name: SEQUENCE unit_strat_names_new_id_seq1; Type: ACL; Schema: macrostrat; Owner: macrostrat-admin
--

GRANT SELECT,USAGE ON SEQUENCE macrostrat.unit_strat_names_new_id_seq1 TO macrostrat;


--
-- Name: SEQUENCE unit_tectonics_id_seq; Type: ACL; Schema: macrostrat; Owner: macrostrat-admin
--

GRANT SELECT,USAGE ON SEQUENCE macrostrat.unit_tectonics_id_seq TO macrostrat;


--
-- Name: SEQUENCE units_id_seq; Type: ACL; Schema: macrostrat; Owner: macrostrat-admin
--

GRANT SELECT,USAGE ON SEQUENCE macrostrat.units_id_seq TO macrostrat;


--
-- Name: SEQUENCE units_sections_id_seq; Type: ACL; Schema: macrostrat; Owner: macrostrat-admin
--

GRANT SELECT,USAGE ON SEQUENCE macrostrat.units_sections_id_seq TO macrostrat;


--
-- Name: SEQUENCE units_sections_new_id_seq; Type: ACL; Schema: macrostrat; Owner: macrostrat-admin
--

GRANT SELECT,USAGE ON SEQUENCE macrostrat.units_sections_new_id_seq TO macrostrat;


--
-- Name: DEFAULT PRIVILEGES FOR SEQUENCES; Type: DEFAULT ACL; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER DEFAULT PRIVILEGES FOR ROLE "macrostrat-admin" IN SCHEMA macrostrat GRANT SELECT,USAGE ON SEQUENCES  TO macrostrat;


--
-- Name: DEFAULT PRIVILEGES FOR TABLES; Type: DEFAULT ACL; Schema: macrostrat; Owner: macrostrat-admin
--

ALTER DEFAULT PRIVILEGES FOR ROLE "macrostrat-admin" IN SCHEMA macrostrat GRANT SELECT ON TABLES  TO macrostrat;


--
-- PostgreSQL database dump complete
--

