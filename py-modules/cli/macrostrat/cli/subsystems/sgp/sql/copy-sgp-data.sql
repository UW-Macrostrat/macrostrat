/** Script to copy some data from the SGP database to Macrostrat
  for further processing and linking.

  This operates in bulk right now but could be optimized into a per-sample
  process if other datasets need to be linked into the same structure.
 */




/** Create local tables for the data we want to copy.
  For now, we drop and recreate but we should eventually
  just truncate these tables and insert new data.
*/

-- set the search path
SET search_path TO sgp, integrations, public;

DROP TABLE IF EXISTS integrations.sgp_samples;
DROP TABLE IF EXISTS integrations.sgp_analyses;


/** Samples */

CREATE TABLE integrations.sgp_samples AS
SELECT
  s.sample_id,
  coalesce(s.igsn, s.parent_igsn) igsn,
  s.original_num,
  s.is_standard,
  s.min_depth,
  s.max_depth,
  s.height_depth_m,
  s.composite_height_m,
  ST_SetSRID(ST_MakePoint(st.long_dec, st.lat_dec), 4326) AS geom,
  l.verbatim_strat,
  s.verbatim_lith,
  l.strat_notes,
  ce.coll_event_notes,
  s.sample_url url,
  ds.data_source,
  gc.geol_context_id,
  l.lithostrat_id,
  ce.coll_event_id,
  dl.macrostrat_id
FROM sample s
       JOIN collecting_event ce ON s.coll_event_id = ce.coll_event_id
       JOIN site st ON st.site_id = ce.site_id
       JOIN interpreted_age ia ON ia.sample_id = s.sample_id
       JOIN geol_context gc ON gc.geol_context_id = s.geol_context_id
       JOIN lithostrat l ON l.lithostrat_id = gc.lithostrat_id
       LEFT JOIN dic_lithostrat dl ON dl.strat_id = l.strat_id
       JOIN batch_sample bs ON bs.sample_id = s.sample_id
       JOIN data_source_batch dsb ON dsb.batch_id = bs.batch_id
       JOIN data_source ds ON ds.data_source_id = dsb.data_source_id;

/** Analyses */

CREATE TABLE integrations.sgp_analyses AS
SELECT ad.sample_id,
       s.original_num,
       ad.analyte_det_id,
       adl.analyte_code,
       ad.abundance,
       ad.determination_unit,
       a.exp_method_id,
       a.ana_method_id,
       ad.reference_id
FROM analyte_determination ad
       LEFT JOIN sample s ON s.sample_id = ad.sample_id
       LEFT JOIN analyte_determination_limits adl ON adl.limit_id = ad.limit_id
       LEFT JOIN analysis a ON a.analysis_id = adl.analysis_id
WHERE abundance IS null;
