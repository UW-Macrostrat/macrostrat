/* The whole compilation graph in one round trip: every node and every edge.

   This is the shape a client actually wants. The hierarchy is small -- a few
   hundred nodes and edges, well under the size of the map catalog -- so a per-
   level request buys nothing but latency, and holding the graph makes filtering,
   grouping and selection ordinary local work.

   The node set is everything that participates in a membership edge, either
   side of `compilation_member`, plus every *ingested* map that participates in
   none -- a real dataset that has not been wrapped into anything larger, which
   a client shows as a standalone fallback. `is_standalone` marks them.

   "Ingested" is the filter that matters: `maps.sources` holds 1249 rows, of
   which 779 are in no compilation, but only 13 of those hold polygons or have a
   boundary. The other 766 are rows for maps that were never brought in, and
   listing them would bury the ones that exist.

   Given `:lng`/`:lat`, only the nodes covering that point, and only the edges
   between them. A compilation is tested through the maps it resolves to: its own
   `map_area.geometry` is an envelope, so asking it directly would answer yes
   across the whole bounding box. That test also makes the surviving set closed
   upward -- a compilation's leaves are a superset of any member's -- so the
   pruned graph still assembles into the same tree.
*/
WITH loc AS (
  SELECT CASE
    WHEN CAST(:lng AS float) IS NULL OR CAST(:lat AS float) IS NULL THEN NULL
    ELSE ST_SetSRID(
      ST_MakePoint(CAST(:lng AS float), CAST(:lat AS float)), 4326)
  END AS geometry
),
/* One spatial scan, resolved up front; exact for leaves. */
covering AS MATERIALIZED (
  SELECT ma.source_id
  FROM map_bounds.map_area ma, loc
  WHERE loc.geometry IS NOT NULL
    AND ST_Intersects(ma.geometry, loc.geometry)
),
member_counts AS (
  SELECT compilation_id AS source_id, count(*) AS n_members
  FROM map_bounds.compilation_member
  GROUP BY compilation_id
),
/* Over `member_counts` (tens of rows), not over every node: `compilation_leaves`
   is a recursive descent, and hanging it off each of the ~470 nodes measured at
   465 ms against 88 ms for the graph as a whole. */
source_counts AS (
  SELECT mc.source_id, l.n_sources
  FROM member_counts mc
  CROSS JOIN LATERAL (
    SELECT count(DISTINCT source_id) AS n_sources
    FROM map_bounds.compilation_leaves(mc.source_id, true)
  ) l
),
linked AS (
  SELECT DISTINCT compilation_id AS source_id FROM map_bounds.compilation_member
  UNION
  SELECT DISTINCT member_id FROM map_bounds.compilation_member
),
/* Ingested but unwrapped: holds polygons, or at least has a footprint in the
   topology. Either is evidence of a real map; a bare `maps.sources` row is not. */
standalone AS (
  SELECT s.source_id
  FROM maps.sources s
  LEFT JOIN map_bounds.map_area ma ON ma.source_id = s.source_id
  WHERE NOT EXISTS (SELECT 1 FROM linked l WHERE l.source_id = s.source_id)
    AND (coalesce(s.is_finalized, false) OR ma.source_id IS NOT NULL)
),
participants AS (
  SELECT source_id FROM linked
  UNION
  SELECT source_id FROM standalone
),
included AS (
  SELECT p.source_id
  FROM participants p
  LEFT JOIN member_counts mc ON mc.source_id = p.source_id
  WHERE (SELECT geometry FROM loc) IS NULL
    OR CASE WHEN coalesce(mc.n_members, 0) > 0 THEN EXISTS (
         SELECT 1
         FROM map_bounds.compilation_leaves(p.source_id, true) l
         WHERE l.source_id IN (SELECT source_id FROM covering)
       )
       ELSE p.source_id IN (SELECT source_id FROM covering)
    END
),
nodes AS (
  SELECT
    s.source_id,
    s.slug,
    /* A served layer carries its name on `map_layer`; its `maps.sources` row is
       a bridge minted by the schema and has none. */
    coalesce(s.name, ml.name) AS name,
    s.scale,
    ml.id IS NOT NULL AS is_served_layer,
    ml.id AS map_layer,
    ml.min_zoom,
    ml.max_zoom,
    coalesce(mc.n_members, 0) > 0 AS is_compilation,
    coalesce(mc.n_members, 0)::int AS n_members,
    map_bounds.holds_polygons(s.source_id) AS holds_polygons,
    coalesce(mc.n_members, 0) > 0
      AND map_bounds.holds_polygons(s.source_id) AS is_materialized,
    map_bounds.is_mosaic_member(s.source_id) AS is_mosaic_member,
    /* In no compilation at all. Not a kind either — just a map nothing has
       wrapped yet, which is worth seeing rather than silently omitting. */
    NOT EXISTS (
      SELECT 1 FROM linked l WHERE l.source_id = s.source_id
    ) AS is_standalone,
    /* Stage I supersession: a strictly-poorer map kept rather than deleted.
       Often the reason a map sits outside every compilation. */
    s.superseded_by,
    coalesce(lv.n_sources, 0)::int AS n_sources,
    cs.assembly_mode,
    cs.content,
    cs.state,
    ma.area_km::float AS area_km,
    /* The layer whose faces represent this map. A served layer *is* one, so it
       has none of its own. */
    ma.map_layer AS placed_in_layer
  FROM included i
  JOIN maps.sources s ON s.source_id = i.source_id
  LEFT JOIN member_counts mc ON mc.source_id = s.source_id
  LEFT JOIN source_counts lv ON lv.source_id = s.source_id
  LEFT JOIN map_bounds.compilation_sync cs ON cs.source_id = s.source_id
  LEFT JOIN map_bounds.map_layer ml ON ml.source_id = s.source_id
  LEFT JOIN map_bounds.map_area ma ON ma.source_id = s.source_id
)
SELECT
  coalesce((
    SELECT jsonb_agg(to_jsonb(n) ORDER BY n.slug) FROM nodes n
  ), '[]'::jsonb) AS nodes,
  coalesce((
    SELECT jsonb_agg(jsonb_build_object(
      'compilation_id', cm.compilation_id,
      'member_id', cm.member_id,
      /* Higher wins where members overlap; null in a disjoint mosaic. */
      'priority', cm.priority,
      'role', cm.role
    ) ORDER BY cm.compilation_id, cm.priority DESC NULLS LAST, cm.member_id)
    FROM map_bounds.compilation_member cm
    WHERE cm.compilation_id IN (SELECT source_id FROM included)
      AND cm.member_id IN (SELECT source_id FROM included)
  ), '[]'::jsonb) AS edges;
