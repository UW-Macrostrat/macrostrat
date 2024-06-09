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

IF z < 3 THEN
  -- Select from carto.tiny table
  _scale := 'tiny'::map_scale;
ELSIF z < 6 THEN
  _scale := 'small'::map_scale;
-- Normally we would do less than 9, but we don't have a 'large' scale right now...
ELSIF z < 11 THEN
  _scale := 'medium'::map_scale;
ELSE
  RAISE EXCEPTION 'only zoom levels <= 10 are supported';
END IF;

IF _t_step = 0 THEN
  RETURN corelle_macrostrat.carto_slim_rotated_present(x, y, z, query_params);
END IF;

mercator_bbox := tile_utils.envelope(x, y, z);
tolerance := 6;

projected_bbox := ST_Transform(mercator_bbox, 4326);

WITH rotated_plates AS (
  SELECT 
    pp.plate_id,
    pp.model_id,
    pp.id plate_polygon_id,
    corelle_macrostrat.rotate_to_web_mercator(geom_simple, rotation, true) geom_merc,
    rc.rotation
  FROM corelle.plate_polygon pp
  JOIN corelle.rotation_cache rc
   ON rc.model_id = pp.model_id
  AND rc.plate_id = pp.plate_id
  AND rc.t_step = _t_step
  WHERE pp.model_id = _model_id
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
    rp.plate_polygon_id,
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
  WHERE _scale = 'tiny'::macrostrat.map_scale
     OR ST_Intersects(coalesce(cpi.geom, u.geom), tile_geom)
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
    corelle_macrostrat.rotation_text(rotation) rotation,
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


CREATE OR REPLACE FUNCTION corelle_macrostrat.carto_slim_rotated_present(
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
mapsize text;
_t_step integer;
_model_id integer;
mercator_bbox geometry;
projected_bbox geometry;
bedrock bytea;
plates bytea;
tolerance double precision;
BEGIN

-- Get the time step and model requested from the query parameters
SELECT
  coalesce((query_params->>'t_step')::integer, 0) AS _t_step,
  (query_params->>'model_id')::integer AS _model_id
INTO _t_step, _model_id;

IF _model_id IS NULL THEN
  RAISE EXCEPTION 'model_id is required';
END IF;

IF _t_step != 0 THEN
  RAISE EXCEPTION 'only works for the present';
END IF;

IF z < 3 THEN
  -- Select from carto.tiny table
  mapsize := 'tiny';
ELSIF z < 6 THEN
  mapsize := 'small';
ELSIF z < 11 THEN
  mapsize := 'medium';
ELSE
  RAISE EXCEPTION 'only zoom levels <= 10 are supported';
END IF;

mercator_bbox := tile_utils.envelope(x, y, z);
tolerance := 6;

projected_bbox := ST_Transform(
  mercator_bbox,
  4326
);

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

-- Plate polygons
WITH mvt_features AS (
  SELECT
    plate_id,
    model_id,
    id,
    old_lim,
    young_lim,
    geometry geom
  FROM
    corelle.plate_polygon pp
  WHERE pp.model_id = _model_id
    AND coalesce(pp.old_lim, 4000) >= _t_step
    AND coalesce(pp.young_lim, 0) <= _t_step
    AND ST_Intersects(pp.geom_simple, projected_bbox)
),
expanded AS (
  SELECT
    plate_id,
    model_id,
    id,
    '1,0,0,0' rotation,
    tile_layers.tile_geom(z.geom, mercator_bbox) AS geom
  FROM mvt_features z
)
SELECT
  ST_AsMVT(expanded, 'plates') INTO plates
FROM expanded;

RETURN bedrock || plates;

END;
$$ LANGUAGE plpgsql IMMUTABLE;