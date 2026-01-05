CREATE VIEW macrostrat_api.sgp_matches AS
SELECT * FROM integrations.sgp_matches;

CREATE VIEW macrostrat_api.sgp_samples AS
SELECT * FROM integrations.sgp_samples;

CREATE VIEW macrostrat_api.sgp_analyses AS
SELECT * FROM integrations.sgp_analyses;

CREATE VIEW macrostrat_api.sgp_unit_matches AS
SELECT
  match_col_id col_id,
  match_unit_id unit_id,
  jsonb_agg(jsonb_build_object(
    'id', sample_id,
    'name', original_num
            ))
    sgp_samples
FROM integrations.sgp_matches
WHERE match_unit_id IS NOT NULL
GROUP BY match_col_id, match_unit_id;

