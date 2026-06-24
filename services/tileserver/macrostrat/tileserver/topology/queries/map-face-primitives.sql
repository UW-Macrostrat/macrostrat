/** Primitive topology faces for the whole topology (no map layer selected).
 *
 * Performance: face_data computes ST_GetFaceGeometry per face and has no
 * spatial index, so filtering on its geometry forces reconstruction of every
 * face. Instead we prune candidates on the stored, GIST-indexed `mbr`:
 *   1. `mbr && projected_bbox` — only faces overlapping the tile.
 *   2. a zoom-dependent size cull — drop faces whose MBR is smaller than ~a
 *      pixel and a half, using the tile's own longitude span as the
 *      degrees-per-pixel scale (approximate; ignores Mercator's latitude
 *      stretch, which is fine for a visibility cull).
 * Both run off `mbr` alone, so ST_GetFaceGeometry is only ever called for the
 * faces that survive — which keeps low zooms tractable.
 */
WITH tile AS (
  SELECT
    ST_TileEnvelope(:z, :x, :y) AS mercator_bbox,
    tile_layers.geographic_envelope(:x, :y, :z, 0.01) AS projected_bbox
),
params AS (
  SELECT
    mercator_bbox,
    projected_bbox,
    -- tile longitude span / 256px * minimum drawable size in px
    (ST_XMax(projected_bbox) - ST_XMin(projected_bbox)) / 256.0 * 1.5 AS min_size
  FROM tile
),
candidates AS (
  SELECT f.face_id
  FROM map_bounds_topology.face f, params p
  WHERE f.face_id <> 0
    AND f.mbr && p.projected_bbox
    AND greatest(
          ST_XMax(f.mbr) - ST_XMin(f.mbr),
          ST_YMax(f.mbr) - ST_YMin(f.mbr)
        ) >= p.min_size
),
face_primitives AS (
  SELECT
    c.face_id,
    tile_layers.tile_geom(
      ST_Intersection(
        topology.ST_GetFaceGeometry('map_bounds_topology', c.face_id),
        p.projected_bbox
      ),
      p.mercator_bbox
    ) AS geom
  FROM candidates c, params p
)
SELECT ST_AsMVT(face_primitives, 'faces', 4096, 'geom')
FROM face_primitives
WHERE geom IS NOT NULL AND NOT ST_IsEmpty(geom);
