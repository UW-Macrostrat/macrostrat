WITH next_polygons AS (
  SELECT
    map_id,
    scale,
    geom,
    row_number() OVER () AS row_num
  FROM carto.polygons
  ORDER BY map_id, scale
),
next_cursor AS (
  SELECT * FROM next_polygons
  WHERE row_num > :last_row
  LIMIT :chunk_size
),
ingested AS (
  INSERT INTO corelle_macrostrat.carto_plate_index
  SELECT
    p.map_id,
    p.scale,
    pp.model_id model_id,
    pp.plate_id,
    pp.id plate_polygon_id,
    CASE WHEN ST_Covers(pp.geometry, p.geom) THEN
      NULL  
    ELSE
      ST_Intersection(pp.geometry, p.geom)
    END AS geom
  FROM next_cursor p
  JOIN corelle.plate_polygon pp
    ON ST_Intersects(p.geom, pp.geometry)
  ON CONFLICT DO NOTHING
)
SELECT max(row_num) last_row
FROM next_cursor;