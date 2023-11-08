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
plates bytea;
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

WITH plates_basic AS (
  SELECT
    rc.plate_id,
    rc.model_id,
    -- Get the tile bounding box rotated to the actual position of the plate on the modern globe
    --ST_Area(corelle_macrostrat.tile_envelope(rc.rotation, t.x, t.y, t.z)::geography)/ST_Area(ST_Transform(tile_utils.envelope(t.x, t.y, t.z), 4326)::geography) tile_area_ratio,
    corelle_macrostrat.rotate(geom_simple, rotation, true) geom
    -- corelle.rotate_geometry(
    --   projected_bbox,
    --   rc.rotation
    -- ) tile_geom,
    -- rc.rotation rotation
  FROM corelle.rotation_cache rc
  JOIN corelle.plate_polygon pp
    ON pp.plate_id = rc.plate_id
    AND pp.model_id = rc.model_id
  WHERE rc.model_id = _model_id
    AND rc.t_step = _t_step
),
plates_ AS (
  SELECT
    plate_id,
    model_id,
    tile_layers.tile_geom(ST_Intersection(u.geom, projected_bbox), mercator_bbox) AS geom
  FROM plates_basic u
  WHERE ST_Intersects(u.geom, projected_bbox)

) 
SELECT ST_AsMVT(plates_, 'plates') INTO plates FROM plates_;

WITH rotation_info AS (
  SELECT
    rc.plate_id,
    rc.model_id,
    rc.geom rotated_plate_geom,
    rc.rotation rotation
  FROM corelle.plate_polygon pp
  JOIN corelle.rotation_cache rc
    ON rc.plate_id = pp.plate_id
    AND rc.model_id = pp.model_id
    AND rc.t_step = _t_step
    AND coalesce(pp.old_lim, 4000) >= _t_step
    AND coalesce(pp.young_lim, 0) <= _t_step
   AND pp.model_id = _model_id
),
relevant_plates AS (
  SELECT *,
    corelle_macrostrat.tile_envelope(rotation, x, y, z) tile_geom
  FROM rotation_info
  WHERE ST_Intersects(rotated_plate_geom, projected_bbox)
),
units AS (
  SELECT 
    u.map_id,
    u.source_id,
    cpi.plate_id,
    rp.rotation,
    rp.tile_geom,
    coalesce(cpi.geom, u.geom) geom
  FROM relevant_plates rp
  --JOIN tile ON true
  -- Right now we pre-cache tile intersections but we could probably skip this
  JOIN corelle_macrostrat.carto_plate_index cpi
    ON cpi.plate_id = rp.plate_id
   AND cpi.model_id = rp.model_id
   AND cpi.scale = _scale
  JOIN carto.polygons u
    ON u.map_id = cpi.map_id
   AND u.scale = _scale
), expanded AS (
  SELECT
    u.map_id,
    u.source_id,
    u.plate_id,
    l.*, -- legend info
    corelle_macrostrat.build_tile_geom(
      u.geom, u.rotation, x, y, z
    ) geom
  FROM units u
  --JOIN tile ON true
  LEFT JOIN maps.map_legend
    ON u.map_id = map_legend.map_id
  LEFT JOIN tile_layers.map_legend_info AS l
    ON l.legend_id = map_legend.legend_id
  WHERE ST_Intersects(u.geom, u.tile_geom)
  -- WHERE (z < 3 AND ST_Intersects(u.geom, u.tile_geom))
  --   -- We have to break this out because we get weird antipodal-edge warnings otherwise
  --   OR (z >= 3 AND ST_Intersects(u.geom::geography, u.tile_geom::geography))
)
SELECT null INTO bedrock;
--   ST_AsMVT(expanded, 'units')
-- INTO bedrock
-- FROM expanded;

RETURN plates;

END;
$$ LANGUAGE plpgsql VOLATILE;