/**
Script to create record in the maps schema for all tables for a given source
*/

INSERT INTO maps.polygons (
  source_id,
  scale,
  orig_id,
  name,
  strat_name,
  age,
  lith,
  descrip,
  comments,
  t_interval,
  b_interval,
  geom
)
SELECT 
  source_id,
  {scale}::macrostrat.map_scale,
  orig_id,
  name,
  strat_name,
  age,
  lith,
  descrip,
  comments,
  t_interval,
  b_interval,
  geom
FROM {polygons_table}
WHERE source_id = {source_id}
  AND NOT coalesce(omit, false);


INSERT INTO maps.lines (
  source_id,
  scale,
  orig_id,
  name,
  type,
  direction,
  descrip,
  geom
)
SELECT 
  source_id,
  {scale}::macrostrat.map_scale,
  orig_id,
  name,
  type,
  direction,
  descrip,
  geom
FROM {lines_table}
WHERE source_id = {source_id}
  AND NOT coalesce(omit, false);


INSERT INTO maps.points (
  source_id,
  strike,
  dip,
  dip_dir,
  point_type,
  certainty,
  comments,
  geom,
  orig_id
)
SELECT 
  source_id,
  strike,
  dip,
  dip_dir,
  point_type,
  certainty,
  comments,
  geom,
  orig_id
FROM {points_table}
WHERE source_id = {source_id}
  AND NOT coalesce(omit, false);