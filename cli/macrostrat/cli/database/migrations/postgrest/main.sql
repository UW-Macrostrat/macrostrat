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
   where concept_id is null
   
CREATE VIEW macrostrat_api.col_base AS 
 SELECT c.id AS col_id,
    c.col_group_id,
    c.project_id,
    c.col_name AS name,
    c.status_code,
    NOT (EXISTS ( SELECT 1
           FROM macrostrat_api.units u2
          WHERE u2.col_id = c.id)) AS empty,
    jsonb_agg(DISTINCT u.id) FILTER (WHERE u.id IS NOT NULL) AS units
   FROM macrostrat.cols c
     LEFT JOIN macrostrat_api.units u ON c.id = u.col_id
  GROUP BY c.id;

CREATE VIEW macrostrat_api.col_data AS 
 SELECT c.id AS col_id,
    c.col_group_id,
    c.project_id,
    c.col_name AS name,
    c.status_code,
    jsonb_agg(DISTINCT l.lith_id) FILTER (WHERE l.lith_id IS NOT NULL) AS liths,
    jsonb_agg(DISTINCT sn.strat_name_id) FILTER (WHERE sn.strat_name_id IS NOT NULL) AS strat_names,
    jsonb_agg(DISTINCT u.id) FILTER (WHERE u.id IS NOT NULL) AS units,
    jsonb_agg(DISTINCT i.int_id) FILTER (WHERE i.int_id IS NOT NULL) AS intervals,
    NOT (EXISTS ( SELECT 1
           FROM macrostrat_api.units u2
          WHERE u2.col_id = c.id)) AS empty
   FROM macrostrat.cols c
     LEFT JOIN macrostrat_api.units u ON c.id = u.col_id
     LEFT JOIN macrostrat_api.unit_strat_names sn ON sn.unit_id = u.id
     LEFT JOIN macrostrat_api.unit_liths l ON l.unit_id = u.id
     LEFT JOIN macrostrat_api.unit_intervals i ON i.unit_id = u.id
  GROUP BY c.id;

CREATE VIEW macrostrat_api.col_filter AS 
 SELECT row_number() OVER () AS id,
    combined.name,
    combined.color,
    combined.lex_id,
    combined.type
   FROM ( SELECT liths.lith AS name,
            liths.lith_color AS color,
            liths.id AS lex_id,
            'lithology'::text AS type
           FROM macrostrat.liths
        UNION ALL
         SELECT strat_names.strat_name AS name,
            NULL::character varying AS color,
            strat_names.id AS lex_id,
            'strat name'::text AS type
           FROM macrostrat.strat_names
        UNION ALL
         SELECT intervals.interval_name AS name,
            intervals.interval_color AS color,
            intervals.id AS lex_id,
            'interval'::text AS type
           FROM macrostrat.intervals
        UNION ALL
         SELECT units.strat_name AS name,
            NULL::character varying AS color,
            units.id AS lex_id,
            'unit'::text AS type
           FROM macrostrat.units) combined;

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

CREATE VIEW macrostrat_api.cols_with_liths AS
 SELECT c.id,
    c.col_group_id,
    c.project_id,
    c.status_code,
    c.col_type,
    c.col_position,
    c.col,
    c.col_name,
    c.lat,
    c.lng,
    c.col_area,
    c.created,
    c.coordinate,
    c.wkt,
    c.poly_geom,
    jsonb_agg(DISTINCT l.lith_id) FILTER (WHERE (l.lith_id IS NOT NULL)) AS liths
   FROM ((macrostrat.cols c
     LEFT JOIN macrostrat_api.units u ON ((c.id = u.col_id)))
     LEFT JOIN macrostrat_api.unit_liths l ON ((l.unit_id = u.id)))
  GROUP BY c.id;

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

CREATE VIEW macrostrat_api.grouped_autocomplete AS
 SELECT t.type,
    json_agg((to_jsonb(t.*) - 'type'::text)) AS items
   FROM macrostrat_api.autocomplete t
  GROUP BY t.type;

CREATE VIEW macrostrat_api.kg_extraction_feedback_type AS
 SELECT extraction_feedback_type.id,
    extraction_feedback_type.type
   FROM macrostrat_xdd.extraction_feedback_type;

CREATE VIEW macrostrat_api.kg_source_text_casted AS
 SELECT (t.id)::text AS id,
    (t.created)::text AS created,
    (t.last_update)::text AS last_update,
    t.paper_id,
    t.paragraph_text,
    t.n_runs,
    t.n_entities,
    t.n_matches,
    t.n_strat_names,
    e.model_id,
    m.name AS model_name,
    bool_or((r.user_id IS NOT NULL)) AS has_feedback
   FROM (((macrostrat_api.kg_source_text t
     LEFT JOIN macrostrat_api.kg_context_entities e ON ((e.source_text = t.id)))
     LEFT JOIN macrostrat_api.kg_model m ON ((m.id = e.model_id)))
     LEFT JOIN macrostrat_api.kg_model_run r ON ((t.id = r.source_text_id)))
  GROUP BY t.id, t.created, t.last_update, t.paper_id, t.paragraph_text, t.n_runs, t.n_entities, t.n_matches, t.n_strat_names, e.model_id, m.name;

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
    s.licence,
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

CREATE VIEW macrostrat_api.people AS
 SELECT people.person_id,
    people.name,
    people.email,
    people.title,
    people.website,
    people.img_id,
    people.active_start,
    people.active_end
   FROM ecosystem.people;

CREATE VIEW macrostrat_api.people_roles AS
 SELECT people_roles.person_id,
    people_roles.role_id
   FROM ecosystem.people_roles;

CREATE VIEW macrostrat_api.people_with_roles AS
 SELECT p.person_id,
    p.name,
    p.email,
    p.title,
    p.website,
    p.img_id,
    p.active_start,
    p.active_end,
    COALESCE(json_agg(json_build_object('name', r.name, 'description', r.description)) FILTER (WHERE (r.role_id IS NOT NULL))) AS roles
   FROM ((ecosystem.people p
     LEFT JOIN ecosystem.people_roles pr ON ((p.person_id = pr.person_id)))
     LEFT JOIN ecosystem.roles r ON ((pr.role_id = r.role_id)))
  GROUP BY p.person_id;

CREATE VIEW macrostrat_api.refs AS
 SELECT refs.id,
    refs.pub_year,
    refs.author,
    refs.ref,
    refs.doi,
    refs.compilation_code,
    refs.url,
    refs.rgeom
   FROM macrostrat.refs;

CREATE VIEW macrostrat_api.roles AS
 SELECT roles.role_id,
    roles.name,
    roles.description
   FROM ecosystem.roles;

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

CREATE VIEW macrostrat_api.strat_names_ref AS
 SELECT s.id,
    s.strat_name,
    s.rank,
    row_to_json(r.*) AS ref,
    row_to_json(sm.*) AS concept
   FROM ((macrostrat.strat_names s
     LEFT JOIN macrostrat.refs r ON ((r.id = s.ref_id)))
     LEFT JOIN macrostrat.strat_names_meta sm ON ((sm.concept_id = s.concept_id)));

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

CREATE VIEW macrostrat_api.strat_tree AS
 SELECT strat_tree.id,
    strat_tree.parent,
    strat_tree.rel,
    strat_tree.child,
    strat_tree.ref_id,
    strat_tree.check_me
   FROM macrostrat.strat_tree;

CREATE VIEW macrostrat_api.test_helper_functions AS
 SELECT user_features.current_app_role() AS current_app_role,
    user_features.current_app_user_id() AS current_app_user_id;

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

CREATE VIEW macrostrat_api.unit_boundaries AS
 SELECT unit_boundaries.id,
    unit_boundaries.t1,
    unit_boundaries.t1_prop,
    unit_boundaries.t1_age,
    unit_boundaries.unit_id,
    unit_boundaries.unit_id_2,
    unit_boundaries.section_id,
    unit_boundaries.boundary_position,
    unit_boundaries.boundary_type,
    unit_boundaries.boundary_status,
    unit_boundaries.paleo_lat,
    unit_boundaries.paleo_lng,
    unit_boundaries.ref_id
   FROM macrostrat.unit_boundaries;

CREATE VIEW macrostrat_api.unit_intervals AS
 SELECT i.id AS int_id,
    u.unit_id
   FROM (macrostrat.intervals i
     JOIN macrostrat.lookup_units u ON (((u.b_age <= i.age_bottom) AND (u.t_age >= i.age_top))));

CREATE VIEW macrostrat_api.user_locations_view AS
 SELECT user_locations.id,
    user_locations.user_id,
    user_locations.name,
    user_locations.description,
    user_locations.point,
    user_locations.zoom,
    user_locations.meters_from_point,
    user_locations.elevation,
    user_locations.azimuth,
    user_locations.pitch,
    user_locations.map_layers
   FROM user_features.user_locations;

CREATE VIEW macrostrat_api.legend_liths AS
 SELECT l.legend_id,
    l.source_id,
    l.name AS map_unit_name,
    array_agg(ll.lith_id) FILTER (WHERE (ll.lith_id IS NOT NULL)) AS lith_ids
   FROM (maps.legend l
     LEFT JOIN maps.legend_liths ll ON ((ll.legend_id = l.legend_id)))
  GROUP BY l.legend_id, l.source_id, l.name;