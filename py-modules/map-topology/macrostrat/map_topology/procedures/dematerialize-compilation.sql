/** Undo materialization: drop the polygons a compilation derived from its members.

  Members keep their own polygons throughout, so this restores the virtual state
  exactly -- resolution goes back to descending through the compilation.

  Nothing stored says these polygons are a cache, so prove it first, polygon by
  polygon: every one must carry a legend entry owned by some *other* source (the
  member it was cut from), which is what `materialize` writes and an ingested
  dataset never has. One polygon that fails -- unlinked, or linked to a legend
  row the compilation itself owns, as all of SGMC's are -- and nothing is deleted.
*/
SELECT map_bounds.assert_dematerializable(:compilation_id);

DELETE FROM maps.map_legend ml
USING maps.polygons p
WHERE ml.map_id = p.map_id
  AND p.source_id = :compilation_id;

DELETE FROM maps.polygons WHERE source_id = :compilation_id;

UPDATE maps.sources SET is_finalized = false WHERE source_id = :compilation_id;

/* Back to virtual: no polygons, so no cache to stamp. */
UPDATE map_bounds.compilation SET member_hash = NULL
WHERE source_id = :compilation_id;

/* Materializing changes who owns the territory while no boundary moves, so
   nothing else notices. `mark-stale-identity` catches faces whose owner stops
   resolving, but not primitive faces left without a `map_face` at all -- and a
   half-dissolved territory leaves exactly those. Mark the whole territory.

   Layers are taken from where the members currently resolve, which is still true
   at this point: the sync that retires them has not run yet. */
INSERT INTO map_bounds_topology.dirty_face (id, map_layer)
SELECT DISTINCT r.element_id, mp.map_layer
FROM map_bounds.compilation_member cm
JOIN map_bounds.map_area a
  ON a.source_id = cm.member_id
 AND a.topo IS NOT NULL
JOIN map_bounds_topology.relation r
  ON r.layer_id = (a.topo).layer_id
 AND r.topogeo_id = (a.topo).id
 AND r.element_type = 3
JOIN map_bounds.map_priority mp ON mp.source_id = cm.member_id
WHERE cm.compilation_id = :compilation_id
ON CONFLICT DO NOTHING;
