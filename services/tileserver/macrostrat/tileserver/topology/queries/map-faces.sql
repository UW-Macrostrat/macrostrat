/* Solved faces, attributed at the level the request asked about.

   Faces are materialised per served layer, so a compilation that is not one
   borrows the faces of the layer it sits in, filtered to the maps it resolves to.
   By default each face is attributed to the *direct member* it is reached
   through -- from `carto-large` a British Columbia face belongs to `medium`, even
   though `bc_2017` is what actually owns it. `expand` attributes to that owning
   map instead.
*/
WITH tile AS (
  SELECT
    ST_TileEnvelope(:z, :x, :y) AS mercator_bbox,
    tile_layers.geographic_envelope(:x, :y, :z, 0.01) AS projected_bbox
), root AS (
  SELECT
    map_bounds.compilation_id(:map_layer) AS source_id,
    map_bounds.face_layer_for(map_bounds.compilation_id(:map_layer)) AS face_layer
), resolved AS (
  SELECT l.source_id, l.via
  FROM root
  CROSS JOIN LATERAL map_bounds.compilation_leaves(root.source_id) l
), map_faces AS (
  SELECT
    DISTINCT ON (f.id)
    f.id AS face_id,
    CASE WHEN :expand THEN r.source_id ELSE r.via END AS source_id,
    CASE WHEN :expand THEN s.name ELSE v.name END AS name,
    CASE WHEN :expand THEN s.slug ELSE v.slug END AS slug,
    s.scale,
    f.map_layer,
    tile_layers.tile_geom(
      ST_Intersection(f.geometry, tile.projected_bbox),
      tile.mercator_bbox
    ) AS geom
  FROM root
  JOIN map_bounds_topology.map_face f ON f.map_layer = root.face_layer
  JOIN tile ON ST_Intersects(f.geometry, tile.projected_bbox)
  -- Both levels are present in `map_face`. By default take the unit's own face,
  -- which for a standalone map is simply its face; `expand` takes the
  -- constituents instead.
  JOIN resolved r
    ON f.map_id = CASE WHEN :expand THEN r.source_id ELSE r.via END
  LEFT JOIN maps.sources s ON s.source_id = r.source_id
  LEFT JOIN maps.sources v ON v.source_id = r.via
)
SELECT ST_AsMVT(map_faces, 'map_faces', 4096, 'geom') FROM map_faces;
