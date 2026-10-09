-- Additional macrostrat_api objects carried over from the former
-- development/9000-macrostrat_api.sql (pg_dump). The core views/functions are
-- defined cleanly in 01-views.sql / 02-functions.sql; these are the remainder
-- plus the API grants. Development-only API objects live with their
-- subsystems in schema/_dev_definitions.

CREATE FUNCTION macrostrat_api.auth_status() RETURNS jsonb
    LANGUAGE sql
    AS $$
  SELECT jsonb_build_object(
    'token', current_setting('request.jwt.claims', true)::jsonb,
    'role', current_user
  );
$$;

/** Entities that can be used to filter columns */
CREATE OR REPLACE VIEW macrostrat_api.col_filters AS
SELECT
  concat('lith:', l.id::text) AS uid,
  l.lith AS name,
  l.lith_color AS color,
  l.id AS lex_id,
  'lithology'::text AS type
FROM macrostrat.liths l
UNION ALL
SELECT
  concat('int:', i.id::text) AS uid,
  i.interval_name AS name,
  i.interval_color AS color,
  i.id AS lex_id,
  'interval'::text AS type
FROM macrostrat.intervals i
UNION ALL
SELECT
  concat('env:', e.id::text) AS uid,
  e.environ AS name,
  e.environ_color AS color,
  e.id AS lex_id,
  'environment'::text AS type
FROM macrostrat.environs e
UNION ALL
SELECT
  concat('concept:', c.concept_id::text) AS uid,
  c.name AS name,
  NULL::character varying AS color,
  c.concept_id AS lex_id,
  'concept'::text AS type
FROM macrostrat.strat_names_meta c
UNION ALL
SELECT
  concat('strat_name:', sn.id::text) AS uid,
  sn.strat_name AS name,
  NULL::character varying AS color,
  sn.id AS lex_id,
  'strat name'::text AS type
FROM macrostrat.strat_names sn;

CREATE VIEW macrostrat_api.cols_with_groups AS
 SELECT mt.id,
    mt.col_group_id,
    mt.project_id,
    mt.status_code,
    mt.col_type,
    mt.col_position,
    mt.col,
    mt.col_name,
    mt.lat,
    mt.lng,
    mt.col_area,
    mt.created,
    mt.coordinate,
    mt.wkt,
    mt.poly_geom,
    cg.col_group_long,
    cg.col_group
   FROM (macrostrat.cols mt
     JOIN macrostrat.col_groups cg ON ((mt.col_group_id = cg.id)));

CREATE VIEW macrostrat_api.fossils AS
 SELECT pbdb_collections.collection_no,
    pbdb_collections.name,
    pbdb_collections.early_age,
    pbdb_collections.late_age,
    pbdb_collections.grp,
    pbdb_collections.grp_clean,
    pbdb_collections.formation,
    pbdb_collections.formation_clean,
    pbdb_collections.member,
    pbdb_collections.member_clean,
    pbdb_collections.lithologies,
    pbdb_collections.environment,
    pbdb_collections.reference_no,
    pbdb_collections.n_occs,
    pbdb_collections.geom
   FROM macrostrat.pbdb_collections;

CREATE VIEW macrostrat_api.legend AS
 WITH _intervals AS (
         SELECT intervals.id,
            json_build_object('id', intervals.id, 'name', intervals.interval_name, 'color', intervals.interval_color, 'rank', intervals.rank, 'b_age', intervals.age_bottom, 't_age', intervals.age_top) AS _interval
           FROM macrostrat.intervals
        ), legend_liths AS (
         SELECT legend_liths.legend_id,
            legend_liths.lith_id,
            json_agg(legend_liths.basis_col) AS basis_cols
           FROM maps.legend_liths
          GROUP BY legend_liths.legend_id, legend_liths.lith_id
        ), legend_liths2 AS (
         SELECT ll_1.legend_id,
            json_build_object('lith_id', ll_1.lith_id, 'basis_col', ll_1.basis_cols, 'name', l_1.lith, 'color', l_1.lith_color, 'fill', l_1.lith_fill) AS liths
           FROM (legend_liths ll_1
             JOIN macrostrat.liths l_1 ON ((ll_1.lith_id = l_1.id)))
        )
 SELECT l.legend_id,
    l.source_id,
    l.name,
    l.strat_name,
    l.age,
    l.lith,
    l.descrip,
    l.comments,
    ( SELECT _intervals._interval
           FROM _intervals
          WHERE (_intervals.id = l.b_interval)) AS b_interval,
    ( SELECT _intervals._interval
           FROM _intervals
          WHERE (_intervals.id = l.t_interval)) AS t_interval,
    l.best_age_bottom,
    l.best_age_top,
    l.color,
    l.unit_ids,
    l.concept_ids,
    l.strat_name_ids,
    l.strat_name_children,
    l.lith_ids,
    l.lith_types,
    l.lith_classes,
    l.all_lith_ids,
    l.all_lith_types,
    l.all_lith_classes,
    l.area,
    json_agg(ll.liths) AS liths
   FROM (maps.legend l
     JOIN legend_liths2 ll USING (legend_id))
  GROUP BY l.legend_id;

CREATE VIEW macrostrat_api.legend_liths AS
 SELECT l.legend_id,
    l.source_id,
    l.name AS map_unit_name,
    array_agg(ll.lith_id) FILTER (WHERE (ll.lith_id IS NOT NULL)) AS lith_ids
   FROM (maps.legend l
     LEFT JOIN maps.legend_liths ll ON ((ll.legend_id = l.legend_id)))
  GROUP BY l.legend_id, l.source_id, l.name;

CREATE VIEW macrostrat_api.mapped_sources AS
 SELECT s.source_id,
    s.slug,
    s.name,
    s.url,
    s.ref_title,
    s.authors,
    s.ref_year,
    s.ref_source,
    s.isbn_doi,
    s.license AS licence,
    s.scale,
    s.features,
    s.area,
    s.display_scales,
    s.raster_url,
    s.web_geom AS envelope,
        CASE
            WHEN (psi.source_id IS NULL) THEN false
            ELSE true
        END AS is_mapped
   FROM (maps.sources s
     LEFT JOIN ( SELECT polygons.source_id
           FROM maps.polygons
          GROUP BY polygons.source_id) psi ON ((s.source_id = psi.source_id)));

CREATE VIEW macrostrat_api.measurements_with_type AS
 SELECT m.id,
    m.sample_name,
    m.lat,
    m.lng,
    m.sample_geo_unit,
    m.sample_lith,
    m.lith_id,
    l.lith_color,
    m.lith_att_id,
    m.age AS int_name,
    i.id AS int_id,
    i.interval_color AS int_color,
    m.sample_descrip,
    m.ref,
    m.ref_id,
    m.geometry,
    ( SELECT ms.measurement_id
           FROM macrostrat.measures ms
          WHERE (ms.measuremeta_id = m.id)
         LIMIT 1) AS measurement_id
   FROM ((macrostrat.measuremeta m
     LEFT JOIN macrostrat.liths l ON ((m.lith_id = l.id)))
     LEFT JOIN macrostrat.intervals i ON (((m.age)::text = (i.interval_name)::text)));

CREATE VIEW macrostrat_api.minerals AS
 SELECT minerals.id,
    minerals.mineral,
    minerals.mineral_type,
    minerals.min_type,
    minerals.hardness_min,
    minerals.hardness_max,
    minerals.crystal_form,
    minerals.color,
    minerals.lustre,
    minerals.formula,
    minerals.formula_tags,
    minerals.url,
    minerals.paragenesis
   FROM macrostrat.minerals;

CREATE VIEW macrostrat_api.new_legend AS
 WITH legend_ages AS (
         SELECT legend_1.legend_id,
            legend_1.age,
            TRIM(BOTH FROM split_part(legend_1.age, '-'::text, 1)) AS min_age,
            NULLIF(TRIM(BOTH FROM split_part(legend_1.age, '-'::text, 2)), ''::text) AS max_age
           FROM maps.legend legend_1
        ), units_agg AS (
         SELECT legend_1.legend_id,
                CASE
                    WHEN (count(units.id) = 0) THEN NULL::jsonb
                    ELSE jsonb_agg(jsonb_build_object('unit_id', units.id, 'col_id', units.col_id, 'name', units.strat_name))
                END AS units
           FROM ((maps.legend legend_1
             LEFT JOIN LATERAL unnest(legend_1.unit_ids) unit_id(unit_id) ON (true))
             LEFT JOIN macrostrat.units units ON ((units.id = unit_id.unit_id)))
          GROUP BY legend_1.legend_id
        ), liths_agg AS (
         SELECT legend_1.legend_id,
                CASE
                    WHEN (count(liths.id) = 0) THEN NULL::jsonb
                    ELSE jsonb_agg(jsonb_build_object('lith_id', liths.id, 'lith_name', liths.lith, 'color', liths.lith_color))
                END AS lithologies
           FROM ((maps.legend legend_1
             LEFT JOIN LATERAL unnest(legend_1.all_lith_ids) lith_id(lith_id) ON (true))
             LEFT JOIN macrostrat.liths liths ON ((liths.id = lith_id.lith_id)))
          GROUP BY legend_1.legend_id
        ), strat_names_agg AS (
         SELECT legend_1.legend_id,
                CASE
                    WHEN (count(sn.id) = 0) THEN NULL::jsonb
                    ELSE jsonb_agg(jsonb_build_object('strat_name_id', sn.id, 'strat_name', sn.strat_name))
                END AS strat_names
           FROM ((maps.legend legend_1
             LEFT JOIN LATERAL unnest(legend_1.strat_name_ids) sn_id(sn_id) ON (true))
             LEFT JOIN macrostrat.strat_names sn ON ((sn.id = sn_id.sn_id)))
          GROUP BY legend_1.legend_id
        )
 SELECT legend.legend_id,
    legend.source_id,
    legend.name,
    legend.strat_name,
    legend.age,
    legend.lith,
    legend.descrip,
    legend.comments,
    legend.b_interval,
    legend.t_interval,
    legend.best_age_bottom,
    legend.best_age_top,
    legend.color,
    legend.unit_ids,
    legend.concept_ids,
    legend.strat_name_ids,
    legend.strat_name_children,
    legend.lith_ids,
    legend.lith_types,
    legend.lith_classes,
    legend.all_lith_ids,
    legend.all_lith_types,
    legend.all_lith_classes,
    legend.area,
    legend.tiny_area,
    legend.small_area,
    legend.medium_area,
    legend.large_area,
    u.units,
    l.lithologies,
    s.strat_names,
        CASE
            WHEN (min_intervals.id IS NULL) THEN NULL::jsonb
            ELSE jsonb_build_object('int_id', min_intervals.id, 'name', min_intervals.interval_name, 'color', min_intervals.interval_color)
        END AS min_age_interval,
        CASE
            WHEN (max_intervals.id IS NULL) THEN NULL::jsonb
            ELSE jsonb_build_object('int_id', max_intervals.id, 'name', max_intervals.interval_name, 'color', max_intervals.interval_color)
        END AS max_age_interval
   FROM ((((((maps.legend legend
     JOIN legend_ages ON ((legend.legend_id = legend_ages.legend_id)))
     LEFT JOIN units_agg u ON ((u.legend_id = legend.legend_id)))
     LEFT JOIN liths_agg l ON ((l.legend_id = legend.legend_id)))
     LEFT JOIN strat_names_agg s ON ((s.legend_id = legend.legend_id)))
     LEFT JOIN macrostrat.intervals min_intervals ON (((min_intervals.interval_name)::text = legend_ages.min_age)))
     LEFT JOIN macrostrat.intervals max_intervals ON (((max_intervals.interval_name)::text = legend_ages.max_age)));

CREATE VIEW macrostrat_api.sources AS
 SELECT s.source_id,
    s.slug,
    s.name,
    s.url,
    s.ref_title,
    s.authors,
    s.ref_year,
    s.ref_source,
    s.isbn_doi,
    s.license,
    s.scale,
    s.features,
    s.area,
    s.display_scales,
    s.priority,
    s.status_code,
    s.raster_url,
    s.web_geom AS envelope,
    s.is_finalized,
    s.scale_denominator,
    s.lines_oriented
   FROM maps.sources s;

/** A map's own public references, labelled and in display order; the citation
  is composed as `map_bounds.polygon_refs_for` composes it. */
CREATE VIEW macrostrat_api.map_refs AS
 SELECT r.source_id,
    t.id AS ref_type,
    t.label,
    t.position,
    f.id AS ref_id,
    concat_ws(', ', nullif(f.author, ''), f.pub_year::text, nullif(f.ref, '')) AS citation,
    f.doi,
    f.url
   FROM maps.map_refs r
     JOIN maps.ref_type t ON t.id = r.ref_type
     JOIN macrostrat.refs f ON f.id = r.ref_id
  WHERE t.is_public;

CREATE VIEW macrostrat_api.sources_ingestion AS
 SELECT s.source_id,
    s.slug,
    s.name,
    s.url,
    s.ref_title,
    s.authors,
    s.ref_year,
    s.ref_source,
    s.isbn_doi,
    s.scale,
    s.license,
    s.features,
    s.area,
    s.display_scales,
    s.priority,
    s.status_code,
    s.raster_url,
    i.state,
    i.comments,
    i.created_on,
    i.completed_on,
    s.is_finalized,
    s.scale_denominator
   FROM  maps.sources_metadata s
  JOIN maps_metadata.ingest_process i ON i.source_id = s.source_id;

CREATE VIEW macrostrat_api.sources_metadata AS
SELECT * FROM maps.sources_metadata;

/** View for active sources only */
CREATE VIEW macrostrat_api.maps AS
SELECT * FROM maps.sources_metadata
WHERE is_finalized
ORDER BY source_id DESC;

CREATE VIEW macrostrat_api.strat_concepts_with_names AS
 SELECT m.concept_id,
    m.orig_id,
    m.name,
    m.geologic_age,
    m.interval_id,
    m.b_int,
    m.t_int,
    m.usage_notes,
    m.other,
    m.province,
    m.url,
    m.ref_id,
    string_agg((s.id)::text, ','::text) AS strat_ids,
    string_agg((s.strat_name)::text, ','::text) AS strat_names,
    string_agg((s.rank)::text, ','::text) AS strat_ranks
   FROM (macrostrat.strat_names_meta m
     LEFT JOIN macrostrat.strat_names s ON ((m.concept_id = s.concept_id)))
  GROUP BY m.concept_id;

CREATE VIEW macrostrat_api.strat_names_test AS
 SELECT m.id,
    m.old_id,
    m.concept_id,
    m.strat_name AS name,
    m.rank,
    m.old_strat_name_id,
    m.ref_id,
    m.places,
    m.orig_id,
    string_agg((s.name)::text, ','::text) AS concept_name
   FROM (macrostrat.strat_names m
     LEFT JOIN macrostrat.strat_names_meta s ON ((m.concept_id = s.concept_id)))
  GROUP BY m.id
  ORDER BY m.id;

CREATE VIEW macrostrat_api.strat_combined AS
 SELECT strat_concepts_with_names.concept_id,
    NULL::integer AS id,
    strat_concepts_with_names.name,
    NULL::macrostrat.strat_names_rank AS rank,
    strat_concepts_with_names.strat_names,
    strat_concepts_with_names.strat_ids,
    concat(strat_concepts_with_names.name, ',', strat_concepts_with_names.strat_names) AS all_names,
    strat_concepts_with_names.concept_id AS combined_id,
    strat_concepts_with_names.strat_ranks
   FROM macrostrat_api.strat_concepts_with_names
UNION ALL
 SELECT strat_names_test.concept_id,
    strat_names_test.id,
    strat_names_test.name,
    strat_names_test.rank,
    NULL::text AS strat_names,
    NULL::text AS strat_ids,
    strat_names_test.name AS all_names,
    (100000 + strat_names_test.id) AS combined_id,
    NULL::text AS strat_ranks
   FROM macrostrat_api.strat_names_test
  WHERE (strat_names_test.concept_id IS NULL);

CREATE VIEW macrostrat_api.strat_concepts_test AS
 SELECT m.concept_id,
    m.orig_id,
    m.name,
    m.geologic_age,
    m.interval_id,
    m.b_int,
    m.t_int,
    m.usage_notes,
    m.other,
    m.province,
    m.url,
    m.ref_id,
    string_agg((s.id)::text, ','::text) AS strat_ids,
    string_agg((s.strat_name)::text, ','::text) AS strat_names
   FROM (macrostrat.strat_names_meta m
     LEFT JOIN macrostrat.strat_names s ON ((m.concept_id = s.concept_id)))
  GROUP BY m.concept_id;

CREATE VIEW macrostrat_api.strat_combined_test AS
 WITH combined_data AS (
         SELECT strat_concepts_test.concept_id,
            strat_concepts_test.name,
            strat_concepts_test.strat_names,
            strat_concepts_test.strat_ids,
            NULL::character varying AS strat_name,
            NULL::text AS concept_name,
            NULL::integer AS id
           FROM macrostrat_api.strat_concepts_test
        UNION
         SELECT strat_names_test.concept_id,
            strat_names_test.concept_name AS name,
            NULL::text AS strat_names,
            NULL::text AS strat_ids,
            strat_names_test.name AS strat_name,
            strat_names_test.concept_name,
            strat_names_test.id
           FROM macrostrat_api.strat_names_test
        )
 SELECT row_number() OVER (ORDER BY combined_data.concept_id, combined_data.name) AS combined_id,
    combined_data.concept_id,
    combined_data.name,
    combined_data.strat_names,
    combined_data.strat_ids,
    combined_data.strat_name,
    combined_data.concept_name,
    combined_data.id
   FROM combined_data;

CREATE VIEW macrostrat_api.strat_name_concepts AS
 SELECT strat_names_meta.concept_id,
    strat_names_meta.orig_id,
    strat_names_meta.name,
    strat_names_meta.geologic_age,
    strat_names_meta.interval_id,
    strat_names_meta.b_int,
    strat_names_meta.t_int,
    strat_names_meta.usage_notes,
    strat_names_meta.other,
    strat_names_meta.province,
    strat_names_meta.url,
    strat_names_meta.ref_id
   FROM macrostrat.strat_names_meta;

CREATE VIEW macrostrat_api.test_helper_functions AS
 SELECT public.current_app_role() AS current_app_role,
    public.current_app_user_id() AS current_app_user_id;

CREATE VIEW macrostrat_api.type_lookup AS
 SELECT liths.lith AS name,
    liths.id,
    'lith'::text AS type
   FROM macrostrat.liths
UNION ALL
 SELECT strat_names.strat_name AS name,
    strat_names.id,
    'strat_name'::text AS type
   FROM macrostrat.strat_names
UNION ALL
 SELECT intervals.interval_name AS name,
    intervals.id,
    'interval'::text AS type
   FROM macrostrat.intervals;

CREATE VIEW macrostrat_api.unit_intervals AS
 SELECT i.id AS int_id,
    u.unit_id
   FROM (macrostrat.intervals i
     JOIN macrostrat.lookup_units u ON (((u.b_age <= i.age_bottom) AND (u.t_age >= i.age_top))));

CREATE OR REPLACE VIEW macrostrat_api.autocomplete as
SELECT autocomplete.id,
       autocomplete.name,
       autocomplete.type,
       autocomplete.category
FROM macrostrat.autocomplete
UNION ALL
SELECT sources.source_id AS id,
       sources.name,
       'sources'::character varying AS type,
       'maps'::character varying AS category
FROM maps.sources
UNION ALL
SELECT cols.id,
       cols.col_name AS name,
       'col'::character varying AS type,
       'columns'::character varying AS category
FROM macrostrat.cols
UNION ALL
SELECT projects.id,
       projects.project::text AS name,
       'project'::character varying AS type,
       'projects'::character varying AS category
FROM macrostrat.projects
UNION ALL
SELECT strat_names.id,
       strat_names.strat_name::text AS name,
       'strat_name'::character varying AS type,
       'strat_names'::character varying AS category
FROM macrostrat.strat_names
where concept_id is null;

GRANT USAGE ON SCHEMA macrostrat_api TO web_anon;

GRANT USAGE ON SCHEMA macrostrat_api TO web_user;

-- These two rewrite the column tree. EXECUTE on a function is PUBLIC by
-- default, so it is revoked outright and granted to administrators alone.
REVOKE ALL ON FUNCTION macrostrat_api.combine_sections(section_ids integer[]) FROM PUBLIC, web_anon;
GRANT EXECUTE ON FUNCTION macrostrat_api.combine_sections(section_ids integer[]) TO web_admin;

GRANT ALL ON FUNCTION macrostrat_api.get_col_strat_names(_col_id integer) TO web_anon;

GRANT ALL ON FUNCTION macrostrat_api.get_strat_name_info(strat_name_id integer) TO web_anon;

GRANT ALL ON FUNCTION macrostrat_api.get_strat_names_col_priority(_col_id integer) TO web_anon;

REVOKE ALL ON FUNCTION macrostrat_api.split_section(unit_ids integer[]) FROM PUBLIC, web_anon;
GRANT EXECUTE ON FUNCTION macrostrat_api.split_section(unit_ids integer[]) TO web_admin;

GRANT SELECT ON TABLE macrostrat_api.col_filters TO web_anon;

GRANT SELECT ON TABLE macrostrat_api.col_group_with_cols TO web_anon;

GRANT SELECT ON TABLE macrostrat_api.col_groups TO web_anon;

GRANT SELECT ON TABLE macrostrat_api.col_ref_expanded TO web_anon;

GRANT SELECT ON TABLE macrostrat_api.col_refs TO web_anon;

GRANT SELECT ON TABLE macrostrat_api.col_section_data TO web_anon;

GRANT SELECT ON TABLE macrostrat_api.col_sections TO web_anon;

GRANT SELECT ON TABLE macrostrat_api.cols TO web_anon;

GRANT SELECT ON TABLE macrostrat_api.cols_with_groups TO web_anon;

GRANT SELECT ON TABLE macrostrat_api.econ_unit TO web_anon;

GRANT SELECT ON TABLE macrostrat_api.environ_unit TO web_anon;

GRANT SELECT ON TABLE macrostrat_api.environs TO web_anon;

GRANT SELECT ON TABLE macrostrat_api.fossils TO web_anon;

GRANT SELECT ON TABLE macrostrat_api.intervals TO web_anon;

GRANT SELECT ON TABLE macrostrat_api.legend TO web_anon;

GRANT SELECT ON TABLE macrostrat_api.legend_liths TO web_anon;

GRANT SELECT ON TABLE macrostrat_api.lith_attr_unit TO web_anon;

GRANT SELECT ON TABLE macrostrat_api.lith_unit TO web_anon;

GRANT SELECT ON TABLE macrostrat_api.liths TO web_anon;

GRANT SELECT ON TABLE macrostrat_api.map_ingest TO web_user;

GRANT SELECT,UPDATE ON TABLE macrostrat_api.map_ingest TO web_admin;

GRANT SELECT ON TABLE macrostrat_api.map_ingest TO web_anon;

GRANT SELECT ON TABLE macrostrat_api.map_ingest_tags TO web_user;

GRANT SELECT,UPDATE ON TABLE macrostrat_api.map_ingest_tags TO web_admin;

GRANT SELECT ON TABLE macrostrat_api.map_ingest_tags TO web_anon;

GRANT SELECT ON TABLE macrostrat_api.mapped_sources TO web_anon;

GRANT SELECT ON TABLE macrostrat_api.mapped_sources TO web_user;

GRANT SELECT ON TABLE macrostrat_api.maps_sources TO web_user;

GRANT SELECT,UPDATE ON TABLE macrostrat_api.maps_sources TO web_admin;

GRANT SELECT ON TABLE macrostrat_api.maps_sources TO web_anon;

GRANT SELECT ON TABLE macrostrat_api.measurements_with_type TO web_anon;

GRANT SELECT ON TABLE macrostrat_api.minerals TO web_anon;

GRANT SELECT ON TABLE macrostrat_api.new_legend TO web_anon;


GRANT SELECT ON TABLE macrostrat_api.projects TO web_anon;

GRANT SELECT ON TABLE macrostrat_api.refs TO web_anon;

GRANT SELECT ON TABLE macrostrat_api.sections TO web_anon;

GRANT SELECT ON TABLE macrostrat_api.sources TO web_anon;

GRANT SELECT ON TABLE macrostrat_api.map_refs TO web_anon;

GRANT SELECT ON TABLE macrostrat_api.sources_ingestion TO web_anon;

GRANT SELECT ON TABLE macrostrat_api.sources_metadata TO web_anon;

GRANT SELECT ON TABLE macrostrat_api.strat_concepts_with_names TO web_anon;

GRANT SELECT ON TABLE macrostrat_api.strat_names_test TO web_anon;

GRANT SELECT ON TABLE macrostrat_api.strat_combined TO web_anon;

GRANT SELECT ON TABLE macrostrat_api.strat_concepts_test TO web_anon;

GRANT SELECT ON TABLE macrostrat_api.strat_combined_test TO web_anon;

GRANT SELECT ON TABLE macrostrat_api.strat_name_concepts TO web_anon;

GRANT SELECT ON TABLE macrostrat_api.strat_names TO web_anon;

GRANT SELECT ON TABLE macrostrat_api.strat_names_meta TO web_anon;

GRANT SELECT ON TABLE macrostrat_api.strat_names_ref TO web_anon;

GRANT SELECT ON TABLE macrostrat_api.strat_tree TO web_anon;

GRANT SELECT ON TABLE macrostrat_api.test_helper_functions TO web_anon;

GRANT SELECT ON TABLE macrostrat_api.timescales TO web_anon;

GRANT SELECT ON TABLE macrostrat_api.type_lookup TO web_anon;

GRANT SELECT ON TABLE macrostrat_api.unit_boundaries TO web_anon;

GRANT SELECT ON TABLE macrostrat_api.unit_environs TO web_anon;

GRANT SELECT ON TABLE macrostrat_api.unit_intervals TO web_anon;

GRANT SELECT ON TABLE macrostrat_api.unit_liths TO web_anon;

GRANT SELECT ON TABLE macrostrat_api.unit_strat_name_expanded TO web_anon;

GRANT SELECT ON TABLE macrostrat_api.unit_strat_names TO web_anon;

GRANT SELECT ON TABLE macrostrat_api.units TO web_anon;

ALTER DEFAULT PRIVILEGES FOR ROLE macrostrat IN SCHEMA macrostrat_api GRANT SELECT,USAGE ON SEQUENCES  TO web_user;

ALTER DEFAULT PRIVILEGES FOR ROLE macrostrat IN SCHEMA macrostrat_api GRANT SELECT,USAGE ON SEQUENCES  TO web_user;

ALTER DEFAULT PRIVILEGES FOR ROLE macrostrat IN SCHEMA macrostrat_api GRANT SELECT ON TABLES  TO web_anon;

ALTER DEFAULT PRIVILEGES FOR ROLE macrostrat IN SCHEMA macrostrat_api GRANT SELECT ON TABLES  TO web_anon;

--this is important so that postgrest works for the ingest process
GRANT USAGE ON SCHEMA macrostrat_api TO web_admin;

GRANT INSERT, SELECT, UPDATE, DELETE
ON ALL TABLES IN SCHEMA macrostrat_api
TO web_admin;

NOTIFY pgrst, 'reload schema';
