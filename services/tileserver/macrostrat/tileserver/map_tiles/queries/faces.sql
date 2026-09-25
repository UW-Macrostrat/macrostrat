/* A tile of a compilation that has faces, drawn through them.

   `:layer_id` is the `map_layer` row of the compilation being drawn -- which one
   answers a request is decided before this runs, by `map_bounds.serving_source`
   (the multiscale hop for `carto`) in the route. No zoom logic lives here.

   Shape, and why (measured on the z6 Midwest tile that took 28 s):

   1. Faces say which maps win where. They are collected *per map* and clipped to
      the tile, so a map with forty sliver faces is one row and its polygons are
      fetched once. Member-level faces (a compilation with no content of its own)
      are skipped: they exist for attribution, not for drawing.
   2. Each map's content is resolved once (`content_of`: itself, or the mosaic
      holding its polygons).
   3. Polygons are fetched through the clipped faces (that is the index condition)
      and immediately clipped to the tile and simplified to the tile's own
      resolution. This is where the time was: a state-map polygon of 400k
      vertices is a few hundred inside one tile, and transforming and snapping
      the full thing cost 20 of the 28 seconds. Sub-pixel polygons collapse and
      drop out.
   4. Ownership: a polygon whose bounding box the map's face covers is inside it
      and needs nothing more. Only the ones straddling a face edge -- a few
      percent -- are repaired if simplification left them invalid (`ST_Buffer(0)`,
      three times cheaper than `ST_MakeValid` here) and clipped to the face.
   5. Then the legend and the tile encoding, over what survives.

   Every stage is a MATERIALIZED CTE on purpose: a subquery column referenced
   twice has its expression evaluated twice, and the geometry expressions here
   are the whole cost. */
WITH tile AS (
    SELECT
      ST_TileEnvelope(:z, :x, :y) AS mercator_bbox,
      tile_layers.geographic_envelope(:x, :y, :z, 0.01) AS projected_bbox,
      -- Half a unit of the 2048-unit tile grid `tile_geom` encodes to.
      360.0 / power(2, :z) / 4096 AS tolerance
),
map_bounds AS MATERIALIZED (
  SELECT
    mf.map_id AS source_id,
    ST_UnaryUnion(ST_Collect(ST_ClipByBox2D(mf.geometry, tile.projected_bbox))) AS geometry
  FROM map_bounds_topology.map_face mf
  JOIN tile ON ST_Intersects(mf.geometry, tile.projected_bbox)
  WHERE mf.map_layer = :layer_id
    AND map_bounds.has_content(mf.map_id)
  GROUP BY mf.map_id
),
map_content AS MATERIALIZED (
  SELECT
    b.source_id,
    b.geometry,
    c.source_id AS content_id,
    c.footprint,
    cs.scale AS content_scale,
    cs.lines_oriented
  FROM map_bounds b
  CROSS JOIN LATERAL map_bounds.content_of(b.source_id) c
  JOIN maps.sources cs
    ON cs.source_id = c.source_id
   AND cs.scale = ANY(enum_range(NULL::maps.map_scale)::text[])
),
-- Units
unit_clipped AS MATERIALIZED (
  SELECT
    p.map_id,
    b.source_id,
    b.geometry AS face,
    ST_Simplify(
      ST_ClipByBox2D(p.geom, (SELECT projected_bbox FROM tile)),
      (SELECT tolerance FROM tile)
    ) AS geom
  FROM map_content b
  JOIN maps.polygons p
    ON p.source_id = b.content_id
   AND p.scale = CAST(b.content_scale AS maps.map_scale)
   AND ST_Intersects(p.geom, b.geometry)
  -- A mosaic member reads its holder's polygons through its own footprint.
  WHERE b.footprint IS NULL OR ST_Contains(b.footprint, ST_PointOnSurface(p.geom))
),
unit_owned AS MATERIALIZED (
  SELECT
    map_id,
    source_id,
    CASE WHEN ST_Covers(face, ST_Envelope(geom)) THEN geom
         ELSE ST_Intersection(
           CASE WHEN ST_IsValid(geom) THEN geom ELSE ST_Buffer(geom, 0) END,
           face)
    END AS geom
  FROM unit_clipped
  WHERE geom IS NOT NULL AND NOT ST_IsEmpty(geom)
),
unit_features AS (
  SELECT
    u.map_id,
    u.source_id,
    l.*, -- legend info
    tile_layers.tile_geom(u.geom, (SELECT mercator_bbox FROM tile)) AS geom
  FROM unit_owned u
  JOIN maps.map_legend
    ON u.map_id = map_legend.map_id
  JOIN tile_layers.map_legend_info AS l
    ON l.legend_id = map_legend.legend_id
),
-- Lines, the same way; a line needs no validity repair.
line_clipped AS MATERIALIZED (
  SELECT
    l.line_id,
    b.source_id,
    b.geometry AS face,
    b.lines_oriented,
    coalesce(l.descrip, '') AS descrip,
    coalesce(l.name, '') AS name,
    coalesce(l.direction, '') AS direction,
    coalesce(l.type, '') AS "type",
    ST_Simplify(
      ST_ClipByBox2D(l.geom, (SELECT projected_bbox FROM tile)),
      (SELECT tolerance FROM tile)
    ) AS geom
  FROM map_content b
  JOIN maps.lines l
    ON l.source_id = b.content_id
   AND l.scale = CAST(b.content_scale AS maps.map_scale)
   AND ST_Intersects(l.geom, b.geometry)
  WHERE b.footprint IS NULL OR ST_Contains(b.footprint, ST_PointOnSurface(l.geom))
),
line_features AS (
  SELECT
    line_id,
    source_id,
    descrip,
    name,
    direction,
    "type",
    lines_oriented AS oriented,
    tile_layers.tile_geom(
      CASE WHEN ST_Covers(face, ST_Envelope(geom)) THEN geom
           ELSE ST_Intersection(geom, face) END,
      (SELECT mercator_bbox FROM tile)) AS geom
  FROM line_clipped
  WHERE geom IS NOT NULL AND NOT ST_IsEmpty(geom)
), units_tile AS (
  SELECT ST_AsMVT(unit_features, 'units') AS units
  FROM unit_features
), lines_tile AS (
  SELECT ST_AsMVT(line_features, 'lines') AS lines
  FROM line_features
)
SELECT units || lines
FROM units_tile, lines_tile;
