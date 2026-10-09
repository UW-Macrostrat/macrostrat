/** One batch of `materialize`: the next `:limit` member polygons after
  `:after`, each clipped to the faces its map owns in the compilation's own
  solved layer, written as the compilation's polygons.

  The faces are the priority, already resolved: in `:layer` a map owns exactly
  the territory it wins among the compilation's members, so clipping a polygon to
  its map's faces is the whole of the assembly -- the same select-and-clip the
  tiles do. Each polygon reads its map's faces only inside its own bounding box,
  padded by `:pad`, so a face of 155,000 vertices costs a polygon no more than
  the part of it that polygon can touch. A polygon whose box a face covers is
  copied untouched; one straddling an ownership edge is intersected with the
  windowed faces; one its map owns no face under is dropped.

  Nothing here is visible until the compilation is finalized
  (`materialize-compilation.sql`): until then it is not materialized, so
  resolution still descends to its members. That is what lets batches commit as
  they go and a stopped run resume after the last polygon it wrote.

  Each written polygon records where it came from: `orig_id` is the member
  polygon's `map_id`, and its legend link is the member's legend entry, which is
  what makes the result recognisable as a cache (`is_derived`) and removable
  (`dematerialize`). Returns the batch's last source polygon, its size, and how
  many polygons were written. */
WITH member AS (
  SELECT cm.member_id, c.source_id AS content_id, c.footprint, cs.scale AS content_scale
  FROM map_bounds.compilation_member cm
  -- Wherever the member's content is: its own polygons, or for a mosaic member
  -- its mosaic's inside its footprint.
  CROSS JOIN LATERAL map_bounds.content_of(cm.member_id) c
  JOIN maps.sources cs
    ON cs.source_id = c.source_id
   AND cs.scale = ANY (enum_range(NULL::maps.map_scale)::text[])
  WHERE cm.compilation_id = :compilation_id
),
batch AS MATERIALIZED (
  SELECT
    m.member_id,
    p.map_id,
    p.name, p.strat_name, p.age, p.lith, p.descrip, p.comments,
    p.t_interval, p.b_interval,
    p.geom
  FROM member m
  JOIN maps.polygons p
    ON p.source_id = m.content_id
   AND p.scale = CAST(m.content_scale AS maps.map_scale)
  WHERE p.map_id > :after
    AND (m.footprint IS NULL OR ST_Contains(m.footprint, ST_PointOnSurface(p.geom)))
  ORDER BY p.map_id
  LIMIT :limit
),
windowed AS MATERIALIZED (
  SELECT b.*, w.face
  FROM batch b
  CROSS JOIN LATERAL (
    /* `ST_ClipByBox2D` is fast because it does not promise a valid result, and
       the union of an invalid piece fails ("unable to assign free hole to a
       shell"). Each piece is windowed to one polygon's box, so making it valid
       costs little. */
    SELECT ST_UnaryUnion(ST_Collect(
      ST_MakeValid(ST_ClipByBox2D(f.geometry, ST_Expand(ST_Envelope(b.geom), :pad)))
    )) AS face
    FROM map_bounds_topology.map_face f
    WHERE f.map_layer = :layer
      AND f.map_id = b.member_id
      AND f.geometry && ST_Expand(ST_Envelope(b.geom), :pad)
  ) w
),
clipped AS MATERIALIZED (
  SELECT
    b.map_id, b.name, b.strat_name, b.age, b.lith, b.descrip, b.comments,
    b.t_interval, b.b_interval,
    ST_CollectionExtract(
      CASE WHEN ST_Covers(b.face, ST_Envelope(b.geom)) THEN b.geom
           ELSE ST_Intersection(b.geom, b.face) END,
      3
    ) AS geom
  FROM windowed b
  WHERE b.face IS NOT NULL
),
/* With no `map_id`: the table's default draws from `maps.map_ids`, the one
   sequence ingestion uses too. */
written AS (
  INSERT INTO maps.polygons (
    source_id, scale, orig_id, name, strat_name, age, lith, descrip,
    comments, t_interval, b_interval, geom
  )
  SELECT
    :compilation_id, CAST(:scale AS maps.map_scale),
    c.map_id::text, c.name, c.strat_name, c.age, c.lith, c.descrip,
    c.comments, c.t_interval, c.b_interval, ST_Multi(c.geom)
  FROM clipped c
  WHERE NOT ST_IsEmpty(c.geom)
  RETURNING map_id, orig_id
),
/* Attribution follows the polygon: a piece keeps the legend unit of the
   member polygon it came from. */
linked AS (
  INSERT INTO maps.map_legend (legend_id, map_id)
  SELECT ml.legend_id, w.map_id
  FROM written w
  JOIN maps.map_legend ml ON ml.map_id = CAST(w.orig_id AS integer)
  ON CONFLICT (legend_id, map_id) DO NOTHING
  RETURNING 1
)
SELECT
  (SELECT max(map_id) FROM batch) AS last_id,
  (SELECT count(*) FROM batch) AS read,
  (SELECT count(*) FROM written) AS written
