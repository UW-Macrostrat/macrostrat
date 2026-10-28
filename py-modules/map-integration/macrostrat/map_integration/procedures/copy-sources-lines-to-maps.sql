/** Several maps' staged lines, copied into `maps` at one scale. */
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
  CAST(:scale AS maps.map_scale),
  orig_id,
  name,
  type,
  direction,
  descrip,
  geom
FROM {lines_table}
WHERE source_id = ANY(:source_ids)
  AND NOT coalesce(omit, false);
