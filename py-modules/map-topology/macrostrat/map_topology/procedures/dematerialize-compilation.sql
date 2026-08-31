/** Undo materialization: drop the polygons a compilation derived from its members.

  Members keep their own polygons throughout, so this restores the virtual state
  exactly -- resolution goes back to descending through the compilation.
*/
DELETE FROM maps.map_legend ml
USING maps.polygons p
WHERE ml.map_id = p.map_id
  AND p.source_id = :compilation_id;

DELETE FROM maps.polygons WHERE source_id = :compilation_id;

UPDATE maps.sources SET is_finalized = false WHERE source_id = :compilation_id;

UPDATE map_bounds.compilation SET member_hash = NULL WHERE source_id = :compilation_id;
