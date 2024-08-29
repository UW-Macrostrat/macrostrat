SELECT
  strat_name_id,
  rank_name,
  name_no_lith,
  concept_id,
  geom,
  best_t_age,
  best_b_age
FROM macrostrat.strat_name_footprints
WHERE ST_Intersects(geom, ST_SetSRID(ST_GeomFromText(:geom), 4326))
  AND :name ILIKE '%' || name_no_lith || '%'
