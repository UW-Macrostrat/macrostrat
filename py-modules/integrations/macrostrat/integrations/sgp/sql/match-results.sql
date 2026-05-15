SELECT
  col_id,
  source_text,
  strat_names,
  match_strat_name_clean strat_name_clean,
  match_basis basis,
  match_spatial_basis spatial_basis,
  match_unit_id unit_id,
  match_min_age b_age,
  match_max_age t_age,
  count(sample_id) n_samples
FROM integrations.sgp_matches
GROUP BY
  col_id,
  source_text,
  strat_names,
  match_strat_name_clean,
  match_basis,
  match_spatial_basis,
  match_unit_id,
  match_min_age,
  match_max_age
ORDER BY col_id NULLS LAST;
