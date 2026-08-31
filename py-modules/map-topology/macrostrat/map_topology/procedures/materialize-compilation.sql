/** Give a compilation polygons of its own, clipped from its members'.

  Each member's polygons are cut to the faces that member actually wins in the
  compilation's layer, so the result is the assembled surface: surficial where it
  exists, bedrock elsewhere, with no overlap left to resolve at query time.

  Clipping runs per face rather than against the member's whole winning
  territory. A face is small and the polygon index does the work -- 200 faces cost
  ~600ms, where unioning a member's 3,816 faces into one territory geometry and
  clipping against that had not finished in two minutes.

  Map ids are drawn from the sequence up front so the legend links can be written
  in the same pass: `INSERT ... RETURNING` gives no way to correlate a new row
  back to the polygon it came from.

  Reversible by construction -- members keep their own polygons untouched, and
  `dematerialize` removes only what this wrote.
*/

/* No ON COMMIT DROP: statements here are committed individually, which would
   drop the staging table out from under the inserts that follow. */
DROP TABLE IF EXISTS _staged;
CREATE TEMP TABLE _staged AS
SELECT
  nextval('maps.map_ids') AS map_id,
  p.map_id AS source_polygon,
  :compilation_id::integer AS source_id,
  s.scale::maps.map_scale AS scale,
  p.orig_id, p.name, p.strat_name, p.age, p.lith, p.descrip, p.comments,
  p.t_interval, p.b_interval,
  ST_Multi(ST_CollectionExtract(ST_MakeValid(clip.geom), 3)) AS geom
FROM maps.sources s
JOIN map_bounds.compilation_member cm ON cm.compilation_id = s.source_id
JOIN map_bounds_topology.map_face f
  ON f.map_id = cm.member_id
 AND f.map_layer = map_bounds.face_layer_for(s.source_id)
JOIN maps.polygons p
  ON p.source_id = cm.member_id
 AND ST_Intersects(p.geom, f.geometry)
CROSS JOIN LATERAL (SELECT ST_Intersection(p.geom, f.geometry) AS geom) clip
WHERE s.source_id = :compilation_id
  AND NOT ST_IsEmpty(clip.geom);

INSERT INTO maps.polygons (
  map_id, source_id, scale, orig_id, name, strat_name, age, lith, descrip,
  comments, t_interval, b_interval, geom
)
SELECT
  map_id, source_id, scale, orig_id, name, strat_name, age, lith, descrip,
  comments, t_interval, b_interval, geom
FROM _staged
WHERE NOT ST_IsEmpty(geom);

/* Attribution follows the polygon: a clipped piece keeps the legend unit of the
   constituent map it came from. */
INSERT INTO maps.map_legend (legend_id, map_id)
SELECT ml.legend_id, st.map_id
FROM _staged st
JOIN maps.map_legend ml ON ml.map_id = st.source_polygon
WHERE NOT ST_IsEmpty(st.geom)
ON CONFLICT (legend_id, map_id) DO NOTHING;

/* Now it holds polygons, so identity resolution stops here rather than descending
   to its members. */
UPDATE maps.sources SET is_finalized = true WHERE source_id = :compilation_id;

INSERT INTO map_bounds.compilation (source_id, member_hash)
VALUES (:compilation_id, map_bounds.compilation_member_hash(:compilation_id))
ON CONFLICT (source_id) DO UPDATE SET member_hash = EXCLUDED.member_hash;

DROP TABLE IF EXISTS _staged;
