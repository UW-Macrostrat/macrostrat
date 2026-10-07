/** A map's staged points, copied into `maps` when it has a points table. */
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
