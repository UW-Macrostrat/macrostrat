/* Cut a map's bounds into the pieces its topogeometry is noded from.

   Simplified, made valid, and subdivided to a vertex budget so each piece nodes
   quickly and a failure is attributable. Existing pieces are replaced: pieces
   are a working set for one noding of one geometry, tagged with `bounds_hash`
   so a later run can tell whether they belong to the current bounds.

   One statement, so the caller gets one result: the delete and the insert see
   the same snapshot, which is fine because they touch different rows.

   The hash and the simplified geometry are computed once, in a materialized
   CTE, so neither is re-evaluated per piece the subdivide emits.
*/
WITH dropped AS (
  DELETE FROM map_bounds.map_topo WHERE source_id = :map_id RETURNING id
),
bounds AS MATERIALIZED (
  SELECT
    a.source_id,
    ST_MakeValid(
      ST_SimplifyPreserveTopology(ST_Multi(a.geometry), :simplify_amount)
    ) AS geometry,
    md5(ST_AsBinary(a.geometry))::uuid AS bounds_hash
  FROM map_bounds.map_area a
  WHERE a.source_id = :map_id
),
inserted AS (
  INSERT INTO map_bounds.map_topo (source_id, geometry, bounds_hash)
  SELECT
    b.source_id,
    ST_Multi(ST_Subdivide(b.geometry, :subdivide_vertices, :simplify_amount)),
    b.bounds_hash
  FROM bounds b
  RETURNING id
)
SELECT count(*) AS pieces FROM inserted;
