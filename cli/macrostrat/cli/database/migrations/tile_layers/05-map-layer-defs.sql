/* This view is a stopgap to prepare for a unified tablespace for map units */
CREATE OR REPLACE VIEW tile_layers.map_units AS
SELECT
  *,
  'tiny' scale
FROM maps.tiny
UNION ALL
SELECT
  *,
  'small' scale
FROM maps.small
UNION ALL
SELECT
  *,
  'medium' scale
FROM maps.medium
UNION ALL
SELECT
  *,
  'large' scale
FROM maps.large;

DROP VIEW IF EXISTS tile_layers.map_lines;

CREATE OR REPLACE VIEW tile_layers.map_lines AS
SELECT
  *,
  'tiny' scale
FROM lines.tiny
UNION ALL
SELECT
  *,
  'small' scale
FROM lines.small
UNION ALL
SELECT
  *,
  'medium' scale
FROM lines.medium
UNION ALL
SELECT
  *,
  'large' scale
FROM lines.large;

CREATE OR REPLACE FUNCTION tile_layers.map(
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
  _source_id integer;
  mercator_bbox geometry;
  projected_bbox geometry;
  bedrock bytea;
  lines bytea;
  points bytea;
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
           sources.lines_oriented oriented,
           tile_layers.tile_geom(z.geom, mercator_bbox) AS geom
         FROM mvt_features z
                JOIN maps.sources ON z.source_id = sources.source_id
                LEFT JOIN tile_layers.line_data q
                          ON z.line_id = q.line_id
         WHERE q.scale = ANY(linesize)
         --AND ST_Length(geom) > tolerance
       )
  SELECT
    ST_AsMVT(expanded, 'lines') INTO lines
  FROM expanded;

  WITH mvt_features AS (
    SELECT
      strike,
      dip,
      dip_dir,
      point_type,
      certainty,
      comments,
      geom
    FROM maps.points
    WHERE source_id = _source_id
      AND ST_Intersects(geom, projected_bbox)
  ),
       expanded AS (
         SELECT
           z.strike,
           z.dip,
           z.dip_dir,
           z.point_type,
           z.certainty,
           z.comments,
           tile_layers.tile_geom(z.geom, mercator_bbox) AS geom
         FROM mvt_features z
       )
  SELECT ST_AsMVT(expanded, 'points') INTO points
  FROM expanded;

  RETURN bedrock || lines || points;

END;
$$ LANGUAGE plpgsql IMMUTABLE;


CREATE OR REPLACE FUNCTION tile_layers.all_maps(
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
    WHERE scale::text = mapsize
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
         WHERE q.scale::text = ANY(linesize)
         --AND ST_Length(geom) > tolerance
       )
  SELECT ST_AsMVT(expanded, 'lines') INTO lines;

  RETURN bedrock || lines;

END;
$$ LANGUAGE plpgsql IMMUTABLE;
