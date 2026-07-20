/* Topology-solving errors as a GeoJSON FeatureCollection. Each feature is a
   map_topo face whose insertion into the topology failed (topology_error set).
   Optionally filtered to one map layer via the ::map_layer_filter slot. */
WITH errors AS (
  SELECT
    t.id,
    t.map_id,
    t.topology_error,
    s.name,
    s.slug,
    t.geometry
  FROM map_bounds.map_topo t
  JOIN maps.sources s ON s.source_id = t.map_id
  LEFT JOIN map_bounds.map_area ma ON ma.id = t.map_id
  LEFT JOIN map_bounds.map_layer ml ON ml.id = ma.map_layer
  WHERE t.topology_error IS NOT NULL
    AND ::map_layer_filter
)
SELECT json_build_object(
  'type', 'FeatureCollection',
  'features', coalesce(
    json_agg(json_build_object(
      'type', 'Feature',
      'geometry', ST_AsGeoJSON(geometry)::json,
      'properties', json_build_object(
        'id', id,
        'map_id', map_id,
        'name', name,
        'slug', slug,
        'topology_error', topology_error
      )
    )),
    '[]'::json
  )
) FROM errors;
