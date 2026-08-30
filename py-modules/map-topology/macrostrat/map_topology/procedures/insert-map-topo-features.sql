WITH existing_count AS (
  SELECT COUNT(*) as n
  FROM map_bounds.map_topo
  WHERE map_id = :map_id
), to_insert AS (
  SELECT
    a.source_id,
    -- We have to remove snapping behavior to make sure that the geometry is valid.
    ST_Multi(ST_Subdivide(
      ST_MakeValid(
        ST_SimplifyPreserveTopology(
          ST_Multi(a.geometry),
          :simplify_amount
        )
      ),
      :subdivide_vertices,
      :simplify_amount
             )) geometry
  FROM map_bounds.map_area a
  JOIN maps.sources_metadata m
  ON a.source_id = m.source_id
  WHERE a.source_id = :map_id
),
ins AS (
  INSERT INTO map_bounds.map_topo (source_id, geometry)
    SELECT source_id, geometry
    FROM to_insert
    WHERE (SELECT n FROM existing_count) = 0
    RETURNING id, source_id
)
SELECT count(*) as inserted, (SELECT n FROM existing_count) as existing
FROM ins
