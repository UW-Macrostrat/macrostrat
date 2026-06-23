/** Get primitive faces */
WITH tile AS (
  SELECT
    ST_TileEnvelope(:z, :x, :y) AS mercator_bbox,
    tile_layers.geographic_envelope(:x, :y, :z, 0.01) AS projected_bbox
),
faces AS (
  SELECT
    f.face_id
  FROM map_bounds_topology.face f
  JOIN tile
    ON f.mbr && tile.projected_bbox
  WHERE f.face_id <> 0
    AND ST_Area(tile_layers.tile_geom(mbr::geometry, mercator_bbox)) > 256
),
face_geoms AS (
  SELECT
    fd.face_id,
    tile_layers.tile_geom(
      ST_Intersection(fd.geometry, tile.projected_bbox),
      tile.mercator_bbox
    ) AS geom
  FROM faces
  CROSS JOIN tile
  JOIN map_bounds_topology.face_data fd
    ON faces.face_id = fd.face_id
)
SELECT ST_AsMVT(face_geoms, 'faces', 4096, 'geom') FROM face_geoms;
