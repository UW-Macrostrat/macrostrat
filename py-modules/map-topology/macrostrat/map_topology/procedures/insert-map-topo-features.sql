WITH existing_count AS (
  SELECT COUNT(*) as n
  FROM map_bounds.map_topo
  WHERE source_id = :source_id
), ins AS (
  INSERT INTO map_bounds.map_topo (source_id, geometry)
    SELECT
      a.id,
      -- We have to remove snapping behavior to make sure that the geometry is valid.
      ST_Multi(ST_Subdivide(
        ST_MakeValid(
          ST_SimplifyPreserveTopology(
            ST_Multi(a.geometry),
            :simplify_amount
          )
        ),
        256,
        0.0001
               ))
    FROM map_bounds.map_area a
    JOIN maps.sources_metadata m
      ON a.id = m.source_id
    WHERE a.id = :source_id
      AND (SELECT n FROM existing_count) = 0
    RETURNING id, source_id
)
SELECT count(*) as inserted, (SELECT n FROM existing_count) as existing
FROM ins
