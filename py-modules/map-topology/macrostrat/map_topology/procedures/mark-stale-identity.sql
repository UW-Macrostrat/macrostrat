/** Mark every face whose attribution disagrees with what the resolver would say.

  Faces are invalidated by boundary edits -- `mark_surrounding_faces` fires on the
  boundary topogeometry -- but identity can change without any boundary moving.
  Materializing a compilation is the clearest case: its members stop resolving and
  it starts, so every face attributed to a member is stale while no geometry has
  changed at all. Editing a priority or moving a map between compilations does the
  same thing.

  An earlier version asked only whether the map a face names is still in
  `map_priority` for its layer. That catches *the owner disappeared* and misses
  the two commoner halves:

    a better owner appeared   adding NGS's 79 maps to a served layer left every
                              pre-existing face with a perfectly valid owner, so
                              nothing was queued and 34% of `medium`'s faces kept
                              an owner that no longer wins them -- one face held
                              35,517 primitive faces across the central and
                              eastern US.
    an owner appeared at all  `ngs-alaska`, `ngs-hawaii` and `ngs-greater-antilles`
                              resolve in `medium` and had no face there at all;
                              2,180 primitive faces belonged to nobody, so a test
                              that starts from existing faces cannot see them.

  Guards that say what may be *added* never say what must be given up, and a test
  anchored on what exists cannot ask for what is missing. So compare both
  directions against the resolver: `resolve_layer_identity` is the function the
  dissolve itself uses, which makes "stale" exactly "the dissolve would not
  produce this". A vanished owner still qualifies -- it resolves to something
  else, or to nothing -- so this is a superset of the membership test, not a
  different one.

  Cost is one resolve per served layer, a few seconds each, once per sync.

  Unit faces are skipped: they are rebuilt outright by `sync-unit-faces`, not
  dissolved.
*/
WITH layers AS (
  /* The layers identity is resolved for. Anchoring on `map_priority` rather than
     on which layers happen to hold faces is what lets a layer that holds none
     yet be built rather than silently skipped. */
  SELECT DISTINCT map_layer FROM map_bounds.map_priority
),
resolved AS (
  SELECT l.map_layer, x.face_id, x.identity::integer AS map_id
  FROM layers l
  CROSS JOIN LATERAL map_bounds_topology.resolve_layer_identity(l.map_layer) x
),
face_owner AS (
  /* The primitive faces each dissolved face claims, with the map it is attributed
     to. Restricted to maps that have content, because a unit face's `map_id`
     names a compilation and `sync-unit-faces` owns those. */
  SELECT r.element_id AS face_id, f.map_layer, f.map_id
  FROM map_bounds_topology.map_face f
  JOIN map_bounds_topology.relation r
    ON r.layer_id = (f.topo).layer_id
   AND r.topogeo_id = (f.topo).id
   AND r.element_type = 3
  JOIN layers l ON l.map_layer = f.map_layer
  WHERE f.map_id IS NOT NULL
    AND f.topo IS NOT NULL
    AND map_bounds.has_content(f.map_id)
)
INSERT INTO map_bounds_topology.dirty_face (id, map_layer)
/* FULL JOIN because either side can be the one that is missing: a face attributed
   to the wrong map, a face attributed to a map that no longer resolves, and a
   face with an owner but no attribution are all the same defect seen from
   different ends. `resolve_layer_identity` never returns a NULL identity, so a
   NULL on that side means "no owner" rather than "unknown". */
SELECT
  coalesce(o.face_id, v.face_id),
  coalesce(o.map_layer, v.map_layer)
FROM face_owner o
FULL JOIN resolved v
  ON v.map_layer = o.map_layer
 AND v.face_id = o.face_id
WHERE o.map_id IS DISTINCT FROM v.map_id
ON CONFLICT DO NOTHING;
