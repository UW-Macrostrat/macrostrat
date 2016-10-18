DROP TABLE IF EXISTS carto.small;
-- Format small
create table carto.small as
-- Get the reference geom of all sources flagged as 'small' and with high priority
WITH priority_ref AS (
  SELECT 1 AS id, ST_SetSRID(ST_Union(rgeom), 4326) geom
  FROM maps.sources
  WHERE scale = 'small'
  AND priority IS TRUE
),
-- Get the actual geometries that belong to the above scale and priority
priorities AS (
  SELECT s.map_id, s.geom
  FROM maps.small s
  JOIN maps.sources ON s.source_id = sources.source_id
  WHERE priority IS TRUE
),
-- Get all polygons of the target source that DON'T intersect the reference geometry of high priority sources
-- These don't need to be cut!
nonpriority_unique AS (
  SELECT s.map_id, s.geom
  FROM maps.small s
  JOIN maps.sources ON s.source_id = sources.source_id
  LEFT JOIN priority_ref pr
  ON ST_Intersects(s.geom, st_setsrid(pr.geom, 4326))
  WHERE pr.id IS NULL
  AND priority IS FALSE
  AND ST_Geometrytype(s.geom) != 'ST_LineString'
),
-- Get all polygons of the target scale that intersect the reference geometry of the high priority sources
-- Cut them by the high priority sources
nonpriority_clipped AS (
  SELECT s.map_id, ST_Difference(s.geom, pr.geom) geom
  FROM maps.small s
  JOIN priority_ref pr
  ON ST_Intersects(s.geom, pr.geom)
  JOIN maps.sources ON s.source_id = sources.source_id
  WHERE priority IS FALSE
),
-- Join together:
--    + All geometries that are high priority (never cut)
--    + Low priority geometries that don't intersect the high priority ones
--    + Low priority geometries that DO intersect the high priority ones
small AS (
  SELECT map_id, geom
  FROM priorities
  WHERE ST_NumGeometries(geom) > 0
  UNION
  SELECT map_id, geom
  FROM nonpriority_unique
  WHERE ST_NumGeometries(geom) > 0
  UNION
  SELECT map_id, geom
  FROM nonpriority_clipped
  WHERE ST_NumGeometries(geom) > 0
),

-- Do the same as above, but for tiny
tiny_priority_ref AS (
  SELECT 1 AS id, ST_SetSRID(ST_Union(rgeom), 4326) geom
  FROM maps.sources
  WHERE scale = 'tiny'
  AND priority IS TRUE
),
tiny_priorities AS (
  SELECT s.map_id, s.geom
  FROM maps.tiny s
  JOIN maps.sources ON s.source_id = sources.source_id
  WHERE priority IS TRUE
),
tiny_nonpriority_unique AS (
  SELECT s.map_id, s.geom
  FROM maps.tiny s
  JOIN maps.sources ON s.source_id = sources.source_id
  LEFT JOIN tiny_priority_ref pr
  ON ST_Intersects(s.geom, st_setsrid(pr.geom, 4326))
  WHERE pr.id IS NULL
  AND priority IS FALSE
  AND ST_Geometrytype(s.geom) != 'ST_LineString'
),
tiny_nonpriority_clipped AS (
  SELECT s.map_id, ST_Difference(s.geom, pr.geom) geom
  FROM maps.tiny s
  JOIN tiny_priority_ref pr
  ON ST_Intersects(s.geom, pr.geom)
  JOIN maps.sources ON s.source_id = sources.source_id
  WHERE priority IS FALSE
),
tiny AS (
  SELECT map_id, geom
  FROM tiny_priorities
  WHERE ST_NumGeometries(geom) > 0
  UNION
  SELECT map_id, geom
  FROM tiny_nonpriority_unique
  WHERE ST_NumGeometries(geom) > 0
  UNION
  SELECT map_id, geom
  FROM tiny_nonpriority_clipped
  WHERE ST_NumGeometries(geom) > 0
),

-- Union the reference geometry of all small sources
small_ref AS (
  SELECT 1 AS id, ST_SetSRID(ST_Union(rgeom), 4326) geom
  FROM maps.sources
  WHERE scale = 'small'
),
-- Get polygons from tiny that don't intersect small at all
unique_tiny AS (
  SELECT t.map_id, t.geom
  FROM tiny t
  LEFT JOIN small_ref sr
  ON ST_Intersects(t.geom, sr.geom)
  WHERE sr.id IS NULL
  AND ST_Geometrytype(t.geom) != 'ST_LineString'
),
-- Clip the parts of tiny the intersect small
tiny_clipped AS (
  SELECT t.map_id, ST_Difference(t.geom, sr.geom) geom
  FROM tiny t
  JOIN small_ref sr
  ON ST_Intersects(t.geom, sr.geom)
),
-- get the result:
--    + All polygons from the 'small' queries
--    + The polygons from tiny that don't touch small
--    + The cut polygons from tiny that intersect tiny
result AS (
  SELECT map_id, 'small' AS scale, geom
  FROM small
  UNION
  SELECT map_id, 'tiny' AS scale, geom
  FROM unique_tiny
  UNION
  SELECT map_id, 'tiny' AS scale, geom
  FROM tiny_clipped
)
-- Synthesize everything into a nice table
SELECT r.map_id, r.scale, m.source_id,
COALESCE(m.name, '') AS name,
COALESCE(m.strat_name, '') AS strat_name,
COALESCE(m.age, '') AS age,
COALESCE(m.lith, '') AS lith,
COALESCE(m.descrip, '') AS descrip,
COALESCE(m.comments, '') AS comments,
cast(l.best_age_top as numeric) AS best_age_top,
cast(l.best_age_bottom as numeric) AS best_age_bottom, it.interval_name t_int, ib.interval_name b_int, l.color,
ST_SetSRID(r.geom, 4326) AS geom
FROM result r
LEFT JOIN (
  SELECT map_id, source_id, name, strat_name, age, lith, descrip, comments, t_interval, b_interval FROM maps.tiny
  UNION
  SELECT map_id, source_id, name, strat_name, age, lith, descrip, comments, t_interval, b_interval FROM maps.small
) m ON r.map_id = m.map_id
LEFT JOIN (
  SELECT map_id, best_age_top, best_age_bottom, color FROM public.lookup_tiny
  UNION
  SELECT map_id, best_age_top, best_age_bottom, color FROM public.lookup_small
) l ON r.map_id = l.map_id
JOIN macrostrat.intervals it ON m.t_interval = it.id
JOIN macrostrat.intervals ib ON m.b_interval = ib.id
WHERE ST_NumGeometries(r.geom) > 0;

CREATE INDEX ON carto.small (map_id);
CREATE INDEX ON carto.small USING GiST (geom);
