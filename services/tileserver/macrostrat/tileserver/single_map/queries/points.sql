
  SELECT
    strike,
    dip,
    dip_dir,
    point_type,
    certainty,
    comments,
    tile_layers.tile_geom(geom, :envelope) AS geom
  FROM maps.points p
  JOIN maps.sources s
  WHERE p.source_id = s.source_id
    AND ST_Intersects(geom, ST_Transform(:envelope, 4326))
