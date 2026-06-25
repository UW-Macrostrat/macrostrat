WITH tile AS (
    SELECT
      ST_TileEnvelope(:z, :x, :y) AS mercator_bbox,
      tile_layers.geographic_envelope(:x, :y, :z, 0.01) AS projected_bbox,
      CASE WHEN :z < 3 THEN 'tiny'
           WHEN :z < 6 THEN 'carto-small'
           WHEN :z < 9 THEN 'carto-medium'
           ELSE 'carto-large'
      END AS layer_slug
),
map_bounds AS (
  SELECT
    map_id AS source_id,
    lines_oriented,
    s.scale,
    ST_Intersection(geometry, tile.projected_bbox) AS geometry,
    tile.mercator_bbox
  FROM map_bounds_topology.map_face mf
  JOIN tile
    ON ST_Intersects(mf.geometry, tile.projected_bbox)
  JOIN maps.sources s
    ON s.source_id = mf.map_id
  WHERE map_layer = map_bounds.layer_id(tile.layer_slug)
    AND ST_Intersects(geometry, tile.projected_bbox)
),
unit_features AS (
  SELECT
    p.map_id,
    b.source_id,
    l.*, -- legend info
    -- TODO: only run intersection if the map is partially visible
    tile_layers.tile_geom(ST_Intersection(p.geom, b.geometry), b.mercator_bbox) AS geom
  FROM
    maps.polygons p
  JOIN map_bounds b
    ON b.source_id = p.source_id
   AND p.scale::text = b.scale::text
   AND ST_Intersects(p.geom, b.geometry)
  LEFT JOIN maps.map_legend
    ON p.map_id = map_legend.map_id
  LEFT JOIN tile_layers.map_legend_info AS l
    ON l.legend_id = map_legend.legend_id
),
-- Lines
line_features AS (
  SELECT
    line_id,
    b.source_id,
    coalesce(l.descrip, '') AS descrip,
    coalesce(l.name, '') AS name,
    coalesce(l.direction, '') AS direction,
    coalesce(l.type, '') AS "type",
    lines_oriented oriented,
    tile_layers.tile_geom(ST_Intersection(geom, b.geometry), b.mercator_bbox) AS geom
  FROM
    maps.lines l
  JOIN map_bounds b
    ON b.source_id = l.source_id
   AND l.scale::text = b.scale::text
   AND ST_Intersects(l.geom, b.geometry)
), units_tile AS (
  SELECT ST_AsMVT(unit_features, 'units') AS units
  FROM unit_features
), lines_tile AS (
  SELECT ST_AsMVT(line_features, 'lines') AS lines
  FROM line_features
)
SELECT units || lines
FROM units_tile, lines_tile;
