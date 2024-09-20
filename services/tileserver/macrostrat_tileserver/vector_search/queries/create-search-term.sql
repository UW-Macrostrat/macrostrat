WITH new_data AS (
  SELECT
    :text AS source_text,
    :model_name AS model_name,
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
    1 - (le.embedding_vector <=> sv.text_vector) distance,
    le.normalized_vector <#> sv.norm_vector norm_distance -- inner product of the normalized vectors
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
),
-- model the population-level 99% CI for the variance
values AS (
  SELECT
    d.source_text,
    d.model_name,
    d.model_version,
    d.text_vector,
    mean - 2 * stdev AS ci_lower,
    mean + 2 * stdev AS ci_upper,
    mean_norm - 2 * stdev_norm AS ci_lower_norm,
    mean_norm + 2 * stdev_norm AS ci_upper_norm
  FROM stats s
  JOIN new_data d ON s.source_text = d.source_text
)
INSERT INTO text_vectors.search_vector (text, model_name, model_version, text_vector, lower_bound, upper_bound, lower_bound_norm, upper_bound_norm)
SELECT source_text, model_name, model_version, text_vector, ci_lower, ci_upper, ci_lower_norm, ci_upper_norm
FROM values
ON CONFLICT (text, model_name)
DO UPDATE SET
            text_vector = excluded.text_vector,
            model_version = excluded.model_version,
            lower_bound = excluded.lower_bound,
            upper_bound = excluded.upper_bound,
            lower_bound_norm = excluded.lower_bound_norm,
            upper_bound_norm = excluded.upper_bound_norm
RETURNING id;

