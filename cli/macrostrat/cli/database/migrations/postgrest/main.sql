CREATE VIEW macrostrat_api.autocomplete AS 
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
   FROM macrostrat.projects;

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

CREATE VIEW macrostrat_api.col_group_with_cols AS 
 SELECT cg.id,
    cg.col_group,
    cg.col_group_long,
    cg.project_id,
    p.project,
    COALESCE(jsonb_agg(jsonb_build_object('col_id', c.id, 'status_code', c.status_code, 'col_number', c.col, 'col_name', c.col_name)) FILTER (WHERE c.id IS NOT NULL), '[]'::jsonb) AS cols
   FROM macrostrat.col_groups cg
     LEFT JOIN macrostrat.cols c ON c.col_group_id = cg.id
     LEFT JOIN macrostrat.projects p ON p.id = cg.project_id
  GROUP BY cg.id, c.project_id, p.project;


CREATE VIEW macrostrat_api.col_groups AS
 SELECT col_groups.id,
    col_groups.col_group,
    col_groups.col_group_long,
    col_groups.project_id
   FROM macrostrat.col_groups;

CREATE VIEW macrostrat_api.col_ref_expanded AS
 SELECT c.id AS col_id,
    c.col_name,
    c.col AS col_number,
    ''::text AS notes,
    c.lat,
    c.lng,
    json_build_object('id', r.id, 'pub_year', r.pub_year, 'author', r.author, 'ref', r.ref, 'doi', r.doi, 'url', r.url) AS ref
   FROM ((macrostrat.cols c
     LEFT JOIN macrostrat.col_refs cr ON ((c.id = cr.col_id)))
     LEFT JOIN macrostrat.refs r ON ((cr.ref_id = r.id)));

CREATE VIEW macrostrat_api.col_refs AS
 SELECT col_refs.id,
    col_refs.col_id,
    col_refs.ref_id
   FROM macrostrat.col_refs;

CREATE VIEW macrostrat_api.col_section_data AS
 WITH a AS (
         SELECT us.unit_id,
            us.section_id,
            us.col_id,
            u.fo,
            fo.age_bottom AS fo_age,
            fo.interval_name AS fo_name,
            u.lo,
            lo.age_top AS lo_age,
            lo.interval_name AS lo_name
           FROM (((macrostrat.units_sections us
             JOIN macrostrat.units u ON ((us.unit_id = u.id)))
             JOIN macrostrat.intervals fo ON ((u.fo = fo.id)))
             JOIN macrostrat.intervals lo ON ((u.lo = lo.id)))
        )
 SELECT DISTINCT ON (a.col_id, a.section_id) a.col_id,
    a.section_id,
    count(*) OVER w AS unit_count,
    first_value(a.fo) OVER w AS fo,
    first_value(a.lo) OVER w AS lo,
    first_value(a.fo_name) OVER w AS bottom,
    first_value(a.fo_age) OVER w AS fo_age,
    first_value(a.lo_name) OVER w1 AS top,
    first_value(a.lo_age) OVER w1 AS lo_age
   FROM a
  WINDOW w AS (PARTITION BY a.col_id, a.section_id ORDER BY a.fo_age DESC), w1 AS (PARTITION BY a.col_id, a.section_id ORDER BY a.lo_age)
  ORDER BY a.col_id, a.section_id;

CREATE VIEW macrostrat_api.col_sections AS
 SELECT c.id AS col_id,
    c.col_name,
    u.section_id,
    u.position_top,
    u.position_bottom,
    fo.interval_name AS bottom,
    lo.interval_name AS top
   FROM (((macrostrat.cols c
     LEFT JOIN macrostrat.units u ON ((u.col_id = c.id)))
     LEFT JOIN macrostrat.intervals fo ON ((u.fo = fo.id)))
     LEFT JOIN macrostrat.intervals lo ON ((u.lo = lo.id)));

CREATE VIEW macrostrat_api.cols AS
 SELECT cols.id,
    cols.col_group_id,
    cols.project_id,
    cols.status_code,
    cols.col_type,
    cols.col_position,
    cols.col,
    cols.col_name,
    cols.lat,
    cols.lng,
    cols.col_area,
    cols.created,
    cols.coordinate,
    cols.wkt,
    cols.poly_geom
   FROM macrostrat.cols;

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

CREATE VIEW macrostrat_api.econ_unit AS
 SELECT e.id,
    e.econ,
    e.econ_type,
    e.econ_class,
    e.econ_color,
    ue.unit_id,
    ue.ref_id
   FROM (macrostrat.econs e
     JOIN macrostrat.unit_econs ue ON ((e.id = ue.econ_id)));

CREATE VIEW macrostrat_api.environ_unit AS
 SELECT e.id,
    e.environ,
    e.environ_type,
    e.environ_class,
    e.environ_fill,
    e.environ_color,
    ue.unit_id,
    ue.ref_id
   FROM (macrostrat.environs e
     JOIN macrostrat.unit_environs ue ON ((e.id = ue.environ_id)));

CREATE VIEW macrostrat_api.environs AS
 SELECT environs.id,
    environs.environ,
    environs.environ_type,
    environs.environ_class,
    environs.environ_fill,
    environs.environ_color
   FROM macrostrat.environs;

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

CREATE VIEW macrostrat_api.intervals AS
 SELECT intervals.id,
    intervals.age_bottom,
    intervals.age_top,
    intervals.interval_name,
    intervals.interval_abbrev,
    intervals.interval_type,
    intervals.interval_color,
    intervals.orig_color,
    intervals.rank
   FROM macrostrat.intervals;

CREATE VIEW macrostrat_api.kg_context_entities AS
 WITH entities AS (
         SELECT kg_entity_tree.source_text,
            kg_entity_tree.paper_id,
            kg_entity_tree.model_run,
            jsonb_agg(kg_entity_tree.tree) AS entities
           FROM macrostrat_api.kg_entity_tree
          GROUP BY kg_entity_tree.source_text, kg_entity_tree.paper_id, kg_entity_tree.model_run
        )
 SELECT st.id AS source_text,
    st.paper_id,
    mr.id AS model_run,
    COALESCE(e.entities, '[]'::jsonb) AS entities,
    st.weaviate_id,
    st.paragraph_text,
    st.hashed_text,
    st.preprocessor_id,
    mr.model_id,
    mr.version_id,
    mr.user_id
   FROM ((macrostrat_xdd.source_text st
     LEFT JOIN macrostrat_xdd.model_run mr ON ((mr.source_text_id = st.id)))
     LEFT JOIN entities e ON ((e.model_run = mr.id)));

CREATE VIEW macrostrat_api.kg_entities AS
 WITH strat_names AS (
         SELECT strat_names.id AS strat_name_id,
            strat_names.concept_id,
            strat_names.strat_name AS name,
            strat_names.rank
           FROM macrostrat.strat_names
        ), liths AS (
         SELECT liths.id AS lith_id,
            liths.lith AS name,
            liths.lith_color AS color
           FROM macrostrat.liths
        ), lith_atts AS (
         SELECT lith_atts.id AS lith_att_id,
            lith_atts.lith_att AS name
           FROM macrostrat.lith_atts
        )
 SELECT e.id,
    et.id AS type,
    e.name,
    ARRAY[e.start_index, e.end_index] AS indices,
    mr.id AS model_run,
    mr.source_text_id AS source,
    COALESCE(to_json(sn.*), to_json(l.*), to_json(la.*)) AS match
   FROM (((((macrostrat_xdd.entity e
     JOIN macrostrat_xdd.entity_type et ON ((et.id = e.entity_type_id)))
     JOIN macrostrat_xdd.model_run mr ON ((mr.id = e.run_id)))
     LEFT JOIN strat_names sn ON ((sn.strat_name_id = e.strat_name_id)))
     LEFT JOIN liths l ON ((l.lith_id = e.lith_id)))
     LEFT JOIN lith_atts la ON ((la.lith_att_id = e.lith_att_id)));

CREATE VIEW macrostrat_api.kg_entity_tree AS
 WITH RECURSIVE start_entities AS (
         SELECT entity.id
           FROM macrostrat_xdd.entity
        EXCEPT
         SELECT relationship.src_entity_id
           FROM macrostrat_xdd.relationship
        ), e0 AS (
         SELECT e.model_run,
            e.id,
            jsonb_strip_nulls(((to_jsonb(e.*) - 'model_run'::text) - 'source'::text)) AS tree,
            ((e.match IS NOT NULL))::integer AS n_matches
           FROM macrostrat_api.kg_entities e
        ), tree AS (
         SELECT e0.model_run,
            r.src_entity_id AS parent_id,
            se.id AS entity_id,
            e0.tree,
            0 AS depth,
            1 AS n_entities,
            e0.n_matches
           FROM ((e0
             JOIN start_entities se ON ((se.id = e0.id)))
             LEFT JOIN macrostrat_xdd.relationship r ON ((r.dst_entity_id = se.id)))
        UNION
         SELECT a.model_run,
            a.src_entity_id,
            a.parent_id,
            (e0.tree || jsonb_build_object('children', json_agg(a.tree))),
            (a.depth + 1),
            ((sum(a.n_entities))::integer + 1),
            ((sum(a.n_matches))::integer + e0.n_matches)
           FROM (( SELECT tree_1.model_run,
                    r1.src_entity_id,
                    tree_1.parent_id,
                    tree_1.tree,
                    tree_1.depth,
                    tree_1.n_entities,
                    tree_1.n_matches
                   FROM (tree tree_1
                     LEFT JOIN macrostrat_xdd.relationship r1 ON ((r1.dst_entity_id = tree_1.parent_id)))) a
             JOIN e0 ON ((e0.id = a.parent_id)))
          GROUP BY a.model_run, a.depth, e0.tree, e0.n_matches, a.src_entity_id, a.parent_id
        )
 SELECT st.paper_id,
    tree.model_run,
    tree.entity_id AS entity,
    (tree.tree ->> 'type'::text) AS type,
    mr.source_text_id AS source_text,
    tree.n_entities,
    tree.n_matches,
    tree.tree,
    tree.depth
   FROM ((tree
     JOIN macrostrat_xdd.model_run mr ON ((mr.id = tree.model_run)))
     JOIN macrostrat_xdd.source_text st ON ((st.id = mr.source_text_id)))
  WHERE (tree.parent_id IS NULL);

CREATE VIEW macrostrat_api.kg_entity_type AS
 SELECT entity_type.id,
    entity_type.name,
    entity_type.description,
    entity_type.color
   FROM macrostrat_xdd.entity_type;

CREATE VIEW macrostrat_api.kg_extraction_feedback_type AS
 SELECT extraction_feedback_type.id,
    extraction_feedback_type.type
   FROM macrostrat_xdd.extraction_feedback_type;

CREATE VIEW macrostrat_api.kg_matches AS
 SELECT DISTINCT ON (s.paragraph_text) e.id,
    e.source,
    s.paragraph_text AS context_text,
    e.match,
    e.name,
    ((e.match ->> 'lith_id'::text))::integer AS lith_id,
    ((e.match ->> 'strat_name_id'::text))::integer AS strat_name_id,
    ((e.match ->> 'lith_att_id'::text))::integer AS lith_att_id,
    ((e.match ->> 'concept_id'::text))::integer AS concept_id,
    e.indices
   FROM (macrostrat_api.kg_entities e
     LEFT JOIN macrostrat_api.kg_source_text s ON ((e.source = s.id)))
  WHERE (e.match IS NOT NULL)
  ORDER BY s.paragraph_text, e.id;

CREATE VIEW macrostrat_api.kg_model AS
 SELECT m.id,
    m.name,
    m.description,
    m.url,
    min(mr."timestamp") AS first_run,
    max(mr."timestamp") AS last_run,
    count(DISTINCT mr.id) AS n_runs,
    count(DISTINCT e.id) AS n_entities,
    count((COALESCE(e.strat_name_id, e.lith_id, e.lith_att_id))::boolean) AS n_matches,
    count((e.strat_name_id)::boolean) AS n_strat_names
   FROM ((macrostrat_xdd.model m
     LEFT JOIN macrostrat_xdd.model_run mr ON ((mr.model_id = m.id)))
     LEFT JOIN macrostrat_xdd.entity e ON ((e.run_id = mr.id)))
  GROUP BY m.id;

CREATE VIEW macrostrat_api.kg_model_run AS
 SELECT mr.id,
    mr.user_id,
    mr."timestamp",
    mr.model_id,
    m.name AS model_name,
    mr.version_id,
    mr.source_text_id,
    st.source_text_type,
    st.map_legend_id,
    st.weaviate_id,
    mr.supersedes,
    mr1.id AS superseded_by
   FROM (((macrostrat_xdd.model_run mr
     LEFT JOIN macrostrat_xdd.model_run mr1 ON ((mr1.supersedes = mr.id)))
     JOIN macrostrat_xdd.model m ON ((m.id = mr.model_id)))
     JOIN macrostrat_xdd.source_text st ON ((st.id = mr.source_text_id)))
  ORDER BY mr.id;

CREATE VIEW macrostrat_api.kg_publication_entities AS
 WITH paper_strat_names AS (
         SELECT p_1.paper_id,
            array_agg(DISTINCT mr.model_id) AS models,
            array_agg(DISTINCT e_1.strat_name_id) AS strat_name_matches,
            count(DISTINCT e_1.strat_name_id) AS n_matches
           FROM (((macrostrat_xdd.publication p_1
             JOIN macrostrat_xdd.source_text st ON ((st.paper_id = p_1.paper_id)))
             JOIN macrostrat_xdd.model_run mr ON ((mr.source_text_id = st.id)))
             JOIN macrostrat_xdd.entity e_1 ON ((mr.id = e_1.run_id)))
          WHERE (e_1.strat_name_id IS NOT NULL)
          GROUP BY p_1.paper_id
        ), entities AS (
         SELECT kg_entity_tree.paper_id,
            jsonb_agg((kg_entity_tree.tree || jsonb_build_object('model_run', kg_entity_tree.model_run, 'depth', kg_entity_tree.depth, 'source', kg_entity_tree.source_text))) AS entities
           FROM macrostrat_api.kg_entity_tree
          GROUP BY kg_entity_tree.paper_id
        )
 SELECT pub.paper_id,
    pub.citation,
    p.strat_name_matches,
    p.n_matches,
    p.models,
    e.entities,
    row_number() OVER () AS id
   FROM ((macrostrat_xdd.publication pub
     LEFT JOIN paper_strat_names p ON ((pub.paper_id = p.paper_id)))
     LEFT JOIN entities e ON ((p.paper_id = e.paper_id)))
  ORDER BY p.n_matches DESC;

CREATE VIEW macrostrat_api.kg_source_text AS
 WITH stats AS (
         SELECT mr.source_text_id,
            count(DISTINCT mr.id) AS n_runs,
            count(DISTINCT e.id) AS n_entities,
            count((COALESCE(e.strat_name_id, e.lith_id, e.lith_att_id))::boolean) AS n_matches,
            count((e.strat_name_id)::boolean) AS n_strat_names,
            min(mr."timestamp") AS created,
            max(mr."timestamp") AS last_update
           FROM (macrostrat_xdd.model_run mr
             LEFT JOIN macrostrat_xdd.entity e ON ((e.run_id = mr.id)))
          GROUP BY mr.source_text_id
        )
 SELECT st.preprocessor_id,
    st.paper_id,
    st.hashed_text,
    st.weaviate_id,
    st.paragraph_text,
    st.id,
    st.map_legend_id,
    st.source_text_type,
    s.n_runs,
    s.n_entities,
    s.n_matches,
    s.n_strat_names,
    s.created,
    s.last_update
   FROM (macrostrat_xdd.source_text st
     JOIN stats s ON ((s.source_text_id = st.id)));

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

CREATE VIEW macrostrat_api.legend AS
 WITH _intervals AS (
         SELECT intervals.id,
            json_build_object('id', intervals.id, 'name', intervals.interval_name, 'color', intervals.interval_color, 'rank', intervals.rank, 'b_age', intervals.age_bottom, 't_age', intervals.age_top) AS _interval
           FROM macrostrat_backup.intervals
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
             JOIN macrostrat_backup.liths l_1 ON ((ll_1.lith_id = l_1.id)))
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

CREATE VIEW macrostrat_api.lith_attr_unit AS
 SELECT la.id AS lith_attr_id,
    la.lith_att,
    la.att_type,
    la.lith_att_fill,
    l.id,
    l.lith,
    l.lith_group,
    l.lith_type,
    l.lith_class,
    l.lith_equiv,
    l.lith_fill,
    l.comp_coef,
    l.initial_porosity,
    l.bulk_density,
    l.lith_color,
    ul.unit_id
   FROM (((macrostrat.lith_atts la
     JOIN macrostrat.unit_liths_atts ula ON ((ula.lith_att_id = la.id)))
     JOIN macrostrat.unit_liths ul ON ((ul.id = ula.unit_lith_id)))
     JOIN macrostrat.liths l ON ((ul.lith_id = l.id)));

CREATE VIEW macrostrat_api.lith_unit AS
 SELECT l.id,
    l.lith,
    l.lith_group,
    l.lith_type,
    l.lith_class,
    l.lith_color,
    ul.dom,
    ul.prop,
    ul.mod_prop,
    ul.comp_prop,
    ul.ref_id,
    ul.unit_id
   FROM (macrostrat.liths l
     JOIN macrostrat.unit_liths ul ON ((ul.lith_id = l.id)));

CREATE VIEW macrostrat_api.liths AS
 SELECT liths.id,
    liths.lith,
    liths.lith_group,
    liths.lith_type,
    liths.lith_class,
    liths.lith_equiv,
    liths.lith_fill,
    liths.comp_coef,
    liths.initial_porosity,
    liths.bulk_density,
    liths.lith_color
   FROM macrostrat.liths;

CREATE VIEW macrostrat_api.location_tags AS
 SELECT location_tags.id,
    location_tags.name,
    location_tags.description,
    location_tags.color
   FROM user_features.location_tags;

CREATE VIEW macrostrat_api.location_tags_intersect AS
 SELECT location_tags_intersect.tag_id,
    location_tags_intersect.user_id,
    location_tags_intersect.location_id
   FROM user_features.location_tags_intersect;

CREATE VIEW macrostrat_api.map_ingest_metadata AS
 SELECT ingest_process.id,
    ingest_process.state,
    ingest_process.comments,
    ingest_process.source_id,
    ingest_process.access_group_id,
    ingest_process.object_group_id,
    ingest_process.created_on,
    ingest_process.completed_on,
    ingest_process.map_id,
    ingest_process.type,
    ingest_process.polygon_state,
    ingest_process.line_state,
    ingest_process.point_state
   FROM maps_metadata.ingest_process;

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

CREATE VIEW macrostrat_api.projects AS
 SELECT projects.id,
    projects.project,
    projects.descrip,
    projects.timescale_id
   FROM macrostrat.projects;

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

CREATE VIEW macrostrat_api.sections AS
 SELECT sections.id,
    sections.col_id,
    sections.fo,
    sections.fo_h,
    sections.lo,
    sections.lo_h
   FROM macrostrat.sections;

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
    s.licence,
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
    s.licence,
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
    i.map_id,
    s.is_finalized,
    s.scale_denominator
   FROM (maps.sources_metadata s
     JOIN maps_metadata.ingest_process i ON ((i.source_id = s.source_id)));

CREATE VIEW macrostrat_api.sources_metadata AS
 SELECT sources_metadata.source_id,
    sources_metadata.slug,
    sources_metadata.name,
    sources_metadata.url,
    sources_metadata.ref_title,
    sources_metadata.authors,
    sources_metadata.ref_year,
    sources_metadata.ref_source,
    sources_metadata.isbn_doi,
    sources_metadata.scale,
    sources_metadata.licence,
    sources_metadata.features,
    sources_metadata.area,
    sources_metadata.display_scales,
    sources_metadata.priority,
    sources_metadata.status_code,
    sources_metadata.raster_url,
    sources_metadata.scale_denominator,
    sources_metadata.is_finalized,
    sources_metadata.lines_oriented,
    sources_metadata.is_finalized AS is_mapped
   FROM maps.sources_metadata;

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

CREATE VIEW macrostrat_api.strat_names AS
 SELECT strat_names.id,
    strat_names.old_id,
    strat_names.concept_id,
    strat_names.strat_name,
    strat_names.rank,
    strat_names.old_strat_name_id,
    strat_names.ref_id,
    strat_names.places,
    strat_names.orig_id
   FROM macrostrat.strat_names;

CREATE VIEW macrostrat_api.strat_names_meta AS
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

CREATE VIEW macrostrat_api.timescales AS
 SELECT timescales.id,
    timescales.timescale,
    timescales.ref_id
   FROM macrostrat.timescales;

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

CREATE VIEW macrostrat_api.unit_environs AS
 SELECT unit_environs.id,
    unit_environs.unit_id,
    unit_environs.environ_id,
    unit_environs.f,
    unit_environs.l,
    unit_environs.ref_id,
    unit_environs.date_mod
   FROM macrostrat.unit_environs;

CREATE VIEW macrostrat_api.unit_intervals AS
 SELECT i.id AS int_id,
    u.unit_id
   FROM (macrostrat.intervals i
     JOIN macrostrat.lookup_units u ON (((u.b_age <= i.age_bottom) AND (u.t_age >= i.age_top))));

CREATE VIEW macrostrat_api.unit_liths AS
 SELECT unit_liths.id,
    unit_liths.lith_id,
    unit_liths.unit_id,
    unit_liths.prop,
    unit_liths.dom,
    unit_liths.comp_prop,
    unit_liths.mod_prop,
    unit_liths.toc,
    unit_liths.ref_id,
    unit_liths.date_mod
   FROM macrostrat.unit_liths;

CREATE VIEW macrostrat_api.unit_strat_name_expanded AS
 SELECT usn.id,
    usn.unit_id,
    usn.strat_name_id,
    sn.strat_name,
    u.color,
    u.outcrop,
    u.fo,
    u.lo,
    u.position_bottom,
    u.position_top,
    u.max_thick,
    u.min_thick,
    u.section_id,
    u.col_id,
    ''::text AS notes,
    fo.interval_name AS name_fo,
    fo.age_bottom,
    lo.interval_name AS name_lo,
    lo.age_top
   FROM ((((macrostrat.unit_strat_names usn
     JOIN macrostrat.units u ON ((u.id = usn.unit_id)))
     LEFT JOIN macrostrat.strat_names sn ON ((usn.strat_name_id = sn.id)))
     LEFT JOIN macrostrat.intervals fo ON ((u.fo = fo.id)))
     LEFT JOIN macrostrat.intervals lo ON ((u.lo = lo.id)));

CREATE VIEW macrostrat_api.unit_strat_names AS
 SELECT unit_strat_names.id,
    unit_strat_names.unit_id,
    unit_strat_names.strat_name_id,
    unit_strat_names.old_strat_name_id
   FROM macrostrat.unit_strat_names;

CREATE VIEW macrostrat_api.units AS
 SELECT units.id,
    units.strat_name,
    units.color,
    units.outcrop,
    units.fo,
    units.fo_h,
    units.lo,
    units.lo_h,
    units.position_bottom,
    units.position_top,
    units.max_thick,
    units.min_thick,
    units.section_id,
    units.col_id,
    units.date_mod
   FROM macrostrat.units;

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