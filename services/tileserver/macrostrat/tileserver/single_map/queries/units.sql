-- `maps.polygons` is partitioned by LIST (scale), so a query without a `scale`
-- predicate touches all four partitions. Every source sits entirely in one
-- partition, and `maps.sources.scale` records which — resolving it in a
-- subquery gives the planner an InitPlan value and lets it prune the other
-- three at execution start. `maps.sources.scale` is free-text varchar, so the
-- enum cast is guarded to values that are actually partition keys; retyping
-- that column to `maps.map_scale` would let the guard go away.
SELECT
  p.map_id,
  p.source_id,
  l.*, --  map legend info
  tile_layers.tile_geom(p.geom, :envelope) AS geom
FROM maps.polygons p
JOIN maps.sources s
  ON p.source_id = s.source_id
LEFT JOIN maps.map_legend ml
  ON p.map_id = ml.map_id
LEFT JOIN tile_layers.map_legend_info AS l
  ON l.legend_id = ml.legend_id
WHERE s.slug = :slug
  AND p.scale = (
    SELECT s1.scale::maps.map_scale
    FROM maps.sources s1
    WHERE s1.slug = :slug
      AND s1.scale = ANY (enum_range(NULL::maps.map_scale)::text[])
  )
  AND ST_Intersects(p.geom, ST_Transform(:envelope, 4326))
