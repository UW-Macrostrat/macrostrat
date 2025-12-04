-- PostgreSQL database dump
-- Dumped from database version 15.3
-- Dumped by pg_dump version 15.5 (Debian 15.5-1.pgdg120+1)
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
-- Name: auth; Type: SCHEMA; Schema: -; Owner: macrostrat
CREATE SCHEMA auth;

-- Name: carto; Type: SCHEMA; Schema: -; Owner: macrostrat
CREATE SCHEMA carto;

-- Name: carto_new; Type: SCHEMA; Schema: -; Owner: macrostrat
CREATE SCHEMA carto_new;

-- Name: corelle_macrostrat; Type: SCHEMA; Schema: -; Owner: macrostrat
CREATE SCHEMA corelle_macrostrat;

-- Name: detrital_zircon; Type: SCHEMA; Schema: -; Owner: macrostrat
CREATE SCHEMA detrital_zircon;

-- Name: geologic_boundaries; Type: SCHEMA; Schema: -; Owner: macrostrat
CREATE SCHEMA geologic_boundaries;

-- Name: hexgrids; Type: SCHEMA; Schema: -; Owner: macrostrat
CREATE SCHEMA hexgrids;

-- Name: lines; Type: SCHEMA; Schema: -; Owner: macrostrat
CREATE SCHEMA lines;

-- Name: macrostrat; Type: SCHEMA; Schema: -; Owner: macrostrat
CREATE SCHEMA macrostrat;

-- Name: macrostrat_api; Type: SCHEMA; Schema: -; Owner: macrostrat
CREATE SCHEMA macrostrat_api;

-- Name: macrostrat_auth; Type: SCHEMA; Schema: -; Owner: macrostrat
CREATE SCHEMA macrostrat_auth;

-- Name: macrostrat_kg; Type: SCHEMA; Schema: -; Owner: macrostrat
CREATE SCHEMA macrostrat_kg;

-- Name: maps; Type: SCHEMA; Schema: -; Owner: macrostrat
CREATE SCHEMA maps;

-- Name: maps_metadata; Type: SCHEMA; Schema: -; Owner: macrostrat-admin
CREATE SCHEMA maps_metadata;

-- Name: points; Type: SCHEMA; Schema: -; Owner: macrostrat
CREATE SCHEMA points;

-- Name: tile_cache; Type: SCHEMA; Schema: -; Owner: macrostrat
CREATE SCHEMA tile_cache;

-- Name: tile_layers; Type: SCHEMA; Schema: -; Owner: macrostrat
CREATE SCHEMA tile_layers;

-- Name: tile_utils; Type: SCHEMA; Schema: -; Owner: macrostrat
CREATE SCHEMA tile_utils;

-- Name: topology; Type: SCHEMA; Schema: -; Owner: macrostrat
CREATE SCHEMA topology;

-- Name: SCHEMA topology; Type: COMMENT; Schema: -; Owner: macrostrat
COMMENT ON SCHEMA topology IS 'PostGIS Topology schema';

-- Name: weaver_api; Type: SCHEMA; Schema: -; Owner: macrostrat
CREATE SCHEMA weaver_api;

-- Name: weaver_macrostrat; Type: SCHEMA; Schema: -; Owner: macrostrat
CREATE SCHEMA weaver_macrostrat;

-- Name: pg_stat_statements; Type: EXTENSION; Schema: -; Owner: -
CREATE EXTENSION IF NOT EXISTS pg_stat_statements WITH SCHEMA public;

-- Name: EXTENSION pg_stat_statements; Type: COMMENT; Schema: -; Owner: 
COMMENT ON EXTENSION pg_stat_statements IS 'track planning and execution statistics of all sql statements executed';

-- Name: pgaudit; Type: EXTENSION; Schema: -; Owner: -
CREATE EXTENSION IF NOT EXISTS pgaudit WITH SCHEMA public;

-- Name: EXTENSION pgaudit; Type: COMMENT; Schema: -; Owner: 
COMMENT ON EXTENSION pgaudit IS 'provides auditing functionality';

-- Name: postgis; Type: EXTENSION; Schema: -; Owner: -
CREATE EXTENSION IF NOT EXISTS postgis WITH SCHEMA public;

-- Name: EXTENSION postgis; Type: COMMENT; Schema: -; Owner: 
COMMENT ON EXTENSION postgis IS 'PostGIS geometry, geography, and raster spatial types and functions';

-- Name: postgis_raster; Type: EXTENSION; Schema: -; Owner: -
CREATE EXTENSION IF NOT EXISTS postgis_raster WITH SCHEMA public;

-- Name: EXTENSION postgis_raster; Type: COMMENT; Schema: -; Owner: 
COMMENT ON EXTENSION postgis_raster IS 'PostGIS raster types and functions';

-- Name: postgis_topology; Type: EXTENSION; Schema: -; Owner: -
CREATE EXTENSION IF NOT EXISTS postgis_topology WITH SCHEMA topology;

-- Name: EXTENSION postgis_topology; Type: COMMENT; Schema: -; Owner: 
COMMENT ON EXTENSION postgis_topology IS 'PostGIS topology spatial types and functions';

-- Name: postgres_fdw; Type: EXTENSION; Schema: -; Owner: -
CREATE EXTENSION IF NOT EXISTS postgres_fdw WITH SCHEMA public;

-- Name: EXTENSION postgres_fdw; Type: COMMENT; Schema: -; Owner: 
COMMENT ON EXTENSION postgres_fdw IS 'foreign-data wrapper for remote PostgreSQL servers';

-- Name: uuid-ossp; Type: EXTENSION; Schema: -; Owner: -
CREATE EXTENSION IF NOT EXISTS "uuid-ossp" WITH SCHEMA public;

-- Name: EXTENSION "uuid-ossp"; Type: COMMENT; Schema: -; Owner: 
COMMENT ON EXTENSION "uuid-ossp" IS 'generate universally unique identifiers (UUIDs)';

-- Name: boundary_status; Type: TYPE; Schema: macrostrat; Owner: macrostrat
CREATE TYPE macrostrat.boundary_status AS ENUM (
    '',
    'modeled',
    'relative',
    'absolute',
    'spike'
);

-- Name: boundary_type; Type: TYPE; Schema: macrostrat; Owner: macrostrat
CREATE TYPE macrostrat.boundary_type AS ENUM (
    '',
    'unconformity',
    'conformity',
    'fault',
    'disconformity',
    'non-conformity',
    'angular unconformity'
);

-- Name: map_scale; Type: TYPE; Schema: macrostrat; Owner: macrostrat
CREATE TYPE macrostrat.map_scale AS ENUM (
    'tiny',
    'small',
    'medium',
    'large'
);

-- Name: schemeenum; Type: TYPE; Schema: macrostrat; Owner: macrostrat
CREATE TYPE macrostrat.schemeenum AS ENUM (
    'http',
    's3'
);

-- Name: measurement_class; Type: TYPE; Schema: public; Owner: macrostrat
CREATE TYPE public.measurement_class AS ENUM (
    '',
    'geophysical',
    'geochemical',
    'sedimentological'
);

-- Name: measurement_class_new; Type: TYPE; Schema: public; Owner: macrostrat
CREATE TYPE public.measurement_class_new AS ENUM (
    '',
    'geophysical',
    'geochemical',
    'sedimentological'
);

-- Name: measurement_type; Type: TYPE; Schema: public; Owner: macrostrat
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

-- Name: measurement_type_new; Type: TYPE; Schema: public; Owner: macrostrat
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

-- Name: antimeridian_split(public.geometry); Type: FUNCTION; Schema: corelle_macrostrat; Owner: macrostrat
CREATE FUNCTION corelle_macrostrat.antimeridian_split(geom public.geometry) RETURNS public.geometry
    LANGUAGE plpgsql STABLE
    AS $$
DECLARE
  g1 geometry;
  meridian geometry;
BEGIN
  g1 := ST_MakeValid(geom);
  g1 := ST_WrapX(g1, -180, 180);
  g1 := ST_WrapX(g1, 180, -180);
  RETURN g1;
EXCEPTION WHEN OTHERS THEN
  RETURN null;
END;
$$;

-- Name: build_tile_geom(public.geometry, numeric[], integer, integer, integer); Type: FUNCTION; Schema: corelle_macrostrat; Owner: macrostrat
CREATE FUNCTION corelle_macrostrat.build_tile_geom(geom public.geometry, rotation numeric[], _x integer, _y integer, _z integer) RETURNS public.geometry
    LANGUAGE plpgsql STABLE
    AS $$
DECLARE
  tile_geom geometry;
BEGIN
  -- Pre-simplify the geometry to reduce the size of the tile
  --geom := ST_SnapToGrid(geom, 0.001/pow(2,_z));
  tile_geom := corelle_macrostrat.rotate(geom, rotation, true);
  --END IF;
  --tile_geom := ST_WrapX(tile_geom, 0, wrap);
  RETURN ST_Simplify(
    ST_AsMVTGeom(
      ST_Transform(
        tile_geom,
        3857
      ),
      ST_TileEnvelope(_z,_x,_y),
      4096,
      12,
      true
    ),
    8
  );
END;
$$;

-- Name: carto_slim_rotated(integer, integer, integer, json); Type: FUNCTION; Schema: corelle_macrostrat; Owner: macrostrat
CREATE FUNCTION corelle_macrostrat.carto_slim_rotated(x integer, y integer, z integer, query_params json) RETURNS bytea
    LANGUAGE plpgsql
    AS $$
DECLARE
srid integer;
features record;
linesize text[];
mercator_bbox geometry;
projected_bbox geometry;
bedrock bytea;
result bytea;
lines bytea;
tolerance double precision;
_t_step integer;
_model_id integer;
_scale macrostrat.map_scale;
BEGIN
-- Get the time step and model requested from the query parameters
SELECT
  coalesce((query_params->>'t_step')::integer, 0) AS _t_step,
  (query_params->>'model_id')::integer AS _model_id
INTO _t_step, _model_id;
IF _model_id IS NULL THEN
  RAISE EXCEPTION 'model_id is required';
END IF;

mercator_bbox := tile_utils.envelope(x, y, z);
tolerance := 6;
projected_bbox := ST_Transform(mercator_bbox, 4326);
IF z < 3 THEN
  -- Select from carto.tiny table
  _scale := 'tiny'::map_scale;
ELSIF z < 6 THEN
  _scale := 'small'::map_scale;
ELSIF z < 9 THEN
  _scale := 'medium'::map_scale;
ELSE
  _scale := 'large'::map_scale;
END IF;
WITH rotated_plates AS (
  SELECT
    pp.plate_id,
    pp.model_id,
    pp.id plate_polygon_id,
    corelle_macrostrat.rotate_to_web_mercator(geom_simple, rotation, true) geom_merc,
    geometry,
    rc.rotation
  FROM corelle.plate_polygon pp
  JOIN corelle.rotation_cache rc
   ON rc.model_id = pp.model_id
  AND rc.plate_id = pp.plate_id
  AND rc.t_step = _t_step
  AND pp.model_id = _model_id
  AND coalesce(pp.old_lim, 4000) >= _t_step
  AND coalesce(pp.young_lim, 0) <= _t_step
),
relevant_plates AS (
  SELECT
    plate_id,
    model_id,
    plate_polygon_id,
    geom_merc,
    rotation,
    corelle.rotate_geometry(
      ST_Segmentize(projected_bbox, 0.5),
      corelle.invert_rotation(rotation)
    ) tile_geom
  FROM rotated_plates
  WHERE ST_Intersects(geom_merc, mercator_bbox)
),
units AS (
  -- We need this distinct because we have duplicates somewhere in our pipeline
  SELECT DISTINCT ON (u.map_id, u.source_id, cpi.plate_id, cpi.plate_polygon_id)
    u.map_id,
    u.source_id,
    cpi.plate_id,
    rp.rotation,
    cpi.plate_polygon_id,
    corelle_macrostrat.rotate_to_web_mercator(
       coalesce(cpi.geom, u.geom),
       rp.rotation,
       TRUE
    ) geom
  FROM relevant_plates rp
  JOIN corelle_macrostrat.carto_plate_index cpi
    ON cpi.plate_polygon_id = rp.plate_polygon_id
   AND cpi.scale = _scale
  JOIN carto.polygons u
    ON u.map_id = cpi.map_id
   AND u.scale = _scale
   -- This causes tile-boundary errors
  WHERE _scale = 'tiny'::macrostrat.map_scale OR ST_Intersects(coalesce(cpi.geom, u.geom), tile_geom)
),
bedrock_ AS (
  SELECT DISTINCT ON (u.map_id, u.source_id, u.plate_id, u.plate_polygon_id)
    u.map_id,
    u.source_id,
    u.plate_id,
    u.plate_polygon_id,
    l.*, -- legend info
    tile_layers.tile_geom(
      u.geom,
      mercator_bbox
    ) geom
  FROM units u
  JOIN maps.map_legend
    ON u.map_id = map_legend.map_id
  JOIN tile_layers.map_legend_info AS l
    ON l.legend_id = map_legend.legend_id
  WHERE ST_Intersects(u.geom, mercator_bbox)
    -- Get rid of young units
    AND l.best_age_bottom >= _t_step
),
plates_ AS (
  SELECT
    plate_id,
    model_id,
    tile_layers.tile_geom(geom_merc, mercator_bbox) AS geom
  FROM relevant_plates
)
SELECT
 (SELECT ST_AsMVT(plates_, 'plates') FROM plates_) ||
 (SELECT ST_AsMVT(bedrock_, 'units') FROM bedrock_)
INTO result;
RETURN result;
END;
$$;

-- Name: carto_slim_rotated_v1(integer, integer, integer, json); Type: FUNCTION; Schema: corelle_macrostrat; Owner: macrostrat
CREATE FUNCTION corelle_macrostrat.carto_slim_rotated_v1(x integer, y integer, z integer, query_params json) RETURNS bytea
    LANGUAGE plpgsql
    AS $$
DECLARE
srid integer;
features record;
mapsize text;
linesize text[];
mercator_bbox geometry;
min_feature_size numeric;
tile_width numeric;
bedrock bytea;
lines bytea;
_t_step integer;
_model_id integer;
BEGIN
-- Get the time step and model requested from the query parameters
SELECT
  coalesce((query_params->>'t_step')::integer, 0) AS _t_step,
  (query_params->>'model_id')::integer AS _model_id
INTO _t_step, _model_id;
IF _t_step = 0 THEN
  /* Just return the basic map layer */
  return tile_layers.carto_slim(x, y, z, query_params);
END IF;
IF _model_id IS NULL THEN
  RAISE EXCEPTION 'model_id is required';
END IF;
IF z < 3 THEN
  -- Select from carto.tiny table
  mapsize := 'tiny';
  linesize := ARRAY['tiny'];
ELSIF z < 6 THEN
  mapsize := 'small';
  linesize := ARRAY['tiny', 'small'];
ELSIF z < 9 THEN
  mapsize := 'medium';
  linesize := ARRAY['small', 'medium'];
ELSE
  mapsize := 'large';
  linesize := ARRAY['medium', 'large'];
END IF;
--wrap_bbox := NOT z = 0;
-- Units
WITH rotation_info AS (
  SELECT
    pp.model_id,
    pp.plate_id,
    pp.geometry,
    rc.rotation,
    rc.t_step,
    -- Get the tile bounding box rotated to the actual position of the plate on the modern globe
    corelle_macrostrat.tile_envelope(rotation, x, y, z) tile_envelope
  FROM corelle.plate_polygon pp
  JOIN corelle.rotation_cache rc
    ON rc.model_id = pp.model_id
   AND rc.plate_id = pp.plate_id
  WHERE pp.model_id = _model_id
  	AND t_step = _t_step
    AND pp.geometry && corelle_macrostrat.tile_envelope(rotation, x, y, z)
    --AND ST_Intersects(pp.geometry, corelle_macrostrat.tile_envelope(rotation, x, y, z))
),
plate_polygons AS (
  SELECT
    plate_id,
    t_step,
    corelle_macrostrat.build_tile_geom(
      ri.geometry, ri.rotation, x, y, z
    ) geom
  FROM rotation_info ri
),
u1 AS (
  SELECT ST_AsMVT(pp, 'plates') mvt1
  FROM plate_polygons pp
)
SELECT mvt1 AS mvt
FROM u1
INTO bedrock; --, plate_polygons;
RETURN bedrock;
END;
$$;

-- Name: igcp_orogens(integer, integer, integer, json); Type: FUNCTION; Schema: corelle_macrostrat; Owner: macrostrat
CREATE FUNCTION corelle_macrostrat.igcp_orogens(x integer, y integer, z integer, query_params json) RETURNS bytea
    LANGUAGE plpgsql STABLE PARALLEL SAFE
    AS $$
DECLARE
  tile bytea;
  envelope geometry;
BEGIN
  envelope := ST_TileEnvelope(z, x, y);
  WITH a AS (
  SELECT
    ST_AsMVTGeom(
      ST_Transform(
        corelle_macrostrat.rotate(
          p.geometry, ARRAY[1,0,0,0],
          true
        ), 3857), envelope, 4096, 8, true) AS geometry,
    name,
    t_age,
    b_age,
    interval_id,
    color
  FROM sources.igcp_orogens_polygons p
  WHERE p.geometry && ST_Transform(envelope, 4326)
  )
  SELECT ST_AsMVT(a.*, 'units') FROM a INTO tile;
  RETURN tile;
END;
$$;

-- Name: igcp_orogens_rotated(integer, integer, integer, json); Type: FUNCTION; Schema: corelle_macrostrat; Owner: macrostrat
CREATE FUNCTION corelle_macrostrat.igcp_orogens_rotated(x integer, y integer, z integer, query_params json) RETURNS bytea
    LANGUAGE plpgsql STABLE PARALLEL SAFE
    AS $$
DECLARE
  geom geometry;
BEGIN
  SELECT
    ST_AsMVTGeom(geom, ST_TileEnvelope(x, y, z), 4096, 8, true),
    color
  FROM corelle_macrostrat.igcp_orogens_index
  INTO geom;
  RETURN ST_AsMVT(geom, 'burwell', 4096, 'geom');
END;
$$;

-- Name: rotate(public.geometry, double precision[], boolean); Type: FUNCTION; Schema: corelle_macrostrat; Owner: macrostrat
CREATE FUNCTION corelle_macrostrat.rotate(geom public.geometry, rotation double precision[], wrap boolean DEFAULT false) RETURNS public.geometry
    LANGUAGE plpgsql
    AS $$
DECLARE
  g1 geometry;
BEGIN
  g1 := corelle.rotate_geometry(geom, rotation);
  -- Heuristic to determine if the geometry crosses the antimeridian
  -- https://gis.stackexchange.com/questions/182728/how-can-i-convert-postgis-geography-to-geometry-and-split-polygons-that-cross-th
  -- https://macwright.com/2016/09/26/the-180th-meridian.html
  -- This has to be run for each tile, because a lot of geometries that
  -- don't properly intersect the tile are still included due to polygon winding effects.
  -- We really should figure out how to exclude geometries with no points
  -- in the tile envelope, so we don't have to run this check on every tile
  RETURN corelle_macrostrat.antimeridian_split(g1);
END;
$$;

-- Name: rotate_to_web_mercator(public.geometry, double precision[], boolean); Type: FUNCTION; Schema: corelle_macrostrat; Owner: macrostrat
CREATE FUNCTION corelle_macrostrat.rotate_to_web_mercator(geom public.geometry, rotation double precision[], wrap boolean DEFAULT false) RETURNS public.geometry
    LANGUAGE plpgsql
    AS $$
DECLARE
  proj_string text;
  proj_string2 text;
  g1 geometry;
  g2 geometry;
  threshold double precision;
  new_rotation double precision[];
BEGIN
  proj_string := corelle.build_proj_string(rotation, '+R=6378137 +o_proj=merc ');
  g1 := ST_SetSRID(ST_Transform(geom, proj_string), 3857);
  threshold := pi() * 6378137;
  IF ST_XMax(g1) - ST_XMin(g1) > 1.8 * threshold THEN
    -- Rotate to the other side of the globe
    proj_string := corelle.build_proj_string(rotation, '+R=6378137 +o_proj=merc ', pi());
    g1 := ST_SetSRID(ST_Transform(geom, proj_string), 3857);
    g1 := ST_Union(
      ST_Translate(g1, -threshold, 0),
      ST_Translate(g1, threshold, 0)
    );
  END IF;
  RETURN g1;
EXCEPTION WHEN OTHERS THEN
  RETURN null;
END;
$$;

-- Name: tile_envelope(numeric[], integer, integer, integer); Type: FUNCTION; Schema: corelle_macrostrat; Owner: macrostrat
CREATE FUNCTION corelle_macrostrat.tile_envelope(rotation numeric[], x integer, y integer, z integer) RETURNS public.geometry
    LANGUAGE plpgsql
    AS $$
DECLARE
  modern_bbox geometry;
BEGIN
  modern_bbox := ST_Transform(ST_TileEnvelope(z, x, y), 4326);
  -- I feel like this bbox needs to be inverted but it seems to work better if not...
  RETURN corelle_macrostrat.rotate(
    modern_bbox,
    corelle.invert_rotation(rotation),
    false
  );
END;
$$;

-- Name: get_lith_comp_prop(integer); Type: FUNCTION; Schema: macrostrat; Owner: macrostrat
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

-- Name: update_unit_lith_comp_props(integer); Type: FUNCTION; Schema: macrostrat; Owner: macrostrat
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

-- Name: update_updated_on(); Type: FUNCTION; Schema: macrostrat; Owner: macrostrat
CREATE FUNCTION macrostrat.update_updated_on() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    NEW.updated_on = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$;

-- Name: combine_sections(integer[]); Type: FUNCTION; Schema: macrostrat_api; Owner: macrostrat
CREATE FUNCTION macrostrat_api.combine_sections(section_ids integer[]) RETURNS void
    LANGUAGE plpgsql
    AS $$
BEGIN
  IF array_length(section_ids, 1) < 2 THEN
    RAISE EXCEPTION 'Not enough section_ids';
  END IF;
  -- arbitrarily choose first section_id to combine into
  UPDATE macrostrat.units
  SET
    section_id = section_ids[1]
  WHERE section_id = ANY(section_ids);
  -- delete from sections table for rest of ids
  DELETE FROM macrostrat.sections
  WHERE id = ANY(section_ids[2:]);
END
$$;

-- Name: get_col_section_data(integer); Type: FUNCTION; Schema: macrostrat_api; Owner: macrostrat
CREATE FUNCTION macrostrat_api.get_col_section_data(column_id integer) RETURNS TABLE(id integer, unit_count bigint, top character varying, bottom character varying)
    LANGUAGE plpgsql
    AS $$
BEGIN 
RETURN QUERY
    SELECT 
        s.id,
        COUNT(uc) as unit_count,
        lo.interval_name as top,
        fo.interval_name as bottom
    FROM macrostrat.sections s 
    JOIN macrostrat.units uc 
      ON uc.section_id = s.id
    JOIN macrostrat.units u 
      ON u.section_id = s.id
    JOIN macrostrat.units un
      ON un.section_id = s.id
    JOIN macrostrat.intervals fo
      ON un.fo = fo.id
    JOIN macrostrat.intervals lo
      ON u.lo = lo.id
    WHERE u.position_bottom = (
        SELECT MIN(position_bottom) FROM macrostrat.units WHERE section_id = u.section_id
    ) AND un.position_bottom = (
        SELECT MAX(position_bottom) FROM macrostrat.units WHERE section_id = un.section_id
    ) AND s.col_id = column_id
    GROUP BY s.id, lo.interval_name, fo.interval_name, fo.age_bottom ORDER BY fo.age_bottom
    ;
END
$$;

-- Name: get_col_strat_names(integer); Type: FUNCTION; Schema: macrostrat_api; Owner: macrostrat
CREATE FUNCTION macrostrat_api.get_col_strat_names(_col_id integer) RETURNS TABLE(id integer, strat_name character varying, rank character varying, ref_id integer, concept_id integer, author character varying, source text)
    LANGUAGE plpgsql
    AS $$
BEGIN
  RETURN QUERY 
  WITH a AS(
SELECT cc.*, ST_Distance(
	ST_Transform(c.coordinate, 3857), 
	ST_Transform(cc.coordinate, 3857)
	) 
	as distance FROM macrostrat.cols c
JOIN macrostrat.cols cc
	ON c.col_group_id = cc.col_group_id
WHERE c.id = _col_id
), b AS(
  SELECT c.col_name from macrostrat.cols c WHERE c.id = _col_id
)
SELECT sn.*, r.author, b.col_name::text as source from b,macrostrat_api.units u 
JOIN macrostrat_api.unit_strat_names usn
 ON u.id = usn.unit_id
JOIN macrostrat_api.strat_names sn
 ON usn.strat_name_id = sn.id
JOIN macrostrat_api.refs r
  ON r.id = sn.ref_id
WHERE u.col_id = _col_id 
AND sn.concept_id IS NULL
UNION ALL
SELECT DISTINCT ON(sn.id) sn.*, r.author, a.col_name::text as source 
FROM a, macrostrat_api.units u 
JOIN macrostrat_api.unit_strat_names usn
 ON u.id = usn.unit_id
JOIN macrostrat_api.strat_names sn
 ON usn.strat_name_id = sn.id
JOIN macrostrat_api.refs r
  ON r.id = sn.ref_id
WHERE u.col_id = _col_id AND sn.concept_id IS NULL or u.col_id = a.id
AND sn.concept_id IS NULL
UNION ALL
SELECT DISTINCT ON(sn.id) sn.*, r.author, 'nearby' as source FROM macrostrat.strat_names sn 
  LEFT JOIN macrostrat.strat_names_meta snm
  ON sn.concept_id = snm.concept_id
  LEFT JOIN macrostrat.refs r
  ON r.id = snm.ref_id
  WHERE ST_Intersects(r.rgeom, (
  	select ST_SetSrid((coordinate)::geometry, 4326) 
  	from macrostrat.cols c where c.id = _col_id
  	)
)
UNION ALL
SELECT DISTINCT ON(sn.id) sn.*, r.author, 'unrelated' as source 
FROM macrostrat_api.units u 
JOIN macrostrat_api.unit_strat_names usn
 ON u.id = usn.unit_id
JOIN macrostrat_api.strat_names sn
 ON usn.strat_name_id = sn.id
JOIN macrostrat_api.refs r
  ON r.id = sn.ref_id
WHERE u.col_id NOT IN (SELECT a.id FROM a) 
	AND sn.concept_id IS NULL 
	AND r.rgeom IS NULL
;
END
$$;

-- Name: get_strat_name_info(integer); Type: FUNCTION; Schema: macrostrat_api; Owner: macrostrat
CREATE FUNCTION macrostrat_api.get_strat_name_info(strat_name_id integer) RETURNS TABLE(id integer, strat_name character varying, rank character varying, author character varying, parent text)
    LANGUAGE plpgsql
    AS $$
BEGIN
RETURN QUERY
  SELECT 
  sn.id, 
  sn.strat_name, 
  sn.rank,
  sn.concept_id,
  r.author,
  st.strat_name ||' '|| st.rank as parent 
  FROM macrostrat.strat_names sn
  JOIN macrostrat.strat_names_meta snm
    ON sn.concept_id = snm.concept_id
  JOIN macrostrat.refs r
    ON r.id = snm.ref_id
  JOIN macrostrat.strat_tree tree
    ON tree.child = sn.id
  JOIN macrostrat.strat_names st
    ON st.id = tree.parent
  WHERE sn.id = strat_name_id
    ;
END
$$;

-- Name: get_strat_names_col_priority(integer); Type: FUNCTION; Schema: macrostrat_api; Owner: macrostrat
CREATE FUNCTION macrostrat_api.get_strat_names_col_priority(_col_id integer) RETURNS TABLE(id integer, strat_name character varying, rank character varying, ref_id integer, concept_id integer, author character varying, source text, parent text)
    LANGUAGE plpgsql
    AS $$
BEGIN
  RETURN QUERY
    SELECT 
    gc.*, 
    st.strat_name ||' '|| st.rank as parent 
    FROM macrostrat_api.get_col_strat_names(_col_id) gc
    LEFT JOIN macrostrat.strat_tree tree
    ON tree.child = gc.id
    LEFT JOIN macrostrat.strat_names st
    ON st.id = tree.parent
    ;
END
$$;

-- Name: split_section(integer[]); Type: FUNCTION; Schema: macrostrat_api; Owner: macrostrat
CREATE FUNCTION macrostrat_api.split_section(unit_ids integer[]) RETURNS void
    LANGUAGE plpgsql
    AS $$
DECLARE
  _col_id integer;
  _section_id integer;
BEGIN
  SELECT col_id FROM macrostrat.units WHERE id = unit_ids[0] INTO _col_id;
  INSERT INTO macrostrat.sections(col_id) VALUES (_col_id) RETURNING id INTO _section_id;
  UPDATE macrostrat.units
    SET 
      section_id = _section_id
    WHERE id = ANY(unit_ids); 
END
$$;

-- Name: lines_geom_is_valid(public.geometry); Type: FUNCTION; Schema: maps; Owner: macrostrat
CREATE FUNCTION maps.lines_geom_is_valid(geom public.geometry) RETURNS boolean
    LANGUAGE sql IMMUTABLE
    AS $$
  SELECT ST_IsValid(geom) AND ST_GeometryType(geom) IN ('ST_LineString', 'ST_MultiLineString');
$$;

-- Name: polygons_geom_is_valid(public.geometry); Type: FUNCTION; Schema: maps; Owner: macrostrat
CREATE FUNCTION maps.polygons_geom_is_valid(geom public.geometry) RETURNS boolean
    LANGUAGE sql IMMUTABLE
    AS $$
  SELECT ST_IsValid(geom) AND ST_GeometryType(geom) IN ('ST_Polygon', 'ST_MultiPolygon');
$$;

-- Name: maps_metadata_update_trigger(); Type: FUNCTION; Schema: maps_metadata; Owner: kateakin
CREATE FUNCTION maps_metadata.maps_metadata_update_trigger() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
	UPDATE
		maps_metadata.sources
	SET
		raster_source_url = NEW.raster_source_url,
		raster_bucket_url = NEW.raster_bucket_url,
		compiler_name = NEW.compiler_name,
		date_compiled = NEW.date_compiled
	WHERE source_id = NEW.source_id;
	RETURN NEW;
END;
$$;

-- Name: count_estimate(text); Type: FUNCTION; Schema: public; Owner: macrostrat
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

-- Name: update_updated_on(); Type: FUNCTION; Schema: public; Owner: postgres
CREATE FUNCTION public.update_updated_on() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    NEW.updated_on = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$;

-- Name: remove_excess_tiles(bigint); Type: FUNCTION; Schema: tile_cache; Owner: macrostrat
CREATE FUNCTION tile_cache.remove_excess_tiles(max_size bigint DEFAULT 100000) RETURNS void
    LANGUAGE plpgsql
    AS $$
DECLARE
  _current_size bigint;
  _num_deleted integer;
BEGIN
  /** Delete the most stale tiles until fewer than max_size tiles remain. */
  -- Get approximate size of cache
  SELECT pg_total_relation_size('tile_cache.tile') INTO _current_size;
  -- Get approximate number of tiles in cache table (without full table scan)
  SELECT reltuples::bigint AS estimate
  FROM pg_class
  WHERE oid = 'tile_cache.tile'::regclass
  INTO _current_size;
  -- Delete tiles until cache size is less than max_size
  _num_deleted := _current_size - max_size;
  IF _current_size > max_size THEN
    DELETE FROM tile_cache.tile
    WHERE last_used < (
      SELECT last_used FROM tile_cache.tile
      ORDER BY last_used ASC
      LIMIT 1
      OFFSET _num_deleted
    );
    RAISE NOTICE 'Deleted % tiles to reduce cache size', _num_deleted;
  END IF;
END;
$$;

-- Name: all_maps(integer, integer, integer, json); Type: FUNCTION; Schema: tile_layers; Owner: macrostrat
CREATE FUNCTION tile_layers.all_maps(x integer, y integer, z integer, query_params json) RETURNS bytea
    LANGUAGE plpgsql IMMUTABLE
    AS $$
DECLARE
srid integer;
features record;
mapsize text;
linesize text[];
mercator_bbox geometry;
projected_bbox geometry;
bedrock bytea;
lines bytea;
tolerance double precision;
BEGIN
mercator_bbox := tile_utils.envelope(x, y, z);
tolerance := 6;
projected_bbox := ST_Transform(
  mercator_bbox,
  4326
);
-- Get map size
IF z < 3 THEN
  -- Select from carto.tiny table
  mapsize := 'tiny';
  linesize := ARRAY['tiny'];
ELSIF z < 6 THEN
  mapsize := 'small';
  linesize := ARRAY['tiny', 'small'];
ELSIF z < 9 THEN
  mapsize := 'medium';
  linesize := ARRAY['small', 'medium'];
ELSE
  mapsize := 'large';
  linesize := ARRAY['medium', 'large'];
END IF;

-- Units
WITH mvt_features AS (
  SELECT
    map_id,
    source_id,
    geom
  FROM
    tile_layers.map_units
  WHERE scale = mapsize
    AND ST_Intersects(geom, projected_bbox)
), expanded AS (
  SELECT
    z.map_id,
    z.source_id,
    l.*, -- map legend info
    tile_layers.tile_geom(z.geom, mercator_bbox) AS geom
  FROM mvt_features z
    LEFT JOIN maps.map_legend ON z.map_id = map_legend.map_id
    LEFT JOIN tile_layers.map_legend_info AS l
      ON l.legend_id = map_legend.legend_id
)
SELECT
  ST_AsMVT(expanded, 'units')
INTO bedrock
FROM expanded;
-- LINES
WITH mvt_features AS (
  SELECT
    line_id,
    source_id,
    geom
  FROM
    tile_layers.map_lines
  WHERE scale = mapsize
    AND ST_Intersects(geom, projected_bbox)
),
expanded AS (
  SELECT
    z.line_id,
    z.source_id,
    coalesce(q.descrip, '') AS descrip,
    coalesce(q.name, '') AS name,
    coalesce(q.direction, '') AS direction,
    coalesce(q.type, '') AS "type",
    tile_layers.tile_geom(z.geom, mercator_bbox) AS geom
  FROM mvt_features z
  LEFT JOIN tile_layers.line_data q
    ON z.line_id = q.line_id
  WHERE q.scale = ANY(linesize)
    --AND ST_Length(geom) > tolerance
)
SELECT
  ST_AsMVT(expanded, 'lines') INTO lines
FROM expanded;
RETURN bedrock || lines;
END;
$$;

-- Name: carto(integer, integer, integer, json); Type: FUNCTION; Schema: tile_layers; Owner: macrostrat
CREATE FUNCTION tile_layers.carto(x integer, y integer, z integer, query_params json) RETURNS bytea
    LANGUAGE plpgsql IMMUTABLE
    AS $$
DECLARE
srid integer;
features record;
mapsize text;
linesize text[];
mercator_bbox geometry;
projected_bbox geometry;
bedrock bytea;
lines bytea;
BEGIN
mercator_bbox := tile_utils.envelope(x, y, z);
projected_bbox := ST_Transform(
  mercator_bbox,
  4326
);
IF z < 3 THEN
  -- Select from carto.tiny table
  mapsize := 'tiny';
  linesize := ARRAY['tiny'];
ELSIF z < 6 THEN
  mapsize := 'small';
  linesize := ARRAY['tiny', 'small'];
ELSIF z < 9 THEN
  mapsize := 'medium';
  linesize := ARRAY['small', 'medium'];
ELSE
  mapsize := 'large';
  linesize := ARRAY['medium', 'large'];
END IF;
-- Units
WITH mvt_features AS (
  SELECT
    map_id,
    source_id,
    geom
  FROM
    tile_layers.carto_units
  WHERE scale::text = mapsize
    AND ST_Intersects(geom, projected_bbox)
), expanded AS (
  SELECT
    z.map_id,
    z.source_id,
    l.legend_id,
    l.best_age_top::double precision AS best_age_top,
    l.best_age_bottom::double precision AS best_age_bottom,
    COALESCE(l.color, '#777777') AS color,
    COALESCE(l.name, '') AS name,
    COALESCE(l.age, '') AS age,
    COALESCE(l.lith, '') AS lith,
    COALESCE(l.descrip, '') AS descrip,
    COALESCE(l.comments, '') AS comments,
    l.t_interval AS t_int_id,
    COALESCE(ta.interval_name, '') AS t_int,
    l.b_interval AS b_int_id,
    tb.interval_name AS b_int,
    COALESCE(sources.url, '') AS ref_url,
    COALESCE(sources.name, '') AS ref_name,
    COALESCE(sources.ref_title, '') AS ref_title,
    COALESCE(sources.authors, '') AS ref_authors,
    COALESCE(sources.ref_source, '') AS ref_source,
    COALESCE(sources.ref_year, '') AS ref_year,
    COALESCE(sources.isbn_doi, '') AS ref_isbn,
    tile_layers.tile_geom(z.geom, mercator_bbox) AS geom
  FROM
    mvt_features z
    LEFT JOIN maps.map_legend ON z.map_id = map_legend.map_id
    LEFT JOIN maps.legend AS l ON l.legend_id = map_legend.legend_id
    LEFT JOIN macrostrat.intervals ta ON ta.id = l.t_interval
    LEFT JOIN macrostrat.intervals tb ON tb.id = l.b_interval
    LEFT JOIN maps.sources ON l.source_id = sources.source_id
  WHERE
    sources.status_code = 'active'
    -- AND ST_Area(geom) > tolerance
)
SELECT
  ST_AsMVT(expanded, 'units')
INTO bedrock
FROM expanded;
-- LINES
WITH mvt_features AS (
  SELECT
    line_id,
    source_id,
    geom
  FROM
    carto.lines
  WHERE
    scale = mapsize
    AND ST_Intersects(geom, projected_bbox)
),
expanded AS (
  SELECT
    z.line_id,
    z.source_id,
    coalesce(q.descrip, '') AS descrip,
    coalesce(q.name, '') AS name,
    coalesce(q.direction, '') AS direction,
    coalesce(q.type, '') AS "type",
    tile_layers.tile_geom(z.geom, mercator_bbox) AS geom
  FROM mvt_features z
  LEFT JOIN tile_layers.line_data q
    ON z.line_id = q.line_id
  LEFT JOIN maps.sources
    ON z.source_id = sources.source_id
  WHERE sources.status_code = 'active'
    AND q.scale = ANY(linesize)
    --AND ST_Length(geom) > tolerance
)
SELECT
  ST_AsMVT(expanded, 'lines') INTO lines
FROM expanded;
RETURN bedrock || lines;
END;
$$;

-- Name: carto_slim(integer, integer, integer, json); Type: FUNCTION; Schema: tile_layers; Owner: macrostrat
CREATE FUNCTION tile_layers.carto_slim(x integer, y integer, z integer, query_params json) RETURNS bytea
    LANGUAGE plpgsql IMMUTABLE
    AS $$
DECLARE
srid integer;
features record;
mapsize text;
linesize text[];
mercator_bbox geometry;
projected_bbox geometry;
bedrock bytea;
lines bytea;
tolerance double precision;
BEGIN
mercator_bbox := tile_utils.envelope(x, y, z);
tolerance := 6;
projected_bbox := ST_Transform(
  mercator_bbox,
  4326
);
IF z < 3 THEN
  -- Select from carto.tiny table
  mapsize := 'tiny';
  linesize := ARRAY['tiny'];
ELSIF z < 6 THEN
  mapsize := 'small';
  linesize := ARRAY['tiny', 'small'];
ELSIF z < 9 THEN
  mapsize := 'medium';
  linesize := ARRAY['small', 'medium'];
ELSE
  mapsize := 'large';
  linesize := ARRAY['medium', 'large'];
END IF;
-- Units
WITH mvt_features AS (
  SELECT
    map_id,
    source_id,
    geom
  FROM
    carto.polygons
  WHERE scale::text = mapsize
    AND ST_Intersects(geom, projected_bbox)
), expanded AS (
  SELECT
    z.map_id,
    z.source_id,
    l.*, -- legend info
    tile_layers.tile_geom(z.geom, mercator_bbox) AS geom
  FROM
    mvt_features z
    LEFT JOIN maps.map_legend ON z.map_id = map_legend.map_id
    LEFT JOIN tile_layers.map_legend_info AS l
      ON l.legend_id = map_legend.legend_id
    LEFT JOIN maps.sources
      ON z.source_id = sources.source_id
  WHERE
    sources.status_code = 'active'
    --AND ST_Area(geom) > tolerance
)
SELECT
  ST_AsMVT(expanded, 'units')
INTO bedrock
FROM expanded;
-- LINES
WITH mvt_features AS (
  SELECT
    line_id,
    source_id,
    geom
  FROM
    carto.lines
  WHERE
    scale::text = mapsize
    AND ST_Intersects(geom, projected_bbox)
),
expanded AS (
  SELECT
    z.line_id,
    z.source_id,
    coalesce(l.descrip, '') AS descrip,
    coalesce(l.name, '') AS name,
    coalesce(l.direction, '') AS direction,
    coalesce(l.type, '') AS "type",
    tile_layers.tile_geom(z.geom, mercator_bbox) AS geom
  FROM mvt_features z
  LEFT JOIN maps.lines l
    ON z.line_id = l.line_id
    AND l.scale::text = ANY(linesize)
  LEFT JOIN maps.sources
    ON z.source_id = sources.source_id
  WHERE sources.status_code = 'active'
    --AND ST_Length(geom) > tolerance
)
SELECT
  ST_AsMVT(expanded, 'lines') INTO lines
FROM expanded;
RETURN bedrock || lines;
END;
$$;

-- Name: map(integer, integer, integer, json); Type: FUNCTION; Schema: tile_layers; Owner: macrostrat
CREATE FUNCTION tile_layers.map(x integer, y integer, z integer, query_params json) RETURNS bytea
    LANGUAGE plpgsql IMMUTABLE
    AS $$
DECLARE
srid integer;
features record;
mapsize text;
linesize text[];
_source_id integer;
mercator_bbox geometry;
projected_bbox geometry;
bedrock bytea;
lines bytea;
tolerance double precision;
BEGIN
-- Get the map id requested from the query params
_source_id := (query_params->>'source_id')::integer;
IF _source_id IS NULL THEN
  RAISE EXCEPTION 'source_id is required';
END IF;
mercator_bbox := tile_utils.envelope(x, y, z);
tolerance := 6;
projected_bbox := ST_Transform(
  mercator_bbox,
  4326
);
-- Get map size
SELECT scale
  FROM tile_layers.map_units
 WHERE source_id = _source_id
 LIMIT 1
INTO mapsize;
IF mapsize = 'tiny' THEN
  linesize := ARRAY['tiny'];
ELSIF mapsize = 'small' THEN
  linesize := ARRAY['tiny', 'small'];
ELSIF mapsize = 'medium' THEN
  linesize := ARRAY['small', 'medium'];
ELSE
  linesize := ARRAY['medium', 'large'];
END IF;
-- Units
WITH mvt_features AS (
  SELECT
    map_id,
    source_id,
    geom
  FROM
    tile_layers.map_units
  WHERE source_id = _source_id
    AND ST_Intersects(geom, projected_bbox)
), expanded AS (
  SELECT
    z.map_id,
    z.source_id,
    l.*, --  map legend info
    tile_layers.tile_geom(z.geom, mercator_bbox) AS geom
  FROM mvt_features z
    LEFT JOIN maps.map_legend ON z.map_id = map_legend.map_id
    LEFT JOIN tile_layers.map_legend_info AS l
      ON l.legend_id = map_legend.legend_id
)
SELECT
  ST_AsMVT(expanded, 'units')
INTO bedrock
FROM expanded;
-- LINES
WITH mvt_features AS (
  SELECT
    line_id,
    source_id,
    geom
  FROM
    tile_layers.map_lines
  WHERE source_id = _source_id
    AND ST_Intersects(geom, projected_bbox)
),
expanded AS (
  SELECT
    z.line_id,
    z.source_id,
    coalesce(q.descrip, '') AS descrip,
    coalesce(q.name, '') AS name,
    coalesce(q.direction, '') AS direction,
    coalesce(q.type, '') AS "type",
    tile_layers.tile_geom(z.geom, mercator_bbox) AS geom
  FROM mvt_features z
  LEFT JOIN tile_layers.line_data q
    ON z.line_id = q.line_id
  WHERE q.scale = ANY(linesize)
    --AND ST_Length(geom) > tolerance
)
SELECT
  ST_AsMVT(expanded, 'lines') INTO lines
FROM expanded;
RETURN bedrock || lines;
END;
$$;

-- Name: tile_geom(public.geometry, public.geometry); Type: FUNCTION; Schema: tile_layers; Owner: macrostrat
CREATE FUNCTION tile_layers.tile_geom(geom public.geometry, bbox public.geometry) RETURNS public.geometry
    LANGUAGE sql IMMUTABLE
    AS $$
  /* It is difficult to reduce tile precision quickly, so we just make a smaller vector tile and scale it up */
  SELECT ST_Scale(ST_Simplify(ST_AsMVTGeom(ST_Transform(geom, 3857), bbox, 2048, 8, true), 1.5), 2, 2);
$$;

-- Name: cluster_expansion_zoom(public.geometry, integer, integer); Type: FUNCTION; Schema: tile_utils; Owner: macrostrat
CREATE FUNCTION tile_utils.cluster_expansion_zoom(geom public.geometry, zoom integer, expanded_pixel_width integer DEFAULT 256) RETURNS integer
    LANGUAGE plpgsql IMMUTABLE
    AS $$
  DECLARE
    bbox_size double precision;
    zoom_delta double precision;
  BEGIN
    SELECT greatest(ST_XMax(geom) - ST_XMin(geom), ST_YMax(geom)-ST_YMin(geom)) INTO bbox_size;
    IF bbox_size = 0 THEN
      RETURN null;
    END IF;
    zoom_delta := sqrt(expanded_pixel_width/bbox_size);
    RETURN round(zoom + zoom_delta);
  END;
$$;

-- Name: containing_tiles(public.geometry, text); Type: FUNCTION; Schema: tile_utils; Owner: macrostrat
CREATE FUNCTION tile_utils.containing_tiles(_geom public.geometry, _tms text DEFAULT NULL::text) RETURNS TABLE(x integer, y integer, z integer)
    LANGUAGE plpgsql STABLE
    AS $$
DECLARE
  _tms_bounds geometry;
  _geom_bbox box2d;
BEGIN
  _tms_bounds := tile_utils.tms_bounds(_tms);
  IF ST_Within(_geom, ST_Transform(_tms_bounds, ST_SRID(_geom))) THEN
    _geom_bbox := ST_Transform(_geom, ST_SRID(_tms_bounds))::box2d;
  ELSE
    RETURN;
  END IF;
  RETURN QUERY
  WITH tile_sizes AS (
    SELECT
      a.zoom
    FROM generate_series(0, 24) AS a(zoom)
  ), tilebounds AS (
    SELECT t.zoom,
      tile_utils.tile_index((ST_XMin(_geom_bbox)-ST_XMin(_tms_bounds))::numeric, t.zoom) xmin,
      tile_utils.tile_index((ST_YMax(_tms_bounds)-ST_YMin(_geom_bbox))::numeric, t.zoom) ymin,
      tile_utils.tile_index((ST_XMax(_geom_bbox)-ST_XMin(_tms_bounds))::numeric, t.zoom) xmax,
      tile_utils.tile_index((ST_YMax(_tms_bounds)-ST_YMax(_geom_bbox))::numeric, t.zoom) ymax
    FROM tile_sizes t
  )
  SELECT
    t.xmin::integer x,
    t.ymin::integer y,
    t.zoom::integer z
  FROM tilebounds t
  WHERE t.xmin = t.xmax
    AND t.ymin = t.ymax
  ORDER BY z DESC;
END;
$$;

-- Name: default_tms(); Type: FUNCTION; Schema: tile_utils; Owner: macrostrat
CREATE FUNCTION tile_utils.default_tms() RETURNS text
    LANGUAGE sql
    AS $$ SELECT 'web_mercator'; $$;

-- Name: envelope(integer, integer, integer, text); Type: FUNCTION; Schema: tile_utils; Owner: macrostrat
CREATE FUNCTION tile_utils.envelope(_x integer, _y integer, _z integer, _tms text DEFAULT NULL::text) RETURNS public.geometry
    LANGUAGE sql IMMUTABLE
    AS $$
  SELECT ST_TileEnvelope(
    _z, _x, _y,
    tile_utils.tms_bounds(_tms)
  );
$$;

-- Name: parent_tile(public.geometry, text); Type: FUNCTION; Schema: tile_utils; Owner: macrostrat
CREATE FUNCTION tile_utils.parent_tile(_geom public.geometry, _tms text DEFAULT NULL::text) RETURNS TABLE(x integer, y integer, z integer)
    LANGUAGE sql STABLE
    AS $$
  SELECT x, y, z FROM tile_utils.containing_tiles(_geom, _tms) LIMIT 1;
$$;

-- Name: set_default_tms(text); Type: FUNCTION; Schema: tile_utils; Owner: macrostrat
CREATE FUNCTION tile_utils.set_default_tms(_tms text) RETURNS void
    LANGUAGE plpgsql
    AS $$
BEGIN
  EXECUTE format('ALTER DATABASE %I SET tile_utils.default_tms = %L', current_database(), _tms);
END;
$$;

-- Name: tile_index(numeric, integer, text); Type: FUNCTION; Schema: tile_utils; Owner: macrostrat
CREATE FUNCTION tile_utils.tile_index(coord numeric, z integer, _tms text DEFAULT NULL::text) RETURNS integer
    LANGUAGE sql STABLE
    AS $$
  SELECT floor(coord/tile_utils.tile_width(z, _tms))::integer;
$$;

-- Name: tile_width(integer, text); Type: FUNCTION; Schema: tile_utils; Owner: macrostrat
CREATE FUNCTION tile_utils.tile_width(_z integer, _tms text DEFAULT NULL::text) RETURNS numeric
    LANGUAGE plpgsql IMMUTABLE
    AS $$
DECLARE
  _tms_bounds geometry;
  _tms_size numeric;
  _tile_size numeric;
BEGIN
  _tms_bounds := tile_utils.tms_bounds(_tms);
  _tms_size := ST_XMax(_tms_bounds) - ST_XMin(_tms_bounds);
  RETURN _tms_size/(2^_z);
END;
$$;

-- Name: tms_bounds(text); Type: FUNCTION; Schema: tile_utils; Owner: macrostrat
CREATE FUNCTION tile_utils.tms_bounds(tms text DEFAULT NULL::text) RETURNS public.geometry
    LANGUAGE sql IMMUTABLE
    AS $$
  SELECT (tile_utils.tms_data(tms)).bounds
$$;

SET default_tablespace = '';
SET default_table_access_method = heap;
-- Name: tms_definition; Type: TABLE; Schema: tile_utils; Owner: macrostrat
CREATE TABLE tile_utils.tms_definition (
    name text NOT NULL,
    bounds public.geometry(Polygon) NOT NULL,
    geographic_srid integer DEFAULT 4326 NOT NULL
);

-- Name: tms_data(text); Type: FUNCTION; Schema: tile_utils; Owner: macrostrat
CREATE FUNCTION tile_utils.tms_data(tms text DEFAULT NULL::text) RETURNS tile_utils.tms_definition
    LANGUAGE sql IMMUTABLE
    AS $$
  SELECT *
  FROM tile_utils.tms_definition
  WHERE name = coalesce(
    tms,
    tile_utils.default_tms()
  );
$$;

-- Name: tms_geographic_srid(text); Type: FUNCTION; Schema: tile_utils; Owner: macrostrat
CREATE FUNCTION tile_utils.tms_geographic_srid(tms text DEFAULT NULL::text) RETURNS integer
    LANGUAGE sql IMMUTABLE
    AS $$
  SELECT coalesce((tile_utils.tms_data(tms)).geographic_srid, 4326);
$$;

-- Name: tms_srid(text); Type: FUNCTION; Schema: tile_utils; Owner: macrostrat
CREATE FUNCTION tile_utils.tms_srid(tms text DEFAULT NULL::text) RETURNS integer
    LANGUAGE sql IMMUTABLE
    AS $$
  SELECT ST_SRID(tile_utils.tms_bounds(tms));
$$;

-- Name: array_agg_mult(anycompatiblearray); Type: AGGREGATE; Schema: public; Owner: postgres
CREATE AGGREGATE public.array_agg_mult(anycompatiblearray) (
    SFUNC = array_cat,
    STYPE = anycompatiblearray,
    INITCOND = '{}'
);

-- Name: elevation; Type: SERVER; Schema: -; Owner: macrostrat
CREATE SERVER elevation FOREIGN DATA WRAPPER postgres_fdw OPTIONS (
    dbname 'elevation',
    host 'localhost',
    port '5432',
    use_remote_estimate 'true'
);

-- Name: users; Type: TABLE; Schema: auth; Owner: macrostrat
CREATE TABLE auth.users (
    id integer NOT NULL,
    username text NOT NULL,
    password text NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL
);

-- Name: users_id_seq; Type: SEQUENCE; Schema: auth; Owner: macrostrat
CREATE SEQUENCE auth.users_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

-- Name: users_id_seq; Type: SEQUENCE OWNED BY; Schema: auth; Owner: macrostrat
ALTER SEQUENCE auth.users_id_seq OWNED BY auth.users.id;

-- Name: lines; Type: TABLE; Schema: carto; Owner: macrostrat
CREATE TABLE carto.lines (
    line_id integer NOT NULL,
    source_id integer,
    geom public.geometry(Geometry,4326) NOT NULL,
    geom_scale macrostrat.map_scale NOT NULL,
    scale macrostrat.map_scale NOT NULL
)
PARTITION BY LIST (scale);

-- Name: lines_large; Type: TABLE; Schema: carto; Owner: macrostrat
CREATE TABLE carto.lines_large (
    line_id integer NOT NULL,
    source_id integer,
    geom_scale macrostrat.map_scale NOT NULL,
    geom public.geometry(Geometry,4326) NOT NULL,
    scale macrostrat.map_scale DEFAULT 'large'::macrostrat.map_scale NOT NULL,
    CONSTRAINT lines_large_scale_check CHECK ((scale = 'large'::macrostrat.map_scale))
);

-- Name: lines_medium; Type: TABLE; Schema: carto; Owner: macrostrat
CREATE TABLE carto.lines_medium (
    line_id integer NOT NULL,
    source_id integer,
    geom_scale macrostrat.map_scale NOT NULL,
    geom public.geometry(Geometry,4326) NOT NULL,
    scale macrostrat.map_scale DEFAULT 'medium'::macrostrat.map_scale NOT NULL,
    CONSTRAINT lines_medium_scale_check CHECK ((scale = 'medium'::macrostrat.map_scale))
);

-- Name: lines_small; Type: TABLE; Schema: carto; Owner: macrostrat
CREATE TABLE carto.lines_small (
    line_id integer NOT NULL,
    source_id integer,
    geom_scale macrostrat.map_scale NOT NULL,
    geom public.geometry(Geometry,4326) NOT NULL,
    scale macrostrat.map_scale DEFAULT 'small'::macrostrat.map_scale NOT NULL,
    CONSTRAINT lines_small_scale_check CHECK ((scale = 'small'::macrostrat.map_scale))
);

-- Name: lines_tiny; Type: TABLE; Schema: carto; Owner: macrostrat
CREATE TABLE carto.lines_tiny (
    line_id integer NOT NULL,
    source_id integer,
    geom_scale macrostrat.map_scale NOT NULL,
    geom public.geometry(Geometry,4326) NOT NULL,
    scale macrostrat.map_scale DEFAULT 'tiny'::macrostrat.map_scale NOT NULL,
    CONSTRAINT lines_tiny_scale_check CHECK ((scale = 'tiny'::macrostrat.map_scale))
);

-- Name: polygons; Type: TABLE; Schema: carto; Owner: macrostrat
CREATE TABLE carto.polygons (
    map_id integer NOT NULL,
    source_id integer,
    geom public.geometry(Geometry,4326) NOT NULL,
    geom_scale macrostrat.map_scale NOT NULL,
    scale macrostrat.map_scale NOT NULL
)
PARTITION BY LIST (scale);

-- Name: polygons_large; Type: TABLE; Schema: carto; Owner: macrostrat
CREATE TABLE carto.polygons_large (
    map_id integer NOT NULL,
    source_id integer,
    geom_scale macrostrat.map_scale NOT NULL,
    geom public.geometry(Geometry,4326) NOT NULL,
    scale macrostrat.map_scale DEFAULT 'large'::macrostrat.map_scale NOT NULL,
    CONSTRAINT polygons_large_scale_check CHECK ((scale = 'large'::macrostrat.map_scale))
);

-- Name: polygons_medium; Type: TABLE; Schema: carto; Owner: macrostrat
CREATE TABLE carto.polygons_medium (
    map_id integer NOT NULL,
    source_id integer,
    geom_scale macrostrat.map_scale NOT NULL,
    geom public.geometry(Geometry,4326) NOT NULL,
    scale macrostrat.map_scale DEFAULT 'medium'::macrostrat.map_scale NOT NULL,
    CONSTRAINT polygons_medium_scale_check CHECK ((scale = 'medium'::macrostrat.map_scale))
);

-- Name: polygons_small; Type: TABLE; Schema: carto; Owner: macrostrat
CREATE TABLE carto.polygons_small (
    map_id integer NOT NULL,
    source_id integer,
    geom_scale macrostrat.map_scale NOT NULL,
    geom public.geometry(Geometry,4326) NOT NULL,
    scale macrostrat.map_scale DEFAULT 'small'::macrostrat.map_scale NOT NULL,
    CONSTRAINT polygons_small_scale_check CHECK ((scale = 'small'::macrostrat.map_scale))
);

-- Name: polygons_tiny; Type: TABLE; Schema: carto; Owner: macrostrat
CREATE TABLE carto.polygons_tiny (
    map_id integer NOT NULL,
    source_id integer,
    geom_scale macrostrat.map_scale NOT NULL,
    geom public.geometry(Geometry,4326) NOT NULL,
    scale macrostrat.map_scale DEFAULT 'tiny'::macrostrat.map_scale NOT NULL,
    CONSTRAINT polygons_tiny_scale_check CHECK ((scale = 'tiny'::macrostrat.map_scale))
);

-- Name: hex_index; Type: TABLE; Schema: carto_new; Owner: macrostrat
CREATE TABLE carto_new.hex_index (
    map_id integer NOT NULL,
    scale text,
    hex_id integer
);

-- Name: large; Type: VIEW; Schema: carto_new; Owner: macrostrat
CREATE VIEW carto_new.large AS
 SELECT polygons.map_id,
    polygons.source_id,
    polygons.geom,
    (polygons.geom_scale)::text AS scale
   FROM carto.polygons
  WHERE (polygons.scale = 'large'::macrostrat.map_scale);

-- Name: lines_large; Type: VIEW; Schema: carto_new; Owner: macrostrat
CREATE VIEW carto_new.lines_large AS
 SELECT lines.line_id,
    lines.source_id,
    lines.geom,
    (lines.geom_scale)::text AS scale
   FROM carto.lines
  WHERE (lines.scale = 'large'::macrostrat.map_scale);

-- Name: lines_medium; Type: VIEW; Schema: carto_new; Owner: macrostrat
CREATE VIEW carto_new.lines_medium AS
 SELECT lines.line_id,
    lines.source_id,
    lines.geom,
    (lines.geom_scale)::text AS scale
   FROM carto.lines
  WHERE (lines.scale = 'medium'::macrostrat.map_scale);

-- Name: lines_small; Type: VIEW; Schema: carto_new; Owner: macrostrat
CREATE VIEW carto_new.lines_small AS
 SELECT lines.line_id,
    lines.source_id,
    lines.geom,
    (lines.geom_scale)::text AS scale
   FROM carto.lines
  WHERE (lines.scale = 'small'::macrostrat.map_scale);

-- Name: lines_tiny; Type: VIEW; Schema: carto_new; Owner: macrostrat
CREATE VIEW carto_new.lines_tiny AS
 SELECT lines.line_id,
    lines.source_id,
    lines.geom,
    (lines.geom_scale)::text AS scale
   FROM carto.lines
  WHERE (lines.scale = 'tiny'::macrostrat.map_scale);

-- Name: medium; Type: VIEW; Schema: carto_new; Owner: macrostrat
CREATE VIEW carto_new.medium AS
 SELECT polygons.map_id,
    polygons.source_id,
    polygons.geom,
    (polygons.geom_scale)::text AS scale
   FROM carto.polygons
  WHERE (polygons.scale = 'medium'::macrostrat.map_scale);

-- Name: pbdb_hex_index; Type: TABLE; Schema: carto_new; Owner: macrostrat
CREATE TABLE carto_new.pbdb_hex_index (
    collection_no integer NOT NULL,
    scale text,
    hex_id integer
);

-- Name: small; Type: VIEW; Schema: carto_new; Owner: macrostrat
CREATE VIEW carto_new.small AS
 SELECT polygons.map_id,
    polygons.source_id,
    polygons.geom,
    (polygons.geom_scale)::text AS scale
   FROM carto.polygons
  WHERE (polygons.scale = 'small'::macrostrat.map_scale);

-- Name: tiny; Type: VIEW; Schema: carto_new; Owner: macrostrat
CREATE VIEW carto_new.tiny AS
 SELECT polygons.map_id,
    polygons.source_id,
    polygons.geom,
    (polygons.geom_scale)::text AS scale
   FROM carto.polygons
  WHERE (polygons.scale = 'tiny'::macrostrat.map_scale);

-- Name: carto_plate_index; Type: TABLE; Schema: corelle_macrostrat; Owner: macrostrat
CREATE TABLE corelle_macrostrat.carto_plate_index (
    map_id integer,
    scale macrostrat.map_scale,
    model_id integer,
    plate_id integer,
    geom public.geometry
);

-- Name: col_areas; Type: TABLE; Schema: macrostrat; Owner: macrostrat
CREATE TABLE macrostrat.col_areas (
    id integer NOT NULL,
    col_id integer,
    col_area public.geometry,
    wkt text
);

-- Name: TABLE col_areas; Type: COMMENT; Schema: macrostrat; Owner: macrostrat
COMMENT ON TABLE macrostrat.col_areas IS 'Last updated from MariaDB - 2022-06-28 15:08';

-- Name: column_index; Type: MATERIALIZED VIEW; Schema: corelle_macrostrat; Owner: macrostrat
CREATE MATERIALIZED VIEW corelle_macrostrat.column_index AS
 SELECT c.col_id,
    pp.model_id,
    pp.plate_id
   FROM (macrostrat.col_areas c
     JOIN corelle.plate_polygon pp ON (public.st_intersects(public.st_centroid(c.col_area), pp.geometry)))
  WITH NO DATA;

-- Name: natural_earth_index; Type: MATERIALIZED VIEW; Schema: corelle_macrostrat; Owner: macrostrat
CREATE MATERIALIZED VIEW corelle_macrostrat.natural_earth_index AS
 SELECT f.id,
    (f.properties ->> 'scalerank'::text) AS scalerank,
    public.st_intersection(f.geometry, pp.geometry) AS geometry,
    pp.model_id,
    pp.plate_id
   FROM (corelle.feature f
     JOIN corelle.plate_polygon pp ON (public.st_intersects(f.geometry, pp.geometry)))
  WHERE (f.dataset_id = 'ne_110m_land'::text)
  WITH NO DATA;

-- Name: located_query_bounds; Type: TABLE; Schema: detrital_zircon; Owner: macrostrat
CREATE TABLE detrital_zircon.located_query_bounds (
    id integer NOT NULL,
    geometry public.geometry(MultiPolygon,4326) NOT NULL,
    name text,
    notes text
);

-- Name: located_query_bounds_id_seq; Type: SEQUENCE; Schema: detrital_zircon; Owner: macrostrat
CREATE SEQUENCE detrital_zircon.located_query_bounds_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

-- Name: located_query_bounds_id_seq; Type: SEQUENCE OWNED BY; Schema: detrital_zircon; Owner: macrostrat
ALTER SEQUENCE detrital_zircon.located_query_bounds_id_seq OWNED BY detrital_zircon.located_query_bounds.id;

-- Name: boundaries; Type: TABLE; Schema: geologic_boundaries; Owner: macrostrat
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

-- Name: boundaries_boundary_id_seq; Type: SEQUENCE; Schema: geologic_boundaries; Owner: macrostrat
CREATE SEQUENCE geologic_boundaries.boundaries_boundary_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

-- Name: boundaries_boundary_id_seq; Type: SEQUENCE OWNED BY; Schema: geologic_boundaries; Owner: macrostrat
ALTER SEQUENCE geologic_boundaries.boundaries_boundary_id_seq OWNED BY geologic_boundaries.boundaries.boundary_id;

-- Name: geologic_boundary_source_seq; Type: SEQUENCE; Schema: public; Owner: macrostrat
CREATE SEQUENCE public.geologic_boundary_source_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

-- Name: sources; Type: TABLE; Schema: geologic_boundaries; Owner: macrostrat
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
    license character varying(100),
    features integer,
    area integer,
    priority boolean,
    rgeom public.geometry,
    display_scales text[],
    web_geom public.geometry
);

-- Name: bedrock_index; Type: TABLE; Schema: hexgrids; Owner: macrostrat
CREATE TABLE hexgrids.bedrock_index (
    legend_id integer NOT NULL,
    hex_id integer NOT NULL,
    coverage numeric
);

-- Name: hexgrids; Type: TABLE; Schema: hexgrids; Owner: macrostrat
CREATE TABLE hexgrids.hexgrids (
    hex_id integer NOT NULL,
    res integer,
    geom public.geometry
);

-- Name: pbdb_index; Type: TABLE; Schema: hexgrids; Owner: macrostrat
CREATE TABLE hexgrids.pbdb_index (
    collection_no integer NOT NULL,
    hex_id integer NOT NULL
);

-- Name: r10; Type: TABLE; Schema: hexgrids; Owner: macrostrat
CREATE TABLE hexgrids.r10 (
    hex_id integer NOT NULL,
    geom public.geometry(MultiPolygon,4326),
    web_geom public.geometry
);

-- Name: r10_ogc_fid_seq; Type: SEQUENCE; Schema: hexgrids; Owner: macrostrat
CREATE SEQUENCE hexgrids.r10_ogc_fid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

-- Name: r10_ogc_fid_seq; Type: SEQUENCE OWNED BY; Schema: hexgrids; Owner: macrostrat
ALTER SEQUENCE hexgrids.r10_ogc_fid_seq OWNED BY hexgrids.r10.hex_id;

-- Name: r11; Type: TABLE; Schema: hexgrids; Owner: macrostrat
CREATE TABLE hexgrids.r11 (
    hex_id integer NOT NULL,
    geom public.geometry(MultiPolygon,4326),
    web_geom public.geometry
);

-- Name: r11_ogc_fid_seq; Type: SEQUENCE; Schema: hexgrids; Owner: macrostrat
CREATE SEQUENCE hexgrids.r11_ogc_fid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

-- Name: r11_ogc_fid_seq; Type: SEQUENCE OWNED BY; Schema: hexgrids; Owner: macrostrat
ALTER SEQUENCE hexgrids.r11_ogc_fid_seq OWNED BY hexgrids.r11.hex_id;

-- Name: r12; Type: TABLE; Schema: hexgrids; Owner: macrostrat
CREATE TABLE hexgrids.r12 (
    hex_id integer NOT NULL,
    geom public.geometry(MultiPolygon,4326),
    web_geom public.geometry
);

-- Name: r12_ogc_fid_seq; Type: SEQUENCE; Schema: hexgrids; Owner: macrostrat
CREATE SEQUENCE hexgrids.r12_ogc_fid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

-- Name: r12_ogc_fid_seq; Type: SEQUENCE OWNED BY; Schema: hexgrids; Owner: macrostrat
ALTER SEQUENCE hexgrids.r12_ogc_fid_seq OWNED BY hexgrids.r12.hex_id;

-- Name: r5; Type: TABLE; Schema: hexgrids; Owner: macrostrat
CREATE TABLE hexgrids.r5 (
    hex_id integer NOT NULL,
    geom public.geometry(MultiPolygon,4326),
    web_geom public.geometry
);

-- Name: r5_ogc_fid_seq; Type: SEQUENCE; Schema: hexgrids; Owner: macrostrat
CREATE SEQUENCE hexgrids.r5_ogc_fid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

-- Name: r5_ogc_fid_seq; Type: SEQUENCE OWNED BY; Schema: hexgrids; Owner: macrostrat
ALTER SEQUENCE hexgrids.r5_ogc_fid_seq OWNED BY hexgrids.r5.hex_id;

-- Name: r6; Type: TABLE; Schema: hexgrids; Owner: macrostrat
CREATE TABLE hexgrids.r6 (
    hex_id integer NOT NULL,
    geom public.geometry(MultiPolygon,4326),
    web_geom public.geometry
);

-- Name: r6_ogc_fid_seq; Type: SEQUENCE; Schema: hexgrids; Owner: macrostrat
CREATE SEQUENCE hexgrids.r6_ogc_fid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

-- Name: r6_ogc_fid_seq; Type: SEQUENCE OWNED BY; Schema: hexgrids; Owner: macrostrat
ALTER SEQUENCE hexgrids.r6_ogc_fid_seq OWNED BY hexgrids.r6.hex_id;

-- Name: r7; Type: TABLE; Schema: hexgrids; Owner: macrostrat
CREATE TABLE hexgrids.r7 (
    hex_id integer NOT NULL,
    geom public.geometry(MultiPolygon,4326),
    web_geom public.geometry
);

-- Name: r7_ogc_fid_seq; Type: SEQUENCE; Schema: hexgrids; Owner: macrostrat
CREATE SEQUENCE hexgrids.r7_ogc_fid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

-- Name: r7_ogc_fid_seq; Type: SEQUENCE OWNED BY; Schema: hexgrids; Owner: macrostrat
ALTER SEQUENCE hexgrids.r7_ogc_fid_seq OWNED BY hexgrids.r7.hex_id;

-- Name: r8; Type: TABLE; Schema: hexgrids; Owner: macrostrat
CREATE TABLE hexgrids.r8 (
    hex_id integer NOT NULL,
    geom public.geometry(MultiPolygon,4326),
    web_geom public.geometry
);

-- Name: r8_ogc_fid_seq; Type: SEQUENCE; Schema: hexgrids; Owner: macrostrat
CREATE SEQUENCE hexgrids.r8_ogc_fid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

-- Name: r8_ogc_fid_seq; Type: SEQUENCE OWNED BY; Schema: hexgrids; Owner: macrostrat
ALTER SEQUENCE hexgrids.r8_ogc_fid_seq OWNED BY hexgrids.r8.hex_id;

-- Name: r9; Type: TABLE; Schema: hexgrids; Owner: macrostrat
CREATE TABLE hexgrids.r9 (
    hex_id integer NOT NULL,
    geom public.geometry(MultiPolygon,4326),
    web_geom public.geometry
);

-- Name: r9_ogc_fid_seq; Type: SEQUENCE; Schema: hexgrids; Owner: macrostrat
CREATE SEQUENCE hexgrids.r9_ogc_fid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

-- Name: r9_ogc_fid_seq; Type: SEQUENCE OWNED BY; Schema: hexgrids; Owner: macrostrat
ALTER SEQUENCE hexgrids.r9_ogc_fid_seq OWNED BY hexgrids.r9.hex_id;

-- Name: line_ids; Type: SEQUENCE; Schema: public; Owner: macrostrat
CREATE SEQUENCE public.line_ids
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

-- Name: lines; Type: TABLE; Schema: maps; Owner: macrostrat
CREATE TABLE maps.lines (
    line_id integer DEFAULT nextval('public.line_ids'::regclass) NOT NULL,
    orig_id integer,
    source_id integer,
    name character varying(255),
    type_legacy character varying(100),
    direction_legacy character varying(40),
    descrip text,
    geom public.geometry(Geometry,4326) NOT NULL,
    type character varying(100),
    direction character varying(40),
    scale macrostrat.map_scale NOT NULL,
    CONSTRAINT maps_lines_geom_check CHECK (maps.lines_geom_is_valid(geom))
)
PARTITION BY LIST (scale);

-- Name: large; Type: VIEW; Schema: lines; Owner: macrostrat
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
  WHERE (lines.scale = 'large'::macrostrat.map_scale);

-- Name: medium; Type: VIEW; Schema: lines; Owner: macrostrat
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
  WHERE (lines.scale = 'medium'::macrostrat.map_scale);

-- Name: small; Type: VIEW; Schema: lines; Owner: macrostrat
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
  WHERE (lines.scale = 'small'::macrostrat.map_scale);

-- Name: tiny; Type: VIEW; Schema: lines; Owner: macrostrat
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
  WHERE (lines.scale = 'tiny'::macrostrat.map_scale);

-- Name: autocomplete; Type: TABLE; Schema: macrostrat; Owner: macrostrat
CREATE TABLE macrostrat.autocomplete (
    id integer NOT NULL,
    name text,
    type text,
    category text
);

-- Name: TABLE autocomplete; Type: COMMENT; Schema: macrostrat; Owner: macrostrat
COMMENT ON TABLE macrostrat.autocomplete IS 'Last updated from MariaDB - 2022-06-28 15:08';

-- Name: col_groups; Type: TABLE; Schema: macrostrat; Owner: macrostrat
CREATE TABLE macrostrat.col_groups (
    id integer NOT NULL,
    col_group character varying(100),
    col_group_long character varying(100)
);

-- Name: TABLE col_groups; Type: COMMENT; Schema: macrostrat; Owner: macrostrat
COMMENT ON TABLE macrostrat.col_groups IS 'Last updated from MariaDB - 2022-06-28 15:06';

-- Name: col_refs; Type: TABLE; Schema: macrostrat; Owner: macrostrat
CREATE TABLE macrostrat.col_refs (
    id integer NOT NULL,
    col_id integer,
    ref_id integer
);

-- Name: TABLE col_refs; Type: COMMENT; Schema: macrostrat; Owner: macrostrat
COMMENT ON TABLE macrostrat.col_refs IS 'Last updated from MariaDB - 2022-06-28 15:07';

-- Name: cols; Type: TABLE; Schema: macrostrat; Owner: macrostrat
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

-- Name: TABLE cols; Type: COMMENT; Schema: macrostrat; Owner: macrostrat
COMMENT ON TABLE macrostrat.cols IS 'Last updated from MariaDB - 2022-06-28 15:06';

-- Name: concepts_places; Type: TABLE; Schema: macrostrat; Owner: macrostrat
CREATE TABLE macrostrat.concepts_places (
    concept_id integer NOT NULL,
    place_id integer NOT NULL
);

-- Name: TABLE concepts_places; Type: COMMENT; Schema: macrostrat; Owner: macrostrat
COMMENT ON TABLE macrostrat.concepts_places IS 'Last updated from MariaDB - 2022-06-28 15:07';

-- Name: econs; Type: TABLE; Schema: macrostrat; Owner: macrostrat
CREATE TABLE macrostrat.econs (
    id integer NOT NULL,
    econ text,
    econ_type text,
    econ_class text,
    econ_color text
);

-- Name: TABLE econs; Type: COMMENT; Schema: macrostrat; Owner: macrostrat
COMMENT ON TABLE macrostrat.econs IS 'Last updated from MariaDB - 2022-06-28 15:07';

-- Name: environs; Type: TABLE; Schema: macrostrat; Owner: macrostrat
CREATE TABLE macrostrat.environs (
    id integer NOT NULL,
    environ text,
    environ_type text,
    environ_class text,
    environ_color text
);

-- Name: TABLE environs; Type: COMMENT; Schema: macrostrat; Owner: macrostrat
COMMENT ON TABLE macrostrat.environs IS 'Last updated from MariaDB - 2022-06-28 15:06';

-- Name: grainsize; Type: TABLE; Schema: macrostrat; Owner: macrostrat
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

-- Name: ingest_process; Type: TABLE; Schema: macrostrat; Owner: macrostrat
CREATE TABLE macrostrat.ingest_process (
    id integer NOT NULL,
    comments text,
    group_id integer,
    object_id integer NOT NULL,
    created_on timestamp with time zone DEFAULT now() NOT NULL,
    completed_on timestamp with time zone
);

-- Name: ingest_process_id_seq; Type: SEQUENCE; Schema: macrostrat; Owner: macrostrat
CREATE SEQUENCE macrostrat.ingest_process_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

-- Name: ingest_process_id_seq; Type: SEQUENCE OWNED BY; Schema: macrostrat; Owner: macrostrat
ALTER SEQUENCE macrostrat.ingest_process_id_seq OWNED BY macrostrat.ingest_process.id;

-- Name: intervals; Type: TABLE; Schema: macrostrat; Owner: macrostrat
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

-- Name: TABLE intervals; Type: COMMENT; Schema: macrostrat; Owner: macrostrat
COMMENT ON TABLE macrostrat.intervals IS 'Last updated from MariaDB - 2022-06-28 15:10';

-- Name: intervals_new_id_seq1; Type: SEQUENCE; Schema: macrostrat; Owner: macrostrat
CREATE SEQUENCE macrostrat.intervals_new_id_seq1
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

-- Name: intervals_new_id_seq1; Type: SEQUENCE OWNED BY; Schema: macrostrat; Owner: macrostrat
ALTER SEQUENCE macrostrat.intervals_new_id_seq1 OWNED BY macrostrat.intervals.id;

-- Name: lith_atts; Type: TABLE; Schema: macrostrat; Owner: macrostrat
CREATE TABLE macrostrat.lith_atts (
    id integer NOT NULL,
    lith_att character varying(75),
    att_type character varying(25),
    lith_att_fill integer
);

-- Name: TABLE lith_atts; Type: COMMENT; Schema: macrostrat; Owner: macrostrat
COMMENT ON TABLE macrostrat.lith_atts IS 'Last updated from MariaDB - 2022-06-28 15:09';

-- Name: liths; Type: TABLE; Schema: macrostrat; Owner: macrostrat
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

-- Name: TABLE liths; Type: COMMENT; Schema: macrostrat; Owner: macrostrat
COMMENT ON TABLE macrostrat.liths IS 'Last updated from MariaDB - 2022-06-28 14:54';

-- Name: lookup_strat_names; Type: TABLE; Schema: macrostrat; Owner: macrostrat
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

-- Name: TABLE lookup_strat_names; Type: COMMENT; Schema: macrostrat; Owner: macrostrat
COMMENT ON TABLE macrostrat.lookup_strat_names IS 'Last updated from MariaDB - 2022-06-28 15:11';

-- Name: lookup_unit_attrs_api; Type: TABLE; Schema: macrostrat; Owner: macrostrat
CREATE TABLE macrostrat.lookup_unit_attrs_api (
    unit_id integer,
    lith json,
    environ json,
    econ json,
    measure_short json,
    measure_long json
);

-- Name: TABLE lookup_unit_attrs_api; Type: COMMENT; Schema: macrostrat; Owner: macrostrat
COMMENT ON TABLE macrostrat.lookup_unit_attrs_api IS 'Last updated from MariaDB - 2022-06-28 15:07';

-- Name: lookup_unit_intervals; Type: TABLE; Schema: macrostrat; Owner: macrostrat
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

-- Name: TABLE lookup_unit_intervals; Type: COMMENT; Schema: macrostrat; Owner: macrostrat
COMMENT ON TABLE macrostrat.lookup_unit_intervals IS 'Last updated from MariaDB - 2022-06-28 15:10';

-- Name: lookup_unit_liths; Type: TABLE; Schema: macrostrat; Owner: macrostrat
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

-- Name: TABLE lookup_unit_liths; Type: COMMENT; Schema: macrostrat; Owner: macrostrat
COMMENT ON TABLE macrostrat.lookup_unit_liths IS 'Last updated from MariaDB - 2022-06-28 15:10';

-- Name: lookup_units; Type: TABLE; Schema: macrostrat; Owner: macrostrat
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

-- Name: TABLE lookup_units; Type: COMMENT; Schema: macrostrat; Owner: macrostrat
COMMENT ON TABLE macrostrat.lookup_units IS 'Last updated from MariaDB - 2022-06-28 15:06';

-- Name: measurements; Type: TABLE; Schema: macrostrat; Owner: macrostrat
CREATE TABLE macrostrat.measurements (
    id integer NOT NULL,
    measurement_class public.measurement_class NOT NULL,
    measurement_type public.measurement_type NOT NULL,
    measurement text NOT NULL
);

-- Name: TABLE measurements; Type: COMMENT; Schema: macrostrat; Owner: macrostrat
COMMENT ON TABLE macrostrat.measurements IS 'Last updated from MariaDB - 2022-06-28 15:10';

-- Name: measurements_new_id_seq; Type: SEQUENCE; Schema: macrostrat; Owner: macrostrat
CREATE SEQUENCE macrostrat.measurements_new_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

-- Name: measurements_new_id_seq; Type: SEQUENCE OWNED BY; Schema: macrostrat; Owner: macrostrat
ALTER SEQUENCE macrostrat.measurements_new_id_seq OWNED BY macrostrat.measurements.id;

-- Name: measuremeta; Type: TABLE; Schema: macrostrat; Owner: macrostrat
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
    ref_id bigint NOT NULL,
    geometry public.geometry(Geometry,4326)
);

-- Name: TABLE measuremeta; Type: COMMENT; Schema: macrostrat; Owner: macrostrat
COMMENT ON TABLE macrostrat.measuremeta IS 'Last updated from MariaDB - 2022-06-28 15:07';

-- Name: measuremeta_new_id_seq1; Type: SEQUENCE; Schema: macrostrat; Owner: macrostrat
CREATE SEQUENCE macrostrat.measuremeta_new_id_seq1
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

-- Name: measuremeta_new_id_seq1; Type: SEQUENCE OWNED BY; Schema: macrostrat; Owner: macrostrat
ALTER SEQUENCE macrostrat.measuremeta_new_id_seq1 OWNED BY macrostrat.measuremeta.id;

-- Name: measures; Type: TABLE; Schema: macrostrat; Owner: macrostrat
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

-- Name: TABLE measures; Type: COMMENT; Schema: macrostrat; Owner: macrostrat
COMMENT ON TABLE macrostrat.measures IS 'Last updated from MariaDB - 2022-06-28 15:06';

-- Name: measures_new_id_seq1; Type: SEQUENCE; Schema: macrostrat; Owner: macrostrat
CREATE SEQUENCE macrostrat.measures_new_id_seq1
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

-- Name: measures_new_id_seq1; Type: SEQUENCE OWNED BY; Schema: macrostrat; Owner: macrostrat
ALTER SEQUENCE macrostrat.measures_new_id_seq1 OWNED BY macrostrat.measures.id;

-- Name: objects; Type: TABLE; Schema: macrostrat; Owner: macrostrat
CREATE TABLE macrostrat.objects (
    id integer NOT NULL,
    scheme macrostrat.schemeenum NOT NULL,
    host character varying(255) NOT NULL,
    bucket character varying(255) NOT NULL,
    key character varying(255) NOT NULL,
    source json NOT NULL,
    mime_type character varying(255) NOT NULL,
    sha256_hash character varying(255) NOT NULL,
    created_on timestamp with time zone DEFAULT now() NOT NULL,
    updated_on timestamp with time zone DEFAULT now() NOT NULL,
    deleted_on timestamp with time zone
);

-- Name: objects_id_seq; Type: SEQUENCE; Schema: macrostrat; Owner: macrostrat
CREATE SEQUENCE macrostrat.objects_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

-- Name: objects_id_seq; Type: SEQUENCE OWNED BY; Schema: macrostrat; Owner: macrostrat
ALTER SEQUENCE macrostrat.objects_id_seq OWNED BY macrostrat.objects.id;

-- Name: pbdb_collections; Type: TABLE; Schema: macrostrat; Owner: macrostrat
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

-- Name: TABLE pbdb_collections; Type: COMMENT; Schema: macrostrat; Owner: macrostrat
COMMENT ON TABLE macrostrat.pbdb_collections IS 'Last updated from MariaDB - 2022-06-28 15:09';

-- Name: pbdb_collections_strat_names; Type: TABLE; Schema: macrostrat; Owner: macrostrat
CREATE TABLE macrostrat.pbdb_collections_strat_names (
    collection_no integer NOT NULL,
    strat_name_id integer NOT NULL,
    basis_col text
);

-- Name: places; Type: TABLE; Schema: macrostrat; Owner: macrostrat
CREATE TABLE macrostrat.places (
    place_id integer NOT NULL,
    name text,
    abbrev text,
    postal text,
    country text,
    country_abbrev text,
    geom public.geometry
);

-- Name: TABLE places; Type: COMMENT; Schema: macrostrat; Owner: macrostrat
COMMENT ON TABLE macrostrat.places IS 'Last updated from MariaDB - 2022-06-28 15:07';

-- Name: projects; Type: TABLE; Schema: macrostrat; Owner: macrostrat
CREATE TABLE macrostrat.projects (
    id integer NOT NULL,
    project text,
    descrip text,
    timescale_id integer
);

-- Name: TABLE projects; Type: COMMENT; Schema: macrostrat; Owner: macrostrat
COMMENT ON TABLE macrostrat.projects IS 'Last updated from MariaDB - 2023-07-28 16:57';

-- Name: projects_new_id_seq; Type: SEQUENCE; Schema: macrostrat; Owner: macrostrat
CREATE SEQUENCE macrostrat.projects_new_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

-- Name: projects_new_id_seq; Type: SEQUENCE OWNED BY; Schema: macrostrat; Owner: macrostrat
ALTER SEQUENCE macrostrat.projects_new_id_seq OWNED BY macrostrat.projects.id;

-- Name: refs; Type: TABLE; Schema: macrostrat; Owner: macrostrat
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

-- Name: TABLE refs; Type: COMMENT; Schema: macrostrat; Owner: macrostrat
COMMENT ON TABLE macrostrat.refs IS 'Last updated from MariaDB - 2022-06-28 15:10';

-- Name: sections; Type: TABLE; Schema: macrostrat; Owner: macrostrat
CREATE TABLE macrostrat.sections (
    id integer NOT NULL,
    col_id integer
);

-- Name: TABLE sections; Type: COMMENT; Schema: macrostrat; Owner: macrostrat
COMMENT ON TABLE macrostrat.sections IS 'Last updated from MariaDB - 2023-07-28 18:11';

-- Name: sections_new_id_seq1; Type: SEQUENCE; Schema: macrostrat; Owner: macrostrat
CREATE SEQUENCE macrostrat.sections_new_id_seq1
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

-- Name: sections_new_id_seq1; Type: SEQUENCE OWNED BY; Schema: macrostrat; Owner: macrostrat
ALTER SEQUENCE macrostrat.sections_new_id_seq1 OWNED BY macrostrat.sections.id;

-- Name: strat_name_footprints; Type: TABLE; Schema: macrostrat; Owner: macrostrat
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

-- Name: strat_names; Type: TABLE; Schema: macrostrat; Owner: macrostrat
CREATE TABLE macrostrat.strat_names (
    id integer NOT NULL,
    strat_name character varying(100) NOT NULL,
    rank character varying(50),
    ref_id integer NOT NULL,
    concept_id integer
);

-- Name: TABLE strat_names; Type: COMMENT; Schema: macrostrat; Owner: macrostrat
COMMENT ON TABLE macrostrat.strat_names IS 'Last updated from MariaDB - 2022-06-28 15:10';

-- Name: strat_names_meta; Type: TABLE; Schema: macrostrat; Owner: macrostrat
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

-- Name: TABLE strat_names_meta; Type: COMMENT; Schema: macrostrat; Owner: macrostrat
COMMENT ON TABLE macrostrat.strat_names_meta IS 'Last updated from MariaDB - 2022-06-28 15:08';

-- Name: strat_names_new_id_seq; Type: SEQUENCE; Schema: macrostrat; Owner: macrostrat
CREATE SEQUENCE macrostrat.strat_names_new_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

-- Name: strat_names_new_id_seq; Type: SEQUENCE OWNED BY; Schema: macrostrat; Owner: macrostrat
ALTER SEQUENCE macrostrat.strat_names_new_id_seq OWNED BY macrostrat.strat_names.id;

-- Name: strat_names_places; Type: TABLE; Schema: macrostrat; Owner: macrostrat
CREATE TABLE macrostrat.strat_names_places (
    strat_name_id integer NOT NULL,
    place_id integer NOT NULL
);

-- Name: TABLE strat_names_places; Type: COMMENT; Schema: macrostrat; Owner: macrostrat
COMMENT ON TABLE macrostrat.strat_names_places IS 'Last updated from MariaDB - 2022-06-28 14:54';

-- Name: strat_tree; Type: TABLE; Schema: macrostrat; Owner: macrostrat
CREATE TABLE macrostrat.strat_tree (
    id integer NOT NULL,
    parent integer,
    child integer,
    ref_id integer
);

-- Name: TABLE strat_tree; Type: COMMENT; Schema: macrostrat; Owner: macrostrat
COMMENT ON TABLE macrostrat.strat_tree IS 'Last updated from MariaDB - 2023-07-28 18:06';

-- Name: strat_tree_new_id_seq1; Type: SEQUENCE; Schema: macrostrat; Owner: macrostrat
CREATE SEQUENCE macrostrat.strat_tree_new_id_seq1
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

-- Name: strat_tree_new_id_seq1; Type: SEQUENCE OWNED BY; Schema: macrostrat; Owner: macrostrat
ALTER SEQUENCE macrostrat.strat_tree_new_id_seq1 OWNED BY macrostrat.strat_tree.id;

-- Name: timescales; Type: TABLE; Schema: macrostrat; Owner: macrostrat
CREATE TABLE macrostrat.timescales (
    id integer NOT NULL,
    timescale character varying(100),
    ref_id integer
);

-- Name: TABLE timescales; Type: COMMENT; Schema: macrostrat; Owner: macrostrat
COMMENT ON TABLE macrostrat.timescales IS 'Last updated from MariaDB - 2022-06-28 14:54';

-- Name: timescales_intervals; Type: TABLE; Schema: macrostrat; Owner: macrostrat
CREATE TABLE macrostrat.timescales_intervals (
    timescale_id integer,
    interval_id integer
);

-- Name: TABLE timescales_intervals; Type: COMMENT; Schema: macrostrat; Owner: macrostrat
COMMENT ON TABLE macrostrat.timescales_intervals IS 'Last updated from MariaDB - 2022-06-28 15:08';

-- Name: unit_boundaries; Type: TABLE; Schema: macrostrat; Owner: macrostrat
CREATE TABLE macrostrat.unit_boundaries (
    id integer NOT NULL,
    t1 numeric NOT NULL,
    t1_prop numeric(6,5) NOT NULL,
    t1_age numeric(8,4) NOT NULL,
    unit_id integer NOT NULL,
    unit_id_2 integer NOT NULL,
    section_id integer NOT NULL,
    boundary_position numeric(6,2) DEFAULT NULL::numeric,
    boundary_type macrostrat.boundary_type DEFAULT ''::macrostrat.boundary_type NOT NULL,
    boundary_status macrostrat.boundary_status DEFAULT 'modeled'::macrostrat.boundary_status NOT NULL,
    paleo_lat numeric(8,5),
    paleo_lng numeric(8,5),
    ref_id integer DEFAULT 217 NOT NULL
);

-- Name: unit_boundaries_id_seq; Type: SEQUENCE; Schema: macrostrat; Owner: macrostrat
CREATE SEQUENCE macrostrat.unit_boundaries_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

-- Name: unit_boundaries_id_seq; Type: SEQUENCE OWNED BY; Schema: macrostrat; Owner: macrostrat
ALTER SEQUENCE macrostrat.unit_boundaries_id_seq OWNED BY macrostrat.unit_boundaries.id;

-- Name: unit_econs; Type: TABLE; Schema: macrostrat; Owner: macrostrat
CREATE TABLE macrostrat.unit_econs (
    id integer NOT NULL,
    unit_id integer,
    econ_id integer,
    ref_id integer,
    date_mod text
);

-- Name: TABLE unit_econs; Type: COMMENT; Schema: macrostrat; Owner: macrostrat
COMMENT ON TABLE macrostrat.unit_econs IS 'Last updated from MariaDB - 2022-06-28 15:06';

-- Name: unit_environs; Type: TABLE; Schema: macrostrat; Owner: macrostrat
CREATE TABLE macrostrat.unit_environs (
    id integer NOT NULL,
    unit_id integer,
    environ_id integer,
    ref_id integer,
    date_mod text
);

-- Name: TABLE unit_environs; Type: COMMENT; Schema: macrostrat; Owner: macrostrat
COMMENT ON TABLE macrostrat.unit_environs IS 'Last updated from MariaDB - 2022-06-28 14:55';

-- Name: unit_lith_atts; Type: TABLE; Schema: macrostrat; Owner: macrostrat
CREATE TABLE macrostrat.unit_lith_atts (
    id integer NOT NULL,
    unit_lith_id integer,
    lith_att_id integer,
    ref_id integer,
    date_mod text
);

-- Name: TABLE unit_lith_atts; Type: COMMENT; Schema: macrostrat; Owner: macrostrat
COMMENT ON TABLE macrostrat.unit_lith_atts IS 'Last updated from MariaDB - 2022-06-28 15:10';

-- Name: unit_liths; Type: TABLE; Schema: macrostrat; Owner: macrostrat
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

-- Name: TABLE unit_liths; Type: COMMENT; Schema: macrostrat; Owner: macrostrat
COMMENT ON TABLE macrostrat.unit_liths IS 'Last updated from MariaDB - 2022-06-28 14:55';

-- Name: unit_measures; Type: TABLE; Schema: macrostrat; Owner: macrostrat
CREATE TABLE macrostrat.unit_measures (
    id integer NOT NULL,
    measuremeta_id integer NOT NULL,
    unit_id integer NOT NULL,
    strat_name_id integer NOT NULL,
    match_basis character varying(10) NOT NULL,
    rel_position numeric(6,5)
);

-- Name: TABLE unit_measures; Type: COMMENT; Schema: macrostrat; Owner: macrostrat
COMMENT ON TABLE macrostrat.unit_measures IS 'Last updated from MariaDB - 2018-09-25 10:40';

-- Name: unit_measures_new_id_seq; Type: SEQUENCE; Schema: macrostrat; Owner: macrostrat
CREATE SEQUENCE macrostrat.unit_measures_new_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

-- Name: unit_measures_new_id_seq; Type: SEQUENCE OWNED BY; Schema: macrostrat; Owner: macrostrat
ALTER SEQUENCE macrostrat.unit_measures_new_id_seq OWNED BY macrostrat.unit_measures.id;

-- Name: unit_strat_names; Type: TABLE; Schema: macrostrat; Owner: macrostrat
CREATE TABLE macrostrat.unit_strat_names (
    id integer NOT NULL,
    unit_id integer NOT NULL,
    strat_name_id integer NOT NULL
);

-- Name: TABLE unit_strat_names; Type: COMMENT; Schema: macrostrat; Owner: macrostrat
COMMENT ON TABLE macrostrat.unit_strat_names IS 'Last updated from MariaDB - 2022-06-28 14:54';

-- Name: unit_strat_names_new_id_seq1; Type: SEQUENCE; Schema: macrostrat; Owner: macrostrat
CREATE SEQUENCE macrostrat.unit_strat_names_new_id_seq1
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

-- Name: unit_strat_names_new_id_seq1; Type: SEQUENCE OWNED BY; Schema: macrostrat; Owner: macrostrat
ALTER SEQUENCE macrostrat.unit_strat_names_new_id_seq1 OWNED BY macrostrat.unit_strat_names.id;

-- Name: units; Type: TABLE; Schema: macrostrat; Owner: macrostrat
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

-- Name: TABLE units; Type: COMMENT; Schema: macrostrat; Owner: macrostrat
COMMENT ON TABLE macrostrat.units IS 'Last updated from MariaDB - 2022-06-28 15:10';

-- Name: units_sections; Type: TABLE; Schema: macrostrat; Owner: macrostrat
CREATE TABLE macrostrat.units_sections (
    id integer NOT NULL,
    unit_id integer NOT NULL,
    section_id integer NOT NULL,
    col_id integer NOT NULL
);

-- Name: TABLE units_sections; Type: COMMENT; Schema: macrostrat; Owner: macrostrat
COMMENT ON TABLE macrostrat.units_sections IS 'Last updated from MariaDB - 2022-06-28 15:07';

-- Name: units_sections_new_id_seq; Type: SEQUENCE; Schema: macrostrat; Owner: macrostrat
CREATE SEQUENCE macrostrat.units_sections_new_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

-- Name: units_sections_new_id_seq; Type: SEQUENCE OWNED BY; Schema: macrostrat; Owner: macrostrat
ALTER SEQUENCE macrostrat.units_sections_new_id_seq OWNED BY macrostrat.units_sections.id;

-- Name: col_groups; Type: VIEW; Schema: macrostrat_api; Owner: macrostrat
CREATE VIEW macrostrat_api.col_groups AS
 SELECT col_groups.id,
    col_groups.col_group,
    col_groups.col_group_long
   FROM macrostrat.col_groups;

-- Name: col_refs; Type: VIEW; Schema: macrostrat_api; Owner: macrostrat
CREATE VIEW macrostrat_api.col_refs AS
 SELECT col_refs.id,
    col_refs.col_id,
    col_refs.ref_id
   FROM macrostrat.col_refs;

-- Name: col_sections; Type: VIEW; Schema: macrostrat_api; Owner: macrostrat
CREATE VIEW macrostrat_api.col_sections AS
 SELECT c.id AS col_id,
    c.col_name,
    u.section_id,
    u.position_top,
    u.position_bottom,
    fo.interval_name AS bottom,
    lo.interval_name AS top
   FROM (((macrostrat.cols c
     LEFT JOIN macrostrat.units u ON ((u.col_id = c.id)))
     LEFT JOIN macrostrat.intervals fo ON ((u.fo = fo.id)))
     LEFT JOIN macrostrat.intervals lo ON ((u.lo = lo.id)));

-- Name: cols; Type: VIEW; Schema: macrostrat_api; Owner: macrostrat
CREATE VIEW macrostrat_api.cols AS
 SELECT cols.id,
    cols.col_group_id,
    cols.project_id,
    cols.col_type,
    cols.status_code,
    cols.col_position,
    cols.col,
    cols.col_name,
    cols.lat,
    cols.lng,
    cols.col_area,
    cols.coordinate,
    cols.wkt,
    cols.created,
    cols.poly_geom
   FROM macrostrat.cols;

-- Name: econ_unit; Type: VIEW; Schema: macrostrat_api; Owner: macrostrat
CREATE VIEW macrostrat_api.econ_unit AS
 SELECT e.id,
    e.econ,
    e.econ_type,
    e.econ_class,
    e.econ_color,
    ue.unit_id,
    ue.ref_id
   FROM (macrostrat.econs e
     JOIN macrostrat.unit_econs ue ON ((e.id = ue.econ_id)));

-- Name: environ_unit; Type: VIEW; Schema: macrostrat_api; Owner: macrostrat
CREATE VIEW macrostrat_api.environ_unit AS
 SELECT e.id,
    e.environ,
    e.environ_type,
    e.environ_class,
    e.environ_color,
    ue.unit_id,
    ue.ref_id
   FROM (macrostrat.environs e
     JOIN macrostrat.unit_environs ue ON ((e.id = ue.environ_id)));

-- Name: environs; Type: VIEW; Schema: macrostrat_api; Owner: macrostrat
CREATE VIEW macrostrat_api.environs AS
 SELECT environs.id,
    environs.environ,
    environs.environ_type,
    environs.environ_class,
    environs.environ_color
   FROM macrostrat.environs;

-- Name: intervals; Type: VIEW; Schema: macrostrat_api; Owner: macrostrat
CREATE VIEW macrostrat_api.intervals AS
 SELECT intervals.id,
    intervals.age_bottom,
    intervals.age_top,
    intervals.interval_name,
    intervals.interval_abbrev,
    intervals.interval_type,
    intervals.interval_color,
    intervals.rank
   FROM macrostrat.intervals;

-- Name: lith_attr_unit; Type: VIEW; Schema: macrostrat_api; Owner: macrostrat
CREATE VIEW macrostrat_api.lith_attr_unit AS
 SELECT la.id AS lith_attr_id,
    la.lith_att,
    la.att_type,
    la.lith_att_fill,
    l.id,
    l.lith,
    l.lith_group,
    l.lith_type,
    l.lith_class,
    l.lith_equiv,
    l.lith_fill,
    l.comp_coef,
    l.initial_porosity,
    l.bulk_density,
    l.lith_color,
    ul.unit_id
   FROM (((macrostrat.lith_atts la
     JOIN macrostrat.unit_lith_atts ula ON ((ula.lith_att_id = la.id)))
     JOIN macrostrat.unit_liths ul ON ((ul.id = ula.unit_lith_id)))
     JOIN macrostrat.liths l ON ((ul.lith_id = l.id)));

-- Name: lith_unit; Type: VIEW; Schema: macrostrat_api; Owner: macrostrat
CREATE VIEW macrostrat_api.lith_unit AS
 SELECT l.id,
    l.lith,
    l.lith_group,
    l.lith_type,
    l.lith_class,
    l.lith_color,
    ul.dom,
    ul.prop,
    ul.mod_prop,
    ul.comp_prop,
    ul.ref_id,
    ul.unit_id
   FROM (macrostrat.unit_liths ul
     JOIN macrostrat.liths l ON ((ul.lith_id = l.id)));

-- Name: liths; Type: VIEW; Schema: macrostrat_api; Owner: macrostrat
CREATE VIEW macrostrat_api.liths AS
 SELECT liths.id,
    liths.lith,
    liths.lith_group,
    liths.lith_type,
    liths.lith_class,
    liths.lith_equiv,
    liths.lith_fill,
    liths.comp_coef,
    liths.initial_porosity,
    liths.bulk_density,
    liths.lith_color
   FROM macrostrat.liths;

-- Name: refs; Type: VIEW; Schema: macrostrat_api; Owner: macrostrat
CREATE VIEW macrostrat_api.refs AS
 SELECT refs.id,
    refs.pub_year,
    refs.author,
    refs.ref,
    refs.doi,
    refs.compilation_code,
    refs.url,
    refs.rgeom
   FROM macrostrat.refs;

-- Name: strat_names; Type: VIEW; Schema: macrostrat_api; Owner: macrostrat
CREATE VIEW macrostrat_api.strat_names AS
 SELECT strat_names.id,
    strat_names.strat_name,
    strat_names.rank,
    strat_names.ref_id,
    strat_names.concept_id
   FROM macrostrat.strat_names;

-- Name: strat_names_meta; Type: VIEW; Schema: macrostrat_api; Owner: macrostrat
CREATE VIEW macrostrat_api.strat_names_meta AS
 SELECT strat_names_meta.concept_id,
    strat_names_meta.orig_id,
    strat_names_meta.name,
    strat_names_meta.geologic_age,
    strat_names_meta.interval_id,
    strat_names_meta.b_int,
    strat_names_meta.t_int,
    strat_names_meta.usage_notes,
    strat_names_meta.other,
    strat_names_meta.province,
    strat_names_meta.url,
    strat_names_meta.ref_id
   FROM macrostrat.strat_names_meta;

-- Name: strat_names_ref; Type: VIEW; Schema: macrostrat_api; Owner: macrostrat
CREATE VIEW macrostrat_api.strat_names_ref AS
 SELECT s.id,
    s.strat_name,
    s.rank,
    row_to_json(r.*) AS ref,
    row_to_json(sm.*) AS concept
   FROM ((macrostrat.strat_names s
     LEFT JOIN macrostrat.refs r ON ((r.id = s.ref_id)))
     LEFT JOIN macrostrat.strat_names_meta sm ON ((sm.concept_id = s.concept_id)));

-- Name: timescales; Type: VIEW; Schema: macrostrat_api; Owner: macrostrat
CREATE VIEW macrostrat_api.timescales AS
 SELECT timescales.id,
    timescales.timescale,
    timescales.ref_id
   FROM macrostrat.timescales;

-- Name: unit_environs; Type: VIEW; Schema: macrostrat_api; Owner: macrostrat
CREATE VIEW macrostrat_api.unit_environs AS
 SELECT unit_environs.id,
    unit_environs.unit_id,
    unit_environs.environ_id,
    unit_environs.ref_id,
    unit_environs.date_mod
   FROM macrostrat.unit_environs;

-- Name: unit_liths; Type: VIEW; Schema: macrostrat_api; Owner: macrostrat
CREATE VIEW macrostrat_api.unit_liths AS
 SELECT unit_liths.id,
    unit_liths.lith_id,
    unit_liths.unit_id,
    unit_liths.prop,
    unit_liths.dom,
    unit_liths.comp_prop,
    unit_liths.mod_prop,
    unit_liths.toc,
    unit_liths.ref_id,
    unit_liths.date_mod
   FROM macrostrat.unit_liths;

-- Name: unit_strat_names; Type: VIEW; Schema: macrostrat_api; Owner: macrostrat
CREATE VIEW macrostrat_api.unit_strat_names AS
 SELECT unit_strat_names.id,
    unit_strat_names.unit_id,
    unit_strat_names.strat_name_id
   FROM macrostrat.unit_strat_names;

-- Name: units; Type: VIEW; Schema: macrostrat_api; Owner: macrostrat
CREATE VIEW macrostrat_api.units AS
 SELECT units.id,
    units.strat_name,
    units.color,
    units.outcrop,
    units.fo,
    units.fo_h,
    units.lo,
    units.lo_h,
    units.position_bottom,
    units.position_top,
    units.max_thick,
    units.min_thick,
    units.section_id,
    units.col_id
   FROM macrostrat.units;

-- Name: group; Type: TABLE; Schema: macrostrat_auth; Owner: macrostrat
CREATE TABLE macrostrat_auth."group" (
    id integer NOT NULL,
    name character varying(255) NOT NULL
);

-- Name: group_id_seq; Type: SEQUENCE; Schema: macrostrat_auth; Owner: macrostrat
CREATE SEQUENCE macrostrat_auth.group_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

-- Name: group_id_seq; Type: SEQUENCE OWNED BY; Schema: macrostrat_auth; Owner: macrostrat
ALTER SEQUENCE macrostrat_auth.group_id_seq OWNED BY macrostrat_auth."group".id;

-- Name: group_members; Type: TABLE; Schema: macrostrat_auth; Owner: macrostrat
CREATE TABLE macrostrat_auth.group_members (
    id integer NOT NULL,
    group_id integer NOT NULL,
    user_id integer NOT NULL
);

-- Name: group_members_id_seq; Type: SEQUENCE; Schema: macrostrat_auth; Owner: macrostrat
CREATE SEQUENCE macrostrat_auth.group_members_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

-- Name: group_members_id_seq; Type: SEQUENCE OWNED BY; Schema: macrostrat_auth; Owner: macrostrat
ALTER SEQUENCE macrostrat_auth.group_members_id_seq OWNED BY macrostrat_auth.group_members.id;

-- Name: token; Type: TABLE; Schema: macrostrat_auth; Owner: macrostrat
CREATE TABLE macrostrat_auth.token (
    id integer NOT NULL,
    token character varying(255) NOT NULL,
    "group" integer NOT NULL,
    used_on timestamp with time zone,
    expires_on timestamp with time zone NOT NULL,
    created_on timestamp with time zone DEFAULT now() NOT NULL
);

-- Name: token_id_seq; Type: SEQUENCE; Schema: macrostrat_auth; Owner: macrostrat
CREATE SEQUENCE macrostrat_auth.token_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

-- Name: token_id_seq; Type: SEQUENCE OWNED BY; Schema: macrostrat_auth; Owner: macrostrat
ALTER SEQUENCE macrostrat_auth.token_id_seq OWNED BY macrostrat_auth.token.id;

-- Name: user; Type: TABLE; Schema: macrostrat_auth; Owner: macrostrat
CREATE TABLE macrostrat_auth."user" (
    id integer NOT NULL,
    sub character varying(255) NOT NULL,
    name character varying(255) NOT NULL,
    email character varying(255) NOT NULL,
    created_on timestamp with time zone DEFAULT now() NOT NULL,
    updated_on timestamp with time zone DEFAULT now() NOT NULL
);

-- Name: user_id_seq; Type: SEQUENCE; Schema: macrostrat_auth; Owner: macrostrat
CREATE SEQUENCE macrostrat_auth.user_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

-- Name: user_id_seq; Type: SEQUENCE OWNED BY; Schema: macrostrat_auth; Owner: macrostrat
ALTER SEQUENCE macrostrat_auth.user_id_seq OWNED BY macrostrat_auth."user".id;

-- Name: metadata; Type: TABLE; Schema: macrostrat_kg; Owner: macrostrat
CREATE TABLE macrostrat_kg.metadata (
    run_id character varying(31),
    start_time numeric,
    end_time numeric,
    run_description character varying(31)
);

-- Name: relations; Type: TABLE; Schema: macrostrat_kg; Owner: macrostrat
CREATE TABLE macrostrat_kg.relations (
    relationship_id integer,
    kg_strat_id integer,
    kg_strat_name character varying(72),
    src character varying(72),
    src_id integer,
    relationship_type character varying(72),
    dst character varying(72),
    dst_id integer
);

-- Name: sources; Type: TABLE; Schema: macrostrat_kg; Owner: macrostrat
CREATE TABLE macrostrat_kg.sources (
    relationship_id integer,
    article_id character varying(1862),
    txt_used character varying(1862)
);

-- Name: map_ids; Type: SEQUENCE; Schema: maps; Owner: macrostrat
CREATE SEQUENCE maps.map_ids
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

-- Name: polygons; Type: TABLE; Schema: maps; Owner: macrostrat
CREATE TABLE maps.polygons (
    map_id integer DEFAULT nextval('maps.map_ids'::regclass) NOT NULL,
    source_id integer NOT NULL,
    scale macrostrat.map_scale NOT NULL,
    orig_id integer,
    name text,
    strat_name text,
    age character varying(255),
    lith text,
    descrip text,
    comments text,
    t_interval integer,
    b_interval integer,
    geom public.geometry(Geometry,4326) NOT NULL,
    CONSTRAINT maps_polygons_geom_check CHECK (maps.polygons_geom_is_valid(geom))
)
PARTITION BY LIST (scale);

-- Name: map_ids; Type: SEQUENCE; Schema: public; Owner: macrostrat
CREATE SEQUENCE public.map_ids
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

-- Name: polygons_large; Type: TABLE; Schema: maps; Owner: macrostrat
CREATE TABLE maps.polygons_large (
    map_id integer DEFAULT nextval('public.map_ids'::regclass) NOT NULL,
    orig_id integer,
    source_id integer NOT NULL,
    name text,
    strat_name text,
    age character varying(255),
    lith text,
    descrip text,
    comments text,
    t_interval integer,
    b_interval integer,
    geom public.geometry(Geometry,4326) NOT NULL,
    scale macrostrat.map_scale DEFAULT 'large'::macrostrat.map_scale NOT NULL,
    CONSTRAINT enforce_valid_geom_large CHECK (public.st_isvalid(geom)),
    CONSTRAINT maps_polygons_geom_check CHECK (maps.polygons_geom_is_valid(geom)),
    CONSTRAINT polygons_large_scale_check CHECK ((scale = 'large'::macrostrat.map_scale))
);

-- Name: large; Type: VIEW; Schema: maps; Owner: macrostrat
CREATE VIEW maps.large AS
 SELECT polygons_large.map_id,
    polygons_large.orig_id,
    polygons_large.source_id,
    polygons_large.name,
    polygons_large.strat_name,
    polygons_large.age,
    polygons_large.lith,
    polygons_large.descrip,
    polygons_large.comments,
    polygons_large.t_interval,
    polygons_large.b_interval,
    polygons_large.geom
   FROM maps.polygons_large;

-- Name: legend; Type: TABLE; Schema: maps; Owner: macrostrat
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

-- Name: legend_legend_id_seq; Type: SEQUENCE; Schema: maps; Owner: macrostrat
CREATE SEQUENCE maps.legend_legend_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

-- Name: legend_legend_id_seq; Type: SEQUENCE OWNED BY; Schema: maps; Owner: macrostrat
ALTER SEQUENCE maps.legend_legend_id_seq OWNED BY maps.legend.legend_id;

-- Name: legend_liths; Type: TABLE; Schema: maps; Owner: macrostrat
CREATE TABLE maps.legend_liths (
    legend_id integer NOT NULL,
    lith_id integer NOT NULL,
    basis_col text NOT NULL
);

-- Name: lines_large; Type: TABLE; Schema: maps; Owner: macrostrat
CREATE TABLE maps.lines_large (
    line_id integer DEFAULT nextval('public.line_ids'::regclass) NOT NULL,
    orig_id integer,
    source_id integer,
    name character varying(255),
    type_legacy character varying(100),
    direction_legacy character varying(40),
    descrip text,
    geom public.geometry(Geometry,4326) NOT NULL,
    type character varying(100),
    direction character varying(40),
    scale macrostrat.map_scale DEFAULT 'large'::macrostrat.map_scale NOT NULL,
    CONSTRAINT lines_large_scale_check CHECK ((scale = 'large'::macrostrat.map_scale)),
    CONSTRAINT maps_lines_geom_check CHECK (maps.lines_geom_is_valid(geom))
);

-- Name: lines_medium; Type: TABLE; Schema: maps; Owner: macrostrat
CREATE TABLE maps.lines_medium (
    line_id integer DEFAULT nextval('public.line_ids'::regclass) NOT NULL,
    orig_id integer,
    source_id integer,
    name character varying(255),
    type_legacy character varying(100),
    direction_legacy character varying(40),
    descrip text,
    geom public.geometry(Geometry,4326) NOT NULL,
    type character varying(100),
    direction character varying(40),
    scale macrostrat.map_scale DEFAULT 'medium'::macrostrat.map_scale NOT NULL,
    CONSTRAINT lines_medium_scale_check CHECK ((scale = 'medium'::macrostrat.map_scale)),
    CONSTRAINT maps_lines_geom_check CHECK (maps.lines_geom_is_valid(geom))
);

-- Name: lines_small; Type: TABLE; Schema: maps; Owner: macrostrat
CREATE TABLE maps.lines_small (
    line_id integer DEFAULT nextval('public.line_ids'::regclass) NOT NULL,
    orig_id integer,
    source_id integer,
    name character varying(255),
    type_legacy character varying(100),
    direction_legacy character varying(40),
    descrip text,
    geom public.geometry(Geometry,4326) NOT NULL,
    type character varying(100),
    direction character varying(40),
    scale macrostrat.map_scale DEFAULT 'small'::macrostrat.map_scale NOT NULL,
    CONSTRAINT lines_small_scale_check CHECK ((scale = 'small'::macrostrat.map_scale)),
    CONSTRAINT maps_lines_geom_check CHECK (maps.lines_geom_is_valid(geom))
);

-- Name: lines_tiny; Type: TABLE; Schema: maps; Owner: macrostrat
CREATE TABLE maps.lines_tiny (
    line_id integer DEFAULT nextval('public.line_ids'::regclass) NOT NULL,
    orig_id integer,
    source_id integer,
    name character varying(255),
    type_legacy character varying(100),
    direction_legacy character varying(40),
    descrip text,
    geom public.geometry(Geometry,4326) NOT NULL,
    type character varying(100),
    direction character varying(40),
    scale macrostrat.map_scale DEFAULT 'tiny'::macrostrat.map_scale NOT NULL,
    CONSTRAINT isvalid CHECK (public.st_isvalid(geom)),
    CONSTRAINT lines_tiny_scale_check CHECK ((scale = 'tiny'::macrostrat.map_scale)),
    CONSTRAINT maps_lines_geom_check CHECK (maps.lines_geom_is_valid(geom))
);

-- Name: manual_matches; Type: TABLE; Schema: maps; Owner: macrostrat
CREATE TABLE maps.manual_matches (
    match_id integer NOT NULL,
    map_id integer NOT NULL,
    strat_name_id integer,
    unit_id integer,
    addition boolean DEFAULT false,
    removal boolean DEFAULT false,
    type character varying(20)
);

-- Name: manual_matches_match_id_seq; Type: SEQUENCE; Schema: maps; Owner: macrostrat
CREATE SEQUENCE maps.manual_matches_match_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

-- Name: manual_matches_match_id_seq; Type: SEQUENCE OWNED BY; Schema: maps; Owner: macrostrat
ALTER SEQUENCE maps.manual_matches_match_id_seq OWNED BY maps.manual_matches.match_id;

-- Name: map_legend; Type: TABLE; Schema: maps; Owner: macrostrat
CREATE TABLE maps.map_legend (
    legend_id integer NOT NULL,
    map_id integer NOT NULL
);

-- Name: map_liths; Type: TABLE; Schema: maps; Owner: macrostrat
CREATE TABLE maps.map_liths (
    map_id integer NOT NULL,
    lith_id integer NOT NULL,
    basis_col character varying(50)
);

-- Name: map_strat_names; Type: TABLE; Schema: maps; Owner: macrostrat
CREATE TABLE maps.map_strat_names (
    map_id integer NOT NULL,
    strat_name_id integer NOT NULL,
    basis_col character varying(50)
);

-- Name: map_units; Type: TABLE; Schema: maps; Owner: macrostrat
CREATE TABLE maps.map_units (
    map_id integer NOT NULL,
    unit_id integer NOT NULL,
    basis_col character varying(50)
);

-- Name: polygons_medium; Type: TABLE; Schema: maps; Owner: macrostrat
CREATE TABLE maps.polygons_medium (
    map_id integer DEFAULT nextval('public.map_ids'::regclass) NOT NULL,
    orig_id integer,
    source_id integer NOT NULL,
    name text,
    strat_name text,
    age character varying(255),
    lith text,
    descrip text,
    comments text,
    t_interval integer,
    b_interval integer,
    geom public.geometry(Geometry,4326) NOT NULL,
    scale macrostrat.map_scale DEFAULT 'medium'::macrostrat.map_scale NOT NULL,
    CONSTRAINT enforce_valid_geom_medium CHECK (public.st_isvalid(geom)),
    CONSTRAINT maps_polygons_geom_check CHECK (maps.polygons_geom_is_valid(geom)),
    CONSTRAINT polygons_medium_scale_check CHECK ((scale = 'medium'::macrostrat.map_scale))
);

-- Name: medium; Type: VIEW; Schema: maps; Owner: macrostrat
CREATE VIEW maps.medium AS
 SELECT polygons_medium.map_id,
    polygons_medium.orig_id,
    polygons_medium.source_id,
    polygons_medium.name,
    polygons_medium.strat_name,
    polygons_medium.age,
    polygons_medium.lith,
    polygons_medium.descrip,
    polygons_medium.comments,
    polygons_medium.t_interval,
    polygons_medium.b_interval,
    polygons_medium.geom
   FROM maps.polygons_medium;

-- Name: points; Type: TABLE; Schema: maps; Owner: macrostrat
CREATE TABLE maps.points (
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

-- Name: points_point_id_seq; Type: SEQUENCE; Schema: maps; Owner: macrostrat
CREATE SEQUENCE maps.points_point_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

-- Name: points_point_id_seq; Type: SEQUENCE OWNED BY; Schema: maps; Owner: macrostrat
ALTER SEQUENCE maps.points_point_id_seq OWNED BY maps.points.point_id;

-- Name: polygons_small; Type: TABLE; Schema: maps; Owner: macrostrat
CREATE TABLE maps.polygons_small (
    map_id integer DEFAULT nextval('public.map_ids'::regclass) NOT NULL,
    orig_id integer,
    source_id integer NOT NULL,
    name text,
    strat_name text,
    age character varying(255),
    lith text,
    descrip text,
    comments text,
    t_interval integer,
    b_interval integer,
    geom public.geometry(Geometry,4326) NOT NULL,
    scale macrostrat.map_scale DEFAULT 'small'::macrostrat.map_scale NOT NULL,
    CONSTRAINT maps_polygons_geom_check CHECK (maps.polygons_geom_is_valid(geom)),
    CONSTRAINT polygons_small_scale_check CHECK ((scale = 'small'::macrostrat.map_scale))
);

-- Name: polygons_tiny; Type: TABLE; Schema: maps; Owner: macrostrat
CREATE TABLE maps.polygons_tiny (
    map_id integer DEFAULT nextval('public.map_ids'::regclass) NOT NULL,
    orig_id integer,
    source_id integer NOT NULL,
    name text,
    strat_name text,
    age character varying(255),
    lith text,
    descrip text,
    comments text,
    t_interval integer,
    b_interval integer,
    geom public.geometry(Geometry,4326) NOT NULL,
    scale macrostrat.map_scale DEFAULT 'tiny'::macrostrat.map_scale NOT NULL,
    CONSTRAINT maps_polygons_geom_check CHECK (maps.polygons_geom_is_valid(geom)),
    CONSTRAINT polygons_tiny_scale_check CHECK ((scale = 'tiny'::macrostrat.map_scale))
);

-- Name: small; Type: VIEW; Schema: maps; Owner: macrostrat
CREATE VIEW maps.small AS
 SELECT polygons_small.map_id,
    polygons_small.orig_id,
    polygons_small.source_id,
    polygons_small.name,
    polygons_small.strat_name,
    polygons_small.age,
    polygons_small.lith,
    polygons_small.descrip,
    polygons_small.comments,
    polygons_small.t_interval,
    polygons_small.b_interval,
    polygons_small.geom
   FROM maps.polygons_small;

-- Name: source_operations; Type: TABLE; Schema: maps; Owner: macrostrat
CREATE TABLE maps.source_operations (
    id integer NOT NULL,
    source_id integer NOT NULL,
    user_id integer,
    operation text NOT NULL,
    app text NOT NULL,
    comments text,
    details jsonb,
    date timestamp with time zone DEFAULT now() NOT NULL
);

-- Name: TABLE source_operations; Type: COMMENT; Schema: maps; Owner: macrostrat
COMMENT ON TABLE maps.source_operations IS 'Tracks management operations for Macrostrat maps';

-- Name: source_operations_id_seq; Type: SEQUENCE; Schema: maps; Owner: macrostrat
CREATE SEQUENCE maps.source_operations_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

-- Name: source_operations_id_seq; Type: SEQUENCE OWNED BY; Schema: maps; Owner: macrostrat
ALTER SEQUENCE maps.source_operations_id_seq OWNED BY maps.source_operations.id;

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
    keywords text[],
    language text,
    description varchar,
    primary_line_table character varying(50),
    license character varying(100),
    features integer,
    area integer,
    priority boolean DEFAULT false,
    rgeom public.geometry,
    display_scales text[],
    web_geom public.geometry,
    new_priority integer DEFAULT 0,
    status_code text DEFAULT 'active'::text,
    slug text NOT NULL
);

COMMENT ON COLUMN maps.sources.slug IS 'Unique identifier for each Macrostrat source';

-- Name: sources_source_id_seq; Type: SEQUENCE; Schema: maps; Owner: macrostrat
CREATE SEQUENCE maps.sources_source_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

-- Name: sources_source_id_seq; Type: SEQUENCE OWNED BY; Schema: maps; Owner: macrostrat
ALTER SEQUENCE maps.sources_source_id_seq OWNED BY maps.sources.source_id;

-- Name: tiny; Type: VIEW; Schema: maps; Owner: macrostrat
CREATE VIEW maps.tiny AS
 SELECT polygons_tiny.map_id,
    polygons_tiny.orig_id,
    polygons_tiny.source_id,
    polygons_tiny.name,
    polygons_tiny.strat_name,
    polygons_tiny.age,
    polygons_tiny.lith,
    polygons_tiny.descrip,
    polygons_tiny.comments,
    polygons_tiny.t_interval,
    polygons_tiny.b_interval,
    polygons_tiny.geom
   FROM maps.polygons_tiny;

-- Name: sources; Type: TABLE; Schema: maps_metadata; Owner: kateakin
CREATE TABLE maps_metadata.sources (
    source_id integer,
    raster_bucket_url text,
    date_compiled timestamp without time zone,
    compiler_name text,
    raster_source_url text
);

-- Name: sources_meta; Type: VIEW; Schema: maps_metadata; Owner: kateakin
CREATE VIEW maps_metadata.sources_meta AS
 SELECT ms.source_id,
    ms.raster_bucket_url,
    ms.date_compiled,
    ms.compiler_name,
    ms.raster_source_url,
    s.name,
    s.url,
    s.ref_title,
    s.authors,
    s.ref_year,
    s.ref_source,
    s.isbn_doi,
    s.scale,
    s.license,
    s.features,
    s.area,
    s.priority,
    s.display_scales,
    s.status_code,
    s.slug
   FROM (maps.sources s
     LEFT JOIN maps_metadata.sources ms ON ((ms.source_id = s.source_id)));

-- Name: points; Type: VIEW; Schema: points; Owner: macrostrat
CREATE VIEW points.points AS
 SELECT points.source_id,
    points.strike,
    points.dip,
    points.dip_dir,
    points.point_type,
    points.certainty,
    points.comments,
    points.geom,
    points.point_id,
    points.orig_id
   FROM maps.points;

-- Name: impervious; Type: TABLE; Schema: public; Owner: macrostrat
CREATE TABLE public.impervious (
    rid integer NOT NULL,
    rast public.raster
);

-- Name: impervious_rid_seq; Type: SEQUENCE; Schema: public; Owner: macrostrat
CREATE SEQUENCE public.impervious_rid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

-- Name: impervious_rid_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: macrostrat
ALTER SEQUENCE public.impervious_rid_seq OWNED BY public.impervious.rid;

-- Name: land; Type: TABLE; Schema: public; Owner: macrostrat
CREATE TABLE public.land (
    gid integer NOT NULL,
    scalerank numeric(10,0),
    featurecla character varying(32),
    geom public.geometry(MultiPolygon,4326)
);

-- Name: land_gid_seq; Type: SEQUENCE; Schema: public; Owner: macrostrat
CREATE SEQUENCE public.land_gid_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

-- Name: land_gid_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: macrostrat
ALTER SEQUENCE public.land_gid_seq OWNED BY public.land.gid;

-- Name: lookup_large; Type: TABLE; Schema: public; Owner: macrostrat
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

-- Name: lookup_medium; Type: TABLE; Schema: public; Owner: macrostrat
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

-- Name: lookup_small; Type: TABLE; Schema: public; Owner: macrostrat
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

-- Name: lookup_tiny; Type: TABLE; Schema: public; Owner: macrostrat
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

-- Name: macrostrat_union; Type: TABLE; Schema: public; Owner: macrostrat
CREATE TABLE public.macrostrat_union (
    id integer NOT NULL,
    geom public.geometry
);

-- Name: macrostrat_union_id_seq; Type: SEQUENCE; Schema: public; Owner: macrostrat
CREATE SEQUENCE public.macrostrat_union_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

-- Name: macrostrat_union_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: macrostrat
ALTER SEQUENCE public.macrostrat_union_id_seq OWNED BY public.macrostrat_union.id;

-- Name: ref_boundaries; Type: TABLE; Schema: public; Owner: macrostrat
CREATE TABLE public.ref_boundaries (
    ref_id integer,
    ref text,
    geom public.geometry
);

-- Name: srtm1; Type: FOREIGN TABLE; Schema: public; Owner: macrostrat
CREATE FOREIGN TABLE public.srtm1 (
    rid integer,
    rast public.raster
)
SERVER elevation
OPTIONS (
    schema_name 'sources',
    table_name 'srtm1'
);

-- Name: units; Type: TABLE; Schema: public; Owner: macrostrat
CREATE TABLE public.units (
    mapunit text,
    description text
);

-- Name: profile; Type: TABLE; Schema: tile_cache; Owner: macrostrat
CREATE TABLE tile_cache.profile (
    name text NOT NULL,
    format text NOT NULL,
    content_type text NOT NULL,
    minzoom integer,
    maxzoom integer
);

-- Name: tile; Type: TABLE; Schema: tile_cache; Owner: macrostrat
CREATE TABLE tile_cache.tile (
    x integer NOT NULL,
    y integer NOT NULL,
    z integer NOT NULL,
    layers text[] NOT NULL,
    tile bytea NOT NULL,
    profile text NOT NULL,
    tms text DEFAULT current_setting('tile_utils.default_tms'::text) NOT NULL,
    created timestamp without time zone DEFAULT now() NOT NULL,
    last_used timestamp without time zone DEFAULT now() NOT NULL,
    CONSTRAINT tile_check CHECK (((x >= 0) AND (y >= 0) AND (z >= 0) AND ((x)::double precision < ((2)::double precision ^ (z)::double precision)) AND ((y)::double precision < ((2)::double precision ^ (z)::double precision))))
);

-- Name: tile_info; Type: VIEW; Schema: tile_cache; Owner: macrostrat
CREATE VIEW tile_cache.tile_info AS
 SELECT tile.x,
    tile.y,
    tile.z,
    tile.layers,
    length(tile.tile) AS tile_size,
    tile.profile,
    tile.tms,
    tile.created,
    tile.last_used
   FROM tile_cache.tile;

-- Name: carto_units; Type: VIEW; Schema: tile_layers; Owner: macrostrat
CREATE VIEW tile_layers.carto_units AS
 SELECT polygons.map_id,
    polygons.source_id,
    polygons.geom,
    (polygons.scale)::text AS scale
   FROM carto.polygons;

-- Name: line_data; Type: VIEW; Schema: tile_layers; Owner: macrostrat
CREATE VIEW tile_layers.line_data AS
 SELECT l.line_id,
    l1.descrip,
    (l1.name)::text AS name,
    (l1.direction)::text AS direction,
    (l1.type)::text AS type,
    (l.scale)::text AS scale
   FROM (carto.lines l
     JOIN maps.lines l1 ON ((l.line_id = l1.line_id)));

-- Name: map_legend_info; Type: VIEW; Schema: tile_layers; Owner: macrostrat
CREATE VIEW tile_layers.map_legend_info AS
 SELECT l.legend_id,
    (l.best_age_top)::double precision AS best_age_top,
    (l.best_age_bottom)::double precision AS best_age_bottom,
    COALESCE(l.color, '#777777'::text) AS color,
    l.all_lith_classes[1] AS lith_class1,
    l.all_lith_classes[2] AS lith_class2,
    l.all_lith_classes[3] AS lith_class3,
    l.all_lith_types[1] AS lith_type1,
    l.all_lith_types[2] AS lith_type2,
    l.all_lith_types[3] AS lith_type3,
    l.all_lith_types[4] AS lith_type4,
    l.all_lith_types[5] AS lith_type5,
    l.all_lith_types[6] AS lith_type6,
    l.all_lith_types[7] AS lith_type7,
    l.all_lith_types[8] AS lith_type8,
    l.all_lith_types[9] AS lith_type9,
    l.all_lith_types[10] AS lith_type10,
    l.all_lith_types[11] AS lith_type11,
    l.all_lith_types[12] AS lith_type12,
    l.all_lith_types[13] AS lith_type13
   FROM maps.legend l;

-- Name: map_lines; Type: VIEW; Schema: tile_layers; Owner: macrostrat
CREATE VIEW tile_layers.map_lines AS
 SELECT lines.line_id,
    lines.orig_id,
    lines.source_id,
    lines.name,
    lines.type_legacy,
    lines.direction_legacy,
    lines.descrip,
    lines.geom,
    lines.type,
    lines.direction,
    lines.scale
   FROM maps.lines;

-- Name: map_units; Type: VIEW; Schema: tile_layers; Owner: macrostrat
CREATE VIEW tile_layers.map_units AS
 SELECT tiny.map_id,
    tiny.orig_id,
    tiny.source_id,
    tiny.name,
    tiny.strat_name,
    tiny.age,
    tiny.lith,
    tiny.descrip,
    tiny.comments,
    tiny.t_interval,
    tiny.b_interval,
    tiny.geom,
    'tiny'::text AS scale
   FROM maps.tiny
UNION ALL
 SELECT small.map_id,
    small.orig_id,
    small.source_id,
    small.name,
    small.strat_name,
    small.age,
    small.lith,
    small.descrip,
    small.comments,
    small.t_interval,
    small.b_interval,
    small.geom,
    'small'::text AS scale
   FROM maps.small
UNION ALL
 SELECT medium.map_id,
    medium.orig_id,
    medium.source_id,
    medium.name,
    medium.strat_name,
    medium.age,
    medium.lith,
    medium.descrip,
    medium.comments,
    medium.t_interval,
    medium.b_interval,
    medium.geom,
    'medium'::text AS scale
   FROM maps.medium
UNION ALL
 SELECT large.map_id,
    large.orig_id,
    large.source_id,
    large.name,
    large.strat_name,
    large.age,
    large.lith,
    large.descrip,
    large.comments,
    large.t_interval,
    large.b_interval,
    large.geom,
    'large'::text AS scale
   FROM maps.large;

-- Name: data_unified_loose; Type: VIEW; Schema: weaver_api; Owner: macrostrat
CREATE VIEW weaver_api.data_unified_loose AS
 SELECT dm.id,
    dd.dataset_id,
    dm.model_name,
    'datum'::text AS type,
    (dm.data ->> 'url'::text) AS url,
    dm.data,
    s.id AS source_id,
    s.name AS source_name,
    s.url AS source_url,
    dm.created_at,
    dm.updated_at,
    d.location
   FROM (((weaver.datum dm
     JOIN weaver.dataset_data dd ON ((dm.id = dd.datum_id)))
     JOIN weaver.dataset d ON ((dd.dataset_id = d.id)))
     JOIN weaver.data_source s ON ((s.id = d.source_id)))
UNION ALL
 SELECT d.id,
    d.id AS dataset_id,
    d.model_name,
    'dataset'::text AS type,
    (d.data ->> 'url'::text) AS url,
    d.data,
    s.id AS source_id,
    s.name AS source_name,
    s.url AS source_url,
    d.created_at,
    d.updated_at,
    d.location
   FROM (weaver.dataset d
     JOIN weaver.data_source s ON ((d.source_id = s.id)));

-- Name: dataset; Type: VIEW; Schema: weaver_api; Owner: macrostrat
CREATE VIEW weaver_api.dataset AS
 WITH data AS (
         SELECT datum.id,
            ARRAY[datum.model_name, (datum.id)::text, (datum.data ->> 'url'::text)] AS val
           FROM weaver.datum
        )
 SELECT d.id,
    d.location,
    s.name,
    s.url,
    d.model_name,
    d.data,
    json_agg(dm.val) AS associated_data
   FROM (((weaver.dataset d
     JOIN weaver.data_link dl ON ((dl.dataset_id = d.id)))
     JOIN weaver.data_source s ON ((d.source_id = s.id)))
     JOIN data dm ON ((dl.datum_id = dm.id)))
  GROUP BY d.id, s.name, s.url
  ORDER BY d.id;

-- Name: model; Type: VIEW; Schema: weaver_api; Owner: macrostrat
CREATE VIEW weaver_api.model AS
 SELECT model.name,
    model.is_meta,
    model.is_data,
    model.is_root,
    model.definition
   FROM weaver.model;

-- Name: measuremeta_dataset; Type: TABLE; Schema: weaver_macrostrat; Owner: macrostrat
CREATE TABLE weaver_macrostrat.measuremeta_dataset (
    measuremeta_id integer NOT NULL,
    dataset_id uuid NOT NULL
);

-- Name: ref_datum; Type: TABLE; Schema: weaver_macrostrat; Owner: macrostrat
CREATE TABLE weaver_macrostrat.ref_datum (
    ref_id integer NOT NULL,
    datum_id uuid NOT NULL
);

-- Name: lines_large; Type: TABLE ATTACH; Schema: carto; Owner: macrostrat
ALTER TABLE ONLY carto.lines ATTACH PARTITION carto.lines_large FOR VALUES IN ('large');

-- Name: lines_medium; Type: TABLE ATTACH; Schema: carto; Owner: macrostrat
ALTER TABLE ONLY carto.lines ATTACH PARTITION carto.lines_medium FOR VALUES IN ('medium');

-- Name: lines_small; Type: TABLE ATTACH; Schema: carto; Owner: macrostrat
ALTER TABLE ONLY carto.lines ATTACH PARTITION carto.lines_small FOR VALUES IN ('small');

-- Name: lines_tiny; Type: TABLE ATTACH; Schema: carto; Owner: macrostrat
ALTER TABLE ONLY carto.lines ATTACH PARTITION carto.lines_tiny FOR VALUES IN ('tiny');

-- Name: polygons_large; Type: TABLE ATTACH; Schema: carto; Owner: macrostrat
ALTER TABLE ONLY carto.polygons ATTACH PARTITION carto.polygons_large FOR VALUES IN ('large');

-- Name: polygons_medium; Type: TABLE ATTACH; Schema: carto; Owner: macrostrat
ALTER TABLE ONLY carto.polygons ATTACH PARTITION carto.polygons_medium FOR VALUES IN ('medium');

-- Name: polygons_small; Type: TABLE ATTACH; Schema: carto; Owner: macrostrat
ALTER TABLE ONLY carto.polygons ATTACH PARTITION carto.polygons_small FOR VALUES IN ('small');

-- Name: polygons_tiny; Type: TABLE ATTACH; Schema: carto; Owner: macrostrat
ALTER TABLE ONLY carto.polygons ATTACH PARTITION carto.polygons_tiny FOR VALUES IN ('tiny');

-- Name: lines_large; Type: TABLE ATTACH; Schema: maps; Owner: macrostrat
ALTER TABLE ONLY maps.lines ATTACH PARTITION maps.lines_large FOR VALUES IN ('large');

-- Name: lines_medium; Type: TABLE ATTACH; Schema: maps; Owner: macrostrat
ALTER TABLE ONLY maps.lines ATTACH PARTITION maps.lines_medium FOR VALUES IN ('medium');

-- Name: lines_small; Type: TABLE ATTACH; Schema: maps; Owner: macrostrat
ALTER TABLE ONLY maps.lines ATTACH PARTITION maps.lines_small FOR VALUES IN ('small');

-- Name: lines_tiny; Type: TABLE ATTACH; Schema: maps; Owner: macrostrat
ALTER TABLE ONLY maps.lines ATTACH PARTITION maps.lines_tiny FOR VALUES IN ('tiny');

-- Name: polygons_large; Type: TABLE ATTACH; Schema: maps; Owner: macrostrat
ALTER TABLE ONLY maps.polygons ATTACH PARTITION maps.polygons_large FOR VALUES IN ('large');

-- Name: polygons_medium; Type: TABLE ATTACH; Schema: maps; Owner: macrostrat
ALTER TABLE ONLY maps.polygons ATTACH PARTITION maps.polygons_medium FOR VALUES IN ('medium');

-- Name: polygons_small; Type: TABLE ATTACH; Schema: maps; Owner: macrostrat
ALTER TABLE ONLY maps.polygons ATTACH PARTITION maps.polygons_small FOR VALUES IN ('small');

-- Name: polygons_tiny; Type: TABLE ATTACH; Schema: maps; Owner: macrostrat
ALTER TABLE ONLY maps.polygons ATTACH PARTITION maps.polygons_tiny FOR VALUES IN ('tiny');

-- Name: users id; Type: DEFAULT; Schema: auth; Owner: macrostrat
ALTER TABLE ONLY auth.users ALTER COLUMN id SET DEFAULT nextval('auth.users_id_seq'::regclass);

-- Name: located_query_bounds id; Type: DEFAULT; Schema: detrital_zircon; Owner: macrostrat
ALTER TABLE ONLY detrital_zircon.located_query_bounds ALTER COLUMN id SET DEFAULT nextval('detrital_zircon.located_query_bounds_id_seq'::regclass);

-- Name: boundaries boundary_id; Type: DEFAULT; Schema: geologic_boundaries; Owner: macrostrat
ALTER TABLE ONLY geologic_boundaries.boundaries ALTER COLUMN boundary_id SET DEFAULT nextval('geologic_boundaries.boundaries_boundary_id_seq'::regclass);

-- Name: r10 hex_id; Type: DEFAULT; Schema: hexgrids; Owner: macrostrat
ALTER TABLE ONLY hexgrids.r10 ALTER COLUMN hex_id SET DEFAULT nextval('hexgrids.r10_ogc_fid_seq'::regclass);

-- Name: r11 hex_id; Type: DEFAULT; Schema: hexgrids; Owner: macrostrat
ALTER TABLE ONLY hexgrids.r11 ALTER COLUMN hex_id SET DEFAULT nextval('hexgrids.r11_ogc_fid_seq'::regclass);

-- Name: r12 hex_id; Type: DEFAULT; Schema: hexgrids; Owner: macrostrat
ALTER TABLE ONLY hexgrids.r12 ALTER COLUMN hex_id SET DEFAULT nextval('hexgrids.r12_ogc_fid_seq'::regclass);

-- Name: r5 hex_id; Type: DEFAULT; Schema: hexgrids; Owner: macrostrat
ALTER TABLE ONLY hexgrids.r5 ALTER COLUMN hex_id SET DEFAULT nextval('hexgrids.r5_ogc_fid_seq'::regclass);

-- Name: r6 hex_id; Type: DEFAULT; Schema: hexgrids; Owner: macrostrat
ALTER TABLE ONLY hexgrids.r6 ALTER COLUMN hex_id SET DEFAULT nextval('hexgrids.r6_ogc_fid_seq'::regclass);

-- Name: r7 hex_id; Type: DEFAULT; Schema: hexgrids; Owner: macrostrat
ALTER TABLE ONLY hexgrids.r7 ALTER COLUMN hex_id SET DEFAULT nextval('hexgrids.r7_ogc_fid_seq'::regclass);

-- Name: r8 hex_id; Type: DEFAULT; Schema: hexgrids; Owner: macrostrat
ALTER TABLE ONLY hexgrids.r8 ALTER COLUMN hex_id SET DEFAULT nextval('hexgrids.r8_ogc_fid_seq'::regclass);

-- Name: r9 hex_id; Type: DEFAULT; Schema: hexgrids; Owner: macrostrat
ALTER TABLE ONLY hexgrids.r9 ALTER COLUMN hex_id SET DEFAULT nextval('hexgrids.r9_ogc_fid_seq'::regclass);

-- Name: ingest_process id; Type: DEFAULT; Schema: macrostrat; Owner: macrostrat
ALTER TABLE ONLY macrostrat.ingest_process ALTER COLUMN id SET DEFAULT nextval('macrostrat.ingest_process_id_seq'::regclass);

-- Name: intervals id; Type: DEFAULT; Schema: macrostrat; Owner: macrostrat
ALTER TABLE ONLY macrostrat.intervals ALTER COLUMN id SET DEFAULT nextval('macrostrat.intervals_new_id_seq1'::regclass);

-- Name: measurements id; Type: DEFAULT; Schema: macrostrat; Owner: macrostrat
ALTER TABLE ONLY macrostrat.measurements ALTER COLUMN id SET DEFAULT nextval('macrostrat.measurements_new_id_seq'::regclass);

-- Name: measuremeta id; Type: DEFAULT; Schema: macrostrat; Owner: macrostrat
ALTER TABLE ONLY macrostrat.measuremeta ALTER COLUMN id SET DEFAULT nextval('macrostrat.measuremeta_new_id_seq1'::regclass);

-- Name: measures id; Type: DEFAULT; Schema: macrostrat; Owner: macrostrat
ALTER TABLE ONLY macrostrat.measures ALTER COLUMN id SET DEFAULT nextval('macrostrat.measures_new_id_seq1'::regclass);

-- Name: objects id; Type: DEFAULT; Schema: macrostrat; Owner: macrostrat
ALTER TABLE ONLY macrostrat.objects ALTER COLUMN id SET DEFAULT nextval('macrostrat.objects_id_seq'::regclass);

-- Name: projects id; Type: DEFAULT; Schema: macrostrat; Owner: macrostrat
ALTER TABLE ONLY macrostrat.projects ALTER COLUMN id SET DEFAULT nextval('macrostrat.projects_new_id_seq'::regclass);

-- Name: sections id; Type: DEFAULT; Schema: macrostrat; Owner: macrostrat
ALTER TABLE ONLY macrostrat.sections ALTER COLUMN id SET DEFAULT nextval('macrostrat.sections_new_id_seq1'::regclass);

-- Name: strat_names id; Type: DEFAULT; Schema: macrostrat; Owner: macrostrat
ALTER TABLE ONLY macrostrat.strat_names ALTER COLUMN id SET DEFAULT nextval('macrostrat.strat_names_new_id_seq'::regclass);

-- Name: strat_tree id; Type: DEFAULT; Schema: macrostrat; Owner: macrostrat
ALTER TABLE ONLY macrostrat.strat_tree ALTER COLUMN id SET DEFAULT nextval('macrostrat.strat_tree_new_id_seq1'::regclass);

-- Name: unit_boundaries id; Type: DEFAULT; Schema: macrostrat; Owner: macrostrat
ALTER TABLE ONLY macrostrat.unit_boundaries ALTER COLUMN id SET DEFAULT nextval('macrostrat.unit_boundaries_id_seq'::regclass);

-- Name: unit_measures id; Type: DEFAULT; Schema: macrostrat; Owner: macrostrat
ALTER TABLE ONLY macrostrat.unit_measures ALTER COLUMN id SET DEFAULT nextval('macrostrat.unit_measures_new_id_seq'::regclass);

-- Name: unit_strat_names id; Type: DEFAULT; Schema: macrostrat; Owner: macrostrat
ALTER TABLE ONLY macrostrat.unit_strat_names ALTER COLUMN id SET DEFAULT nextval('macrostrat.unit_strat_names_new_id_seq1'::regclass);

-- Name: units_sections id; Type: DEFAULT; Schema: macrostrat; Owner: macrostrat
ALTER TABLE ONLY macrostrat.units_sections ALTER COLUMN id SET DEFAULT nextval('macrostrat.units_sections_new_id_seq'::regclass);

-- Name: group id; Type: DEFAULT; Schema: macrostrat_auth; Owner: macrostrat
ALTER TABLE ONLY macrostrat_auth."group" ALTER COLUMN id SET DEFAULT nextval('macrostrat_auth.group_id_seq'::regclass);

-- Name: group_members id; Type: DEFAULT; Schema: macrostrat_auth; Owner: macrostrat
ALTER TABLE ONLY macrostrat_auth.group_members ALTER COLUMN id SET DEFAULT nextval('macrostrat_auth.group_members_id_seq'::regclass);

-- Name: token id; Type: DEFAULT; Schema: macrostrat_auth; Owner: macrostrat
ALTER TABLE ONLY macrostrat_auth.token ALTER COLUMN id SET DEFAULT nextval('macrostrat_auth.token_id_seq'::regclass);

-- Name: user id; Type: DEFAULT; Schema: macrostrat_auth; Owner: macrostrat
ALTER TABLE ONLY macrostrat_auth."user" ALTER COLUMN id SET DEFAULT nextval('macrostrat_auth.user_id_seq'::regclass);

-- Name: legend legend_id; Type: DEFAULT; Schema: maps; Owner: macrostrat
ALTER TABLE ONLY maps.legend ALTER COLUMN legend_id SET DEFAULT nextval('maps.legend_legend_id_seq'::regclass);

-- Name: manual_matches match_id; Type: DEFAULT; Schema: maps; Owner: macrostrat
ALTER TABLE ONLY maps.manual_matches ALTER COLUMN match_id SET DEFAULT nextval('maps.manual_matches_match_id_seq'::regclass);

-- Name: points point_id; Type: DEFAULT; Schema: maps; Owner: macrostrat
ALTER TABLE ONLY maps.points ALTER COLUMN point_id SET DEFAULT nextval('maps.points_point_id_seq'::regclass);

-- Name: source_operations id; Type: DEFAULT; Schema: maps; Owner: macrostrat
ALTER TABLE ONLY maps.source_operations ALTER COLUMN id SET DEFAULT nextval('maps.source_operations_id_seq'::regclass);

-- Name: sources source_id; Type: DEFAULT; Schema: maps; Owner: macrostrat
ALTER TABLE ONLY maps.sources ALTER COLUMN source_id SET DEFAULT nextval('maps.sources_source_id_seq'::regclass);

-- Name: impervious rid; Type: DEFAULT; Schema: public; Owner: macrostrat
ALTER TABLE ONLY public.impervious ALTER COLUMN rid SET DEFAULT nextval('public.impervious_rid_seq'::regclass);

-- Name: land gid; Type: DEFAULT; Schema: public; Owner: macrostrat
ALTER TABLE ONLY public.land ALTER COLUMN gid SET DEFAULT nextval('public.land_gid_seq'::regclass);

-- Name: macrostrat_union id; Type: DEFAULT; Schema: public; Owner: macrostrat
ALTER TABLE ONLY public.macrostrat_union ALTER COLUMN id SET DEFAULT nextval('public.macrostrat_union_id_seq'::regclass);

-- Name: users users_pkey; Type: CONSTRAINT; Schema: auth; Owner: macrostrat
ALTER TABLE ONLY auth.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);

-- Name: users users_username_key; Type: CONSTRAINT; Schema: auth; Owner: macrostrat
ALTER TABLE ONLY auth.users
    ADD CONSTRAINT users_username_key UNIQUE (username);

-- Name: polygons polygons_unique; Type: CONSTRAINT; Schema: carto; Owner: macrostrat
ALTER TABLE ONLY carto.polygons
    ADD CONSTRAINT polygons_unique UNIQUE (map_id, scale);

-- Name: polygons_large polygons_large_map_id_scale_key; Type: CONSTRAINT; Schema: carto; Owner: macrostrat
ALTER TABLE ONLY carto.polygons_large
    ADD CONSTRAINT polygons_large_map_id_scale_key UNIQUE (map_id, scale);

-- Name: polygons polygons_pkey; Type: CONSTRAINT; Schema: carto; Owner: macrostrat
ALTER TABLE ONLY carto.polygons
    ADD CONSTRAINT polygons_pkey PRIMARY KEY (map_id, scale);

-- Name: polygons_large polygons_large_pkey; Type: CONSTRAINT; Schema: carto; Owner: macrostrat
ALTER TABLE ONLY carto.polygons_large
    ADD CONSTRAINT polygons_large_pkey PRIMARY KEY (map_id, scale);

-- Name: polygons_medium polygons_medium_map_id_scale_key; Type: CONSTRAINT; Schema: carto; Owner: macrostrat
ALTER TABLE ONLY carto.polygons_medium
    ADD CONSTRAINT polygons_medium_map_id_scale_key UNIQUE (map_id, scale);

-- Name: polygons_medium polygons_medium_pkey; Type: CONSTRAINT; Schema: carto; Owner: macrostrat
ALTER TABLE ONLY carto.polygons_medium
    ADD CONSTRAINT polygons_medium_pkey PRIMARY KEY (map_id, scale);

-- Name: polygons_small polygons_small_map_id_scale_key; Type: CONSTRAINT; Schema: carto; Owner: macrostrat
ALTER TABLE ONLY carto.polygons_small
    ADD CONSTRAINT polygons_small_map_id_scale_key UNIQUE (map_id, scale);

-- Name: polygons_small polygons_small_pkey; Type: CONSTRAINT; Schema: carto; Owner: macrostrat
ALTER TABLE ONLY carto.polygons_small
    ADD CONSTRAINT polygons_small_pkey PRIMARY KEY (map_id, scale);

-- Name: polygons_tiny polygons_tiny_map_id_scale_key; Type: CONSTRAINT; Schema: carto; Owner: macrostrat
ALTER TABLE ONLY carto.polygons_tiny
    ADD CONSTRAINT polygons_tiny_map_id_scale_key UNIQUE (map_id, scale);

-- Name: polygons_tiny polygons_tiny_pkey; Type: CONSTRAINT; Schema: carto; Owner: macrostrat
ALTER TABLE ONLY carto.polygons_tiny
    ADD CONSTRAINT polygons_tiny_pkey PRIMARY KEY (map_id, scale);

-- Name: located_query_bounds located_query_bounds_pkey; Type: CONSTRAINT; Schema: detrital_zircon; Owner: macrostrat
ALTER TABLE ONLY detrital_zircon.located_query_bounds
    ADD CONSTRAINT located_query_bounds_pkey PRIMARY KEY (id);

-- Name: sources sources_pkey; Type: CONSTRAINT; Schema: geologic_boundaries; Owner: macrostrat
ALTER TABLE ONLY geologic_boundaries.sources
    ADD CONSTRAINT sources_pkey PRIMARY KEY (source_id);

-- Name: hexgrids hexgrids_pkey; Type: CONSTRAINT; Schema: hexgrids; Owner: macrostrat
ALTER TABLE ONLY hexgrids.hexgrids
    ADD CONSTRAINT hexgrids_pkey PRIMARY KEY (hex_id);

-- Name: r10 r10_pkey; Type: CONSTRAINT; Schema: hexgrids; Owner: macrostrat
ALTER TABLE ONLY hexgrids.r10
    ADD CONSTRAINT r10_pkey PRIMARY KEY (hex_id);

-- Name: r11 r11_pkey; Type: CONSTRAINT; Schema: hexgrids; Owner: macrostrat
ALTER TABLE ONLY hexgrids.r11
    ADD CONSTRAINT r11_pkey PRIMARY KEY (hex_id);

-- Name: r12 r12_pkey; Type: CONSTRAINT; Schema: hexgrids; Owner: macrostrat
ALTER TABLE ONLY hexgrids.r12
    ADD CONSTRAINT r12_pkey PRIMARY KEY (hex_id);

-- Name: r5 r5_pkey; Type: CONSTRAINT; Schema: hexgrids; Owner: macrostrat
ALTER TABLE ONLY hexgrids.r5
    ADD CONSTRAINT r5_pkey PRIMARY KEY (hex_id);

-- Name: r6 r6_pkey; Type: CONSTRAINT; Schema: hexgrids; Owner: macrostrat
ALTER TABLE ONLY hexgrids.r6
    ADD CONSTRAINT r6_pkey PRIMARY KEY (hex_id);

-- Name: r7 r7_pkey; Type: CONSTRAINT; Schema: hexgrids; Owner: macrostrat
ALTER TABLE ONLY hexgrids.r7
    ADD CONSTRAINT r7_pkey PRIMARY KEY (hex_id);

-- Name: r8 r8_pkey; Type: CONSTRAINT; Schema: hexgrids; Owner: macrostrat
ALTER TABLE ONLY hexgrids.r8
    ADD CONSTRAINT r8_pkey PRIMARY KEY (hex_id);

-- Name: r9 r9_pkey; Type: CONSTRAINT; Schema: hexgrids; Owner: macrostrat
ALTER TABLE ONLY hexgrids.r9
    ADD CONSTRAINT r9_pkey PRIMARY KEY (hex_id);

-- Name: col_areas col_areas_new_pkey; Type: CONSTRAINT; Schema: macrostrat; Owner: macrostrat
ALTER TABLE ONLY macrostrat.col_areas
    ADD CONSTRAINT col_areas_new_pkey PRIMARY KEY (id);

-- Name: col_groups col_groups_new_pkey1; Type: CONSTRAINT; Schema: macrostrat; Owner: macrostrat
ALTER TABLE ONLY macrostrat.col_groups
    ADD CONSTRAINT col_groups_new_pkey1 PRIMARY KEY (id);

-- Name: col_refs col_refs_new_pkey1; Type: CONSTRAINT; Schema: macrostrat; Owner: macrostrat
ALTER TABLE ONLY macrostrat.col_refs
    ADD CONSTRAINT col_refs_new_pkey1 PRIMARY KEY (id);

-- Name: cols cols_new_pkey; Type: CONSTRAINT; Schema: macrostrat; Owner: macrostrat
ALTER TABLE ONLY macrostrat.cols
    ADD CONSTRAINT cols_new_pkey PRIMARY KEY (id);

-- Name: econs econs_new_pkey; Type: CONSTRAINT; Schema: macrostrat; Owner: macrostrat
ALTER TABLE ONLY macrostrat.econs
    ADD CONSTRAINT econs_new_pkey PRIMARY KEY (id);

-- Name: environs environs_new_pkey1; Type: CONSTRAINT; Schema: macrostrat; Owner: macrostrat
ALTER TABLE ONLY macrostrat.environs
    ADD CONSTRAINT environs_new_pkey1 PRIMARY KEY (id);

-- Name: grainsize grainsize_pkey; Type: CONSTRAINT; Schema: macrostrat; Owner: macrostrat
ALTER TABLE ONLY macrostrat.grainsize
    ADD CONSTRAINT grainsize_pkey PRIMARY KEY (grain_id);

-- Name: ingest_process ingest_process_pkey; Type: CONSTRAINT; Schema: macrostrat; Owner: macrostrat
ALTER TABLE ONLY macrostrat.ingest_process
    ADD CONSTRAINT ingest_process_pkey PRIMARY KEY (id);

-- Name: lith_atts lith_atts_new_pkey1; Type: CONSTRAINT; Schema: macrostrat; Owner: macrostrat
ALTER TABLE ONLY macrostrat.lith_atts
    ADD CONSTRAINT lith_atts_new_pkey1 PRIMARY KEY (id);

-- Name: liths liths_new_pkey1; Type: CONSTRAINT; Schema: macrostrat; Owner: macrostrat
ALTER TABLE ONLY macrostrat.liths
    ADD CONSTRAINT liths_new_pkey1 PRIMARY KEY (id);

-- Name: lookup_units lookup_units_new_pkey1; Type: CONSTRAINT; Schema: macrostrat; Owner: macrostrat
ALTER TABLE ONLY macrostrat.lookup_units
    ADD CONSTRAINT lookup_units_new_pkey1 PRIMARY KEY (unit_id);

-- Name: measurements measurements_new_pkey; Type: CONSTRAINT; Schema: macrostrat; Owner: macrostrat
ALTER TABLE ONLY macrostrat.measurements
    ADD CONSTRAINT measurements_new_pkey PRIMARY KEY (id);

-- Name: measuremeta measuremeta_new_pkey; Type: CONSTRAINT; Schema: macrostrat; Owner: macrostrat
ALTER TABLE ONLY macrostrat.measuremeta
    ADD CONSTRAINT measuremeta_new_pkey PRIMARY KEY (id);

-- Name: objects objects_pkey; Type: CONSTRAINT; Schema: macrostrat; Owner: macrostrat
ALTER TABLE ONLY macrostrat.objects
    ADD CONSTRAINT objects_pkey PRIMARY KEY (id);

-- Name: places places_new_pkey; Type: CONSTRAINT; Schema: macrostrat; Owner: macrostrat
ALTER TABLE ONLY macrostrat.places
    ADD CONSTRAINT places_new_pkey PRIMARY KEY (place_id);

-- Name: projects projects_new_pkey; Type: CONSTRAINT; Schema: macrostrat; Owner: macrostrat
ALTER TABLE ONLY macrostrat.projects
    ADD CONSTRAINT projects_new_pkey PRIMARY KEY (id);

-- Name: refs refs_new_pkey1; Type: CONSTRAINT; Schema: macrostrat; Owner: macrostrat
ALTER TABLE ONLY macrostrat.refs
    ADD CONSTRAINT refs_new_pkey1 PRIMARY KEY (id);

-- Name: sections sections_new_pkey1; Type: CONSTRAINT; Schema: macrostrat; Owner: macrostrat
ALTER TABLE ONLY macrostrat.sections
    ADD CONSTRAINT sections_new_pkey1 PRIMARY KEY (id);

-- Name: strat_names_meta strat_names_meta_new_pkey1; Type: CONSTRAINT; Schema: macrostrat; Owner: macrostrat
ALTER TABLE ONLY macrostrat.strat_names_meta
    ADD CONSTRAINT strat_names_meta_new_pkey1 PRIMARY KEY (concept_id);

-- Name: strat_names strat_names_new_pkey; Type: CONSTRAINT; Schema: macrostrat; Owner: macrostrat
ALTER TABLE ONLY macrostrat.strat_names
    ADD CONSTRAINT strat_names_new_pkey PRIMARY KEY (id);

-- Name: strat_tree strat_tree_new_pkey1; Type: CONSTRAINT; Schema: macrostrat; Owner: macrostrat
ALTER TABLE ONLY macrostrat.strat_tree
    ADD CONSTRAINT strat_tree_new_pkey1 PRIMARY KEY (id);

-- Name: timescales timescales_new_pkey1; Type: CONSTRAINT; Schema: macrostrat; Owner: macrostrat
ALTER TABLE ONLY macrostrat.timescales
    ADD CONSTRAINT timescales_new_pkey1 PRIMARY KEY (id);

-- Name: objects unique_file; Type: CONSTRAINT; Schema: macrostrat; Owner: macrostrat
ALTER TABLE ONLY macrostrat.objects
    ADD CONSTRAINT unique_file UNIQUE (scheme, host, bucket, key);

-- Name: unit_boundaries unit_boundaries_pkey; Type: CONSTRAINT; Schema: macrostrat; Owner: macrostrat
ALTER TABLE ONLY macrostrat.unit_boundaries
    ADD CONSTRAINT unit_boundaries_pkey PRIMARY KEY (id);

-- Name: unit_econs unit_econs_new_pkey1; Type: CONSTRAINT; Schema: macrostrat; Owner: macrostrat
ALTER TABLE ONLY macrostrat.unit_econs
    ADD CONSTRAINT unit_econs_new_pkey1 PRIMARY KEY (id);

-- Name: unit_environs unit_environs_new_pkey1; Type: CONSTRAINT; Schema: macrostrat; Owner: macrostrat
ALTER TABLE ONLY macrostrat.unit_environs
    ADD CONSTRAINT unit_environs_new_pkey1 PRIMARY KEY (id);

-- Name: unit_lith_atts unit_lith_atts_new_pkey1; Type: CONSTRAINT; Schema: macrostrat; Owner: macrostrat
ALTER TABLE ONLY macrostrat.unit_lith_atts
    ADD CONSTRAINT unit_lith_atts_new_pkey1 PRIMARY KEY (id);

-- Name: unit_liths unit_liths_new_pkey1; Type: CONSTRAINT; Schema: macrostrat; Owner: macrostrat
ALTER TABLE ONLY macrostrat.unit_liths
    ADD CONSTRAINT unit_liths_new_pkey1 PRIMARY KEY (id);

-- Name: unit_measures unit_measures_new_pkey; Type: CONSTRAINT; Schema: macrostrat; Owner: macrostrat
ALTER TABLE ONLY macrostrat.unit_measures
    ADD CONSTRAINT unit_measures_new_pkey PRIMARY KEY (id);

-- Name: unit_strat_names unit_strat_names_new_pkey1; Type: CONSTRAINT; Schema: macrostrat; Owner: macrostrat
ALTER TABLE ONLY macrostrat.unit_strat_names
    ADD CONSTRAINT unit_strat_names_new_pkey1 PRIMARY KEY (id);

-- Name: units units_new_pkey; Type: CONSTRAINT; Schema: macrostrat; Owner: macrostrat
ALTER TABLE ONLY macrostrat.units
    ADD CONSTRAINT units_new_pkey PRIMARY KEY (id);

-- Name: units_sections units_sections_new_pkey; Type: CONSTRAINT; Schema: macrostrat; Owner: macrostrat
ALTER TABLE ONLY macrostrat.units_sections
    ADD CONSTRAINT units_sections_new_pkey PRIMARY KEY (id);

-- Name: group_members group_members_pkey; Type: CONSTRAINT; Schema: macrostrat_auth; Owner: macrostrat
ALTER TABLE ONLY macrostrat_auth.group_members
    ADD CONSTRAINT group_members_pkey PRIMARY KEY (id);

-- Name: group group_pkey; Type: CONSTRAINT; Schema: macrostrat_auth; Owner: macrostrat
ALTER TABLE ONLY macrostrat_auth."group"
    ADD CONSTRAINT group_pkey PRIMARY KEY (id);

-- Name: token token_pkey; Type: CONSTRAINT; Schema: macrostrat_auth; Owner: macrostrat
ALTER TABLE ONLY macrostrat_auth.token
    ADD CONSTRAINT token_pkey PRIMARY KEY (id);

-- Name: token token_token_key; Type: CONSTRAINT; Schema: macrostrat_auth; Owner: macrostrat
ALTER TABLE ONLY macrostrat_auth.token
    ADD CONSTRAINT token_token_key UNIQUE (token);

-- Name: user user_pkey; Type: CONSTRAINT; Schema: macrostrat_auth; Owner: macrostrat
ALTER TABLE ONLY macrostrat_auth."user"
    ADD CONSTRAINT user_pkey PRIMARY KEY (id);

-- Name: legend_liths legend_liths_legend_id_lith_id_basis_col_key; Type: CONSTRAINT; Schema: maps; Owner: macrostrat
ALTER TABLE ONLY maps.legend_liths
    ADD CONSTRAINT legend_liths_legend_id_lith_id_basis_col_key UNIQUE (legend_id, lith_id, basis_col);

-- Name: legend legend_pkey; Type: CONSTRAINT; Schema: maps; Owner: macrostrat
ALTER TABLE ONLY maps.legend
    ADD CONSTRAINT legend_pkey PRIMARY KEY (legend_id);

-- Name: lines lines_pkey; Type: CONSTRAINT; Schema: maps; Owner: macrostrat
ALTER TABLE ONLY maps.lines
    ADD CONSTRAINT lines_pkey PRIMARY KEY (line_id, scale);

-- Name: lines_large lines_large_pkey; Type: CONSTRAINT; Schema: maps; Owner: macrostrat
ALTER TABLE ONLY maps.lines_large
    ADD CONSTRAINT lines_large_pkey PRIMARY KEY (line_id, scale);

-- Name: lines_medium lines_medium_pkey; Type: CONSTRAINT; Schema: maps; Owner: macrostrat
ALTER TABLE ONLY maps.lines_medium
    ADD CONSTRAINT lines_medium_pkey PRIMARY KEY (line_id, scale);

-- Name: lines_small lines_small_pkey; Type: CONSTRAINT; Schema: maps; Owner: macrostrat
ALTER TABLE ONLY maps.lines_small
    ADD CONSTRAINT lines_small_pkey PRIMARY KEY (line_id, scale);

-- Name: lines_tiny lines_tiny_pkey; Type: CONSTRAINT; Schema: maps; Owner: macrostrat
ALTER TABLE ONLY maps.lines_tiny
    ADD CONSTRAINT lines_tiny_pkey PRIMARY KEY (line_id, scale);

-- Name: map_legend map_legend_legend_id_map_id_key; Type: CONSTRAINT; Schema: maps; Owner: macrostrat
ALTER TABLE ONLY maps.map_legend
    ADD CONSTRAINT map_legend_legend_id_map_id_key UNIQUE (legend_id, map_id);

-- Name: sources map_sources_name_key; Type: CONSTRAINT; Schema: maps; Owner: macrostrat
ALTER TABLE ONLY maps.sources
    ADD CONSTRAINT map_sources_name_key UNIQUE (primary_table);

-- Name: polygons maps_polygons_pkey; Type: CONSTRAINT; Schema: maps; Owner: macrostrat
ALTER TABLE ONLY maps.polygons
    ADD CONSTRAINT maps_polygons_pkey PRIMARY KEY (map_id, scale);

-- Name: polygons_large maps_polygons_large_pkey; Type: CONSTRAINT; Schema: maps; Owner: macrostrat
ALTER TABLE ONLY maps.polygons_large
    ADD CONSTRAINT maps_polygons_large_pkey PRIMARY KEY (map_id, scale);

-- Name: polygons_medium maps_polygons_medium_pkey; Type: CONSTRAINT; Schema: maps; Owner: macrostrat
ALTER TABLE ONLY maps.polygons_medium
    ADD CONSTRAINT maps_polygons_medium_pkey PRIMARY KEY (map_id, scale);

-- Name: polygons_small maps_polygons_small_pkey; Type: CONSTRAINT; Schema: maps; Owner: macrostrat
ALTER TABLE ONLY maps.polygons_small
    ADD CONSTRAINT maps_polygons_small_pkey PRIMARY KEY (map_id, scale);

-- Name: polygons_tiny maps_polygons_tiny_pkey; Type: CONSTRAINT; Schema: maps; Owner: macrostrat
ALTER TABLE ONLY maps.polygons_tiny
    ADD CONSTRAINT maps_polygons_tiny_pkey PRIMARY KEY (map_id, scale);

-- Name: source_operations source_operations_pkey; Type: CONSTRAINT; Schema: maps; Owner: macrostrat
ALTER TABLE ONLY maps.source_operations
    ADD CONSTRAINT source_operations_pkey PRIMARY KEY (id);

-- Name: sources sources_pkey; Type: CONSTRAINT; Schema: maps; Owner: macrostrat
ALTER TABLE ONLY maps.sources
    ADD CONSTRAINT sources_pkey PRIMARY KEY (source_id);

-- Name: sources sources_slug_key; Type: CONSTRAINT; Schema: maps; Owner: macrostrat
ALTER TABLE ONLY maps.sources
    ADD CONSTRAINT sources_slug_key UNIQUE (slug);

-- Name: sources sources_slug_key1; Type: CONSTRAINT; Schema: maps; Owner: macrostrat
ALTER TABLE ONLY maps.sources
    ADD CONSTRAINT sources_slug_key1 UNIQUE (slug);

-- Name: sources sources_slug_key2; Type: CONSTRAINT; Schema: maps; Owner: macrostrat
ALTER TABLE ONLY maps.sources
    ADD CONSTRAINT sources_slug_key2 UNIQUE (slug);

-- Name: sources sources_slug_key3; Type: CONSTRAINT; Schema: maps; Owner: macrostrat
ALTER TABLE ONLY maps.sources
    ADD CONSTRAINT sources_slug_key3 UNIQUE (slug);

-- Name: sources sources_source_id_key; Type: CONSTRAINT; Schema: maps; Owner: macrostrat
ALTER TABLE ONLY maps.sources
    ADD CONSTRAINT sources_source_id_key UNIQUE (source_id);

-- Name: impervious impervious_pkey; Type: CONSTRAINT; Schema: public; Owner: macrostrat
ALTER TABLE ONLY public.impervious
    ADD CONSTRAINT impervious_pkey PRIMARY KEY (rid);

-- Name: land land_pkey; Type: CONSTRAINT; Schema: public; Owner: macrostrat
ALTER TABLE ONLY public.land
    ADD CONSTRAINT land_pkey PRIMARY KEY (gid);

-- Name: macrostrat_union macrostrat_union_pkey; Type: CONSTRAINT; Schema: public; Owner: macrostrat
ALTER TABLE ONLY public.macrostrat_union
    ADD CONSTRAINT macrostrat_union_pkey PRIMARY KEY (id);

-- Name: profile profile_pkey; Type: CONSTRAINT; Schema: tile_cache; Owner: macrostrat
ALTER TABLE ONLY tile_cache.profile
    ADD CONSTRAINT profile_pkey PRIMARY KEY (name);

-- Name: tile tile_pkey; Type: CONSTRAINT; Schema: tile_cache; Owner: macrostrat
ALTER TABLE ONLY tile_cache.tile
    ADD CONSTRAINT tile_pkey PRIMARY KEY (x, y, z, layers);

-- Name: tms_definition tms_definition_pkey; Type: CONSTRAINT; Schema: tile_utils; Owner: macrostrat
ALTER TABLE ONLY tile_utils.tms_definition
    ADD CONSTRAINT tms_definition_pkey PRIMARY KEY (name);

-- Name: carto_polygons_geom_gist; Type: INDEX; Schema: carto; Owner: macrostrat
CREATE INDEX carto_polygons_geom_gist ON ONLY carto.polygons USING gist (geom);

-- Name: large_geom_idx; Type: INDEX; Schema: carto; Owner: macrostrat
CREATE INDEX large_geom_idx ON carto.polygons_large USING gist (geom);

-- Name: large_map_id_idx; Type: INDEX; Schema: carto; Owner: macrostrat
CREATE INDEX large_map_id_idx ON carto.polygons_large USING btree (map_id);

-- Name: lines_large_geom_idx; Type: INDEX; Schema: carto; Owner: macrostrat
CREATE INDEX lines_large_geom_idx ON carto.lines_large USING gist (geom);

-- Name: lines_large_line_id_idx; Type: INDEX; Schema: carto; Owner: macrostrat
CREATE INDEX lines_large_line_id_idx ON carto.lines_large USING btree (line_id);

-- Name: lines_medium_geom_idx; Type: INDEX; Schema: carto; Owner: macrostrat
CREATE INDEX lines_medium_geom_idx ON carto.lines_medium USING gist (geom);

-- Name: lines_medium_line_id_idx; Type: INDEX; Schema: carto; Owner: macrostrat
CREATE INDEX lines_medium_line_id_idx ON carto.lines_medium USING btree (line_id);

-- Name: lines_small_geom_idx; Type: INDEX; Schema: carto; Owner: macrostrat
CREATE INDEX lines_small_geom_idx ON carto.lines_small USING gist (geom);

-- Name: lines_small_line_id_idx; Type: INDEX; Schema: carto; Owner: macrostrat
CREATE INDEX lines_small_line_id_idx ON carto.lines_small USING btree (line_id);

-- Name: lines_tiny_geom_idx; Type: INDEX; Schema: carto; Owner: macrostrat
CREATE INDEX lines_tiny_geom_idx ON carto.lines_tiny USING gist (geom);

-- Name: lines_tiny_line_id_idx; Type: INDEX; Schema: carto; Owner: macrostrat
CREATE INDEX lines_tiny_line_id_idx ON carto.lines_tiny USING btree (line_id);

-- Name: medium_geom_idx; Type: INDEX; Schema: carto; Owner: macrostrat
CREATE INDEX medium_geom_idx ON carto.polygons_medium USING gist (geom);

-- Name: medium_map_id_idx; Type: INDEX; Schema: carto; Owner: macrostrat
CREATE INDEX medium_map_id_idx ON carto.polygons_medium USING btree (map_id);

-- Name: small_geom_idx; Type: INDEX; Schema: carto; Owner: macrostrat
CREATE INDEX small_geom_idx ON carto.polygons_small USING gist (geom);

-- Name: small_map_id_idx; Type: INDEX; Schema: carto; Owner: macrostrat
CREATE INDEX small_map_id_idx ON carto.polygons_small USING btree (map_id);

-- Name: tiny_geom_idx; Type: INDEX; Schema: carto; Owner: macrostrat
CREATE INDEX tiny_geom_idx ON carto.polygons_tiny USING gist (geom);

-- Name: tiny_map_id_idx; Type: INDEX; Schema: carto; Owner: macrostrat
CREATE INDEX tiny_map_id_idx ON carto.polygons_tiny USING btree (map_id);

-- Name: hex_index_hex_id_idx; Type: INDEX; Schema: carto_new; Owner: macrostrat
CREATE INDEX hex_index_hex_id_idx ON carto_new.hex_index USING btree (hex_id);

-- Name: hex_index_map_id_idx; Type: INDEX; Schema: carto_new; Owner: macrostrat
CREATE INDEX hex_index_map_id_idx ON carto_new.hex_index USING btree (map_id);

-- Name: hex_index_scale_idx; Type: INDEX; Schema: carto_new; Owner: macrostrat
CREATE INDEX hex_index_scale_idx ON carto_new.hex_index USING btree (scale);

-- Name: pbdb_hex_index_collection_no_idx; Type: INDEX; Schema: carto_new; Owner: macrostrat
CREATE INDEX pbdb_hex_index_collection_no_idx ON carto_new.pbdb_hex_index USING btree (collection_no);

-- Name: pbdb_hex_index_hex_id_idx; Type: INDEX; Schema: carto_new; Owner: macrostrat
CREATE INDEX pbdb_hex_index_hex_id_idx ON carto_new.pbdb_hex_index USING btree (hex_id);

-- Name: pbdb_hex_index_scale_idx; Type: INDEX; Schema: carto_new; Owner: macrostrat
CREATE INDEX pbdb_hex_index_scale_idx ON carto_new.pbdb_hex_index USING btree (scale);

-- Name: carto_plate_index_geom_idx; Type: INDEX; Schema: corelle_macrostrat; Owner: macrostrat
CREATE INDEX carto_plate_index_geom_idx ON corelle_macrostrat.carto_plate_index USING gist (geom);

-- Name: carto_plate_index_model_plate_scale_idx; Type: INDEX; Schema: corelle_macrostrat; Owner: macrostrat
CREATE INDEX carto_plate_index_model_plate_scale_idx ON corelle_macrostrat.carto_plate_index USING btree (model_id, plate_id, scale);

-- Name: boundaries_boundary_class_idx; Type: INDEX; Schema: geologic_boundaries; Owner: macrostrat
CREATE INDEX boundaries_boundary_class_idx ON geologic_boundaries.boundaries USING btree (boundary_class);

-- Name: boundaries_boundary_id_idx; Type: INDEX; Schema: geologic_boundaries; Owner: macrostrat
CREATE INDEX boundaries_boundary_id_idx ON geologic_boundaries.boundaries USING btree (boundary_id);

-- Name: boundaries_geom_idx; Type: INDEX; Schema: geologic_boundaries; Owner: macrostrat
CREATE INDEX boundaries_geom_idx ON geologic_boundaries.boundaries USING gist (geom);

-- Name: boundaries_orig_id_idx; Type: INDEX; Schema: geologic_boundaries; Owner: macrostrat
CREATE INDEX boundaries_orig_id_idx ON geologic_boundaries.boundaries USING btree (orig_id);

-- Name: boundaries_source_id_idx; Type: INDEX; Schema: geologic_boundaries; Owner: macrostrat
CREATE INDEX boundaries_source_id_idx ON geologic_boundaries.boundaries USING btree (source_id);

-- Name: bedrock_index_hex_id_idx; Type: INDEX; Schema: hexgrids; Owner: macrostrat
CREATE INDEX bedrock_index_hex_id_idx ON hexgrids.bedrock_index USING btree (hex_id);

-- Name: bedrock_index_legend_id_hex_id_idx; Type: INDEX; Schema: hexgrids; Owner: macrostrat
CREATE UNIQUE INDEX bedrock_index_legend_id_hex_id_idx ON hexgrids.bedrock_index USING btree (legend_id, hex_id);

-- Name: bedrock_index_legend_id_idx; Type: INDEX; Schema: hexgrids; Owner: macrostrat
CREATE INDEX bedrock_index_legend_id_idx ON hexgrids.bedrock_index USING btree (legend_id);

-- Name: hexgrids_geom_idx; Type: INDEX; Schema: hexgrids; Owner: macrostrat
CREATE INDEX hexgrids_geom_idx ON hexgrids.hexgrids USING gist (geom);

-- Name: hexgrids_res_idx; Type: INDEX; Schema: hexgrids; Owner: macrostrat
CREATE INDEX hexgrids_res_idx ON hexgrids.hexgrids USING btree (res);

-- Name: pbdb_index_collection_no_hex_id_idx; Type: INDEX; Schema: hexgrids; Owner: macrostrat
CREATE UNIQUE INDEX pbdb_index_collection_no_hex_id_idx ON hexgrids.pbdb_index USING btree (collection_no, hex_id);

-- Name: pbdb_index_collection_no_idx; Type: INDEX; Schema: hexgrids; Owner: macrostrat
CREATE INDEX pbdb_index_collection_no_idx ON hexgrids.pbdb_index USING btree (collection_no);

-- Name: pbdb_index_hex_id_idx; Type: INDEX; Schema: hexgrids; Owner: macrostrat
CREATE INDEX pbdb_index_hex_id_idx ON hexgrids.pbdb_index USING btree (hex_id);

-- Name: r10_geom_geom_idx; Type: INDEX; Schema: hexgrids; Owner: macrostrat
CREATE INDEX r10_geom_geom_idx ON hexgrids.r10 USING gist (geom);

-- Name: r10_geom_idx; Type: INDEX; Schema: hexgrids; Owner: macrostrat
CREATE INDEX r10_geom_idx ON hexgrids.r10 USING gist (geom);

-- Name: r10_web_geom_idx; Type: INDEX; Schema: hexgrids; Owner: macrostrat
CREATE INDEX r10_web_geom_idx ON hexgrids.r10 USING gist (web_geom);

-- Name: r11_geom_geom_idx; Type: INDEX; Schema: hexgrids; Owner: macrostrat
CREATE INDEX r11_geom_geom_idx ON hexgrids.r11 USING gist (geom);

-- Name: r11_web_geom_idx; Type: INDEX; Schema: hexgrids; Owner: macrostrat
CREATE INDEX r11_web_geom_idx ON hexgrids.r11 USING gist (web_geom);

-- Name: r12_geom_geom_idx; Type: INDEX; Schema: hexgrids; Owner: macrostrat
CREATE INDEX r12_geom_geom_idx ON hexgrids.r12 USING gist (geom);

-- Name: r12_web_geom_idx; Type: INDEX; Schema: hexgrids; Owner: macrostrat
CREATE INDEX r12_web_geom_idx ON hexgrids.r12 USING gist (web_geom);

-- Name: r5_geom_idx; Type: INDEX; Schema: hexgrids; Owner: macrostrat
CREATE INDEX r5_geom_idx ON hexgrids.r5 USING gist (geom);

-- Name: r5_web_geom_idx; Type: INDEX; Schema: hexgrids; Owner: macrostrat
CREATE INDEX r5_web_geom_idx ON hexgrids.r5 USING gist (web_geom);

-- Name: r6_geom_idx; Type: INDEX; Schema: hexgrids; Owner: macrostrat
CREATE INDEX r6_geom_idx ON hexgrids.r6 USING gist (geom);

-- Name: r6_web_geom_idx; Type: INDEX; Schema: hexgrids; Owner: macrostrat
CREATE INDEX r6_web_geom_idx ON hexgrids.r6 USING gist (web_geom);

-- Name: r7_geom_idx; Type: INDEX; Schema: hexgrids; Owner: macrostrat
CREATE INDEX r7_geom_idx ON hexgrids.r7 USING gist (geom);

-- Name: r7_geom_idx1; Type: INDEX; Schema: hexgrids; Owner: macrostrat
CREATE INDEX r7_geom_idx1 ON hexgrids.r7 USING gist (geom);

-- Name: r7_geom_idx2; Type: INDEX; Schema: hexgrids; Owner: macrostrat
CREATE INDEX r7_geom_idx2 ON hexgrids.r7 USING gist (geom);

-- Name: r7_web_geom_idx; Type: INDEX; Schema: hexgrids; Owner: macrostrat
CREATE INDEX r7_web_geom_idx ON hexgrids.r7 USING gist (web_geom);

-- Name: r8_geom_idx; Type: INDEX; Schema: hexgrids; Owner: macrostrat
CREATE INDEX r8_geom_idx ON hexgrids.r8 USING gist (geom);

-- Name: r8_geom_idx1; Type: INDEX; Schema: hexgrids; Owner: macrostrat
CREATE INDEX r8_geom_idx1 ON hexgrids.r8 USING gist (geom);

-- Name: r8_geom_idx2; Type: INDEX; Schema: hexgrids; Owner: macrostrat
CREATE INDEX r8_geom_idx2 ON hexgrids.r8 USING gist (geom);

-- Name: r8_web_geom_idx; Type: INDEX; Schema: hexgrids; Owner: macrostrat
CREATE INDEX r8_web_geom_idx ON hexgrids.r8 USING gist (web_geom);

-- Name: r9_geom_idx; Type: INDEX; Schema: hexgrids; Owner: macrostrat
CREATE INDEX r9_geom_idx ON hexgrids.r9 USING gist (geom);

-- Name: r9_geom_idx1; Type: INDEX; Schema: hexgrids; Owner: macrostrat
CREATE INDEX r9_geom_idx1 ON hexgrids.r9 USING gist (geom);

-- Name: r9_web_geom_idx; Type: INDEX; Schema: hexgrids; Owner: macrostrat
CREATE INDEX r9_web_geom_idx ON hexgrids.r9 USING gist (web_geom);

-- Name: autocomplete_new_category_idx1; Type: INDEX; Schema: macrostrat; Owner: macrostrat
CREATE INDEX autocomplete_new_category_idx1 ON macrostrat.autocomplete USING btree (category);

-- Name: autocomplete_new_id_idx1; Type: INDEX; Schema: macrostrat; Owner: macrostrat
CREATE INDEX autocomplete_new_id_idx1 ON macrostrat.autocomplete USING btree (id);

-- Name: autocomplete_new_name_idx1; Type: INDEX; Schema: macrostrat; Owner: macrostrat
CREATE INDEX autocomplete_new_name_idx1 ON macrostrat.autocomplete USING btree (name);

-- Name: autocomplete_new_type_idx1; Type: INDEX; Schema: macrostrat; Owner: macrostrat
CREATE INDEX autocomplete_new_type_idx1 ON macrostrat.autocomplete USING btree (type);

-- Name: col_areas_new_col_area_idx; Type: INDEX; Schema: macrostrat; Owner: macrostrat
CREATE INDEX col_areas_new_col_area_idx ON macrostrat.col_areas USING gist (col_area);

-- Name: col_areas_new_col_id_idx; Type: INDEX; Schema: macrostrat; Owner: macrostrat
CREATE INDEX col_areas_new_col_id_idx ON macrostrat.col_areas USING btree (col_id);

-- Name: col_groups_new_id_idx1; Type: INDEX; Schema: macrostrat; Owner: macrostrat
CREATE INDEX col_groups_new_id_idx1 ON macrostrat.col_groups USING btree (id);

-- Name: col_refs_new_col_id_idx1; Type: INDEX; Schema: macrostrat; Owner: macrostrat
CREATE INDEX col_refs_new_col_id_idx1 ON macrostrat.col_refs USING btree (col_id);

-- Name: col_refs_new_ref_id_idx1; Type: INDEX; Schema: macrostrat; Owner: macrostrat
CREATE INDEX col_refs_new_ref_id_idx1 ON macrostrat.col_refs USING btree (ref_id);

-- Name: cols_new_col_group_id_idx; Type: INDEX; Schema: macrostrat; Owner: macrostrat
CREATE INDEX cols_new_col_group_id_idx ON macrostrat.cols USING btree (col_group_id);

-- Name: cols_new_coordinate_idx; Type: INDEX; Schema: macrostrat; Owner: macrostrat
CREATE INDEX cols_new_coordinate_idx ON macrostrat.cols USING gist (coordinate);

-- Name: cols_new_poly_geom_idx; Type: INDEX; Schema: macrostrat; Owner: macrostrat
CREATE INDEX cols_new_poly_geom_idx ON macrostrat.cols USING gist (poly_geom);

-- Name: cols_new_project_id_idx; Type: INDEX; Schema: macrostrat; Owner: macrostrat
CREATE INDEX cols_new_project_id_idx ON macrostrat.cols USING btree (project_id);

-- Name: cols_new_status_code_idx; Type: INDEX; Schema: macrostrat; Owner: macrostrat
CREATE INDEX cols_new_status_code_idx ON macrostrat.cols USING btree (status_code);

-- Name: concepts_places_new_concept_id_idx; Type: INDEX; Schema: macrostrat; Owner: macrostrat
CREATE INDEX concepts_places_new_concept_id_idx ON macrostrat.concepts_places USING btree (concept_id);

-- Name: concepts_places_new_place_id_idx; Type: INDEX; Schema: macrostrat; Owner: macrostrat
CREATE INDEX concepts_places_new_place_id_idx ON macrostrat.concepts_places USING btree (place_id);

-- Name: intervals_new_age_bottom_idx1; Type: INDEX; Schema: macrostrat; Owner: macrostrat
CREATE INDEX intervals_new_age_bottom_idx1 ON macrostrat.intervals USING btree (age_bottom);

-- Name: intervals_new_age_top_idx1; Type: INDEX; Schema: macrostrat; Owner: macrostrat
CREATE INDEX intervals_new_age_top_idx1 ON macrostrat.intervals USING btree (age_top);

-- Name: intervals_new_id_idx1; Type: INDEX; Schema: macrostrat; Owner: macrostrat
CREATE INDEX intervals_new_id_idx1 ON macrostrat.intervals USING btree (id);

-- Name: intervals_new_interval_name_idx1; Type: INDEX; Schema: macrostrat; Owner: macrostrat
CREATE INDEX intervals_new_interval_name_idx1 ON macrostrat.intervals USING btree (interval_name);

-- Name: intervals_new_interval_type_idx1; Type: INDEX; Schema: macrostrat; Owner: macrostrat
CREATE INDEX intervals_new_interval_type_idx1 ON macrostrat.intervals USING btree (interval_type);

-- Name: lith_atts_new_att_type_idx1; Type: INDEX; Schema: macrostrat; Owner: macrostrat
CREATE INDEX lith_atts_new_att_type_idx1 ON macrostrat.lith_atts USING btree (att_type);

-- Name: lith_atts_new_lith_att_idx1; Type: INDEX; Schema: macrostrat; Owner: macrostrat
CREATE INDEX lith_atts_new_lith_att_idx1 ON macrostrat.lith_atts USING btree (lith_att);

-- Name: liths_new_lith_class_idx1; Type: INDEX; Schema: macrostrat; Owner: macrostrat
CREATE INDEX liths_new_lith_class_idx1 ON macrostrat.liths USING btree (lith_class);

-- Name: liths_new_lith_idx1; Type: INDEX; Schema: macrostrat; Owner: macrostrat
CREATE INDEX liths_new_lith_idx1 ON macrostrat.liths USING btree (lith);

-- Name: liths_new_lith_type_idx1; Type: INDEX; Schema: macrostrat; Owner: macrostrat
CREATE INDEX liths_new_lith_type_idx1 ON macrostrat.liths USING btree (lith_type);

-- Name: lookup_strat_names_new_bed_id_idx; Type: INDEX; Schema: macrostrat; Owner: macrostrat
CREATE INDEX lookup_strat_names_new_bed_id_idx ON macrostrat.lookup_strat_names USING btree (bed_id);

-- Name: lookup_strat_names_new_concept_id_idx; Type: INDEX; Schema: macrostrat; Owner: macrostrat
CREATE INDEX lookup_strat_names_new_concept_id_idx ON macrostrat.lookup_strat_names USING btree (concept_id);

-- Name: lookup_strat_names_new_fm_id_idx; Type: INDEX; Schema: macrostrat; Owner: macrostrat
CREATE INDEX lookup_strat_names_new_fm_id_idx ON macrostrat.lookup_strat_names USING btree (fm_id);

-- Name: lookup_strat_names_new_gp_id_idx; Type: INDEX; Schema: macrostrat; Owner: macrostrat
CREATE INDEX lookup_strat_names_new_gp_id_idx ON macrostrat.lookup_strat_names USING btree (gp_id);

-- Name: lookup_strat_names_new_mbr_id_idx; Type: INDEX; Schema: macrostrat; Owner: macrostrat
CREATE INDEX lookup_strat_names_new_mbr_id_idx ON macrostrat.lookup_strat_names USING btree (mbr_id);

-- Name: lookup_strat_names_new_sgp_id_idx; Type: INDEX; Schema: macrostrat; Owner: macrostrat
CREATE INDEX lookup_strat_names_new_sgp_id_idx ON macrostrat.lookup_strat_names USING btree (sgp_id);

-- Name: lookup_strat_names_new_strat_name_id_idx; Type: INDEX; Schema: macrostrat; Owner: macrostrat
CREATE INDEX lookup_strat_names_new_strat_name_id_idx ON macrostrat.lookup_strat_names USING btree (strat_name_id);

-- Name: lookup_strat_names_new_strat_name_idx; Type: INDEX; Schema: macrostrat; Owner: macrostrat
CREATE INDEX lookup_strat_names_new_strat_name_idx ON macrostrat.lookup_strat_names USING btree (strat_name);

-- Name: lookup_unit_attrs_api_new_unit_id_idx1; Type: INDEX; Schema: macrostrat; Owner: macrostrat
CREATE INDEX lookup_unit_attrs_api_new_unit_id_idx1 ON macrostrat.lookup_unit_attrs_api USING btree (unit_id);

-- Name: lookup_unit_intervals_new_best_interval_id_idx; Type: INDEX; Schema: macrostrat; Owner: macrostrat
CREATE INDEX lookup_unit_intervals_new_best_interval_id_idx ON macrostrat.lookup_unit_intervals USING btree (best_interval_id);

-- Name: lookup_unit_intervals_new_unit_id_idx; Type: INDEX; Schema: macrostrat; Owner: macrostrat
CREATE INDEX lookup_unit_intervals_new_unit_id_idx ON macrostrat.lookup_unit_intervals USING btree (unit_id);

-- Name: lookup_unit_liths_new_unit_id_idx; Type: INDEX; Schema: macrostrat; Owner: macrostrat
CREATE INDEX lookup_unit_liths_new_unit_id_idx ON macrostrat.lookup_unit_liths USING btree (unit_id);

-- Name: lookup_units_new_b_int_idx1; Type: INDEX; Schema: macrostrat; Owner: macrostrat
CREATE INDEX lookup_units_new_b_int_idx1 ON macrostrat.lookup_units USING btree (b_int);

-- Name: lookup_units_new_project_id_idx1; Type: INDEX; Schema: macrostrat; Owner: macrostrat
CREATE INDEX lookup_units_new_project_id_idx1 ON macrostrat.lookup_units USING btree (project_id);

-- Name: lookup_units_new_t_int_idx1; Type: INDEX; Schema: macrostrat; Owner: macrostrat
CREATE INDEX lookup_units_new_t_int_idx1 ON macrostrat.lookup_units USING btree (t_int);

-- Name: measurements_new_id_idx; Type: INDEX; Schema: macrostrat; Owner: macrostrat
CREATE INDEX measurements_new_id_idx ON macrostrat.measurements USING btree (id);

-- Name: measurements_new_measurement_class_idx; Type: INDEX; Schema: macrostrat; Owner: macrostrat
CREATE INDEX measurements_new_measurement_class_idx ON macrostrat.measurements USING btree (measurement_class);

-- Name: measurements_new_measurement_type_idx; Type: INDEX; Schema: macrostrat; Owner: macrostrat
CREATE INDEX measurements_new_measurement_type_idx ON macrostrat.measurements USING btree (measurement_type);

-- Name: measuremeta_new_lith_att_id_idx1; Type: INDEX; Schema: macrostrat; Owner: macrostrat
CREATE INDEX measuremeta_new_lith_att_id_idx1 ON macrostrat.measuremeta USING btree (lith_att_id);

-- Name: measuremeta_new_lith_id_idx1; Type: INDEX; Schema: macrostrat; Owner: macrostrat
CREATE INDEX measuremeta_new_lith_id_idx1 ON macrostrat.measuremeta USING btree (lith_id);

-- Name: measuremeta_new_ref_id_idx1; Type: INDEX; Schema: macrostrat; Owner: macrostrat
CREATE INDEX measuremeta_new_ref_id_idx1 ON macrostrat.measuremeta USING btree (ref_id);

-- Name: measures_new_measurement_id_idx1; Type: INDEX; Schema: macrostrat; Owner: macrostrat
CREATE INDEX measures_new_measurement_id_idx1 ON macrostrat.measures USING btree (measurement_id);

-- Name: measures_new_measuremeta_id_idx1; Type: INDEX; Schema: macrostrat; Owner: macrostrat
CREATE INDEX measures_new_measuremeta_id_idx1 ON macrostrat.measures USING btree (measuremeta_id);

-- Name: pbdb_collections_new_collection_no_idx1; Type: INDEX; Schema: macrostrat; Owner: macrostrat
CREATE INDEX pbdb_collections_new_collection_no_idx1 ON macrostrat.pbdb_collections USING btree (collection_no);

-- Name: pbdb_collections_new_early_age_idx1; Type: INDEX; Schema: macrostrat; Owner: macrostrat
CREATE INDEX pbdb_collections_new_early_age_idx1 ON macrostrat.pbdb_collections USING btree (early_age);

-- Name: pbdb_collections_new_geom_idx1; Type: INDEX; Schema: macrostrat; Owner: macrostrat
CREATE INDEX pbdb_collections_new_geom_idx1 ON macrostrat.pbdb_collections USING gist (geom);

-- Name: pbdb_collections_new_late_age_idx1; Type: INDEX; Schema: macrostrat; Owner: macrostrat
CREATE INDEX pbdb_collections_new_late_age_idx1 ON macrostrat.pbdb_collections USING btree (late_age);

-- Name: places_new_geom_idx; Type: INDEX; Schema: macrostrat; Owner: macrostrat
CREATE INDEX places_new_geom_idx ON macrostrat.places USING gist (geom);

-- Name: projects_new_project_idx; Type: INDEX; Schema: macrostrat; Owner: macrostrat
CREATE INDEX projects_new_project_idx ON macrostrat.projects USING btree (project);

-- Name: projects_new_timescale_id_idx; Type: INDEX; Schema: macrostrat; Owner: macrostrat
CREATE INDEX projects_new_timescale_id_idx ON macrostrat.projects USING btree (timescale_id);

-- Name: refs_new_rgeom_idx1; Type: INDEX; Schema: macrostrat; Owner: macrostrat
CREATE INDEX refs_new_rgeom_idx1 ON macrostrat.refs USING gist (rgeom);

-- Name: sections_new_col_id_idx1; Type: INDEX; Schema: macrostrat; Owner: macrostrat
CREATE INDEX sections_new_col_id_idx1 ON macrostrat.sections USING btree (col_id);

-- Name: sections_new_id_idx1; Type: INDEX; Schema: macrostrat; Owner: macrostrat
CREATE INDEX sections_new_id_idx1 ON macrostrat.sections USING btree (id);

-- Name: strat_name_footprints_new_geom_idx; Type: INDEX; Schema: macrostrat; Owner: macrostrat
CREATE INDEX strat_name_footprints_new_geom_idx ON macrostrat.strat_name_footprints USING gist (geom);

-- Name: strat_name_footprints_new_strat_name_id_idx; Type: INDEX; Schema: macrostrat; Owner: macrostrat
CREATE INDEX strat_name_footprints_new_strat_name_id_idx ON macrostrat.strat_name_footprints USING btree (strat_name_id);

-- Name: strat_names_meta_new_b_int_idx1; Type: INDEX; Schema: macrostrat; Owner: macrostrat
CREATE INDEX strat_names_meta_new_b_int_idx1 ON macrostrat.strat_names_meta USING btree (b_int);

-- Name: strat_names_meta_new_interval_id_idx1; Type: INDEX; Schema: macrostrat; Owner: macrostrat
CREATE INDEX strat_names_meta_new_interval_id_idx1 ON macrostrat.strat_names_meta USING btree (interval_id);

-- Name: strat_names_meta_new_ref_id_idx1; Type: INDEX; Schema: macrostrat; Owner: macrostrat
CREATE INDEX strat_names_meta_new_ref_id_idx1 ON macrostrat.strat_names_meta USING btree (ref_id);

-- Name: strat_names_meta_new_t_int_idx1; Type: INDEX; Schema: macrostrat; Owner: macrostrat
CREATE INDEX strat_names_meta_new_t_int_idx1 ON macrostrat.strat_names_meta USING btree (t_int);

-- Name: strat_names_new_concept_id_idx; Type: INDEX; Schema: macrostrat; Owner: macrostrat
CREATE INDEX strat_names_new_concept_id_idx ON macrostrat.strat_names USING btree (concept_id);

-- Name: strat_names_new_rank_idx; Type: INDEX; Schema: macrostrat; Owner: macrostrat
CREATE INDEX strat_names_new_rank_idx ON macrostrat.strat_names USING btree (rank);

-- Name: strat_names_new_ref_id_idx; Type: INDEX; Schema: macrostrat; Owner: macrostrat
CREATE INDEX strat_names_new_ref_id_idx ON macrostrat.strat_names USING btree (ref_id);

-- Name: strat_names_new_strat_name_idx; Type: INDEX; Schema: macrostrat; Owner: macrostrat
CREATE INDEX strat_names_new_strat_name_idx ON macrostrat.strat_names USING btree (strat_name);

-- Name: strat_names_places_new_place_id_idx1; Type: INDEX; Schema: macrostrat; Owner: macrostrat
CREATE INDEX strat_names_places_new_place_id_idx1 ON macrostrat.strat_names_places USING btree (place_id);

-- Name: strat_names_places_new_strat_name_id_idx1; Type: INDEX; Schema: macrostrat; Owner: macrostrat
CREATE INDEX strat_names_places_new_strat_name_id_idx1 ON macrostrat.strat_names_places USING btree (strat_name_id);

-- Name: strat_tree_new_child_idx1; Type: INDEX; Schema: macrostrat; Owner: macrostrat
CREATE INDEX strat_tree_new_child_idx1 ON macrostrat.strat_tree USING btree (child);

-- Name: strat_tree_new_parent_idx1; Type: INDEX; Schema: macrostrat; Owner: macrostrat
CREATE INDEX strat_tree_new_parent_idx1 ON macrostrat.strat_tree USING btree (parent);

-- Name: strat_tree_new_ref_id_idx1; Type: INDEX; Schema: macrostrat; Owner: macrostrat
CREATE INDEX strat_tree_new_ref_id_idx1 ON macrostrat.strat_tree USING btree (ref_id);

-- Name: timescales_intervals_new_interval_id_idx1; Type: INDEX; Schema: macrostrat; Owner: macrostrat
CREATE INDEX timescales_intervals_new_interval_id_idx1 ON macrostrat.timescales_intervals USING btree (interval_id);

-- Name: timescales_intervals_new_timescale_id_idx1; Type: INDEX; Schema: macrostrat; Owner: macrostrat
CREATE INDEX timescales_intervals_new_timescale_id_idx1 ON macrostrat.timescales_intervals USING btree (timescale_id);

-- Name: timescales_new_ref_id_idx1; Type: INDEX; Schema: macrostrat; Owner: macrostrat
CREATE INDEX timescales_new_ref_id_idx1 ON macrostrat.timescales USING btree (ref_id);

-- Name: timescales_new_timescale_idx1; Type: INDEX; Schema: macrostrat; Owner: macrostrat
CREATE INDEX timescales_new_timescale_idx1 ON macrostrat.timescales USING btree (timescale);

-- Name: unit_boundaries_section_id_idx; Type: INDEX; Schema: macrostrat; Owner: macrostrat
CREATE INDEX unit_boundaries_section_id_idx ON macrostrat.unit_boundaries USING btree (section_id);

-- Name: unit_boundaries_t1_idx; Type: INDEX; Schema: macrostrat; Owner: macrostrat
CREATE INDEX unit_boundaries_t1_idx ON macrostrat.unit_boundaries USING btree (t1);

-- Name: unit_boundaries_unit_id_2_idx; Type: INDEX; Schema: macrostrat; Owner: macrostrat
CREATE INDEX unit_boundaries_unit_id_2_idx ON macrostrat.unit_boundaries USING btree (unit_id_2);

-- Name: unit_boundaries_unit_id_idx; Type: INDEX; Schema: macrostrat; Owner: macrostrat
CREATE INDEX unit_boundaries_unit_id_idx ON macrostrat.unit_boundaries USING btree (unit_id);

-- Name: unit_econs_new_econ_id_idx1; Type: INDEX; Schema: macrostrat; Owner: macrostrat
CREATE INDEX unit_econs_new_econ_id_idx1 ON macrostrat.unit_econs USING btree (econ_id);

-- Name: unit_econs_new_ref_id_idx1; Type: INDEX; Schema: macrostrat; Owner: macrostrat
CREATE INDEX unit_econs_new_ref_id_idx1 ON macrostrat.unit_econs USING btree (ref_id);

-- Name: unit_econs_new_unit_id_idx1; Type: INDEX; Schema: macrostrat; Owner: macrostrat
CREATE INDEX unit_econs_new_unit_id_idx1 ON macrostrat.unit_econs USING btree (unit_id);

-- Name: unit_environs_new_environ_id_idx1; Type: INDEX; Schema: macrostrat; Owner: macrostrat
CREATE INDEX unit_environs_new_environ_id_idx1 ON macrostrat.unit_environs USING btree (environ_id);

-- Name: unit_environs_new_ref_id_idx1; Type: INDEX; Schema: macrostrat; Owner: macrostrat
CREATE INDEX unit_environs_new_ref_id_idx1 ON macrostrat.unit_environs USING btree (ref_id);

-- Name: unit_environs_new_unit_id_idx1; Type: INDEX; Schema: macrostrat; Owner: macrostrat
CREATE INDEX unit_environs_new_unit_id_idx1 ON macrostrat.unit_environs USING btree (unit_id);

-- Name: unit_lith_atts_new_lith_att_id_idx1; Type: INDEX; Schema: macrostrat; Owner: macrostrat
CREATE INDEX unit_lith_atts_new_lith_att_id_idx1 ON macrostrat.unit_lith_atts USING btree (lith_att_id);

-- Name: unit_lith_atts_new_ref_id_idx1; Type: INDEX; Schema: macrostrat; Owner: macrostrat
CREATE INDEX unit_lith_atts_new_ref_id_idx1 ON macrostrat.unit_lith_atts USING btree (ref_id);

-- Name: unit_lith_atts_new_unit_lith_id_idx1; Type: INDEX; Schema: macrostrat; Owner: macrostrat
CREATE INDEX unit_lith_atts_new_unit_lith_id_idx1 ON macrostrat.unit_lith_atts USING btree (unit_lith_id);

-- Name: unit_liths_new_lith_id_idx1; Type: INDEX; Schema: macrostrat; Owner: macrostrat
CREATE INDEX unit_liths_new_lith_id_idx1 ON macrostrat.unit_liths USING btree (lith_id);

-- Name: unit_liths_new_ref_id_idx1; Type: INDEX; Schema: macrostrat; Owner: macrostrat
CREATE INDEX unit_liths_new_ref_id_idx1 ON macrostrat.unit_liths USING btree (ref_id);

-- Name: unit_liths_new_unit_id_idx1; Type: INDEX; Schema: macrostrat; Owner: macrostrat
CREATE INDEX unit_liths_new_unit_id_idx1 ON macrostrat.unit_liths USING btree (unit_id);

-- Name: unit_measures_new_measuremeta_id_idx; Type: INDEX; Schema: macrostrat; Owner: macrostrat
CREATE INDEX unit_measures_new_measuremeta_id_idx ON macrostrat.unit_measures USING btree (measuremeta_id);

-- Name: unit_measures_new_strat_name_id_idx; Type: INDEX; Schema: macrostrat; Owner: macrostrat
CREATE INDEX unit_measures_new_strat_name_id_idx ON macrostrat.unit_measures USING btree (strat_name_id);

-- Name: unit_measures_new_unit_id_idx; Type: INDEX; Schema: macrostrat; Owner: macrostrat
CREATE INDEX unit_measures_new_unit_id_idx ON macrostrat.unit_measures USING btree (unit_id);

-- Name: unit_strat_names_new_strat_name_id_idx1; Type: INDEX; Schema: macrostrat; Owner: macrostrat
CREATE INDEX unit_strat_names_new_strat_name_id_idx1 ON macrostrat.unit_strat_names USING btree (strat_name_id);

-- Name: unit_strat_names_new_unit_id_idx1; Type: INDEX; Schema: macrostrat; Owner: macrostrat
CREATE INDEX unit_strat_names_new_unit_id_idx1 ON macrostrat.unit_strat_names USING btree (unit_id);

-- Name: units_new_col_id_idx; Type: INDEX; Schema: macrostrat; Owner: macrostrat
CREATE INDEX units_new_col_id_idx ON macrostrat.units USING btree (col_id);

-- Name: units_new_color_idx; Type: INDEX; Schema: macrostrat; Owner: macrostrat
CREATE INDEX units_new_color_idx ON macrostrat.units USING btree (color);

-- Name: units_new_section_id_idx; Type: INDEX; Schema: macrostrat; Owner: macrostrat
CREATE INDEX units_new_section_id_idx ON macrostrat.units USING btree (section_id);

-- Name: units_new_strat_name_idx; Type: INDEX; Schema: macrostrat; Owner: macrostrat
CREATE INDEX units_new_strat_name_idx ON macrostrat.units USING btree (strat_name);

-- Name: units_sections_new_col_id_idx; Type: INDEX; Schema: macrostrat; Owner: macrostrat
CREATE INDEX units_sections_new_col_id_idx ON macrostrat.units_sections USING btree (col_id);

-- Name: units_sections_new_section_id_idx; Type: INDEX; Schema: macrostrat; Owner: macrostrat
CREATE INDEX units_sections_new_section_id_idx ON macrostrat.units_sections USING btree (section_id);

-- Name: units_sections_new_unit_id_idx; Type: INDEX; Schema: macrostrat; Owner: macrostrat
CREATE INDEX units_sections_new_unit_id_idx ON macrostrat.units_sections USING btree (unit_id);

-- Name: polygons_b_interval_idx; Type: INDEX; Schema: maps; Owner: macrostrat
CREATE INDEX polygons_b_interval_idx ON ONLY maps.polygons USING btree (b_interval);

-- Name: large_b_interval_idx; Type: INDEX; Schema: maps; Owner: macrostrat
CREATE INDEX large_b_interval_idx ON maps.polygons_large USING btree (b_interval);

-- Name: polygons_geom_idx; Type: INDEX; Schema: maps; Owner: macrostrat
CREATE INDEX polygons_geom_idx ON ONLY maps.polygons USING gist (geom);

-- Name: large_geom_idx; Type: INDEX; Schema: maps; Owner: macrostrat
CREATE INDEX large_geom_idx ON maps.polygons_large USING gist (geom);

-- Name: polygons_name_idx; Type: INDEX; Schema: maps; Owner: macrostrat
CREATE INDEX polygons_name_idx ON ONLY maps.polygons USING btree (name);

-- Name: large_name_idx; Type: INDEX; Schema: maps; Owner: macrostrat
CREATE INDEX large_name_idx ON maps.polygons_large USING btree (name);

-- Name: polygons_orig_id_idx; Type: INDEX; Schema: maps; Owner: macrostrat
CREATE INDEX polygons_orig_id_idx ON ONLY maps.polygons USING btree (orig_id);

-- Name: large_orig_id_idx; Type: INDEX; Schema: maps; Owner: macrostrat
CREATE INDEX large_orig_id_idx ON maps.polygons_large USING btree (orig_id);

-- Name: polygons_source_id_idx; Type: INDEX; Schema: maps; Owner: macrostrat
CREATE INDEX polygons_source_id_idx ON ONLY maps.polygons USING btree (source_id);

-- Name: large_source_id_idx; Type: INDEX; Schema: maps; Owner: macrostrat
CREATE INDEX large_source_id_idx ON maps.polygons_large USING btree (source_id);

-- Name: polygons_t_interval_idx; Type: INDEX; Schema: maps; Owner: macrostrat
CREATE INDEX polygons_t_interval_idx ON ONLY maps.polygons USING btree (t_interval);

-- Name: large_t_interval_idx; Type: INDEX; Schema: maps; Owner: macrostrat
CREATE INDEX large_t_interval_idx ON maps.polygons_large USING btree (t_interval);

-- Name: legend_liths_legend_id_idx; Type: INDEX; Schema: maps; Owner: macrostrat
CREATE INDEX legend_liths_legend_id_idx ON maps.legend_liths USING btree (legend_id);

-- Name: legend_liths_lith_id_idx; Type: INDEX; Schema: maps; Owner: macrostrat
CREATE INDEX legend_liths_lith_id_idx ON maps.legend_liths USING btree (lith_id);

-- Name: legend_source_id_idx; Type: INDEX; Schema: maps; Owner: macrostrat
CREATE INDEX legend_source_id_idx ON maps.legend USING btree (source_id);

-- Name: lines_geom_idx; Type: INDEX; Schema: maps; Owner: macrostrat
CREATE INDEX lines_geom_idx ON ONLY maps.lines USING gist (geom);

-- Name: lines_large_geom_idx; Type: INDEX; Schema: maps; Owner: macrostrat
CREATE INDEX lines_large_geom_idx ON maps.lines_large USING gist (geom);

-- Name: lines_line_id_idx; Type: INDEX; Schema: maps; Owner: macrostrat
CREATE INDEX lines_line_id_idx ON ONLY maps.lines USING btree (line_id);

-- Name: lines_large_line_id_idx; Type: INDEX; Schema: maps; Owner: macrostrat
CREATE INDEX lines_large_line_id_idx ON maps.lines_large USING btree (line_id);

-- Name: lines_orig_id_idx; Type: INDEX; Schema: maps; Owner: macrostrat
CREATE INDEX lines_orig_id_idx ON ONLY maps.lines USING btree (orig_id);

-- Name: lines_large_orig_id_idx; Type: INDEX; Schema: maps; Owner: macrostrat
CREATE INDEX lines_large_orig_id_idx ON maps.lines_large USING btree (orig_id);

-- Name: lines_source_id_idx; Type: INDEX; Schema: maps; Owner: macrostrat
CREATE INDEX lines_source_id_idx ON ONLY maps.lines USING btree (source_id);

-- Name: lines_large_source_id_idx; Type: INDEX; Schema: maps; Owner: macrostrat
CREATE INDEX lines_large_source_id_idx ON maps.lines_large USING btree (source_id);

-- Name: lines_medium_geom_idx; Type: INDEX; Schema: maps; Owner: macrostrat
CREATE INDEX lines_medium_geom_idx ON maps.lines_medium USING gist (geom);

-- Name: lines_medium_line_id_idx; Type: INDEX; Schema: maps; Owner: macrostrat
CREATE INDEX lines_medium_line_id_idx ON maps.lines_medium USING btree (line_id);

-- Name: lines_medium_orig_id_idx; Type: INDEX; Schema: maps; Owner: macrostrat
CREATE INDEX lines_medium_orig_id_idx ON maps.lines_medium USING btree (orig_id);

-- Name: lines_medium_source_id_idx; Type: INDEX; Schema: maps; Owner: macrostrat
CREATE INDEX lines_medium_source_id_idx ON maps.lines_medium USING btree (source_id);

-- Name: lines_small_geom_idx; Type: INDEX; Schema: maps; Owner: macrostrat
CREATE INDEX lines_small_geom_idx ON maps.lines_small USING gist (geom);

-- Name: lines_small_line_id_idx; Type: INDEX; Schema: maps; Owner: macrostrat
CREATE INDEX lines_small_line_id_idx ON maps.lines_small USING btree (line_id);

-- Name: lines_small_orig_id_idx; Type: INDEX; Schema: maps; Owner: macrostrat
CREATE INDEX lines_small_orig_id_idx ON maps.lines_small USING btree (orig_id);

-- Name: lines_small_source_id_idx; Type: INDEX; Schema: maps; Owner: macrostrat
CREATE INDEX lines_small_source_id_idx ON maps.lines_small USING btree (source_id);

-- Name: lines_tiny_geom_idx; Type: INDEX; Schema: maps; Owner: macrostrat
CREATE INDEX lines_tiny_geom_idx ON maps.lines_tiny USING gist (geom);

-- Name: lines_tiny_line_id_idx; Type: INDEX; Schema: maps; Owner: macrostrat
CREATE INDEX lines_tiny_line_id_idx ON maps.lines_tiny USING btree (line_id);

-- Name: lines_tiny_orig_id_idx; Type: INDEX; Schema: maps; Owner: macrostrat
CREATE INDEX lines_tiny_orig_id_idx ON maps.lines_tiny USING btree (orig_id);

-- Name: lines_tiny_source_id_idx; Type: INDEX; Schema: maps; Owner: macrostrat
CREATE INDEX lines_tiny_source_id_idx ON maps.lines_tiny USING btree (source_id);

-- Name: manual_matches_map_id_idx; Type: INDEX; Schema: maps; Owner: macrostrat
CREATE INDEX manual_matches_map_id_idx ON maps.manual_matches USING btree (map_id);

-- Name: manual_matches_strat_name_id_idx; Type: INDEX; Schema: maps; Owner: macrostrat
CREATE INDEX manual_matches_strat_name_id_idx ON maps.manual_matches USING btree (strat_name_id);

-- Name: manual_matches_unit_id_idx; Type: INDEX; Schema: maps; Owner: macrostrat
CREATE INDEX manual_matches_unit_id_idx ON maps.manual_matches USING btree (unit_id);

-- Name: map_legend_legend_id_idx; Type: INDEX; Schema: maps; Owner: macrostrat
CREATE INDEX map_legend_legend_id_idx ON maps.map_legend USING btree (legend_id);

-- Name: map_legend_map_id_idx; Type: INDEX; Schema: maps; Owner: macrostrat
CREATE INDEX map_legend_map_id_idx ON maps.map_legend USING btree (map_id);

-- Name: map_liths_lith_id_idx; Type: INDEX; Schema: maps; Owner: macrostrat
CREATE INDEX map_liths_lith_id_idx ON maps.map_liths USING btree (lith_id);

-- Name: map_liths_map_id_idx; Type: INDEX; Schema: maps; Owner: macrostrat
CREATE INDEX map_liths_map_id_idx ON maps.map_liths USING btree (map_id);

-- Name: map_strat_names_map_id_idx; Type: INDEX; Schema: maps; Owner: macrostrat
CREATE INDEX map_strat_names_map_id_idx ON maps.map_strat_names USING btree (map_id);

-- Name: map_strat_names_strat_name_id_idx; Type: INDEX; Schema: maps; Owner: macrostrat
CREATE INDEX map_strat_names_strat_name_id_idx ON maps.map_strat_names USING btree (strat_name_id);

-- Name: map_units_map_id_idx; Type: INDEX; Schema: maps; Owner: macrostrat
CREATE INDEX map_units_map_id_idx ON maps.map_units USING btree (map_id);

-- Name: map_units_unit_id_idx; Type: INDEX; Schema: maps; Owner: macrostrat
CREATE INDEX map_units_unit_id_idx ON maps.map_units USING btree (unit_id);

-- Name: medium_b_interval_idx; Type: INDEX; Schema: maps; Owner: macrostrat
CREATE INDEX medium_b_interval_idx ON maps.polygons_medium USING btree (b_interval);

-- Name: medium_geom_idx; Type: INDEX; Schema: maps; Owner: macrostrat
CREATE INDEX medium_geom_idx ON maps.polygons_medium USING gist (geom);

-- Name: medium_orig_id_idx; Type: INDEX; Schema: maps; Owner: macrostrat
CREATE INDEX medium_orig_id_idx ON maps.polygons_medium USING btree (orig_id);

-- Name: medium_source_id_idx; Type: INDEX; Schema: maps; Owner: macrostrat
CREATE INDEX medium_source_id_idx ON maps.polygons_medium USING btree (source_id);

-- Name: medium_t_interval_idx; Type: INDEX; Schema: maps; Owner: macrostrat
CREATE INDEX medium_t_interval_idx ON maps.polygons_medium USING btree (t_interval);

-- Name: points_geom_idx; Type: INDEX; Schema: maps; Owner: macrostrat
CREATE INDEX points_geom_idx ON maps.points USING gist (geom);

-- Name: points_source_id_idx; Type: INDEX; Schema: maps; Owner: macrostrat
CREATE INDEX points_source_id_idx ON maps.points USING btree (source_id);

-- Name: polygons_medium_name_idx; Type: INDEX; Schema: maps; Owner: macrostrat
CREATE INDEX polygons_medium_name_idx ON maps.polygons_medium USING btree (name);

-- Name: polygons_small_name_idx; Type: INDEX; Schema: maps; Owner: macrostrat
CREATE INDEX polygons_small_name_idx ON maps.polygons_small USING btree (name);

-- Name: polygons_tiny_name_idx; Type: INDEX; Schema: maps; Owner: macrostrat
CREATE INDEX polygons_tiny_name_idx ON maps.polygons_tiny USING btree (name);

-- Name: small_b_interval_idx; Type: INDEX; Schema: maps; Owner: macrostrat
CREATE INDEX small_b_interval_idx ON maps.polygons_small USING btree (b_interval);

-- Name: small_geom_idx; Type: INDEX; Schema: maps; Owner: macrostrat
CREATE INDEX small_geom_idx ON maps.polygons_small USING gist (geom);

-- Name: small_orig_id_idx; Type: INDEX; Schema: maps; Owner: macrostrat
CREATE INDEX small_orig_id_idx ON maps.polygons_small USING btree (orig_id);

-- Name: small_source_id_idx; Type: INDEX; Schema: maps; Owner: macrostrat
CREATE INDEX small_source_id_idx ON maps.polygons_small USING btree (source_id);

-- Name: small_t_interval_idx; Type: INDEX; Schema: maps; Owner: macrostrat
CREATE INDEX small_t_interval_idx ON maps.polygons_small USING btree (t_interval);

-- Name: sources_rgeom_idx; Type: INDEX; Schema: maps; Owner: macrostrat
CREATE INDEX sources_rgeom_idx ON maps.sources USING gist (rgeom);

-- Name: sources_web_geom_idx; Type: INDEX; Schema: maps; Owner: macrostrat
CREATE INDEX sources_web_geom_idx ON maps.sources USING gist (web_geom);

-- Name: tiny_b_interval_idx; Type: INDEX; Schema: maps; Owner: macrostrat
CREATE INDEX tiny_b_interval_idx ON maps.polygons_tiny USING btree (b_interval);

-- Name: tiny_geom_idx; Type: INDEX; Schema: maps; Owner: macrostrat
CREATE INDEX tiny_geom_idx ON maps.polygons_tiny USING gist (geom);

-- Name: tiny_orig_id_idx; Type: INDEX; Schema: maps; Owner: macrostrat
CREATE INDEX tiny_orig_id_idx ON maps.polygons_tiny USING btree (orig_id);

-- Name: tiny_source_id_idx; Type: INDEX; Schema: maps; Owner: macrostrat
CREATE INDEX tiny_source_id_idx ON maps.polygons_tiny USING btree (source_id);

-- Name: tiny_t_interval_idx; Type: INDEX; Schema: maps; Owner: macrostrat
CREATE INDEX tiny_t_interval_idx ON maps.polygons_tiny USING btree (t_interval);

-- Name: impervious_st_convexhull_idx; Type: INDEX; Schema: public; Owner: macrostrat
CREATE INDEX impervious_st_convexhull_idx ON public.impervious USING gist (public.st_convexhull(rast));

-- Name: land_geom_idx; Type: INDEX; Schema: public; Owner: macrostrat
CREATE INDEX land_geom_idx ON public.land USING gist (geom);

-- Name: lookup_large_concept_ids_idx; Type: INDEX; Schema: public; Owner: macrostrat
CREATE INDEX lookup_large_concept_ids_idx ON public.lookup_large USING gin (concept_ids);

-- Name: lookup_large_legend_id_idx; Type: INDEX; Schema: public; Owner: macrostrat
CREATE INDEX lookup_large_legend_id_idx ON public.lookup_large USING btree (legend_id);

-- Name: lookup_large_lith_ids_idx; Type: INDEX; Schema: public; Owner: macrostrat
CREATE INDEX lookup_large_lith_ids_idx ON public.lookup_large USING gin (lith_ids);

-- Name: lookup_large_map_id_idx; Type: INDEX; Schema: public; Owner: macrostrat
CREATE INDEX lookup_large_map_id_idx ON public.lookup_large USING btree (map_id);

-- Name: lookup_large_strat_name_children_idx; Type: INDEX; Schema: public; Owner: macrostrat
CREATE INDEX lookup_large_strat_name_children_idx ON public.lookup_large USING gin (strat_name_children);

-- Name: lookup_medium_concept_ids_idx; Type: INDEX; Schema: public; Owner: macrostrat
CREATE INDEX lookup_medium_concept_ids_idx ON public.lookup_medium USING gin (concept_ids);

-- Name: lookup_medium_legend_id_idx; Type: INDEX; Schema: public; Owner: macrostrat
CREATE INDEX lookup_medium_legend_id_idx ON public.lookup_medium USING btree (legend_id);

-- Name: lookup_medium_lith_ids_idx; Type: INDEX; Schema: public; Owner: macrostrat
CREATE INDEX lookup_medium_lith_ids_idx ON public.lookup_medium USING gin (lith_ids);

-- Name: lookup_medium_map_id_idx; Type: INDEX; Schema: public; Owner: macrostrat
CREATE INDEX lookup_medium_map_id_idx ON public.lookup_medium USING btree (map_id);

-- Name: lookup_medium_strat_name_children_idx; Type: INDEX; Schema: public; Owner: macrostrat
CREATE INDEX lookup_medium_strat_name_children_idx ON public.lookup_medium USING gin (strat_name_children);

-- Name: lookup_small_concept_ids_idx; Type: INDEX; Schema: public; Owner: macrostrat
CREATE INDEX lookup_small_concept_ids_idx ON public.lookup_small USING gin (concept_ids);

-- Name: lookup_small_legend_id_idx; Type: INDEX; Schema: public; Owner: macrostrat
CREATE INDEX lookup_small_legend_id_idx ON public.lookup_small USING btree (legend_id);

-- Name: lookup_small_lith_ids_idx; Type: INDEX; Schema: public; Owner: macrostrat
CREATE INDEX lookup_small_lith_ids_idx ON public.lookup_small USING gin (lith_ids);

-- Name: lookup_small_map_id_idx; Type: INDEX; Schema: public; Owner: macrostrat
CREATE INDEX lookup_small_map_id_idx ON public.lookup_small USING btree (map_id);

-- Name: lookup_small_strat_name_children_idx; Type: INDEX; Schema: public; Owner: macrostrat
CREATE INDEX lookup_small_strat_name_children_idx ON public.lookup_small USING gin (strat_name_children);

-- Name: lookup_tiny_concept_ids_idx; Type: INDEX; Schema: public; Owner: macrostrat
CREATE INDEX lookup_tiny_concept_ids_idx ON public.lookup_tiny USING gin (concept_ids);

-- Name: lookup_tiny_legend_id_idx; Type: INDEX; Schema: public; Owner: macrostrat
CREATE INDEX lookup_tiny_legend_id_idx ON public.lookup_tiny USING btree (legend_id);

-- Name: lookup_tiny_lith_ids_idx; Type: INDEX; Schema: public; Owner: macrostrat
CREATE INDEX lookup_tiny_lith_ids_idx ON public.lookup_tiny USING gin (lith_ids);

-- Name: lookup_tiny_map_id_idx; Type: INDEX; Schema: public; Owner: macrostrat
CREATE INDEX lookup_tiny_map_id_idx ON public.lookup_tiny USING btree (map_id);

-- Name: lookup_tiny_strat_name_children_idx; Type: INDEX; Schema: public; Owner: macrostrat
CREATE INDEX lookup_tiny_strat_name_children_idx ON public.lookup_tiny USING gin (strat_name_children);

-- Name: tile_cache_tile_last_used_idx; Type: INDEX; Schema: tile_cache; Owner: macrostrat
CREATE INDEX tile_cache_tile_last_used_idx ON tile_cache.tile USING btree (last_used);

-- Name: measuremeta_dataset_measuremeta_id_idx; Type: INDEX; Schema: weaver_macrostrat; Owner: macrostrat
CREATE INDEX measuremeta_dataset_measuremeta_id_idx ON weaver_macrostrat.measuremeta_dataset USING btree (measuremeta_id);

-- Name: large_geom_idx; Type: INDEX ATTACH; Schema: carto; Owner: macrostrat
ALTER INDEX carto.carto_polygons_geom_gist ATTACH PARTITION carto.large_geom_idx;

-- Name: medium_geom_idx; Type: INDEX ATTACH; Schema: carto; Owner: macrostrat
ALTER INDEX carto.carto_polygons_geom_gist ATTACH PARTITION carto.medium_geom_idx;

-- Name: polygons_large_map_id_scale_key; Type: INDEX ATTACH; Schema: carto; Owner: macrostrat
ALTER INDEX carto.polygons_unique ATTACH PARTITION carto.polygons_large_map_id_scale_key;

-- Name: polygons_large_pkey; Type: INDEX ATTACH; Schema: carto; Owner: macrostrat
ALTER INDEX carto.polygons_pkey ATTACH PARTITION carto.polygons_large_pkey;

-- Name: polygons_medium_map_id_scale_key; Type: INDEX ATTACH; Schema: carto; Owner: macrostrat
ALTER INDEX carto.polygons_unique ATTACH PARTITION carto.polygons_medium_map_id_scale_key;

-- Name: polygons_medium_pkey; Type: INDEX ATTACH; Schema: carto; Owner: macrostrat
ALTER INDEX carto.polygons_pkey ATTACH PARTITION carto.polygons_medium_pkey;

-- Name: polygons_small_map_id_scale_key; Type: INDEX ATTACH; Schema: carto; Owner: macrostrat
ALTER INDEX carto.polygons_unique ATTACH PARTITION carto.polygons_small_map_id_scale_key;

-- Name: polygons_small_pkey; Type: INDEX ATTACH; Schema: carto; Owner: macrostrat
ALTER INDEX carto.polygons_pkey ATTACH PARTITION carto.polygons_small_pkey;

-- Name: polygons_tiny_map_id_scale_key; Type: INDEX ATTACH; Schema: carto; Owner: macrostrat
ALTER INDEX carto.polygons_unique ATTACH PARTITION carto.polygons_tiny_map_id_scale_key;

-- Name: polygons_tiny_pkey; Type: INDEX ATTACH; Schema: carto; Owner: macrostrat
ALTER INDEX carto.polygons_pkey ATTACH PARTITION carto.polygons_tiny_pkey;

-- Name: small_geom_idx; Type: INDEX ATTACH; Schema: carto; Owner: macrostrat
ALTER INDEX carto.carto_polygons_geom_gist ATTACH PARTITION carto.small_geom_idx;

-- Name: tiny_geom_idx; Type: INDEX ATTACH; Schema: carto; Owner: macrostrat
ALTER INDEX carto.carto_polygons_geom_gist ATTACH PARTITION carto.tiny_geom_idx;

-- Name: large_b_interval_idx; Type: INDEX ATTACH; Schema: maps; Owner: macrostrat
ALTER INDEX maps.polygons_b_interval_idx ATTACH PARTITION maps.large_b_interval_idx;

-- Name: large_geom_idx; Type: INDEX ATTACH; Schema: maps; Owner: macrostrat
ALTER INDEX maps.polygons_geom_idx ATTACH PARTITION maps.large_geom_idx;

-- Name: large_name_idx; Type: INDEX ATTACH; Schema: maps; Owner: macrostrat
ALTER INDEX maps.polygons_name_idx ATTACH PARTITION maps.large_name_idx;

-- Name: large_orig_id_idx; Type: INDEX ATTACH; Schema: maps; Owner: macrostrat
ALTER INDEX maps.polygons_orig_id_idx ATTACH PARTITION maps.large_orig_id_idx;

-- Name: large_source_id_idx; Type: INDEX ATTACH; Schema: maps; Owner: macrostrat
ALTER INDEX maps.polygons_source_id_idx ATTACH PARTITION maps.large_source_id_idx;

-- Name: large_t_interval_idx; Type: INDEX ATTACH; Schema: maps; Owner: macrostrat
ALTER INDEX maps.polygons_t_interval_idx ATTACH PARTITION maps.large_t_interval_idx;

-- Name: lines_large_geom_idx; Type: INDEX ATTACH; Schema: maps; Owner: macrostrat
ALTER INDEX maps.lines_geom_idx ATTACH PARTITION maps.lines_large_geom_idx;

-- Name: lines_large_line_id_idx; Type: INDEX ATTACH; Schema: maps; Owner: macrostrat
ALTER INDEX maps.lines_line_id_idx ATTACH PARTITION maps.lines_large_line_id_idx;

-- Name: lines_large_orig_id_idx; Type: INDEX ATTACH; Schema: maps; Owner: macrostrat
ALTER INDEX maps.lines_orig_id_idx ATTACH PARTITION maps.lines_large_orig_id_idx;

-- Name: lines_large_pkey; Type: INDEX ATTACH; Schema: maps; Owner: macrostrat
ALTER INDEX maps.lines_pkey ATTACH PARTITION maps.lines_large_pkey;

-- Name: lines_large_source_id_idx; Type: INDEX ATTACH; Schema: maps; Owner: macrostrat
ALTER INDEX maps.lines_source_id_idx ATTACH PARTITION maps.lines_large_source_id_idx;

-- Name: lines_medium_geom_idx; Type: INDEX ATTACH; Schema: maps; Owner: macrostrat
ALTER INDEX maps.lines_geom_idx ATTACH PARTITION maps.lines_medium_geom_idx;

-- Name: lines_medium_line_id_idx; Type: INDEX ATTACH; Schema: maps; Owner: macrostrat
ALTER INDEX maps.lines_line_id_idx ATTACH PARTITION maps.lines_medium_line_id_idx;

-- Name: lines_medium_orig_id_idx; Type: INDEX ATTACH; Schema: maps; Owner: macrostrat
ALTER INDEX maps.lines_orig_id_idx ATTACH PARTITION maps.lines_medium_orig_id_idx;

-- Name: lines_medium_pkey; Type: INDEX ATTACH; Schema: maps; Owner: macrostrat
ALTER INDEX maps.lines_pkey ATTACH PARTITION maps.lines_medium_pkey;

-- Name: lines_medium_source_id_idx; Type: INDEX ATTACH; Schema: maps; Owner: macrostrat
ALTER INDEX maps.lines_source_id_idx ATTACH PARTITION maps.lines_medium_source_id_idx;

-- Name: lines_small_geom_idx; Type: INDEX ATTACH; Schema: maps; Owner: macrostrat
ALTER INDEX maps.lines_geom_idx ATTACH PARTITION maps.lines_small_geom_idx;

-- Name: lines_small_line_id_idx; Type: INDEX ATTACH; Schema: maps; Owner: macrostrat
ALTER INDEX maps.lines_line_id_idx ATTACH PARTITION maps.lines_small_line_id_idx;

-- Name: lines_small_orig_id_idx; Type: INDEX ATTACH; Schema: maps; Owner: macrostrat
ALTER INDEX maps.lines_orig_id_idx ATTACH PARTITION maps.lines_small_orig_id_idx;

-- Name: lines_small_pkey; Type: INDEX ATTACH; Schema: maps; Owner: macrostrat
ALTER INDEX maps.lines_pkey ATTACH PARTITION maps.lines_small_pkey;

-- Name: lines_small_source_id_idx; Type: INDEX ATTACH; Schema: maps; Owner: macrostrat
ALTER INDEX maps.lines_source_id_idx ATTACH PARTITION maps.lines_small_source_id_idx;

-- Name: lines_tiny_geom_idx; Type: INDEX ATTACH; Schema: maps; Owner: macrostrat
ALTER INDEX maps.lines_geom_idx ATTACH PARTITION maps.lines_tiny_geom_idx;

-- Name: lines_tiny_line_id_idx; Type: INDEX ATTACH; Schema: maps; Owner: macrostrat
ALTER INDEX maps.lines_line_id_idx ATTACH PARTITION maps.lines_tiny_line_id_idx;

-- Name: lines_tiny_orig_id_idx; Type: INDEX ATTACH; Schema: maps; Owner: macrostrat
ALTER INDEX maps.lines_orig_id_idx ATTACH PARTITION maps.lines_tiny_orig_id_idx;

-- Name: lines_tiny_pkey; Type: INDEX ATTACH; Schema: maps; Owner: macrostrat
ALTER INDEX maps.lines_pkey ATTACH PARTITION maps.lines_tiny_pkey;

-- Name: lines_tiny_source_id_idx; Type: INDEX ATTACH; Schema: maps; Owner: macrostrat
ALTER INDEX maps.lines_source_id_idx ATTACH PARTITION maps.lines_tiny_source_id_idx;

-- Name: maps_polygons_large_pkey; Type: INDEX ATTACH; Schema: maps; Owner: macrostrat
ALTER INDEX maps.maps_polygons_pkey ATTACH PARTITION maps.maps_polygons_large_pkey;

-- Name: maps_polygons_medium_pkey; Type: INDEX ATTACH; Schema: maps; Owner: macrostrat
ALTER INDEX maps.maps_polygons_pkey ATTACH PARTITION maps.maps_polygons_medium_pkey;

-- Name: maps_polygons_small_pkey; Type: INDEX ATTACH; Schema: maps; Owner: macrostrat
ALTER INDEX maps.maps_polygons_pkey ATTACH PARTITION maps.maps_polygons_small_pkey;

-- Name: maps_polygons_tiny_pkey; Type: INDEX ATTACH; Schema: maps; Owner: macrostrat
ALTER INDEX maps.maps_polygons_pkey ATTACH PARTITION maps.maps_polygons_tiny_pkey;

-- Name: medium_b_interval_idx; Type: INDEX ATTACH; Schema: maps; Owner: macrostrat
ALTER INDEX maps.polygons_b_interval_idx ATTACH PARTITION maps.medium_b_interval_idx;

-- Name: medium_geom_idx; Type: INDEX ATTACH; Schema: maps; Owner: macrostrat
ALTER INDEX maps.polygons_geom_idx ATTACH PARTITION maps.medium_geom_idx;

-- Name: medium_orig_id_idx; Type: INDEX ATTACH; Schema: maps; Owner: macrostrat
ALTER INDEX maps.polygons_orig_id_idx ATTACH PARTITION maps.medium_orig_id_idx;

-- Name: medium_source_id_idx; Type: INDEX ATTACH; Schema: maps; Owner: macrostrat
ALTER INDEX maps.polygons_source_id_idx ATTACH PARTITION maps.medium_source_id_idx;

-- Name: medium_t_interval_idx; Type: INDEX ATTACH; Schema: maps; Owner: macrostrat
ALTER INDEX maps.polygons_t_interval_idx ATTACH PARTITION maps.medium_t_interval_idx;

-- Name: polygons_medium_name_idx; Type: INDEX ATTACH; Schema: maps; Owner: macrostrat
ALTER INDEX maps.polygons_name_idx ATTACH PARTITION maps.polygons_medium_name_idx;

-- Name: polygons_small_name_idx; Type: INDEX ATTACH; Schema: maps; Owner: macrostrat
ALTER INDEX maps.polygons_name_idx ATTACH PARTITION maps.polygons_small_name_idx;

-- Name: polygons_tiny_name_idx; Type: INDEX ATTACH; Schema: maps; Owner: macrostrat
ALTER INDEX maps.polygons_name_idx ATTACH PARTITION maps.polygons_tiny_name_idx;

-- Name: small_b_interval_idx; Type: INDEX ATTACH; Schema: maps; Owner: macrostrat
ALTER INDEX maps.polygons_b_interval_idx ATTACH PARTITION maps.small_b_interval_idx;

-- Name: small_geom_idx; Type: INDEX ATTACH; Schema: maps; Owner: macrostrat
ALTER INDEX maps.polygons_geom_idx ATTACH PARTITION maps.small_geom_idx;

-- Name: small_orig_id_idx; Type: INDEX ATTACH; Schema: maps; Owner: macrostrat
ALTER INDEX maps.polygons_orig_id_idx ATTACH PARTITION maps.small_orig_id_idx;

-- Name: small_source_id_idx; Type: INDEX ATTACH; Schema: maps; Owner: macrostrat
ALTER INDEX maps.polygons_source_id_idx ATTACH PARTITION maps.small_source_id_idx;

-- Name: small_t_interval_idx; Type: INDEX ATTACH; Schema: maps; Owner: macrostrat
ALTER INDEX maps.polygons_t_interval_idx ATTACH PARTITION maps.small_t_interval_idx;

-- Name: tiny_b_interval_idx; Type: INDEX ATTACH; Schema: maps; Owner: macrostrat
ALTER INDEX maps.polygons_b_interval_idx ATTACH PARTITION maps.tiny_b_interval_idx;

-- Name: tiny_geom_idx; Type: INDEX ATTACH; Schema: maps; Owner: macrostrat
ALTER INDEX maps.polygons_geom_idx ATTACH PARTITION maps.tiny_geom_idx;

-- Name: tiny_orig_id_idx; Type: INDEX ATTACH; Schema: maps; Owner: macrostrat
ALTER INDEX maps.polygons_orig_id_idx ATTACH PARTITION maps.tiny_orig_id_idx;

-- Name: tiny_source_id_idx; Type: INDEX ATTACH; Schema: maps; Owner: macrostrat
ALTER INDEX maps.polygons_source_id_idx ATTACH PARTITION maps.tiny_source_id_idx;

-- Name: tiny_t_interval_idx; Type: INDEX ATTACH; Schema: maps; Owner: macrostrat
ALTER INDEX maps.polygons_t_interval_idx ATTACH PARTITION maps.tiny_t_interval_idx;

-- Name: user update_updated_on_trigger; Type: TRIGGER; Schema: macrostrat_auth; Owner: macrostrat
CREATE TRIGGER update_updated_on_trigger BEFORE UPDATE ON macrostrat_auth."user" FOR EACH ROW WHEN ((old.* IS DISTINCT FROM new.*)) EXECUTE FUNCTION public.update_updated_on();

-- Name: sources_meta maps_metadata_update_trigger; Type: TRIGGER; Schema: maps_metadata; Owner: kateakin
CREATE TRIGGER maps_metadata_update_trigger INSTEAD OF UPDATE ON maps_metadata.sources_meta FOR EACH ROW EXECUTE FUNCTION maps_metadata.maps_metadata_update_trigger();

-- Name: lines lines_source_id_fkey; Type: FK CONSTRAINT; Schema: carto; Owner: macrostrat
ALTER TABLE carto.lines
    ADD CONSTRAINT lines_source_id_fkey FOREIGN KEY (source_id) REFERENCES maps.sources(source_id);

-- Name: polygons polygons_source_id_fkey; Type: FK CONSTRAINT; Schema: carto; Owner: macrostrat
ALTER TABLE carto.polygons
    ADD CONSTRAINT polygons_source_id_fkey FOREIGN KEY (source_id) REFERENCES maps.sources(source_id);

-- Name: ingest_process ingest_process_group_id_fkey; Type: FK CONSTRAINT; Schema: macrostrat; Owner: macrostrat
ALTER TABLE ONLY macrostrat.ingest_process
    ADD CONSTRAINT ingest_process_group_id_fkey FOREIGN KEY (group_id) REFERENCES macrostrat_auth."group"(id);

-- Name: ingest_process ingest_process_object_id_fkey; Type: FK CONSTRAINT; Schema: macrostrat; Owner: macrostrat
ALTER TABLE ONLY macrostrat.ingest_process
    ADD CONSTRAINT ingest_process_object_id_fkey FOREIGN KEY (object_id) REFERENCES macrostrat.objects(id);

-- Name: group_members group_members_group_id_fkey; Type: FK CONSTRAINT; Schema: macrostrat_auth; Owner: macrostrat
ALTER TABLE ONLY macrostrat_auth.group_members
    ADD CONSTRAINT group_members_group_id_fkey FOREIGN KEY (group_id) REFERENCES macrostrat_auth."group"(id);

-- Name: group_members group_members_user_id_fkey; Type: FK CONSTRAINT; Schema: macrostrat_auth; Owner: macrostrat
ALTER TABLE ONLY macrostrat_auth.group_members
    ADD CONSTRAINT group_members_user_id_fkey FOREIGN KEY (user_id) REFERENCES macrostrat_auth."user"(id);

-- Name: token token_group_fkey; Type: FK CONSTRAINT; Schema: macrostrat_auth; Owner: macrostrat
ALTER TABLE ONLY macrostrat_auth.token
    ADD CONSTRAINT token_group_fkey FOREIGN KEY ("group") REFERENCES macrostrat_auth."group"(id);

-- Name: lines lines_source_id_fkey; Type: FK CONSTRAINT; Schema: maps; Owner: macrostrat
ALTER TABLE maps.lines
    ADD CONSTRAINT lines_source_id_fkey FOREIGN KEY (source_id) REFERENCES maps.sources(source_id);

-- Name: points points_source_id_fkey; Type: FK CONSTRAINT; Schema: maps; Owner: macrostrat
ALTER TABLE ONLY maps.points
    ADD CONSTRAINT points_source_id_fkey FOREIGN KEY (source_id) REFERENCES maps.sources(source_id);

-- Name: polygons polygons_source_id_fkey; Type: FK CONSTRAINT; Schema: maps; Owner: macrostrat
ALTER TABLE maps.polygons
    ADD CONSTRAINT polygons_source_id_fkey FOREIGN KEY (source_id) REFERENCES maps.sources(source_id);

-- Name: source_operations source_operations_source_id_fkey; Type: FK CONSTRAINT; Schema: maps; Owner: macrostrat
ALTER TABLE ONLY maps.source_operations
    ADD CONSTRAINT source_operations_source_id_fkey FOREIGN KEY (source_id) REFERENCES maps.sources(source_id) ON DELETE CASCADE;

-- Name: source_operations source_operations_user_id_fkey; Type: FK CONSTRAINT; Schema: maps; Owner: macrostrat
ALTER TABLE ONLY maps.source_operations
    ADD CONSTRAINT source_operations_user_id_fkey FOREIGN KEY (user_id) REFERENCES macrostrat_auth."user"(id) ON DELETE SET NULL;

-- Name: tile tile_profile_fkey; Type: FK CONSTRAINT; Schema: tile_cache; Owner: macrostrat
ALTER TABLE ONLY tile_cache.tile
    ADD CONSTRAINT tile_profile_fkey FOREIGN KEY (profile) REFERENCES tile_cache.profile(name);

-- Name: tile tile_tms_fkey; Type: FK CONSTRAINT; Schema: tile_cache; Owner: macrostrat
ALTER TABLE ONLY tile_cache.tile
    ADD CONSTRAINT tile_tms_fkey FOREIGN KEY (tms) REFERENCES tile_utils.tms_definition(name);

-- Name: tms_definition tms_definition_geographic_srid_fkey; Type: FK CONSTRAINT; Schema: tile_utils; Owner: macrostrat
ALTER TABLE ONLY tile_utils.tms_definition
    ADD CONSTRAINT tms_definition_geographic_srid_fkey FOREIGN KEY (geographic_srid) REFERENCES public.spatial_ref_sys(srid);

-- Name: measuremeta_dataset measuremeta_dataset_dataset_id_fkey; Type: FK CONSTRAINT; Schema: weaver_macrostrat; Owner: macrostrat
ALTER TABLE ONLY weaver_macrostrat.measuremeta_dataset
    ADD CONSTRAINT measuremeta_dataset_dataset_id_fkey FOREIGN KEY (dataset_id) REFERENCES weaver.dataset(id) ON DELETE CASCADE;

-- PostgreSQL database dump complete
