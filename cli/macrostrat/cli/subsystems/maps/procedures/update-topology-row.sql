WITH candidates AS (
  SELECT id FROM map_bounds.map_topo WHERE source_id = :source_id AND topo IS NULL
),
to_update AS (
  SELECT id FROM candidates LIMIT :batch_size
),
update AS (
  UPDATE map_bounds.map_topo t
    SET
      topo = topology.toTopoGeom(
        t.geometry,
        'map_bounds_topology',
        (SELECT layer_id
         FROM topology.layer
         WHERE schema_name='map_bounds'
           AND table_name='map_topo'
           AND feature_column='topo'
        ),
        0.0001
      ),
      geometry_hash = md5(ST_AsBinary(t.geometry))::uuid,
      topology_error = NULL
    WHERE t.source_id = :source_id
    AND t.topo IS NULL
    AND id IN (SELECT id FROM to_update)
    RETURNING t.id
)
SELECT
  count(*) updated,
  (SELECT count(*) FROM candidates) - count(*) remaining
FROM update;
