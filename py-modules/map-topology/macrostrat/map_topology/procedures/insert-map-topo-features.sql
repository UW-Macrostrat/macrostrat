/* Derive a map's `map_topo` parts from its boundary.

   Parts are inserted when a map has none, and **rebuilt when the boundary has
   changed since they were derived** -- `map_area.geometry_hash` records which
   boundary they came from. Before boundary composition, `map_area.geometry` was
   effectively write-once, so "insert only if empty" was safe; it is not any more,
   and stale parts silently keep the topology on an old boundary.

   Delete and insert sit in one statement, so both see the same snapshot: the
   insert cannot observe the delete, and its condition is therefore the staleness
   test rather than "no rows exist".
*/
WITH target AS (
  SELECT
    a.source_id,
    a.geometry,
    a.geometry_hash IS DISTINCT FROM md5(ST_AsBinary(a.geometry))::uuid AS stale,
    NOT EXISTS (
      SELECT 1 FROM map_bounds.map_topo t WHERE t.source_id = a.source_id
    ) AS empty
  FROM map_bounds.map_area a
  JOIN maps.sources_metadata m ON a.source_id = m.source_id
  WHERE a.source_id = :map_id
),
dropped AS (
  DELETE FROM map_bounds.map_topo t
  USING target
  WHERE t.source_id = target.source_id
    AND target.stale
  RETURNING t.id
),
inserted AS (
  INSERT INTO map_bounds.map_topo (source_id, geometry)
  SELECT
    target.source_id,
    -- Snapping is removed so the geometry stays valid through subdivision.
    ST_Multi(ST_Subdivide(
      ST_MakeValid(
        ST_SimplifyPreserveTopology(ST_Multi(target.geometry), :simplify_amount)
      ),
      :subdivide_vertices,
      :simplify_amount
    ))
  FROM target
  WHERE target.stale OR target.empty
  RETURNING id
),
recorded AS (
  -- Record the boundary these parts were derived from.
  UPDATE map_bounds.map_area a
  SET geometry_hash = md5(ST_AsBinary(a.geometry))::uuid
  FROM target
  WHERE a.source_id = target.source_id
    AND (target.stale OR target.empty)
  RETURNING a.source_id
)
SELECT
  (SELECT count(*) FROM inserted) AS inserted,
  (SELECT count(*) FROM dropped) AS deleted,
  (SELECT count(*) FROM map_bounds.map_topo WHERE source_id = :map_id) AS existing;
