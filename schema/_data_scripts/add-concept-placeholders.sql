
INSERT INTO macrostrat.strat_names_meta (concept_id, orig_id, name, b_int, t_int, url, ref_id)
SELECT DISTINCT (concept_id) concept_id, -1, 'Placeholder - concept not in meta table', 132, 1, '', 1
FROM macrostrat.strat_names
WHERE concept_id NOT IN (SELECT concept_id FROM macrostrat.strat_names_meta);
