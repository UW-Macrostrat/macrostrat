/* The map units at a location, resolved through the compilation system.

   Two phases, which is the shape the topology exists to make possible:

     1. `map_face` is a *partition* of each layer -- non-overlapping footprints,
        one per source region, saying which map wins where. One indexed lookup
        against it answers "whose polygons are here", and returns a handful of
        rows.
     2. For each of those faces, one indexed lookup for that map's polygons:
        `source_id` and `scale` prune `maps.polygons` to a single partition and
        a single map before the GiST index is consulted.

   The step between them is `content_of`, which says where a map actually keeps
   its polygons -- itself, or for a mosaic member the ancestor that holds them,
   read through the member's own footprint. It is resolved **once per face**.

   `map_bounds.polygons_of` wraps steps 2 and 3 together, and is right for a
   caller with one map and one envelope (the single-map tile query). Lateral'ing
   it per face is not: the planner re-runs the mosaic walk per *output polygon*
   rather than per face, and loses the constant envelope it needs to reach the
   GiST index. Splitting it here keeps the ownership rules in `content_of` and
   the spatial work in one plain join.

   Nothing is chosen here. A request against a stack of layers gets every
   layer's answer, flagged with which one the caller's zoom would have drawn,
   because "the two cartos disagree" often means "they resolved at different
   layers" -- which is invisible if the server picks one.

   Legend fields are coalesced over the polygon's own columns: a polygon whose
   map has no legend entry still names itself. `map_id` and `orig_id` are there
   so a client can go to the polygon for the source map's unedited text.
*/
WITH target AS (
  SELECT
    s.source_id,
    s.slug,
    ml.id AS layer_id,
    ml.slug AS layer_slug
  FROM maps.sources s
  LEFT JOIN map_bounds.map_layer ml ON ml.source_id = s.source_id
  WHERE s.slug = ANY(CAST(:slugs AS text[]))
),
/* Phase 1: the layer's coverage here. A map asked for directly has no face and
   answers for itself. */
faces AS MATERIALIZED (
  SELECT
    t.layer_id,
    t.layer_slug,
    mf.id AS map_face_id,
    mf.map_id AS source_id
  FROM target t
  JOIN map_bounds_topology.map_face mf ON mf.map_layer = t.layer_id
  WHERE t.layer_id IS NOT NULL
    AND ST_Intersects(mf.geometry, ST_SetSRID(ST_GeomFromText(:bounds), 4326))
  UNION ALL
  SELECT NULL, NULL, NULL, t.source_id
  FROM target t
  WHERE t.layer_id IS NULL
),
/* Where each face's map keeps its polygons, and at what scale. MATERIALIZED so
   the mosaic walk runs once per face -- which is the difference between this
   and lateral'ing `polygons_of`.

   Face geometry is deliberately absent: a face is a whole map's dissolve (the
   largest is 189k points), so carrying it through a CTE -- or clipping it to
   the request, which copies it -- is how this turns into a memory problem. The
   one test that needs it fetches it by id at the end. */
holders AS MATERIALIZED (
  SELECT
    f.layer_id,
    f.layer_slug,
    f.map_face_id,
    c.source_id AS content_id,
    c.footprint,
    cs.scale AS content_scale
  FROM faces f
  CROSS JOIN LATERAL map_bounds.content_of(f.source_id) c
  JOIN maps.sources cs
    ON cs.source_id = c.source_id
   /* `maps.sources.scale` is free text, so the partition-key cast is guarded to
      real keys, as `polygons_of` guards it. */
   AND cs.scale = ANY(enum_range(NULL::maps.map_scale)::text[])
),
/* Phase 2: one indexed lookup per face for the polygons themselves, ordered and
   capped here. Everything below only *decorates* a row -- names, legend text,
   interval names -- so it runs against at most `:limit` rows instead of against
   everything the request contains. Left inline, those lookups dominated an area
   request: the planner estimates one row out of the spatial join, picks nested
   loops, and rescans `maps.sources` and `macrostrat.intervals` per polygon. */
units AS (
  SELECT
    h.layer_id,
    h.layer_slug,
    h.map_face_id,
    mp.priority_path,
    mp.via,
    p.map_id,
    p.orig_id,
    p.scale,
    p.source_id,
    p.name,
    p.strat_name,
    p.age,
    p.lith,
    p.descrip,
    p.comments,
    p.t_interval,
    p.b_interval
  FROM holders h
  JOIN maps.polygons p
    ON p.source_id = h.content_id
   AND p.scale = CAST(h.content_scale AS maps.map_scale)
   AND ST_Intersects(p.geom, ST_SetSRID(ST_GeomFromText(:bounds), 4326))
  LEFT JOIN map_bounds.map_priority mp
    ON mp.map_layer = h.layer_id
   AND mp.source_id = p.source_id
  /* The face bounds what its map answers for. Redundant for a point -- the face
     and the polygon both contain it -- but an area request can span several
     faces, and a map's polygons must not be reported where another map's face
     covers them. Fetched by id and tested against the polygon's representative
     point, the way `content_of` footprints are tested. */
  WHERE (
      h.map_face_id IS NULL
      OR EXISTS (
        SELECT 1
        FROM map_bounds_topology.map_face f
        WHERE f.id = h.map_face_id
          AND ST_Contains(f.geometry, ST_PointOnSurface(p.geom))
      )
    )
    /* A mosaic member reads its ancestor's polygons through its own footprint. */
    AND (
      h.footprint IS NULL
      OR ST_Contains(h.footprint, ST_PointOnSurface(p.geom))
    )
  ORDER BY
    /* Layers coarse to fine, then the highest-priority map within each. */
    h.layer_id NULLS FIRST,
    mp.priority_path DESC NULLS LAST,
    p.map_id
  LIMIT :limit
)
SELECT
  u.layer_slug AS map_layer,
  /* NULL-safe on both sides: no layer, or no current layer, is not a match. */
  coalesce(u.layer_slug = CAST(:current_layer AS text), false) AS is_current_layer,
  u.map_face_id,
  u.map_id,
  u.orig_id,
  u.scale,
  u.source_id,
  s.slug AS source_slug,
  s.name AS source_name,
  /* Rank within the layer, as the path of priorities taken on the way down to
     this map. Null outside a layer, or before the layer has been solved. */
  array_to_string(u.priority_path, '.') AS priority,
  coalesce(u.priority_path, '{}') AS priority_path,
  /* The member of the layer this map is presented as -- a face in `carto-large`
     belongs to member `medium` from the layer's point of view even when the map
     that owns it is further down. */
  u.via AS unit_id,
  v.slug AS unit_slug,
  v.name AS unit_name,
  l.legend_id,
  coalesce(l.name, u.name) AS map_unit_name,
  coalesce(l.strat_name, u.strat_name) AS strat_name,
  coalesce(l.age, u.age) AS age,
  coalesce(l.lith, u.lith) AS lith,
  coalesce(l.descrip, u.descrip) AS descrip,
  coalesce(l.comments, u.comments) AS comments,
  l.best_age_top::float AS t_age,
  l.best_age_bottom::float AS b_age,
  coalesce(l.t_interval, u.t_interval) AS t_interval,
  /* Joined on each candidate separately rather than on a `coalesce` of the two:
     a coalesce in the join condition is not an indexable key, and the interval
     table then gets rescanned per row. */
  coalesce(lti.interval_name, uti.interval_name) AS t_int_name,
  coalesce(l.b_interval, u.b_interval) AS b_interval,
  coalesce(lbi.interval_name, ubi.interval_name) AS b_int_name,
  l.color,
  coalesce(l.lith_ids, '{}') AS lith_id,
  coalesce(l.all_lith_types, '{}') AS lith_types,
  coalesce(l.all_lith_classes, '{}') AS lith_classes,
  coalesce(l.strat_name_ids, '{}') AS strat_name_id,
  coalesce(l.unit_ids, '{}') AS unit_ids
FROM units u
JOIN maps.sources s ON s.source_id = u.source_id
LEFT JOIN maps.sources v ON v.source_id = u.via
LEFT JOIN maps.map_legend ON map_legend.map_id = u.map_id
LEFT JOIN maps.legend l ON l.legend_id = map_legend.legend_id
LEFT JOIN macrostrat.intervals lti ON lti.id = l.t_interval
LEFT JOIN macrostrat.intervals uti ON uti.id = u.t_interval
LEFT JOIN macrostrat.intervals lbi ON lbi.id = l.b_interval
LEFT JOIN macrostrat.intervals ubi ON ubi.id = u.b_interval
ORDER BY
  u.layer_id NULLS FIRST,
  u.priority_path DESC NULLS LAST,
  u.map_id;
