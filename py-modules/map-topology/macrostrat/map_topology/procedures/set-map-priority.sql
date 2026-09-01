/** Place each map in the compilation matching its scale.

  `large` is the compilation of all large-scale maps, so placing a map in a layer
  is an ordinary membership edge -- there is no separate layer-to-map table.
  `priority` is the plain within-compilation value authored on `maps.sources`; it
  used to be packed together with a per-scale band (-20000/-10000/0/+10000) so a
  single integer could order maps across layers as well as within one. That job
  now belongs to `priority_path`.
*/
INSERT INTO map_bounds.compilation_member (compilation_id, member_id, priority)
SELECT
  ml.source_id,
  s.source_id,
  coalesce(s.new_priority, 0)
FROM maps.sources s
JOIN map_bounds.map_layer ml
  ON ml.slug = s.scale
/* Only maps that are actually in the topology. A source with a matching scale but
   no boundary is not in the layer -- most of `maps.sources` has never been
   ingested. */
JOIN map_bounds.map_area a
  ON a.source_id = s.source_id
WHERE s.scale IS NOT NULL
  AND ml.source_id IS NOT NULL
  /* A map that belongs to a real compilation is placed *through* it, not beside
     it: its standing in the layer descends from the compilation's, which is
     exactly what the flattened path expresses. Membership of a served layer does
     not count -- that is the placement being written here. */
  AND NOT EXISTS (
    SELECT 1 FROM map_bounds.compilation_member cm
    WHERE cm.member_id = s.source_id
      AND NOT map_bounds.is_served_layer(cm.compilation_id)
  )
ON CONFLICT (compilation_id, member_id)
DO UPDATE SET priority = EXCLUDED.priority;

/** Drop layer placements for maps that no longer have a boundary -- and clear out
  any that were placed without one. */
DELETE FROM map_bounds.compilation_member cm
WHERE map_bounds.is_served_layer(cm.compilation_id)
  /* Leaf maps only. A served layer is a compilation by construction -- its
     boundary derives from its members -- so it legitimately has none on a first
     run. Testing "does it have members?" instead would misread an empty layer as
     a leaf and strip the carto layers' composition before it could be built. */
  AND NOT map_bounds.is_served_layer(cm.member_id)
  AND NOT EXISTS (
    SELECT 1 FROM map_bounds.map_area a WHERE a.source_id = cm.member_id
  );

/** Retire the direct layer placement of any map that has since become a member
  of a real compilation. */
DELETE FROM map_bounds.compilation_member cm
WHERE map_bounds.is_served_layer(cm.compilation_id)
  AND EXISTS (
    SELECT 1 FROM map_bounds.compilation_member other
    WHERE other.member_id = cm.member_id
      AND NOT map_bounds.is_served_layer(other.compilation_id)
  );


/** Temporary: associate maps directly with layers (means maps can only be in one layer) **/
UPDATE map_bounds.map_area
SET map_layer = map_bounds.layer_id(s.scale)
FROM maps.sources s
WHERE map_bounds.map_area.source_id = s.source_id
  AND s.scale IS NOT NULL;
