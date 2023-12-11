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
linesize text[];
mercator_bbox geometry;
projected_bbox geometry;
bedrock bytea;
result bytea;
lines bytea;
tolerance double precision;
_t_step integer;
_model_id integer;
_scale map_scale;

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

WITH rotated_plates AS (
  SELECT DISTINCT ON (plate_id, model_id, geometry)
    pp.plate_id,
    pp.model_id,
    corelle_macrostrat.rotate_to_web_mercator(geom_simple, rotation, true) geom,
    rc.rotation
  FROM corelle.plate_polygon pp
  JOIN corelle.rotation_cache rc
   ON rc.model_id = pp.model_id
  AND rc.plate_id = pp.plate_id
  AND rc.t_step = _t_step
  AND pp.model_id = _model_id
  AND coalesce(pp.old_lim, 4000) >= _t_step
  AND coalesce(pp.young_lim, 0) <= _t_step
  -- AND (z < 3 OR ST_Intersects(corelle_macrostrat.tile_envelope(rotation, x, y, z)::geography, geometry::geography))
),
relevant_plates AS (
  SELECT
    plate_id,
    model_id,
    geom,
    rotation,
    corelle_macrostrat.tile_envelope(rotation, x, y, z) tile_geom
  FROM rotated_plates
  WHERE ST_Intersects(geom, mercator_bbox)
),
-- units AS (
--   SELECT 
--     u.map_id,
--     u.source_id,
--     cpi.plate_id,
--     rp.rotation,
--     rp.tile_geom,
--     coalesce(cpi.geom, u.geom) geom
--   FROM relevant_plates rp
--   --JOIN tile ON true
--   -- Right now we pre-cache tile intersections but we could probably skip this
--   JOIN corelle_macrostrat.carto_plate_index cpi
--     ON cpi.plate_id = rp.plate_id
--    AND cpi.model_id = rp.model_id
--    AND cpi.scale = _scale
--   JOIN carto.polygons u
--     ON u.map_id = cpi.map_id
--    AND u.scale = _scale
-- ),
-- bedrock_ AS (
--   SELECT
--     u.map_id,
--     u.source_id,
--     u.plate_id,
--     l.*, -- legend info
--     tile_layers.tile_geom(
--       corelle_macrostrat.rotate_to_web_mercator(u.geom, u.rotation),
--       mercator_bbox
--     ) geom
--   FROM units u
--   --JOIN tile ON true
--   LEFT JOIN maps.map_legend
--     ON u.map_id = map_legend.map_id
--   LEFT JOIN tile_layers.map_legend_info AS l
--     ON l.legend_id = map_legend.legend_id
--   WHERE ST_Intersects(u.geom, u.tile_geom)
--   -- WHERE (z < 3 AND ST_Intersects(u.geom, u.tile_geom))
--   --   -- We have to break this out because we get weird antipodal-edge warnings otherwise
--   --   OR (z >= 3 AND ST_Intersects(u.geom::geography, u.tile_geom::geography))
-- ),
plates_ AS (
  SELECT
    plate_id,
    model_id,
    tile_layers.tile_geom(geom, mercator_bbox) AS geom
  FROM relevant_plates
)
SELECT ST_AsMVT(plates_, 'plates') -- || ST_AsMVT(bedrock_, 'units')
INTO result
FROM plates_;

RETURN result;

END;
$$ LANGUAGE plpgsql VOLATILE;