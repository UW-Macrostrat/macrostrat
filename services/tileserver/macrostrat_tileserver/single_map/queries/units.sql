WITH mvt_features AS (
  SELECT
    map_id,
    source_id,
    geom
  FROM maps.polygons
  WHERE source_id = :source_id
    AND ST_Intersects(geom, ST_Transform(:envelope, 4326))
)
SELECT
  z.map_id,
  z.source_id,
  l.*, --  map legend info
  tile_layers.tile_geom(z.geom, :envelope) AS geom
FROM mvt_features z
LEFT JOIN maps.map_legend ON z.map_id = map_legend.map_id
LEFT JOIN tile_layers.map_legend_info AS l
  ON l.legend_id = map_legend.legend_id;
