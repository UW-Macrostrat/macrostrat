/** Finalize `materialize`: the compilation holds its polygons from here.

  Runs once every batch (`materialize-batch.sql`) has been written. Until this,
  the polygons sit under the compilation's `source_id` but it is not
  materialized, so nothing reads them and resolution descends to its members.

  Reversible by construction: members keep their own polygons, and
  `dematerialize` removes only what `materialize` wrote.
*/

/* Now it holds polygons, so identity resolution stops here rather than descending
   to its members. */
UPDATE maps.sources SET is_finalized = true WHERE source_id = :compilation_id;

INSERT INTO map_bounds.compilation (source_id, member_hash)
VALUES (:compilation_id, map_bounds.compilation_member_hash(:compilation_id))
ON CONFLICT (source_id) DO UPDATE
  SET member_hash = EXCLUDED.member_hash;

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
JOIN map_bounds.map_priority mp ON mp.map_id = cm.member_id
WHERE cm.compilation_id = :compilation_id
ON CONFLICT DO NOTHING;
