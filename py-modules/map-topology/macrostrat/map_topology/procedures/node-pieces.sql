/* Node a batch of a map's pending pieces into its topogeometry.

   `update_boundary_topo(row, piece, tolerance)` is the library's accumulating
   form: the first piece creates `map_area.topo`, later ones add to it under the
   same id, each marking the faces it touches dirty. It returns the error text
   on failure and leaves the row alone, so the outcome is recorded here, on the
   piece. Every call is a separate statement inside the function, so each sees
   what the previous piece added.

   `:failed` selects pieces that failed before (a retry at another tolerance)
   rather than pieces not yet attempted.
*/
WITH pieces AS (
  SELECT t.id, t.geometry
  FROM map_bounds.map_topo t
  WHERE t.source_id = :map_id
    AND NOT t.noded
    AND (t.topology_error IS NOT NULL) = :failed
  ORDER BY t.id
  LIMIT :batch_size
),
outcome AS (
  SELECT
    p.id,
    map_bounds_topology.update_boundary_topo(l, p.geometry, CAST(:tolerance AS numeric)) AS err
  FROM pieces p
  JOIN map_bounds.map_area l ON l.id = :map_id
),
recorded AS (
  UPDATE map_bounds.map_topo t
  SET noded = (o.err IS NULL),
      topology_error = o.err,
      tolerance = :tolerance
  FROM outcome o
  WHERE t.id = o.id
  RETURNING t.noded
)
SELECT
  count(*) FILTER (WHERE noded) AS noded,
  count(*) FILTER (WHERE NOT noded) AS failed
FROM recorded;
