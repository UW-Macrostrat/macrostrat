CREATE SCHEMA IF NOT EXISTS tile_layers;

INSERT INTO tile_cache.profile
  (name, format, content_type, minzoom, maxzoom)
VALUES
  ('carto', 'pbf', 'application/x-protobuf', 0, 14),
  ('carto-slim', 'pbf', 'application/x-protobuf', 0, 14),
  ('carto-image', 'png', 'image/png', 0, 14)
ON CONFLICT (name) DO NOTHING;

/* This view is a little slow. We could speed things up by unifying the table perhaps */
CREATE OR REPLACE VIEW tile_layers.carto_units AS
SELECT
  map_id,
  source_id,
  geom,
  'tiny' scale
FROM
  carto_new.tiny
UNION ALL
SELECT
  map_id,
  source_id,
  geom,
  'small' scale
FROM
  carto_new.small
UNION ALL
SELECT
  map_id,
  source_id,
  geom,
  'medium' scale
FROM
  carto_new.medium
UNION ALL
SELECT
  map_id,
  source_id,
  geom,
  'large' scale
FROM carto_new.large;

CREATE OR REPLACE VIEW tile_layers.line_data AS
SELECT
  line_id,
  descrip::text AS descrip,
  name::text AS name,
  new_direction::text AS direction,
  new_type::text AS "type",
  'tiny' scale
FROM lines.tiny
UNION ALL
SELECT
  line_id,
  descrip::text AS descrip,
  name::text AS name,
  new_direction::text AS direction,
  new_type::text AS "type",
  'small' scale
FROM lines.small
UNION ALL
SELECT
  line_id,
  descrip::text AS descrip,
  name::text AS name,
  new_direction::text AS direction,
  new_type::text AS "type",
  'medium' scale
FROM lines.medium
UNION ALL
SELECT
  line_id,
  descrip::text AS descrip,
  name::text AS name,
  new_direction::text AS direction,
  new_type::text AS "type",
  'large' scale
FROM lines.large;

CREATE OR REPLACE VIEW tile_layers.carto_lines AS
SELECT
  x.line_id,
  x.source_id,
  x.geom,
  'tiny' scale
FROM carto_new.lines_tiny x
UNION ALL
SELECT
  x.line_id,
  x.source_id,
  x.geom,
  'small' scale
FROM carto_new.lines_small x
UNION ALL
SELECT
  x.line_id,
  x.source_id,
  x.geom,
  'medium' scale
FROM carto_new.lines_medium x
UNION ALL
SELECT
  x.line_id,
  x.source_id,
  x.geom,
  'large' scale
FROM carto_new.lines_large x;

/**
  == MAP LEGEND INFO ==
  A utility view to assemble "carto-slim" tile data for a given map legend entry
  - We have modified this from its original design to be easier to parse and more straightforward
  - all_lith_classes, all_lith_types are strict supersets of lith_classes, lith_types, with a looser set
    of criteria. So we can simply use the all_lith_* fields and not worry about the others.
  - If we were to break this strict superset rule, we could coalesce() the lith_classes and lith_types
    fields with the all_lith_* fields.

  Testing SQL:
  SELECT count(*) FROM maps.legend l
  WHERE array_length(l.all_lith_classes, 1) > array_length(l.lith_classes, 1)
    AND NOT l.lith_classes <@ l.all_lith_classes
  LIMIT 100;
*/

DROP VIEW IF EXISTS tile_layers.map_legend_info CASCADE;
CREATE OR REPLACE VIEW tile_layers.map_legend_info AS
SELECT
  l.legend_id,
  l.best_age_top :: numeric AS best_age_top,
  l.best_age_bottom :: numeric AS best_age_bottom,
  coalesce(l.color, '#777777') AS color,
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
FROM maps.legend AS l;


CREATE OR REPLACE FUNCTION tile_layers.carto_slim(
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
  WHERE scale = mapsize
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
    tile_layers.carto_lines
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
$$ LANGUAGE plpgsql IMMUTABLE;


--- CARTO
CREATE OR REPLACE FUNCTION tile_layers.carto(
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
  WHERE scale = mapsize AND ST_Intersects(geom, projected_bbox)
), expanded AS (
  SELECT
    z.map_id,
    z.source_id,
    l.legend_id,
    l.best_age_top :: numeric AS best_age_top,
    l.best_age_bottom :: numeric AS best_age_bottom,
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
    tile_layers.carto_lines
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
$$ LANGUAGE plpgsql IMMUTABLE;

CREATE OR REPLACE FUNCTION tile_layers.tile_geom(
  geom geometry,
  bbox geometry
) RETURNS geometry AS $$
  /* It is difficult to reduce tile precision quickly, so we just make a smaller vector tile and scale it up */
  SELECT ST_Scale(ST_Simplify(ST_AsMVTGeom(ST_Transform(geom, 3857), bbox, 2048, 8, true), 1.5), 2, 2);
$$ LANGUAGE sql IMMUTABLE;