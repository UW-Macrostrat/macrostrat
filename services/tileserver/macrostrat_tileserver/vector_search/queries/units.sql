WITH envelope AS (
  SELECT tile_utils.envelope(:x, :y, :z) AS geom
),
term AS (
  SELECT
    id,
    text_vector,
    model_name,
    lower_bound,
    upper_bound
  FROM text_vectors.search_vector
  WHERE id = :term_id
  AND model_name = :model_name
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
f1 AS (SELECT z.map_id,
              z.source_id,
              l.legend_id,
              l.name,
              l.age,
              l.descrip,
              tile_layers.tile_geom(z.geom, (SELECT geom FROM envelope)) AS geom
       FROM mvt_features z
              JOIN maps.map_legend ml ON z.map_id = ml.map_id
              JOIN maps.legend l ON ml.legend_id = l.legend_id
              JOIN maps.sources
                        ON z.source_id = sources.source_id
       WHERE sources.status_code = 'active'
)
SELECT
  f1.*,
  term.id AS term_id,
  -- cosine similarity between the term and the legend embedding
  1 - (le.embedding_vector <=> term.text_vector) AS raw_similarity,
  (1 - (le.embedding_vector <=> term.text_vector) - term.lower_bound
      ) / (term.upper_bound - term.lower_bound) AS similarity
FROM f1
JOIN term
  ON true
JOIN text_vectors.legend_embedding AS le
  ON f1.legend_id = le.legend_id
  AND le.source_model = term.model_name
WHERE geom IS NOT NULL;
