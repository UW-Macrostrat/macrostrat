
WITH a AS (SELECT max(ps.project_id)                                                   AS latest_project_id,

                  s.sample_id,
                  s.original_num,
                  string_agg(DISTINCT an.alternate_num::text, ', '::text)              AS alternate_nums,
                  string_agg(DISTINCT an.notes::text, ', '::text)                      AS alternate_num_notes,
                  s.height_depth_m,
                  s.is_standard,
                  s.sample_notes,
                  dc.color_name_full,
                  dlc.lith_composition,
                  dlt.lith_texture,
                  dlith.lith_name,
                  s.is_bioturbated,
                  s.lith_notes,
                  string_agg(DISTINCT fs.verbatim_fossil::text, ', '::text)            AS fossils,
                  string_agg(DISTINCT ss.sed_structure_name::text, ', '::text)         AS sed_structures,
                  s.min_depth,
                  s.max_depth,
                  s.verbatim_lith,
                  s.composite_height_m,
                  dst.sample_type,
                  s.coll_event_id,
                  ce.start_date_verbatim                                               AS start_date,
                  ce.end_date_verbatim                                                 AS end_date,
                  string_agg(p4.last_name::text, ', '::text ORDER BY p4.last_name)     AS collectors,
                  st.section_name,
                  st.site_type,
                  st.country,
                  st.state_province,
                  st.county,
                  st.lat_dec,
                  st.long_dec,
                  ct.ct_name,
                  db.basin_type,
                  b.basin_name,
                  CASE
                    WHEN st.metamorphic_bin = 1 THEN 'diagenetic'::text
                    WHEN st.metamorphic_bin = 2 THEN 'anchizone'::text
                    WHEN st.metamorphic_bin = 3 THEN 'epizone'::text
                    ELSE NULL::text
                    END                                                                AS meta_bin,
                  gc.geol_context_id,
                  e.env_bin                                                            AS dep_env_bin,
                  e.is_turbiditic,
                  ded.env_detail,
                  l.verbatim_strat,
                  dl.gp                                                                AS "group",
                  dl.fm                                                                AS formation,
                  dl.mbr                                                               AS member,
                  da.ics_name,
                  ia.interpreted_age,
                  ia.interpreted_age_notes,
                  ia.min_age,
                  ia.max_age,

                  bt.verbatim_biostrat,
                  dbt.biozone_name,
                  string_agg(p.project_name::text, ', '::text ORDER BY p.project_name) AS projects,
                  string_agg(DISTINCT p1.last_name::text, ', '::text)                  AS sample_by,
                  string_agg(DISTINCT p2.last_name::text, ', '::text)                  AS age_by,
                  string_agg(DISTINCT p3.last_name::text, ', '::text)                  AS context_by,
                  ds.data_source                                                       AS data_source
           FROM sample s
                  LEFT JOIN alternate_num an ON an.sample_id = s.sample_id
                  LEFT JOIN collecting_event ce ON s.coll_event_id = ce.coll_event_id
                  LEFT JOIN site st ON st.site_id = ce.site_id
                  LEFT JOIN craton_terrane ct ON ct.craton_terrane_id = st.craton_terrane_id
                  LEFT JOIN basin b ON b.basin_id = st.basin_id
                  LEFT JOIN dic_basin_type db ON db.basin_type_id = b.basin_type_id
                  JOIN interpreted_age ia ON ia.sample_id = s.sample_id
                  LEFT JOIN geol_context gc ON gc.geol_context_id = s.geol_context_id
                  LEFT JOIN environment e ON e.env_id = gc.env_id
                  LEFT JOIN lithostrat l ON l.lithostrat_id = gc.lithostrat_id
                  LEFT JOIN dic_lithostrat dl ON dl.strat_id = l.strat_id
                  LEFT JOIN geol_age ga ON ga.age_id = gc.age_id
                  LEFT JOIN dic_ics_age da ON da.ics_id = ga.ics_id
                  LEFT JOIN biostrat bt ON bt.biostrat_id = gc.biostrat_id
                  LEFT JOIN dic_biostrat dbt ON dbt.dic_biostrat_id = bt.dic_biostrat_id
                  LEFT JOIN project_sample ps ON ps.sample_id = s.sample_id
                  LEFT JOIN project p ON p.project_id = ps.project_id
                  LEFT JOIN dic_lithology dlith ON dlith.lith_id = s.lith_id
                  LEFT JOIN dic_lith_texture dlt ON dlt.lith_texture_id = s.lith_texture_id
                  LEFT JOIN dic_lith_composition dlc ON dlc.lith_composition_id = s.lith_composition_id
                  LEFT JOIN dic_color dc ON dc.color_id = s.color_id
                  LEFT JOIN dic_env_detail ded ON ded.env_detail_id = e.env_detail_id
                  LEFT JOIN dic_sample_type dst ON dst.sample_type_id = s.sample_type_id
                  LEFT JOIN sed_structure_sample sss ON sss.sample_id = s.sample_id
                  LEFT JOIN dic_sed_structure ss ON ss.sed_structure_id = sss.sed_structure_id
                  LEFT JOIN fossil_sample fs ON fs.sample_id = s.sample_id
                  LEFT JOIN fossil f ON f.fossil_id = fs.fossil_id
                  LEFT JOIN sample_provided_by spb ON spb.sample_id = s.sample_id
                  LEFT JOIN geol_context_provided_by gcpb ON gcpb.geol_context_id = gc.geol_context_id
                  LEFT JOIN interpreted_age_provided_by iapb ON iapb.interpreted_age_id = ia.interpreted_age_id
                  LEFT JOIN person p1 ON p1.person_id = spb.person_id
                  LEFT JOIN person p2 ON p2.person_id = iapb.person_id
                  LEFT JOIN person p3 ON p3.person_id = gcpb.person_id
                  LEFT JOIN collector coll ON coll.coll_event_id = ce.coll_event_id
                  LEFT JOIN person p4 ON p4.person_id = coll.person_id
                  JOIN batch_sample bs ON bs.sample_id = s.sample_id
                  JOIN data_source_batch dsb ON dsb.batch_id = bs.batch_id
                  JOIN data_source ds ON ds.data_source_id = dsb.data_source_id
           WHERE ds.data_source IN ('USGS-CMIBS', 'USGS-NGDB')
             AND interpreted_age_notes ILIKE '%Macrostrat%'
           GROUP BY s.sample_id, ds.data_source, s.original_num, gc.geol_context_id, ded.env_detail, s.coll_event_id,
                    s.height_depth_m, dc.color_name_full, dlc.lith_composition, dlt.lith_texture, dlith.lith_name,
                    st.section_name, st.site_type, st.country, st.state_province, st.county, st.lat_dec, st.long_dec,
                    ct.ct_name, db.basin_type, b.basin_name, st.metamorphic_bin,
                    (
                      CASE
                        WHEN st.metamorphic_bin = 1 THEN 'diagenetic'::text
                        WHEN st.metamorphic_bin = 2 THEN 'anchizone'::text
                        WHEN st.metamorphic_bin = 3 THEN 'epizone'::text
                        ELSE NULL::text
                        END), e.env_bin, e.is_turbiditic, l.verbatim_strat, dl.gp, dl.fm, dl.mbr, da.ics_name,
                    ia.interpreted_age, bt.verbatim_biostrat, dbt.biozone_name, dst.sample_type,
                    ia.interpreted_age_notes, ia.min_age, ia.max_age, ce.start_date_verbatim, ce.end_date_verbatim
           ORDER BY s.sample_id)
SELECT * FROM a;


-- Target count: 49505
-- Actual count (current): 49673
