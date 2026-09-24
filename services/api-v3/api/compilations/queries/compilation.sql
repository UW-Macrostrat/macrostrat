/* One node of the compilation graph, with the edges on either side of it.

   Takes any map, not just a compilation: an ordinary map comes back with no
   members and whatever compilations claim it, which is what makes this usable as
   "where does this map sit?" as well as "what is this compilation made of?".

   Members carry enough of their own facts for a client to render them without a
   second request -- including `n_members`, so it knows which rows are worth
   expanding. One round trip per level of the tree.

   Given `:lng`/`:lat`, the *members* are pruned to those covering that point.
   The node's own counts (`n_members`, `n_sources`) stay global, so a client can
   say "12 of 249 here" rather than losing the denominator.
*/
WITH loc AS (
  SELECT CASE
    WHEN CAST(:lng AS float) IS NULL OR CAST(:lat AS float) IS NULL THEN NULL
    ELSE ST_SetSRID(
      ST_MakePoint(CAST(:lng AS float), CAST(:lat AS float)), 4326)
  END AS geometry
),
/* One spatial scan, resolved up front. Exact for leaves; a compilation's own
   `map_area.geometry` is an envelope, which is why the member test below asks
   about a compilation's leaves rather than the compilation itself. */
covering AS MATERIALIZED (
  SELECT ma.source_id
  FROM map_bounds.map_area ma, loc
  WHERE loc.geometry IS NOT NULL
    AND ST_Intersects(ma.geometry, loc.geometry)
),
target AS (
  SELECT source_id FROM maps.sources
  WHERE slug = :ident OR source_id = :source_id
)
SELECT
  s.source_id,
  s.slug,
  coalesce(s.name, ml.name) AS name,
  s.scale,
  s.ref_title,
  s.authors,
  s.ref_year,
  s.url,
  s.status_code,
  s.is_finalized,
  ml.id IS NOT NULL AS is_served_layer,
  ml.id AS map_layer,
  ml.min_zoom,
  ml.max_zoom,
  ml.description AS layer_description,
  n.n_members > 0 AS is_compilation,
  n.holds_polygons,
  map_bounds.is_materialized(s.source_id) AS is_materialized,
  map_bounds.is_mosaic_member(s.source_id) AS is_mosaic_member,
  n.n_members,
  lv.n_sources,
  c.assembly_mode,
  c.note,
  cs.state,
  /* The member set the polygon cache was built from, against the current one.
     Equal means the cache is current; different means it is stale. Both null on
     a virtual compilation, which has no cache to be stale. */
  c.member_hash::text AS member_hash,
  cs.current_member_hash::text AS current_member_hash,
  ma.area_km::float AS area_km,
  ma.map_layer AS placed_in_layer,
  coalesce(par.parents, '[]'::jsonb) AS parents,
  coalesce(mem.members, '[]'::jsonb) AS members
FROM target t
JOIN maps.sources s ON s.source_id = t.source_id
CROSS JOIN LATERAL (
  SELECT
    map_bounds.holds_polygons(s.source_id) AS holds_polygons,
    (SELECT count(*) FROM map_bounds.compilation_member cm
      WHERE cm.compilation_id = s.source_id) AS n_members
) n
LEFT JOIN map_bounds.map_layer ml ON ml.source_id = s.source_id
LEFT JOIN map_bounds.compilation c ON c.source_id = s.source_id
LEFT JOIN map_bounds.compilation_sync cs ON cs.source_id = s.source_id
LEFT JOIN map_bounds.map_area ma ON ma.source_id = s.source_id
CROSS JOIN LATERAL (
  SELECT count(DISTINCT source_id) AS n_sources
  FROM map_bounds.compilation_leaves(s.source_id, true)
) lv
LEFT JOIN LATERAL (
  SELECT jsonb_agg(jsonb_build_object(
    'source_id', p.source_id,
    'slug', p.slug,
    'name', coalesce(p.name, pl.name),
    'priority', cm.priority,
    'role', cm.role,
    'is_served_layer', pl.id IS NOT NULL
  ) ORDER BY p.slug) AS parents
  FROM map_bounds.compilation_member cm
  JOIN maps.sources p ON p.source_id = cm.compilation_id
  LEFT JOIN map_bounds.map_layer pl ON pl.source_id = p.source_id
  WHERE cm.member_id = s.source_id
) par ON true
LEFT JOIN LATERAL (
  SELECT jsonb_agg(jsonb_build_object(
    'source_id', m.source_id,
    'slug', m.slug,
    'name', coalesce(m.name, mlr.name),
    'scale', m.scale,
    'priority', cm.priority,
    'role', cm.role,
    'is_served_layer', mlr.id IS NOT NULL,
    'is_compilation', mn.n_members > 0,
    'holds_polygons', mn.holds_polygons,
    'is_materialized', map_bounds.is_materialized(m.source_id),
    'is_mosaic_member', map_bounds.is_mosaic_member(m.source_id),
    'n_members', mn.n_members,
    'state', mcs.state,
    'area_km', mma.area_km::float
  /* Highest priority first -- the member that wins where they overlap. A null
     priority is a mosaic, where the ordering carries no meaning. */
  ) ORDER BY cm.priority DESC NULLS LAST, m.slug) AS members
  FROM map_bounds.compilation_member cm
  JOIN maps.sources m ON m.source_id = cm.member_id
  CROSS JOIN LATERAL (
    SELECT
      map_bounds.holds_polygons(m.source_id) AS holds_polygons,
      (SELECT count(*) FROM map_bounds.compilation_member c2
        WHERE c2.compilation_id = m.source_id) AS n_members
  ) mn
  LEFT JOIN map_bounds.map_layer mlr ON mlr.source_id = m.source_id
  LEFT JOIN map_bounds.compilation mc ON mc.source_id = m.source_id
  LEFT JOIN map_bounds.compilation_sync mcs ON mcs.source_id = m.source_id
  LEFT JOIN map_bounds.map_area mma ON mma.source_id = m.source_id
  WHERE cm.compilation_id = s.source_id
    AND (
      (SELECT geometry FROM loc) IS NULL
      /* A compilation covers the point when one of the maps it resolves to
         does; an ordinary map, when its own footprint does. */
      OR CASE WHEN mn.n_members > 0 THEN EXISTS (
           SELECT 1
           FROM map_bounds.compilation_leaves(m.source_id, true) l
           WHERE l.source_id IN (SELECT source_id FROM covering)
         )
         ELSE m.source_id IN (SELECT source_id FROM covering)
      END
    )
) mem ON true;
