/** Several maps' staged points, copied into `maps`. Points carry no scale. */
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
WHERE source_id = ANY(:source_ids)
  AND NOT coalesce(omit, false);
