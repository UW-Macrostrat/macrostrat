-- Which polygons a map shows is `map_bounds.polygons_of`'s question, not this
-- query's: an ordinary map's own, a mosaic member's parent's inside its
-- footprint. It also carries the partition pruning that `maps.polygons` being
-- LIST-partitioned by scale needs, so nothing about scale appears here.
SELECT
  p.map_id,
  p.source_id,
  l.*, --  map legend info
  tile_layers.tile_geom(p.geom, :envelope) AS geom
FROM map_bounds.polygons_of(
  map_bounds.source_id(:slug),
  ST_Transform(:envelope, 4326)
) p
LEFT JOIN maps.map_legend ml
  ON p.map_id = ml.map_id
LEFT JOIN tile_layers.map_legend_info AS l
  ON l.legend_id = ml.legend_id
