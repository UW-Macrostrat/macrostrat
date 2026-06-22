WITH tile AS (
  SELECT
    ST_TileEnvelope(:z, :x, :y) AS mercator_bbox,
    tile_layers.geographic_envelope(:x, :y, :z, 0.01) AS projected_bbox
),
map_faces AS (
  SELECT
    s.source_id,
    s.name,
    s.slug,
    s.scale,
    f.map_layer,
    tile_layers.tile_geom(
      ST_Intersection(geometry, tile.projected_bbox),
      tile.mercator_bbox
    ) AS geom
  FROM map_bounds_topology.map_face f
  JOIN tile ON ST_Intersects(geometry, tile.projected_bbox)
  JOIN maps.sources s ON f.map_id = s.source_id
  WHERE f.map_layer = map_bounds.layer_id(:map_layer)
)
SELECT ST_AsMVT(map_faces, 'map_faces', 4096, 'geom') FROM map_faces;
