WITH envelope AS (
  SELECT tile_utils.envelope(:x, :y, :z) AS geom
),
term AS (
  SELECT
    sv.*
  FROM text_vectors.search_vector sv
  JOIN text_vectors.model m
    ON sv.model_id = m.id
  WHERE sv.id = :term_id
  AND m.name = :model_name
  LIMIT 1
),
mvt_features AS (
SELECT
  p.map_id,
  p.source_id,
  p.geom
FROM
  carto.polygons AS p
WHERE scale::text = :mapsize
  AND ST_Intersects(geom, ST_Transform((SELECT geom FROM envelope), 4326))
),
f1 AS (
  SELECT z.map_id,
        z.source_id,
        l.legend_id,
        l.name,
        l.age,
        l.descrip,
        l.color,
        tile_layers.tile_geom(z.geom, (SELECT geom FROM envelope)) AS geom
 FROM mvt_features z
        JOIN maps.map_legend ml ON z.map_id = ml.map_id
        JOIN maps.legend l ON ml.legend_id = l.legend_id
        JOIN maps.sources
                  ON z.source_id = sources.source_id
 WHERE sources.status_code = 'active'
),
res AS (
  SELECT f1.*,
    term.id AS term_id,
    -- cosine similarity between the term and the legend embedding
    text_vectors.distance(le.embedding_vector, term.text_vector) AS raw_similarity
  FROM f1
  JOIN term ON true
  JOIN text_vectors.legend_embedding AS le
      ON f1.legend_id = le.legend_id
        AND le.model_id = term.model_id
  WHERE geom IS NOT NULL
),
boundaries AS (
  SELECT
    term.lower_bound,
    term.upper_bound
  FROM term
  WHERE :norm_method = 'global'
  UNION ALL
  SELECT
    min(raw_similarity) AS lower_bound,
    max(raw_similarity) AS upper_bound
  FROM res
  WHERE :norm_method = 'tile'
),
res2 AS (
  SELECT
    res.*,
    -- cosine similarity between the term and the legend embedding
    (raw_similarity - lower_bound) / (upper_bound - lower_bound)  AS similarity
  FROM res
  JOIN boundaries ON true
)
SELECT * FROM res2
