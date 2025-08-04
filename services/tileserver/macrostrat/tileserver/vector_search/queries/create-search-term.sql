WITH new_data AS (
  SELECT
    :text AS source_text,
    (SELECT id FROM text_vectors.model WHERE name = :model_name) AS model_id,
    :model_version AS model_version,
    :text_vector::vector AS text_vector,
    :norm_vector::vector AS norm_vector
), approx_rows AS (
  -- Quick estimate of table size
  SELECT (reltuples / relpages * (pg_relation_size(oid) / 8192))::bigint AS ct
  FROM   pg_class
  WHERE oid = 'text_vectors.legend_embedding'::regclass::oid
), target AS (
  -- Get a target fraction of rows to return
  SELECT :sample_size::float / ct::float frac
  FROM approx_rows
), sample AS (
  -- Sample the data
  SELECT
    legend_id,
    sv.source_text,
    -- Squared Cosine similarity, to enhance high similarity outliers
    text_vectors.distance(le.embedding_vector, sv.text_vector) distance,
    text_vectors.norm_distance(le.normalized_vector, sv.norm_vector) norm_distance
  FROM text_vectors.legend_embedding le,
       new_data sv
  WHERE random() < (SELECT frac FROM target)
),
stats AS (
  -- Compute summary statistics
  SELECT
    source_text,
    avg(distance)    mean,
    stddev(distance) stdev,
    avg(norm_distance)    mean_norm,
    stddev(norm_distance) stdev_norm,
    count(*)         n
  FROM sample
  GROUP BY source_text
)
INSERT INTO text_vectors.search_vector (text, model_id, model_version, text_vector, norm_vector, lower_bound, upper_bound, lower_bound_norm, upper_bound_norm)
-- model the population-level 99% CI for the variance
SELECT
  d.source_text,
  d.model_id,
  d.model_version,
  d.text_vector,
  d.norm_vector,
  mean - 2 * stdev,
  mean + 2 * stdev,
  mean_norm - 2 * stdev_norm,
  mean_norm + 2 * stdev_norm
FROM stats s
       JOIN new_data d ON s.source_text = d.source_text
ON CONFLICT (text, model_id)
DO UPDATE SET
            text_vector = excluded.text_vector,
            norm_vector = excluded.norm_vector,
            model_version = excluded.model_version,
            lower_bound = excluded.lower_bound,
            upper_bound = excluded.upper_bound,
            lower_bound_norm = excluded.lower_bound_norm,
            upper_bound_norm = excluded.upper_bound_norm
RETURNING id;

