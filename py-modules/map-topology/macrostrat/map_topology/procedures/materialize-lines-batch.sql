/** One batch of `materialize`'s line pass: the next `:limit` member lines after
  `:after`, each clipped to the faces its map owns in `:layer`, written as the
  compilation's lines.

  The same select-and-clip as `materialize-batch.sql`, so a line survives exactly
  where its map's polygons do: a bedrock contact under surficial cover is cut
  away with the bedrock it bounds. Membership in a mosaic member's footprint uses
  the representative-point test of `lines_of`.

  `orig_id` is the member line's `line_id`. Lines carry no legend link, so they
  cannot show they are a cache; `dematerialize` removes them on the strength of
  the polygon check. Returns the batch's last source line, its size, and how
  many lines were written. */
WITH member AS (
  SELECT cm.member_id, c.source_id AS content_id, c.footprint, cs.scale AS content_scale
  FROM map_bounds.compilation_member cm
  CROSS JOIN LATERAL map_bounds.content_of(cm.member_id) c
  JOIN maps.sources cs
    ON cs.source_id = c.source_id
   AND cs.scale = ANY (enum_range(NULL::maps.map_scale)::text[])
  WHERE cm.compilation_id = :compilation_id
),
batch AS MATERIALIZED (
  SELECT
    m.member_id,
    l.line_id,
    l.name, l.type_legacy, l.direction_legacy, l.descrip, l.type, l.direction,
    l.geom
  FROM member m
  JOIN maps.lines l
    ON l.source_id = m.content_id
   AND l.scale = CAST(m.content_scale AS maps.map_scale)
  WHERE l.line_id > :after
    AND (m.footprint IS NULL OR ST_Contains(m.footprint, ST_PointOnSurface(l.geom)))
  ORDER BY l.line_id
  LIMIT :limit
),
windowed AS MATERIALIZED (
  SELECT b.*, w.face
  FROM batch b
  CROSS JOIN LATERAL (
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
    b.line_id, b.name, b.type_legacy, b.direction_legacy, b.descrip, b.type,
    b.direction,
    ST_CollectionExtract(
      CASE WHEN ST_Covers(b.face, ST_Envelope(b.geom)) THEN b.geom
           ELSE ST_Intersection(b.geom, b.face) END,
      2
    ) AS geom
  FROM windowed b
  WHERE b.face IS NOT NULL
),
written AS (
  INSERT INTO maps.lines (
    source_id, scale, orig_id, name, type_legacy, direction_legacy, descrip,
    type, direction, geom
  )
  SELECT
    :compilation_id, CAST(:scale AS maps.map_scale),
    c.line_id::text, c.name, c.type_legacy, c.direction_legacy, c.descrip,
    c.type, c.direction, ST_Multi(c.geom)
  FROM clipped c
  -- A clip can leave a zero-length sliver, which the table's check refuses.
  WHERE NOT ST_IsEmpty(c.geom)
    AND ST_IsValid(c.geom)
  RETURNING line_id
)
SELECT
  (SELECT max(line_id) FROM batch) AS last_id,
  (SELECT count(*) FROM batch) AS read,
  (SELECT count(*) FROM written) AS written
