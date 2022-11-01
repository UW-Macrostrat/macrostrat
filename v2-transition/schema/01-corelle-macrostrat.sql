CREATE SCHEMA IF NOT EXISTS corelle_macrostrat;

--DROP MATERIALIZED VIEW IF EXISTS corelle_macrostrat.carto_plate_index;

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


mercator_bbox := tile_utils.envelope(x, y, z);

projected_bbox := ST_Transform(
  mercator_bbox,
  4326
);

min_feature_size := ST_Area(projected_bbox) / 10000;

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
  SELECT DISTINCT ON (pp.plate_id)
    pp.plate_id,
    -- Get the tile bounding box rotated to the actual position of the plate on the modern globe
    corelle.rotate_geometry(projected_bbox, corelle.invert_rotation(rc.rotation)) AS tile_envelope,
    rc.rotation rotation
  FROM corelle.plate_polygon pp
  JOIN corelle.rotation_cache rc
    ON rc.plate_id = pp.plate_id
    AND rc.t_step = _t_step
    AND rc.model_id = _model_id
  WHERE ST_Intersects(geometry, projected_bbox)
),
mvt_features AS (
  SELECT
    u.map_id,
    u.source_id,
    cpi.plate_id,
    cpi.model_id,
    ST_AsMVTGeom(
      ST_Transform(
        corelle.rotate_geometry(
          coalesce(cpi.geom, u.geom),
          ri.rotation
        ),
        3857
      ),
      mercator_bbox,
      4096
    ) geom
  FROM tile_layers.carto_units u
  JOIN corelle_macrostrat.carto_plate_index cpi
    ON cpi.map_id = u.map_id
    AND cpi.scale = u.scale
    AND cpi.model_id = _model_id
  JOIN rotation_info ri
    ON ri.plate_id = cpi.plate_id
  WHERE
    ST_Intersects(coalesce(cpi.geom, u.geom), ri.tile_envelope)
    AND u.scale = mapsize
    AND ST_Area(coalesce(cpi.geom, u.geom)) > min_feature_size
), expanded AS (
  SELECT
    z.plate_id,
    z.model_id,
    z.map_id,
    z.source_id,
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
    l.all_lith_types [13] AS lith_type13,
    ST_Simplify(z.geom, 2) AS geom
  FROM
    mvt_features z
    LEFT JOIN maps.map_legend ON z.map_id = map_legend.map_id
    LEFT JOIN maps.legend AS l ON l.legend_id = map_legend.legend_id
    LEFT JOIN maps.sources ON l.source_id = sources.source_id
  WHERE
    sources.status_code = 'active'
    AND ST_Area(geom) > 2
)
SELECT
  ST_AsMVT(expanded, 'units')
INTO bedrock
FROM expanded;

RETURN bedrock;

END;
$$ LANGUAGE plpgsql IMMUTABLE;