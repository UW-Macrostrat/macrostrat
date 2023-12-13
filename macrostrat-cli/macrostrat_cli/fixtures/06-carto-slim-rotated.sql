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
  WHERE geom_merc && mercator_bbox
),
land1 AS (
  SELECT
    corelle_macrostrat.rotate_to_web_mercator(
       ix.geometry,
       ri.rotation,
       TRUE
    ) geom
  FROM corelle_macrostrat.natural_earth_index ix
  JOIN relevant_plates ri
    ON ri.plate_id = ix.plate_id
   AND ri.model_id = ix.model_id
  WHERE ix.geometry && ri.tile_geom
),
land AS (
  SELECT
    tile_layers.tile_geom(geom, mercator_bbox) geom
  FROM land1
  WHERE ST_Intersects(geom, mercator_bbox)
),
columns AS (
  SELECT DISTINCT ON (col_id)
    tile_layers.tile_geom(
      corelle_macrostrat.rotate_to_web_mercator(
        ST_CollectionExtract(ca.col_area, 3),
        ri.rotation,
        true
      ),
      mercator_bbox
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
  JOIN relevant_plates ri
    ON ri.plate_id = c.plate_id
   AND ri.model_id = c.model_id
  JOIN macrostrat.col_areas ca
    ON ca.col_id = c.col_id
  JOIN macrostrat.units u
    ON u.col_id = c.col_id
  JOIN macrostrat.lookup_units u1
    ON u1.unit_id = u.id
  WHERE ca.col_area && ri.tile_geom
    AND t_age <= _t_step
    AND b_age >= _t_step
  ORDER BY col_id, max_thick DESC
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
),
u1 AS (
  SELECT ST_AsMVT(pp, 'plates') mvt1
  FROM plates_ pp
),
u2 AS (
  SElECT ST_AsMVT(bedrock_, 'units') mvt2
  FROM bedrock_
) --,
-- u3 AS (
--   SELECT ST_AsMVT(land, 'land') mvt3
--   FROM land
-- ),
-- u4 AS (
--   SELECT ST_AsMVT(columns, 'columns') mvt4
--   FROM columns
-- )
SELECT u1.mvt1 || u2.mvt2  --|| u4.mvt4
INTO result
FROM u1, u2 --, u4; --, u4;

RETURN result;

END;
$$ LANGUAGE plpgsql VOLATILE;