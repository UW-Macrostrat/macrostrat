-- PostgREST routes for integrated datasets and SGP

CREATE VIEW macrostrat_api.dataset AS
 SELECT d.id,
    d.uid,
    d.name,
    d.url,
    d.type,
    d.geom,
    d.symbol,
    d.data,
    d.created_at,
    d.updated_at,
    dt.name AS type_name,
    dt.organization
   FROM (integrations.dataset d
     JOIN integrations.dataset_type dt ON ((d.type = dt.id)));

CREATE VIEW macrostrat_api.dataset_type AS
 SELECT dataset_type.id,
    dataset_type.name,
    dataset_type.organization,
    dataset_type.updated_at
   FROM integrations.dataset_type;

CREATE VIEW macrostrat_api.sgp_analyses AS
 SELECT sgp_analyses.sample_id,
    sgp_analyses.original_num,
    sgp_analyses.analyte_det_id,
    sgp_analyses.analyte_code,
    sgp_analyses.abundance,
    sgp_analyses.determination_unit,
    sgp_analyses.exp_method_id,
    sgp_analyses.ana_method_id,
    sgp_analyses.reference_id
   FROM integrations.sgp_analyses;

CREATE VIEW macrostrat_api.sgp_matches AS
 SELECT sgp_matches.sample_id,
    sgp_matches.match_set,
    sgp_matches.created_at,
    sgp_matches.original_num,
    sgp_matches.is_standard,
    sgp_matches.max_depth,
    sgp_matches.composite_height_m,
    sgp_matches.geom,
    sgp_matches.interpreted_age,
    sgp_matches.interpreted_age_notes,
    sgp_matches.min_age,
    sgp_matches.max_age,
    sgp_matches.age_by,
    sgp_matches.data_source,
    sgp_matches.source_text,
    sgp_matches.col_id,
    sgp_matches.count,
    sgp_matches.strat_names,
    sgp_matches.match_strat_name_id,
    sgp_matches.match_strat_name,
    sgp_matches.match_strat_name_clean,
    sgp_matches.match_rank,
    sgp_matches.match_parent_id,
    sgp_matches.match_concept_id,
    sgp_matches.match_unit_id,
    sgp_matches.match_col_id,
    sgp_matches.match_depth,
    sgp_matches.match_basis,
    sgp_matches.match_spatial_basis,
    sgp_matches.match_min_age,
    sgp_matches.match_max_age,
    sgp_matches.match_mid_age,
    sgp_matches.match_age_span,
    sgp_matches.age_span_delta,
    sgp_matches.mid_age_delta
   FROM integrations.sgp_matches;

CREATE VIEW macrostrat_api.sgp_samples AS
 SELECT sgp_samples.sample_id,
    sgp_samples.igsn,
    sgp_samples.original_num,
    sgp_samples.is_standard,
    sgp_samples.min_depth,
    sgp_samples.max_depth,
    sgp_samples.height_depth_m,
    sgp_samples.composite_height_m,
    sgp_samples.geom,
    sgp_samples.verbatim_strat,
    sgp_samples.verbatim_lith,
    sgp_samples.strat_notes,
    sgp_samples.coll_event_notes,
    sgp_samples.url,
    sgp_samples.data_source,
    sgp_samples.geol_context_id,
    sgp_samples.lithostrat_id,
    sgp_samples.coll_event_id,
    sgp_samples.macrostrat_id
   FROM integrations.sgp_samples;

CREATE VIEW macrostrat_api.sgp_unit_matches AS
 SELECT sgp_matches.match_col_id AS col_id,
    sgp_matches.match_unit_id AS unit_id,
    jsonb_agg(jsonb_build_object('id', sgp_matches.sample_id, 'name', sgp_matches.original_num)) AS sgp_samples
   FROM integrations.sgp_matches
  WHERE (sgp_matches.match_unit_id IS NOT NULL)
  GROUP BY sgp_matches.match_col_id, sgp_matches.match_unit_id;

GRANT SELECT ON TABLE macrostrat_api.dataset TO web_anon;

GRANT SELECT ON TABLE macrostrat_api.dataset_type TO web_anon;

GRANT SELECT ON TABLE macrostrat_api.sgp_analyses TO web_anon;

GRANT SELECT ON TABLE macrostrat_api.sgp_matches TO web_anon;

GRANT SELECT ON TABLE macrostrat_api.sgp_samples TO web_anon;

GRANT SELECT ON TABLE macrostrat_api.sgp_unit_matches TO web_anon;
