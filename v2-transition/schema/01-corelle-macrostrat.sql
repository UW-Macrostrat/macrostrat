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
projected_bbox geometry;
min_feature_size numeric;
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


mercator_bbox := tile_utils.envelope(x,y,z);

projected_bbox := ST_Envelope(ST_Transform(
  mercator_bbox,
  4326
));

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
WITH rotation_info AS (
  SELECT
    pp.plate_id,
    pp.model_id,
    -- Get the tile bounding box rotated to the actual position of the plate on the modern globe
    ST_MakeValid(ST_WrapX(ST_Envelope(corelle.rotate_geometry(projected_bbox, corelle.invert_rotation(rc.rotation))), -180, 180)) AS tile_envelope,
    geometry,
    rc.rotation rotation
  FROM corelle.plate_polygon pp
  JOIN corelle.rotation_cache rc
    ON rc.plate_id = pp.plate_id
    AND rc.model_id = pp.model_id
  WHERE ST_Intersects(geometry, ST_MakeValid(ST_WrapX(ST_Envelope(corelle.rotate_geometry(projected_bbox, corelle.invert_rotation(rc.rotation))), -180, 180)))
    AND rc.model_id = _model_id
    AND rc.t_step = _t_step
),
units AS (
  SELECT
    u.map_id,
    u.source_id,
    cpi.plate_id,
    cpi.model_id,
    ST_Simplify(ST_AsMVTGeom(
      ST_Transform(
        corelle.rotate_geometry(
          coalesce(cpi.geom, u.geom),
          ri.rotation
        ),
        3857
      ),
      mercator_bbox,
      4096,
      12,
      true
    ), 2) geom,
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
  WHERE
    ST_Intersects(coalesce(cpi.geom, u.geom), ri.tile_envelope)
    AND u.scale = mapsize
    AND sources.status_code = 'active'
    AND ST_Area(coalesce(cpi.geom, u.geom)) > ST_Area(ri.tile_envelope) / 50000
    AND l.best_age_top >= _t_step
),
-- ),
plate_polygons AS (
  SELECT
    plate_id,
    _t_step t_step,
    ST_AsMVTGeom(
      ST_Transform(
        corelle.rotate_geometry(
         ST_Intersection(ri.geometry, ri.tile_envelope),
          rotation
        ),
        3857
      ),
      mercator_bbox,
      4096,
      12,
      true
    ) geom
  FROM rotation_info ri
),
land1 AS (
  SELECT
    ST_AsMVTGeom(
      ST_Transform(
        corelle.rotate_geometry(
          ix.geometry,
          ri.rotation
        ),
        3857
      ),
      mercator_bbox,
      4096,
      12,
      true
    ) geom
  FROM corelle_macrostrat.natural_earth_index ix
  JOIN rotation_info ri
    ON ri.plate_id = ix.plate_id
   AND ri.model_id = ix.model_id
  WHERE ST_Intersects(ix.geometry, ri.tile_envelope)
),
columns AS (
  SELECT DISTINCT ON (col_id)
    ST_AsMVTGeom(
      ST_Transform(
        corelle.rotate_geometry(
          ca.col_area,
          ri.rotation
        ),
        3857
      ),
      mercator_bbox,
      4096,
      12,
      true
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
  WHERE ST_Intersects(ca.col_area, ri.tile_envelope)
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
),
u4 AS (
  SELECT ST_AsMVT(cols, 'columns') mvt4
  FROM columns cols
)
SELECT mvt1 || mvt2 || mvt3 || mvt4 AS mvt
FROM u1, u2, u3, u4
INTO bedrock; --, plate_polygons;

RETURN bedrock;

END;
$$ LANGUAGE plpgsql IMMUTABLE;