/** Mark faces whose owner no longer resolves in their layer.

  Faces are invalidated by boundary edits -- `mark_surrounding_faces` fires on the
  boundary topogeometry -- but identity can change without any boundary moving.
  Materializing a compilation is the clearest case: its members stop resolving and
  it starts, so every face attributed to a member is stale while no geometry has
  changed at all. Editing a priority or moving a map between compilations does the
  same thing.

  A face is stale when the map it names is no longer in `map_priority` for its
  layer. That is exactly the set materialization invalidates, and it costs a join
  rather than an identity lookup per face.

  Unit faces are skipped: they are rebuilt outright by `sync-unit-faces`, not
  dissolved.
*/
INSERT INTO map_bounds_topology.dirty_face (id, map_layer)
SELECT r.element_id, f.map_layer
FROM map_bounds_topology.map_face f
JOIN map_bounds_topology.relation r
  ON r.layer_id = (f.topo).layer_id
 AND r.topogeo_id = (f.topo).id
 AND r.element_type = 3
WHERE f.map_id IS NOT NULL
  AND f.topo IS NOT NULL
  AND map_bounds.holds_polygons(f.map_id)
  AND NOT EXISTS (
    SELECT 1 FROM map_bounds.map_priority mp
    WHERE mp.map_layer = f.map_layer
      AND mp.source_id = f.map_id
  )
ON CONFLICT DO NOTHING;
