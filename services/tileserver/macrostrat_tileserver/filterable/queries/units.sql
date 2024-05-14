WITH mvt_features AS (
SELECT
  p.map_id,
  p.source_id,
  p.geom
FROM
  :compilation AS p
LEFT JOIN maps.map_liths AS ml ON ml.map_id = p.map_id
LEFT JOIN macrostrat.liths AS liths ON liths.id = ml.lith_id
WHERE scale::text = :mapsize
  AND ST_Intersects(geom, ST_Transform(:envelope, 4326))
  :where_lithology
)
SELECT
  z.map_id,
  z.source_id,
  l.*, -- legend info
  tile_layers.tile_geom(z.geom, :envelope) AS geom
FROM
  mvt_features z
  LEFT JOIN maps.map_legend ON z.map_id = map_legend.map_id
  LEFT JOIN tile_layers.map_legend_info AS l
    ON l.legend_id = map_legend.legend_id
  LEFT JOIN maps.sources
    ON z.source_id = sources.source_id
WHERE
  sources.status_code = 'active'