WITH a AS (SELECT
  s.sample_id,
  s.original_num,
  s.is_standard,
  s.max_depth,
  s.composite_height_m,
  ST_SetSRID(ST_MakePoint(st.long_dec, st.lat_dec), 4326) AS geom,
  l.verbatim_strat,
  dl.gp                                                                AS "group",
  dl.fm                                                                AS formation,
  dl.mbr                                                               AS member,
  ia.interpreted_age,
  ia.interpreted_age_notes,
  ia.min_age,
  ia.max_age,
  string_agg(DISTINCT p2.last_name::text, ', '::text)::text                  AS age_by,
  ds.data_source                                                       AS data_source
  FROM sample s
      JOIN collecting_event ce ON s.coll_event_id = ce.coll_event_id
      JOIN site st ON st.site_id = ce.site_id
      JOIN interpreted_age ia ON ia.sample_id = s.sample_id
      JOIN geol_context gc ON gc.geol_context_id = s.geol_context_id
      JOIN lithostrat l ON l.lithostrat_id = gc.lithostrat_id
      LEFT JOIN dic_lithostrat dl ON dl.strat_id = l.strat_id
      LEFT JOIN interpreted_age_provided_by iapb ON iapb.interpreted_age_id = ia.interpreted_age_id
      LEFT JOIN person p2 ON p2.person_id = iapb.person_id
      JOIN batch_sample bs ON bs.sample_id = s.sample_id
      JOIN data_source_batch dsb ON dsb.batch_id = bs.batch_id
      JOIN data_source ds ON ds.data_source_id = dsb.data_source_id
  GROUP BY s.sample_id, ds.data_source, s.original_num, gc.geol_context_id, s.coll_event_id,
        s.height_depth_m,
        st.lat_dec, st.long_dec,
        st.metamorphic_bin,
        l.verbatim_strat, dl.gp, dl.fm, dl.mbr,
        ia.interpreted_age,
        ia.interpreted_age_notes, ia.min_age, ia.max_age
  ORDER BY s.sample_id
)
SELECT *
FROM a
-- Don't include samples from USGS-CMIBS and USGS-NGDB
WHERE NOT (
    data_source IN ('USGS-CMIBS', 'USGS-NGDB')
    AND age_by IN ('Husson', 'Peters')
  )
AND geom IS NOT NULL;

