WITH a AS (
  SELECT ma.id,
    ma.map_id,
    ma.geometry_hash,
    ma.topo,
    ma.topology_error,
    (geometry_hash = MD5(ST_AsBinary(geometry))::uuid AND topo IS NOT NULL) success,
    ma.topology_error IS NOT NULL failure
  FROM map_bounds.map_topo ma
  WHERE map_id = :map_id
)
SELECT
  count(*) AS total,
    count(*) FILTER (WHERE success OR failure) AS processed,
    count(*) FILTER (WHERE success) AS success,
    count(*) FILTER (WHERE failure) AS failure
FROM a;
