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

IF _t_step = 0 THEN
  /* Just return the basic map layer */
  return tile_layers.carto_slim(x, y, z, query_params);
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
    corelle_macrostrat.rotate_to_web_mercator(geometry, rotation, true) geom_merc,
    corelle.rotate_geometry(
      projected_bbox,
      corelle.invert_rotation(rc.rotation)
    ) tile_geom,
    rc.rotation
  FROM corelle.plate_polygon pp
  JOIN corelle.rotation_cache rc
    ON rc.model_id = pp.model_id
    AND rc.plate_id = pp.plate_id
  WHERE rc.t_step = _t_step
    AND pp.model_id = _model_id
    AND coalesce(pp.old_lim, 4000) >= _t_step
    AND coalesce(pp.young_lim, 0) <= _t_step
  -- AND (z < 3 OR ST_Intersects(corelle_macrostrat.tile_envelope(rotation, x, y, z)::geography, geometry::geography))
),
relevant_plates AS (
  SELECT
    plate_id,
    model_id,
    plate_polygon_id,
    geom_merc,
    rotation,
    tile_geom
  FROM rotated_plates
  WHERE ST_Intersects(geom_merc, mercator_bbox)
),
units AS (
  -- We need this distinct because we have duplicates somewhere in our pipeline
  SELECT  -- DISTINCT ON (u.map_id, u.source_id, cpi.plate_id, cpi.plate_polygon_id)
    u.map_id,
    u.source_id,
    cpi.plate_id,
    rp.rotation,
    rp.tile_geom,
    cpi.plate_polygon_id,
    coalesce(cpi.geom, u.geom) geom
  FROM relevant_plates rp
  JOIN corelle_macrostrat.carto_plate_index cpi
    ON cpi.plate_polygon_id = rp.plate_polygon_id
   AND cpi.scale = _scale
  JOIN carto.polygons u
    ON u.map_id = cpi.map_id
   AND u.scale = _scale
   -- This causes tile-boundary errors
       -- We have to break this out because we get weird antipodal-edge warnings otherwise
),
units2 AS (
  -- We need this distinct because we have duplicates somewhere in our pipeline
  SELECT  -- DISTINCT ON (u.map_id, u.source_id, cpi.plate_id, cpi.plate_polygon_id)
    *,
    corelle_macrostrat.rotate_to_web_mercator(
       u.geom,
       u.rotation,
       true
    ) geom_merc
  FROM units u
   -- This causes tile-boundary errors
       -- We have to break this out because we get weird antipodal-edge warnings otherwise
  WHERE z < 3 OR ST_Intersects(ST_Envelope(u.geom)::geography, tile_geom::geography)
),
bedrock_ AS (
  SELECT
    u.map_id,
    u.source_id,
    u.plate_id,
    u.plate_polygon_id,
    l.*, -- legend info
    tile_layers.tile_geom(
      u.geom_merc,
      mercator_bbox
    ) geom
  FROM units2 u
  JOIN maps.map_legend
    ON u.map_id = map_legend.map_id
  JOIN tile_layers.map_legend_info AS l
    ON l.legend_id = map_legend.legend_id
  WHERE ST_Intersects(u.geom_merc, mercator_bbox)
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
$$ LANGUAGE plpgsql VOLATILE;