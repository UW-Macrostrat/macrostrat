/* The topology edges of a compilation's maps: every map ranked in the layer it
   draws at the tile's zoom (for `carto`, its member's), whose boundaries are
   barriers there. `:map_layer` is the compilation's slug. */
WITH tile AS (
  SELECT
    ST_TileEnvelope(:z, :x, :y) AS mercator_bbox,
    tile_layers.geographic_envelope(:x, :y, :z, 0.01) AS projected_bbox
  ),
  compilation_maps AS MATERIALIZED (
    SELECT ts.source_id
    FROM map_bounds.map_priority mp
    CROSS JOIN LATERAL map_bounds.topology_sources_of(mp.map_id) ts
    WHERE mp.map_layer = map_bounds.face_layer_for(map_bounds.source_id(:map_layer), :z)
  ),
  e0 AS (
    SELECT
      e.edge_id,
      e.start_node,
      e.end_node,
      tile_layers.tile_geom(
        ST_Intersection(geom, tile.projected_bbox),
        tile.mercator_bbox
      ) AS geom
    FROM map_bounds_topology.edge_data e
    JOIN tile ON ST_Intersects(geom, tile.projected_bbox)
    JOIN map_bounds_topology.__edge_relation er
      ON er.edge_id = e.edge_id
    WHERE er.line_id IN (SELECT source_id FROM compilation_maps)
  ),
  n0 AS (
    SELECT
      tile_layers.tile_geom(
        n.geom,
        tile.mercator_bbox
      ) AS geom
    FROM map_bounds_topology.node n
    JOIN tile ON ST_Intersects(geom, tile.projected_bbox)
    JOIN e0 ON n.node_id = e0.start_node OR n.node_id = e0.end_node
  ),
  edges AS (
    SELECT edge_id, geom FROM e0
  ),
  nodes AS (
    SELECT geom FROM n0 GROUP BY geom
  )
SELECT (SELECT ST_AsMVT(edges, 'edges', 4096, 'geom') FROM edges)
    || (SELECT ST_AsMVT(nodes, 'nodes', 4096, 'geom') FROM nodes) AS mvt;
