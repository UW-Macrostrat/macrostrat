/** A map's staged polygons, copied into `maps`. Required of every map. */
INSERT INTO {polygons_table_maps} (
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
  {scale}::maps.map_scale,
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
