/** A map's staged lines, copied into `maps` when it has a lines table. */
INSERT INTO {lines_table_maps} (
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
  {scale}::maps.map_scale,
  orig_id,
  name,
  type,
  direction,
  descrip,
  geom
FROM {lines_table}
WHERE source_id = {source_id}
  AND NOT coalesce(omit, false);
