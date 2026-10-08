/* Other maps covering or near the same ground as this one, at this scale or
   finer.

   "This area" is the map's own footprint, so the question is polygon overlap
   rather than a point query -- `map_area.geometry` on both sides, which is the
   composed boundary and therefore the honest answer. Maps that do not overlap
   but sit within a short reach of the footprint come back as `nearby`, after
   the overlapping ones.

   **Coarser maps are excluded by default.** Every map is covered by the handful
   of global and continental sheets, so listing them makes the same few answers
   appear on every page and buries the ones that mean something. What a reader
   wants is peers -- maps at the same scale -- and then the finer maps that cover
   part of this one. `:include_coarser` puts them back.

   Rows come back ordered by relation (overlapping, then nearby), then by *scale
   distance*, then by coverage or by gap. Ordering purely by coverage would put
   a global sheet covering 100% above a partner sheet covering 20%, which is the
   noise this is meant to remove.

   **Coverage is an estimate from bounding boxes**: the share of this map's box
   that the neighbour's box covers. This is a list of maps worth a look, not a
   measurement; the exact polygon overlap cost seconds per map, and could not
   be computed at all for a global footprint.

   The carto stacks' own nodes are excluded: the multiscale compilations
   (`carto`, `carto-v1`), their composite layers and base layers. They cover
   everything by construction, so they would head every list; a map's place in
   carto is reported as `in_carto` instead. Empty compilations go too. Regional
   compilations are *not* excluded: `sgmc` covering your area is exactly the
   kind of thing this should say.
*/
WITH RECURSIVE stack AS (
  SELECT c.source_id, 0 AS depth
  FROM map_bounds.compilation c
  WHERE c.assembly_mode = 'multiscale'
  UNION
  SELECT cm.member_id, stack.depth + 1
  FROM map_bounds.compilation_member cm
  JOIN stack ON cm.compilation_id = stack.source_id
  WHERE stack.depth < 2 AND map_bounds.is_compilation(cm.member_id)
),
structural AS (
  SELECT source_id FROM stack
  UNION
  SELECT c.source_id FROM map_bounds.compilation c
  WHERE NOT map_bounds.is_compilation(c.source_id)
),
target AS (
  SELECT
    ma.source_id,
    ma.geometry,
    /* Bounding boxes computed once: deriving them per candidate re-reads the
       whole footprint each time, which costs seconds for a map like `sgmc`. */
    ma.geometry::box2d AS box,
    (ST_XMax(ma.geometry) - ST_XMin(ma.geometry))
      * (ST_YMax(ma.geometry) - ST_YMin(ma.geometry)) AS box_area,
    ST_Envelope(ma.geometry) AS envelope,
    /* How far beyond the footprint counts as nearby: half its larger side,
       capped so a continental map does not sweep in a hemisphere. */
    ST_Expand(ma.geometry::box2d, least(
      greatest(ST_XMax(ma.geometry) - ST_XMin(ma.geometry),
               ST_YMax(ma.geometry) - ST_YMin(ma.geometry)) / 2,
      2.0
    )) AS search_box,
    /* Finest first, so "at this scale or finer" is `rank <= target rank`. */
    CASE s.scale
      WHEN 'large' THEN 0 WHEN 'medium' THEN 1
      WHEN 'small' THEN 2 WHEN 'tiny' THEN 3 ELSE 4 END AS scale_rank
  FROM map_bounds.map_area ma
  JOIN maps.sources s ON s.source_id = ma.source_id
  WHERE s.slug = :ident OR s.source_id = :source_id
),
/* This map's own membership chain, in both directions. */
related AS (
  WITH RECURSIVE up AS (
    SELECT t.source_id FROM target t
    UNION
    SELECT cm.compilation_id
    FROM map_bounds.compilation_member cm
    JOIN up ON cm.member_id = up.source_id
  ), down AS (
    SELECT t.source_id FROM target t
    UNION
    SELECT cm.member_id
    FROM map_bounds.compilation_member cm
    JOIN down ON cm.compilation_id = down.source_id
  )
  SELECT source_id FROM up
  UNION
  SELECT source_id FROM down
),
candidates AS (
  SELECT
    ma.source_id,
    ma.geometry,
    ma.area_km,
    sc.scale_distance,
    /* Peers, then finer bands, then (only when asked for) coarser ones. */
    CASE
      WHEN sc.scale_distance >= 0 THEN sc.scale_distance
      ELSE 100 - sc.scale_distance
    END AS band,
    ST_Intersects(ma.geometry, t.geometry) AS intersects,
    ma.geometry <#> t.envelope AS gap,
    /* How much of this map's box the neighbour's box covers. */
    (
      greatest(least(ST_XMax(b.box), ST_XMax(t.box))
        - greatest(ST_XMin(b.box), ST_XMin(t.box)), 0)
      * greatest(least(ST_YMax(b.box), ST_YMax(t.box))
        - greatest(ST_YMin(b.box), ST_YMin(t.box)), 0)
      / nullif(t.box_area, 0)
    ) AS coverage
  FROM map_bounds.map_area ma
  JOIN maps.sources cs ON cs.source_id = ma.source_id
  CROSS JOIN target t
  CROSS JOIN LATERAL (SELECT ma.geometry::box2d AS box) b
  CROSS JOIN LATERAL (
    SELECT t.scale_rank - CASE cs.scale
      WHEN 'large' THEN 0 WHEN 'medium' THEN 1
      WHEN 'small' THEN 2 WHEN 'tiny' THEN 3 ELSE 4 END AS scale_distance
  ) sc
  WHERE ma.source_id NOT IN (SELECT source_id FROM related)
    AND ma.source_id NOT IN (SELECT source_id FROM structural)
    /* A global source -- bounds spanning the world -- would overlap everything
       meaninglessly. */
    AND ma.area_km IS NOT NULL
    AND NOT map_bounds.is_global(ma.source_id)
    AND ma.geometry && t.search_box
    AND (:include_coarser OR sc.scale_distance >= 0)
),
picked AS (
  (SELECT c.source_id, c.band, c.gap, c.coverage, true AS intersects
   FROM candidates c WHERE c.intersects
   ORDER BY c.band, c.coverage DESC NULLS LAST, c.area_km
   LIMIT :limit)
  UNION ALL
  (SELECT c.source_id, c.band, c.gap, NULL, false
   FROM candidates c WHERE NOT c.intersects
   ORDER BY c.band, c.gap
   LIMIT :nearby_limit)
),
/* Every compilation above each picked map, to say whether it is in carto and
   which other compilations it belongs to. */
ancestry AS (
  WITH RECURSIVE up AS (
    SELECT p.source_id AS map_id, cm.compilation_id
    FROM picked p
    JOIN map_bounds.compilation_member cm ON cm.member_id = p.source_id
    UNION
    SELECT up.map_id, cm.compilation_id
    FROM up
    JOIN map_bounds.compilation_member cm ON cm.member_id = up.compilation_id
  )
  SELECT * FROM up
)
SELECT
  s.source_id,
  s.slug,
  s.name,
  s.scale,
  s.ref_title,
  s.authors,
  s.ref_year,
  s.superseded_by,
  ma.area_km::float AS area_km,
  CASE WHEN o.intersects THEN 'overlaps' ELSE 'nearby' END AS relation,
  /* Roughly how much of *this* map the neighbour covers, 0-1. */
  least(o.coverage, 1)::float AS overlap_fraction,
  (SELECT count(*) > 0 FROM map_bounds.compilation_member cm
    WHERE cm.compilation_id = s.source_id) AS is_compilation,
  map_bounds.is_materialized(s.source_id) AS is_materialized,
  map_bounds.is_mosaic_member(s.source_id) AS is_mosaic_member,
  EXISTS (
    SELECT 1 FROM ancestry a
    JOIN maps.sources c ON c.source_id = a.compilation_id
    WHERE a.map_id = s.source_id AND c.slug = 'carto'
  ) AS in_carto,
  /* The other compilations this map belongs to, so the page can say "part of
     SGMC" rather than leaving the reader to guess why it is here. */
  coalesce((
    SELECT array_agg(DISTINCT c.slug ORDER BY c.slug)
    FROM ancestry a
    JOIN maps.sources c ON c.source_id = a.compilation_id
    WHERE a.map_id = s.source_id
      AND a.compilation_id NOT IN (SELECT source_id FROM structural)
  ), '{}'::text[]) AS in_compilations,
  /* 0 for a peer at the same scale, 1 for one band finer, and so on. */
  t.scale_rank - CASE s.scale
    WHEN 'large' THEN 0 WHEN 'medium' THEN 1
    WHEN 'small' THEN 2 WHEN 'tiny' THEN 3 ELSE 4 END AS scale_distance
FROM picked o
JOIN maps.sources s ON s.source_id = o.source_id
JOIN map_bounds.map_area ma ON ma.source_id = o.source_id
CROSS JOIN target t
ORDER BY
  o.intersects DESC,
  o.band,
  o.coverage DESC NULLS LAST,
  o.gap,
  ma.area_km;
