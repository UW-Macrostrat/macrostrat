WITH mvt_features AS (
  SELECT
    source_id,
    rgeom geom
  FROM maps.sources
  WHERE
    rgeom is NOT NULL
    AND status_code = 'active'
    AND ST_Intersects(geom, ST_Transform(:envelope, 4326))

)
SELECT
  source_id,
  tile_layers.tile_geom(z.geom, :envelope) AS geom
FROM mvt_features z
