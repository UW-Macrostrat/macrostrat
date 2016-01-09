WITH first AS (
  SELECT map_id, source_id, geom FROM maps.tiny
  UNION
  SELECT map_id, source_id, geom FROM maps.small
  UNION
  SELECT map_id, source_id, geom FROM maps.medium
  UNION
  SELECT map_id, source_id, geom FROM maps.large
),
second AS (
  SELECT source_id, round(sum(ST_Area(geom::geography)*0.000001)) area, COUNT(*) features, ST_Extent(geom) AS envelope
  FROM first
  GROUP BY source_id
)
UPDATE maps.sources AS a
SET area = s.area, features = s.features, bbox = s.envelope
FROM second AS s
WHERE s.source_id = a.source_id;
