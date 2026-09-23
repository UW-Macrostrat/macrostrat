WITH tile AS (
    SELECT
      ST_TileEnvelope(:z, :x, :y) AS mercator_bbox,
      tile_layers.geographic_envelope(:x, :y, :z, 0.01) AS projected_bbox,
      CASE WHEN :z < 3 THEN 'tiny'
           WHEN :z < 6 THEN 'carto-small'
           WHEN :z < 9 THEN 'carto-medium'
           ELSE 'carto-large'
      END AS layer_slug
),
map_bounds AS (
  SELECT
    mf.map_id AS source_id,
    ST_Intersection(mf.geometry, tile.projected_bbox) AS geometry,
    tile.mercator_bbox
  FROM map_bounds_topology.map_face mf
  JOIN tile
    ON ST_Intersects(mf.geometry, tile.projected_bbox)
  WHERE mf.map_layer = map_bounds.layer_id(tile.layer_slug)
),
/* Which polygons fill a face is `map_bounds.content_of`'s question: the face's
   owner need not hold them -- a mosaic member placed in a layer (Nevada from SGMC
   at `large`) shows its parent's polygons inside its footprint -- and the answer
   also carries the content's scale, which is the partition to prune to.

   `map_bounds.polygons_of` wraps this together with the polygon lookup, and is
   right for a caller with one map and one envelope. Lateral'ing it per face is
   not: the planner re-ran the mosaic walk per output row and lost the constant
   envelope it needs to reach the GiST index on `maps.polygons`, so every tile —
   including empty ones — sequentially scanned all four partitions (3.5M rows,
   a flat ~2.3 s per tile). Resolved once per face here, with the polygon and
   line lookups as plain indexed joins below, a sparse tile costs single-digit
   milliseconds and a dense one scales with what it contains. */
map_content AS MATERIALIZED (
  SELECT
    b.source_id,
    b.geometry,
    b.mercator_bbox,
    c.source_id AS content_id,
    c.footprint,
    cs.scale AS content_scale
  FROM map_bounds b
  CROSS JOIN LATERAL map_bounds.content_of(b.source_id) c
  JOIN maps.sources cs
    ON cs.source_id = c.source_id
   AND cs.scale = ANY(enum_range(NULL::maps.map_scale)::text[])
),
unit_features AS (
  SELECT
    p.map_id,
    b.source_id,
    l.*, -- legend info
    -- TODO: only run intersection if the map is partially visible
    tile_layers.tile_geom(ST_Intersection(p.geom, b.geometry), b.mercator_bbox) AS geom
  FROM map_content b
  JOIN maps.polygons p
    ON p.source_id = b.content_id
   AND p.scale = CAST(b.content_scale AS maps.map_scale)
   /* Written against the tile envelope, not `b.geometry`: the planner only
      reaches the GiST index with a value constant across the scan, and a face
      clipped per row is not one. The clipped face then prunes the survivors. */
   AND ST_Intersects(p.geom, tile_layers.geographic_envelope(:x, :y, :z, 0.01))
  JOIN maps.map_legend
    ON p.map_id = map_legend.map_id
  JOIN tile_layers.map_legend_info AS l
    ON l.legend_id = map_legend.legend_id
  WHERE ST_Intersects(p.geom, b.geometry)
    AND (b.footprint IS NULL OR ST_Contains(b.footprint, ST_PointOnSurface(p.geom)))
),
-- Lines
line_features AS (
  SELECT
    l.line_id,
    b.source_id,
    coalesce(l.descrip, '') AS descrip,
    coalesce(l.name, '') AS name,
    coalesce(l.direction, '') AS direction,
    coalesce(l.type, '') AS "type",
    cs.lines_oriented AS oriented,
    tile_layers.tile_geom(ST_Intersection(l.geom, b.geometry), b.mercator_bbox) AS geom
  FROM map_content b
  JOIN maps.lines l
    ON l.source_id = b.content_id
   AND l.scale = CAST(b.content_scale AS maps.map_scale)
   -- Constant across the scan, so the GiST index is reachable; see above.
   AND ST_Intersects(l.geom, tile_layers.geographic_envelope(:x, :y, :z, 0.01))
  -- `lines_oriented` belongs to whoever holds the lines.
  JOIN maps.sources cs ON cs.source_id = l.source_id
  WHERE ST_Intersects(l.geom, b.geometry)
    AND (b.footprint IS NULL OR ST_Contains(b.footprint, ST_PointOnSurface(l.geom)))
), units_tile AS (
  SELECT ST_AsMVT(unit_features, 'units') AS units
  FROM unit_features
), lines_tile AS (
  SELECT ST_AsMVT(line_features, 'lines') AS lines
  FROM line_features
)
SELECT units || lines
FROM units_tile, lines_tile;
