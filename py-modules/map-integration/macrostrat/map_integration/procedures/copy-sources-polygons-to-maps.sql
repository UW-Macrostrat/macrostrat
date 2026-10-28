/** Several maps' staged polygons, copied into `maps` at one scale. */
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
  CAST(:scale AS maps.map_scale),
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
WHERE source_id = ANY(:source_ids)
  AND NOT coalesce(omit, false);
