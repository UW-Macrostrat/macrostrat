CREATE SCHEMA IF NOT EXISTS corelle_macrostrat;

--DROP MATERIALIZED VIEW IF EXISTS corelle_macrostrat.carto_plate_index;

CREATE MATERIALIZED VIEW IF NOT EXISTS corelle_macrostrat.natural_earth_index AS
SELECT
  f.id,
  properties ->> 'scalerank' AS scalerank,
  ST_Intersection(f.geometry, pp.geometry) geometry,
  model_id,
  plate_id
FROM corelle.feature f
JOIN corelle.plate_polygon pp
  ON ST_Intersects(f.geometry, pp.geometry)
WHERE dataset_id = 'ne_110m_land';

CREATE MATERIALIZED VIEW IF NOT EXISTS corelle_macrostrat.column_index AS
SELECT
	col_id,
	model_id,
	plate_id
FROM macrostrat.col_areas c
JOIN corelle.plate_polygon pp
  ON ST_Intersects(ST_Centroid(col_area), pp.geometry);

CREATE MATERIALIZED VIEW IF NOT EXISTS corelle_macrostrat.carto_plate_index AS
WITH map_units AS (
  SELECT
    map_id,
    'tiny' scale,
    geom
  FROM maps.tiny
  UNION ALL
  SELECT
    map_id,
    'small' scale,
    geom
  FROM maps.small
)
SELECT
	p.map_id,
	p.scale,
	m.id model_id,
	pp.plate_id,
	CASE WHEN ST_Covers(pp.geometry, p.geom) THEN
		NULL  
	ELSE
		ST_Intersection(pp.geometry, p.geom)
	END AS geom
FROM map_units p
JOIN corelle.plate_polygon pp
  ON ST_Intersects(pp.geometry, p.geom)
JOIN corelle.model m
  ON m.id = pp.model_id;

CREATE OR REPLACE FUNCTION corelle_macrostrat.carto_slim_rotated_v1(
  -- bounding box
  x integer,
  y integer,
  z integer,
  -- additional parameters
  query_params json
)
RETURNS bytea
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
$$ LANGUAGE plpgsql VOLATILE;


CREATE OR REPLACE FUNCTION corelle_macrostrat.tile_envelope(
  rotation numeric[],
  x integer,
  y integer,
  z integer
) RETURNS geometry AS $$
    -- I feel like this bbox needs to be inverted but it seems to work better if not...
  SELECT corelle_macrostrat.rotate(
    --ST_Transform(mercator_bbox, 4326),
    ST_Transform(ST_Segmentize(tile_utils.envelope(x, y, z), tile_utils.tile_width(z)/8), 4326),
    corelle.invert_rotation(rotation),
    true
  );
$$ LANGUAGE sql STABLE;

CREATE OR REPLACE FUNCTION corelle_macrostrat.build_tile_geom(
  geom geometry,
  rotation numeric[],
  _x integer,
  _y integer,
  _z integer
)
RETURNS geometry
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
$$ LANGUAGE plpgsql STABLE; 

CREATE OR REPLACE FUNCTION corelle_macrostrat.rotate(
  geom geometry,
  rotation double precision[],
  wrap boolean DEFAULT false
) RETURNS geometry AS $$
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
  IF wrap AND ST_XMin(g1) < -150 AND ST_XMax(g1) > 150 THEN
    g1 := ST_WrapX(
      ST_Split(
        ST_MakeValid(ST_ShiftLongitude(g1)),
        -- Antimeridian
        ST_GeomFromText('LINESTRING(180 -90, 180 90)', 4326)
      ),
      180,
      -360
    );
  END IF;
  RETURN g1;
END;
$$ LANGUAGE plpgsql STABLE;

-- Drop outdated functions
--DROP FUNCTION IF EXISTS corelle_macrostrat.rotate(geometry, numeric[], boolean);
DROP FUNCTION IF EXISTS corelle_macrostrat.rotated_web_mercator_proj(numeric[]);



CREATE OR REPLACE FUNCTION corelle_macrostrat.carto_slim_rotated(
  -- bounding box
  x integer,
  y integer,
  z integer,
  -- additional parameters
  query_params json
)
RETURNS bytea
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
    pp.plate_id,
    pp.model_id,
    -- Get the tile bounding box rotated to the actual position of the plate on the modern globe
    corelle_macrostrat.tile_envelope(rc.rotation, x, y, z) tile_envelope,
    geometry,
    rc.rotation rotation
  FROM corelle.plate_polygon pp
  JOIN corelle.rotation_cache rc
    ON rc.plate_id = pp.plate_id
    AND rc.model_id = pp.model_id
  WHERE rc.model_id = _model_id
    AND rc.t_step = _t_step
    AND coalesce(pp.old_lim, 4000) >= _t_step
    AND coalesce(pp.young_lim, 0) <= _t_step
    AND corelle_macrostrat.tile_envelope(rc.rotation, x, y, z) && pp.geometry
    AND ST_Intersects(corelle_macrostrat.tile_envelope(rc.rotation, x, y, z), pp.geometry)
),
units AS (
  SELECT
    u.map_id,
    u.source_id,
    cpi.plate_id,
    cpi.model_id,
    corelle_macrostrat.build_tile_geom(
      u.geom, ri.rotation, x, y, z
    ) geom,
    l.legend_id,
    l.best_age_top :: numeric AS best_age_top,
    l.best_age_bottom :: numeric AS best_age_bottom,
    coalesce(l.color, '#777777') AS color,
    l.lith_classes [1] AS lith_class1,
    l.lith_classes [2] AS lith_class2,
    l.lith_classes [3] AS lith_class3,
    l.lith_types [1] AS lith_type1,
    l.lith_types [2] AS lith_type2,
    l.lith_types [3] AS lith_type3,
    l.lith_types [4] AS lith_type4,
    l.lith_types [5] AS lith_type5,
    l.lith_types [6] AS lith_type6,
    l.lith_types [7] AS lith_type7,
    l.lith_types [8] AS lith_type8,
    l.lith_types [9] AS lith_type9,
    l.lith_types [10] AS lith_type10,
    l.lith_types [11] AS lith_type11,
    l.lith_types [12] AS lith_type12,
    l.lith_types [13] AS lith_type13,
    l.all_lith_classes [1] AS lith_class1,
    l.all_lith_classes [2] AS lith_class2,
    l.all_lith_classes [3] AS lith_class3,
    l.all_lith_types [1] AS lith_type1,
    l.all_lith_types [2] AS lith_type2,
    l.all_lith_types [3] AS lith_type3,
    l.all_lith_types [4] AS lith_type4,
    l.all_lith_types [5] AS lith_type5,
    l.all_lith_types [6] AS lith_type6,
    l.all_lith_types [7] AS lith_type7,
    l.all_lith_types [8] AS lith_type8,
    l.all_lith_types [9] AS lith_type9,
    l.all_lith_types [10] AS lith_type10,
    l.all_lith_types [11] AS lith_type11,
    l.all_lith_types [12] AS lith_type12,
    l.all_lith_types [13] AS lith_type13
  FROM tile_layers.carto_units u
  JOIN corelle_macrostrat.carto_plate_index cpi
    ON cpi.map_id = u.map_id
    AND cpi.scale = u.scale
    AND cpi.model_id = _model_id
  JOIN rotation_info ri
    ON ri.plate_id = cpi.plate_id
  LEFT JOIN maps.map_legend ON u.map_id = map_legend.map_id
  LEFT JOIN maps.legend AS l ON l.legend_id = map_legend.legend_id
  LEFT JOIN maps.sources ON l.source_id = sources.source_id
  WHERE u.geom && ri.tile_envelope
    AND u.scale = mapsize
    AND sources.status_code = 'active'
    AND l.best_age_top >= _t_step
),
-- ),
plate_polygons AS (
  SELECT
    plate_id,
    _t_step t_step,
    corelle_macrostrat.build_tile_geom(
      ri.geometry, ri.rotation, x, y, z
    ) geom
  FROM rotation_info ri
),
land1 AS (
  SELECT
    corelle_macrostrat.build_tile_geom(
      ix.geometry, ri.rotation, x, y, z
    ) geom
  FROM corelle_macrostrat.natural_earth_index ix
  JOIN rotation_info ri
    ON ri.plate_id = ix.plate_id
   AND ri.model_id = ix.model_id
  WHERE ix.geometry && ri.tile_envelope
    --AND ST_Intersects(ix.geometry, ri.tile_envelope)
),
columns AS (
  SELECT DISTINCT ON (col_id)
    corelle_macrostrat.build_tile_geom(
      ca.col_area, ri.rotation, x, y, z
    ) geom,
    u.col_id,
    u.id unit_id,
    ri.model_id,
    ri.plate_id,
    u.strat_name,
    nullif(outcrop, '') outcrop,
    t_age,
    b_age,
    u.color,
    u1.color color1
  FROM corelle_macrostrat.column_index c
  JOIN rotation_info ri
    ON ri.plate_id = c.plate_id
   AND ri.model_id = c.model_id
  JOIN macrostrat.col_areas ca
    ON ca.col_id = c.col_id
  JOIN macrostrat.units u
    ON u.col_id = c.col_id
  JOIN macrostrat.lookup_units u1
    ON u1.unit_id = u.id
  WHERE ca.col_area && ri.tile_envelope
    AND t_age <= _t_step
    AND b_age >= _t_step
  ORDER BY col_id, max_thick DESC
),
u1 AS (
  SELECT ST_AsMVT(pp, 'plates') mvt1
  FROM plate_polygons pp
),
u2 AS (
  SElECT ST_AsMVT(units, 'units') mvt2
  FROM units
),
u3 AS (
  SELECT ST_AsMVT(land, 'land') mvt3
  FROM land1 land
)
-- u4 AS (
--   SELECT ST_AsMVT(cols, 'columns') mvt4
--   FROM columns cols
-- )
SELECT mvt1 || mvt2 || mvt3 AS mvt
FROM u1, u2, u3
INTO bedrock; --, plate_polygons;

RETURN bedrock;

END;
$$ LANGUAGE plpgsql STABLE PARALLEL SAFE;

CREATE OR REPLACE FUNCTION corelle_macrostrat.tile_envelope(
  rotation numeric[],
  x integer,
  y integer,
  z integer
) RETURNS geometry AS $$
  SELECT corelle_macrostrat.rotate(
    --ST_Transform(mercator_bbox, 4326),
    ST_Transform(ST_Segmentize(tile_utils.envelope(x, y, z), tile_utils.tile_width(z)/8), 4326),
    corelle.invert_rotation(rotation),
    false
  );
$$ LANGUAGE sql STABLE PARALLEL SAFE;

CREATE OR REPLACE FUNCTION corelle_macrostrat.build_tile_geom(
  geom geometry,
  rotation numeric[],
  _x integer,
  _y integer,
  _z integer
)
RETURNS geometry
AS $$
DECLARE
  mercator_bbox geometry;
  proj4text text;
  proj_additions text;
  wrap numeric = 0;
  tile_geom geometry;
  tms_width numeric;
  meridian geometry;
  shifted geometry;
BEGIN
  mercator_bbox := tile_utils.envelope(_x,_y,_z);
  tms_width := tile_utils.tile_width(0);

  -- Pre-simplify the geometry to reduce the size of the tile
  geom := ST_SnapToGrid(geom, 0.001/pow(2,_z));

  IF true THEN
    tile_geom := ST_Transform(corelle_macrostrat.rotate(geom, rotation, true), 3857);
  ELSE
    proj4text := corelle.build_proj_string(
      rotation,
      '+o_proj=merc +R=6378137 +over'
    );
    tile_geom := ST_SetSRID(ST_Transform(geom, proj4text), 3857); 
  END IF;

  RETURN ST_Simplify(
    ST_AsMVTGeom(
      tile_geom,
      mercator_bbox,
      4096,
      12,
      true
    ),
    8
  );
END;
$$ LANGUAGE plpgsql STABLE PARALLEL SAFE;

CREATE OR REPLACE FUNCTION corelle_macrostrat.rotate(
  geom geometry,
  rotation double precision[],
  wrap boolean DEFAULT false
) RETURNS geometry AS $$
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
  IF wrap AND ST_XMin(g1) < -150 AND ST_XMax(g1) > 150 THEN
    g1 := ST_WrapX(
      ST_Split(
        ST_MakeValid(ST_ShiftLongitude(g1)),
        -- Antimeridian
        ST_GeomFromText('LINESTRING(180 -90, 180 90)', 4326)
      ),
      180,
      -360
    );
  END IF;
  RETURN g1;
END;
$$ LANGUAGE plpgsql STABLE;

-- Drop outdated functions
DROP FUNCTION IF EXISTS corelle_macrostrat.rotate(geometry, numeric[], boolean);
DROP FUNCTION IF EXISTS corelle_macrostrat.rotated_web_mercator_proj(numeric[]);