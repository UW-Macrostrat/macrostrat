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
  /* The scale layers are *surface* layers -- `medium` means "the surface at
     medium scale", not "every medium-scale map". A map depicting a different
     slice of the record is a real map with a real boundary and a place of its
     own, but not in a surface stack. NULL is unspecified and read as surface,
     which is what every map served before `geolayer` existed is. */
  AND coalesce(s.geolayer, 'surface') = 'surface'
  /* A superseded map is not a candidate at all. This is exclusion rather than
     ranking on purpose: a strictly poorer product placed at low priority still
     shows through wherever its replacement happens not to cover, which is the
     one place it is most likely to be wrong. */
  AND s.superseded_by IS NULL
  /* A mosaic member is never placed by scale. Its content is already in every
     layer its mosaic is placed in, so placing it beside the mosaic would show the
     same ground twice; and it has a footprint without being in the topology, so
     the `map_area` join above does not screen it out. It reaches a layer only by
     an authored edge -- which the sweep below leaves alone. */
  AND NOT map_bounds.is_mosaic_member(s.source_id)
  /* A map that belongs to a topological compilation is placed *through* it, not
     beside it: its standing in the layer descends from the compilation's, which
     is exactly what the flattened path expresses. Membership of a served layer
     does not count -- that is the placement being written here. Nor does
     membership of a mosaic: that records where a map's content came from, not
     where it stands, and a mosaic member may be placed in a layer on its own
     account (Nevada from SGMC above NGS at `large`). */
  AND NOT EXISTS (
    SELECT 1 FROM map_bounds.compilation_member cm
    WHERE cm.member_id = s.source_id
      AND NOT map_bounds.is_served_layer(cm.compilation_id)
      AND NOT map_bounds.is_mosaic(cm.compilation_id)
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
  of a topological compilation. Mosaic membership retires nothing: an authored
  `large -> sgmc-nv001` edge is exactly the placement this must keep. */
DELETE FROM map_bounds.compilation_member cm
WHERE map_bounds.is_served_layer(cm.compilation_id)
  AND EXISTS (
    SELECT 1 FROM map_bounds.compilation_member other
    WHERE other.member_id = cm.member_id
      AND NOT map_bounds.is_served_layer(other.compilation_id)
      AND NOT map_bounds.is_mosaic(other.compilation_id)
  );


/** Retire the layer placement of any map that has stopped qualifying for one.

  The guards on the INSERT above only decide what gets *added*; a map placed
  before it was superseded, or before `geolayer` said it depicts something other
  than the surface, keeps that placement until it is taken away. Both conditions
  are the same statement -- this map does not belong in a surface stack -- so
  they are withdrawn together, and only from served layers: an authored
  compilation's own membership is nobody's to rewrite.
*/
DELETE FROM map_bounds.compilation_member cm
USING maps.sources s
WHERE s.source_id = cm.member_id
  AND map_bounds.is_served_layer(cm.compilation_id)
  AND (
    s.superseded_by IS NOT NULL
    OR coalesce(s.geolayer, 'surface') <> 'surface'
  );
