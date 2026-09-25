/* Cut a map's bounds into the pieces its topogeometry is noded from.

   Simplified, made valid, and subdivided to a vertex budget so each piece nodes
   quickly and a failure is attributable. Existing pieces are replaced: pieces
   are a working set for one noding of one geometry, tagged with `bounds_hash`
   so a later run can tell whether they belong to the current bounds.

   One statement, so the caller gets one result: the delete and the insert see
   the same snapshot, which is fine because they touch different rows.
*/
WITH dropped AS (
  DELETE FROM map_bounds.map_topo WHERE source_id = :map_id RETURNING id
),
inserted AS (
  INSERT INTO map_bounds.map_topo (source_id, geometry, bounds_hash)
  SELECT
    a.source_id,
    ST_Multi(ST_Subdivide(
      ST_MakeValid(
        ST_SimplifyPreserveTopology(ST_Multi(a.geometry), :simplify_amount)
      ),
      :subdivide_vertices,
      :simplify_amount
    )),
    md5(ST_AsBinary(a.geometry))::uuid
  FROM map_bounds.map_area a
  WHERE a.source_id = :map_id
  RETURNING id
)
SELECT count(*) AS pieces FROM inserted;
