WITH tile AS (
  SELECT
    ST_TileEnvelope(:z, :x, :y) AS mercator_bbox,
    tile_layers.geographic_envelope(:x, :y, :z, 0.01) AS projected_bbox
  ),
  edges AS (
    SELECT
      edge_id,
      tile_layers.tile_geom(
        ST_Intersection(geom, tile.projected_bbox),
        tile.mercator_bbox
      ) AS geom
    FROM map_bounds_topology.edge_data e
    JOIN tile ON ST_Intersects(geom, tile.projected_bbox)
  ),
  n0 AS (
    SELECT
      tile_layers.tile_geom(
        n.geom,
        tile.mercator_bbox
      ) AS geom
    FROM map_bounds_topology.node n
    JOIN tile ON ST_Intersects(geom, tile.projected_bbox)
  ),
  nodes AS (
    SELECT geom FROM n0 GROUP BY geom
  )
SELECT (SELECT ST_AsMVT(edges, 'edges', 4096, 'geom') FROM edges)
    || (SELECT ST_AsMVT(nodes, 'nodes', 4096, 'geom') FROM nodes) AS mvt;
