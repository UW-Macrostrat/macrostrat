WITH first AS (
  SELECT ST_SetSRID((ST_Dump(
  ST_LocateAlong(
    ST_AddMeasure(my_line, 0, 200), generate_series(0, 200)
  )
  )).geom, 4326) AS geom FROM (
    SELECT ST_GeomFromText($1) AS my_line
  ) q
)
SELECT
  ST_X(geom) AS lng,
  ST_Y(geom) AS lat,
  round((ST_DistanceSphere(geom, $2) * 0.001)::numeric, 2)::float AS d,
  (
    SELECT elevation
    FROM (
        SELECT ST_Value(rast, 1, geom) AS elevation, 1 as priority
        FROM sources.srtm1
        WHERE ST_Intersects(geom, rast)
        UNION ALL
        SELECT ST_Value(rast, 1, geom) AS elevation, 2 as priority
        FROM sources.etopo1
        WHERE ST_Intersects(geom, rast)
    ) first
    WHERE elevation IS NOT NULL AND elevation != 0
    ORDER BY priority ASC
    LIMIT 1
  ) AS elevation
FROM first