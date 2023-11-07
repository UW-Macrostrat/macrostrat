CREATE TABLE elevation_stats AS
WITH first AS (
 SELECT map_id, (ST_Intersection(geom, rast)).val
 FROM sources.etopo1
 INNER JOIN maps.tiny ON ST_Intersects(rast, geom)
)

SELECT map_id, COUNT(val), SUM(val), AVG(val), stddev(val), MIN(val), MAX(val)
FROM first
GROUP BY map_id;

INSERT INTO elevation_stats (map_id, count, sum, avg, stddev, min, max)
WITH first AS (
 SELECT map_id, (ST_Intersection(geom, rast)).val
 FROM sources.etopo1
 INNER JOIN maps.small ON ST_Intersects(rast, geom)
)

SELECT map_id, COUNT(val), SUM(val), AVG(val), stddev(val), MIN(val), MAX(val)
FROM first
GROUP BY map_id;

INSERT INTO elevation_stats (map_id, count, sum, avg, stddev, min, max)
WITH first AS (
 SELECT map_id, (ST_Intersection(geom, rast)).val
 FROM sources.etopo1
 INNER JOIN maps.medium ON ST_Intersects(rast, geom)
)

SELECT map_id, COUNT(val), SUM(val), AVG(val), stddev(val), MIN(val), MAX(val)
FROM first
GROUP BY map_id;

INSERT INTO elevation_stats (map_id, count, sum, avg, stddev, min, max)
WITH first AS (
 SELECT map_id, (ST_Intersection(geom, rast)).val
 FROM sources.etopo1
 INNER JOIN maps.large ON ST_Intersects(rast, geom)
)

SELECT map_id, COUNT(val), SUM(val), AVG(val), stddev(val), MIN(val), MAX(val)
FROM first
GROUP BY map_id;
