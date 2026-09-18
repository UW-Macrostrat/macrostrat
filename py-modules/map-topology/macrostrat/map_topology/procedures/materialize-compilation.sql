/** Give a compilation polygons of its own, assembled from its members'.

  Priority is resolved *between members* and nowhere else: the highest-priority
  member wins wherever it exists, so its polygons are copied untouched, and each
  lower member keeps only what the members above it do not cover. External
  competition is deliberately not considered -- an ordinary map's polygons are not
  clipped to where it beats its neighbours either, and the topology decides who
  shows. Clipping to faces would bake one layer's context into content that
  belongs to the compilation itself.

  Most polygons need no geometry work at all. Of British Columbia's 33,409 bedrock
  polygons only 10,453 are touched by surficial; the rest are copied, as are all
  1,300 surficial polygons.

  `:scale` is the compilation's own scale, written onto the rows it gets;
  members' polygons are read at the scale of whatever holds their content.

  Map ids are drawn from the sequence up front so the legend links can be written
  in the same pass -- `INSERT ... RETURNING` gives no way to correlate a new row
  back to the polygon it came from.

  Reversible by construction: members keep their own polygons, and
  `dematerialize` removes only what this wrote.
*/

/* No ON COMMIT DROP: statements here are committed individually, which would drop
   the staging table out from under the inserts that follow. */
DROP TABLE IF EXISTS _staged;

CREATE TEMP TABLE _staged AS
WITH member AS (
  SELECT cm.member_id, cm.priority
  FROM map_bounds.compilation_member cm
  WHERE cm.compilation_id = :compilation_id
),
/* What each member is covered by: the footprints of everything ranked above it.
   Null for the top member, which is why its polygons pass through untouched. */
covered_by AS (
  SELECT m.member_id, ST_Union(a.geometry) AS geometry
  FROM member m
  JOIN member higher
    ON higher.priority > m.priority
  JOIN map_bounds.map_area a ON a.source_id = higher.member_id
  GROUP BY m.member_id
)
SELECT
  nextval('maps.map_ids') AS map_id,
  p.map_id AS source_polygon,
  :compilation_id::integer AS source_id,
  :scale::maps.map_scale AS scale,
  p.orig_id, p.name, p.strat_name, p.age, p.lith, p.descrip, p.comments,
  p.t_interval, p.b_interval,
  CASE
    WHEN c.geometry IS NULL OR NOT ST_Intersects(p.geom, c.geometry)
      THEN p.geom
    ELSE ST_Difference(p.geom, c.geometry)
  END AS geom
FROM member m
/* A member's polygons are wherever its content is -- its own, or for a mosaic
   member its parent's inside its footprint. `polygons_of` answers that and
   prunes the partition by the content's scale, since a `large` compilation may
   draw on `medium` content. */
CROSS JOIN LATERAL map_bounds.polygons_of(m.member_id) p
LEFT JOIN covered_by c ON c.member_id = m.member_id;

/* A polygon wholly beneath a higher member differences away to nothing. */
DELETE FROM _staged
WHERE ST_IsEmpty(geom)
   OR ST_IsEmpty(ST_CollectionExtract(geom, 3));

INSERT INTO maps.polygons (
  map_id, source_id, scale, orig_id, name, strat_name, age, lith, descrip,
  comments, t_interval, b_interval, geom
)
SELECT
  map_id, source_id, scale, orig_id, name, strat_name, age, lith, descrip,
  comments, t_interval, b_interval, ST_Multi(ST_CollectionExtract(geom, 3))
FROM _staged;

/* Attribution follows the polygon: a piece keeps the legend unit of the
   constituent map it came from. */
INSERT INTO maps.map_legend (legend_id, map_id)
SELECT ml.legend_id, st.map_id
FROM _staged st
JOIN maps.map_legend ml ON ml.map_id = st.source_polygon
ON CONFLICT (legend_id, map_id) DO NOTHING;

/* Now it holds polygons, so identity resolution stops here rather than descending
   to its members. */
UPDATE maps.sources SET is_finalized = true WHERE source_id = :compilation_id;

INSERT INTO map_bounds.compilation (source_id, member_hash, is_derived)
VALUES (:compilation_id, map_bounds.compilation_member_hash(:compilation_id), true)
ON CONFLICT (source_id) DO UPDATE
  SET member_hash = EXCLUDED.member_hash,
      -- These polygons came from the members and can go back; recording that is
      -- what makes `dematerialize` safe to offer.
      is_derived = true;

DROP TABLE IF EXISTS _staged;

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
