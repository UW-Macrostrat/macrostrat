/** Materialize the layer placements that used to be inferred on every sync.

  Until now a served layer's membership was a function of `maps.sources.scale`:
  `set-map-priority.sql` swept every finalized surface map into the layer whose
  slug matched its scale band, and withdrew it again when it stopped qualifying.
  That made "which layer is this map in" underivable from the edges -- and, more
  to the point, made a layer *singleton per scale band*. There could be exactly
  one `medium`, so there was no way to stand a second compositing of the same
  maps beside it, which is what `carto-v1` and `ngs-bedrock` both need.

  This runs that inference one final time, writing its answer down as ordinary
  authored edges. Afterwards nothing re-derives them: layer membership is
  curated, like every other compilation's.

  `DO NOTHING`, not `DO UPDATE` -- the sweep overwrote `compilation_member.priority`
  from `maps.sources.new_priority` on every run, which is exactly the behaviour
  being retired. An edge that already exists has been authored, and its priority
  is the authored one.

  The predicates below are the sweep's own, so the frozen state matches what
  was being served the moment before. They do not survive as rules: from here
  `superseded_by` is checked when membership is authored (`compilations add`,
  `compilations lint`), not enforced behind the operator.
*/
INSERT INTO map_bounds.compilation_member (compilation_id, member_id, priority)
SELECT ml.source_id, s.source_id, coalesce(s.new_priority, 0)
FROM maps.sources s
JOIN map_bounds.map_layer ml
  ON ml.slug = s.scale
/* Only maps actually in the topology. A source with a matching scale but no
   boundary was never in the layer. */
JOIN map_bounds.map_area a
  ON a.source_id = s.source_id
WHERE s.scale IS NOT NULL
  AND ml.source_id IS NOT NULL
  AND s.superseded_by IS NULL
  /* A mosaic member reached a layer only by an authored edge, which is already
     present and must not be duplicated by a scale-derived one. */
  AND NOT map_bounds.is_mosaic_member(s.source_id)
  /* A map belonging to a topological compilation was placed *through* it, so it
     had no direct edge of its own to freeze. */
  AND NOT EXISTS (
    SELECT 1 FROM map_bounds.compilation_member cm
    WHERE cm.member_id = s.source_id
      AND NOT map_bounds.has_faces(cm.compilation_id)
      AND NOT map_bounds.is_mosaic(cm.compilation_id)
  )
ON CONFLICT (compilation_id, member_id) DO NOTHING;
