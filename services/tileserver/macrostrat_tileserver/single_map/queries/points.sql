
  SELECT
    strike,
    dip,
    dip_dir,
    point_type,
    certainty,
    comments,
    tile_layers.tile_geom(geom, :envelope) AS geom
  FROM maps.points
  WHERE source_id = :source_id
    AND ST_Intersects(geom, ST_Transform(:envelope, 4326))
