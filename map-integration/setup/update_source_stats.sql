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

/*
WITH a AS (
select st_union(st_envelope(geom)) geometry from maps.small
WHERE source_id = 11
)
update maps.sources
set ref_geom = a.geometry
from a
where source_id = 11;
*/
