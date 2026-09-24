/* Other maps covering the same ground as this one, at this scale or finer.

   "This area" is the map's own footprint, so the question is polygon overlap
   rather than a point query -- `map_area.geometry` on both sides, which is the
   composed boundary and therefore the honest answer.

   **Coarser maps are excluded by default.** Every map is covered by the handful
   of global and continental sheets, so listing them makes the same few answers
   appear on every page and buries the ones that mean something. What a reader
   wants is peers -- maps at the same scale -- and then the finer maps that cover
   part of this one. `:include_coarser` puts them back.

   Rows come back ordered by *scale distance* first and coverage second, so the
   same-scale peers lead, then maps one band finer, and so on. Ordering purely by
   coverage would put a global sheet covering 100% above a partner sheet covering
   20%, which is the noise this is meant to remove.

   Two costs are bounded deliberately:

   - **The candidate set is capped.** `ST_Intersects` is cheap (a GiST scan), but
     the overlap area is not, so only the top `:limit` candidates by a *cheap*
     ranking -- finest scale first, then smallest footprint -- get that far. A
     map page wants the most relevant neighbours, not all 474 things that touch a
     global map.

   - **The overlap area is skipped for an enormous target.** Cost is roughly the
     target's vertex count times the number of candidates: `bc_2017` (9,331
     points, 43 candidates) measures at 1.0 s, `global2` (1,381,399 points, 474)
     at 57 s. Above `:max_points` the overlap comes back null and
     `overlap_available` says so, rather than making the page wait a minute for
     the answer "all of them". Simplifying the target instead was tried and is
     not viable: `ST_SimplifyPreserveTopology` yields geometries `ST_Intersection`
     then rejects as invalid.

   Served layers are excluded -- they are structural, cover the world, and would
   head every list. Regional compilations are *not*: `sgmc` covering your area is
   exactly the kind of thing this should say, and `is_compilation` lets a client
   group them apart from ordinary maps.
*/
WITH target AS (
  SELECT
    ma.source_id,
    ma.geometry,
    ma.area_km,
    ST_NPoints(ma.geometry) AS n_points,
    /* Finest first, so "at this scale or finer" is `rank <= target rank`.
       Null sorts coarsest; every null-scale row with a boundary is a served
       layer, which is excluded anyway. */
    CASE s.scale
      WHEN 'large' THEN 0 WHEN 'medium' THEN 1
      WHEN 'small' THEN 2 WHEN 'tiny' THEN 3 ELSE 4 END AS scale_rank
  FROM map_bounds.map_area ma
  JOIN maps.sources s ON s.source_id = ma.source_id
  WHERE s.slug = :ident OR s.source_id = :source_id
),
scaled AS (
  SELECT
    ma.source_id,
    ma.geometry,
    ma.area_km,
    CASE cs.scale
      WHEN 'large' THEN 0 WHEN 'medium' THEN 1
      WHEN 'small' THEN 2 WHEN 'tiny' THEN 3 ELSE 4 END AS scale_rank
  FROM map_bounds.map_area ma
  JOIN maps.sources cs ON cs.source_id = ma.source_id
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
  SELECT ma.source_id, ma.geometry
  FROM scaled ma
  CROSS JOIN target t
  WHERE ma.source_id NOT IN (SELECT source_id FROM related)
    /* A global source -- bounds spanning the world -- would overlap everything
       meaninglessly. */
    AND ma.area_km IS NOT NULL
    AND NOT map_bounds.is_global(ma.source_id)
    AND ST_Intersects(ma.geometry, t.geometry)
    AND (:include_coarser OR ma.scale_rank <= t.scale_rank)
  ORDER BY
    /* The cheap proxy for the final ordering, applied before any overlap is
       computed so the expensive work is bounded: peers, then finer, then (only
       when asked for) coarser, and within a band the more focused footprint. */
    CASE
      WHEN t.scale_rank - ma.scale_rank >= 0 THEN t.scale_rank - ma.scale_rank
      ELSE 100 - (t.scale_rank - ma.scale_rank)
    END,
    ma.area_km
  LIMIT :limit
),
overlap AS (
  SELECT
    c.source_id,
    CASE WHEN t.n_points <= :max_points THEN
      ST_Area(
        ST_Intersection(ST_ClipByBox2D(c.geometry, t.geometry::box2d), t.geometry)
        ::geography
      ) / 1e6
    END AS overlap_km
  FROM candidates c, target t
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
  o.overlap_km::float AS overlap_km,
  /* How much of *this* map the neighbour covers. The complementary fraction --
     how much of the neighbour this map covers -- is a different question, and
     the one a reader asks on this page is the first. */
  CASE WHEN t.area_km > 0 THEN (o.overlap_km / t.area_km)::float END
    AS overlap_fraction,
  (SELECT count(*) > 0 FROM map_bounds.compilation_member cm
    WHERE cm.compilation_id = s.source_id) AS is_compilation,
  map_bounds.is_materialized(s.source_id) AS is_materialized,
  map_bounds.is_mosaic_member(s.source_id) AS is_mosaic_member,
  /* The compilations this map belongs to, so the page can say "part of SGMC"
     rather than leaving the reader to guess why it is here. */
  coalesce((
    SELECT array_agg(p.slug ORDER BY p.slug)
    FROM map_bounds.compilation_member cm
    JOIN maps.sources p ON p.source_id = cm.compilation_id
    WHERE cm.member_id = s.source_id
  ), '{}'::text[]) AS in_compilations,
  t.n_points <= :max_points AS overlap_available,
  /* 0 for a peer at the same scale, 1 for one band finer, and so on. The client
     groups on this rather than re-deriving the ordering. */
  t.scale_rank - sc.scale_rank AS scale_distance
FROM overlap o
JOIN maps.sources s ON s.source_id = o.source_id
JOIN map_bounds.map_area ma ON ma.source_id = o.source_id
JOIN scaled sc ON sc.source_id = o.source_id
CROSS JOIN target t
/* Peers first, then each finer band, then the coarser ones if they were asked
   for -- they are context, not the answer. Coverage decides within a band. */
ORDER BY
  CASE
    WHEN t.scale_rank - sc.scale_rank >= 0 THEN t.scale_rank - sc.scale_rank
    ELSE 100 - (t.scale_rank - sc.scale_rank)
  END,
  o.overlap_km DESC NULLS LAST,
  ma.area_km;
