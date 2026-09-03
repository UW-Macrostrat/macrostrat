
CREATE VIEW macrostrat_api.kg_entities AS
WITH matches AS (SELECT mt.id,
                   json_build_object(
                     'macrostrat_terms_id', mt.id,
                     'entity_id', mt.entity_id,
                     'entity_type', mt.entity_type,
                     'name', mt.name
                   ) AS match
                 FROM macrostrat_kg.macrostrat_terms mt)
SELECT e.id,
  et.id                                                AS type,
  e.name,
  ARRAY [e.start_index, e.end_index]                   AS indices,
  mr.id                                                AS model_run,
  mr.source_text_id                                    AS source,
  m.match
FROM macrostrat_kg.entity e
JOIN macrostrat_kg.entity_type et ON et.id = e.entity_type_id
JOIN macrostrat_kg.model_run mr ON mr.id = e.run_id
LEFT JOIN matches m ON m.id = e.macrostrat_terms_id;


CREATE OR REPLACE VIEW macrostrat_api.kg_entity_tree AS
WITH RECURSIVE
  start_entities AS (
    SELECT e.id
    FROM macrostrat_kg.entity e

    EXCEPT

    SELECT r.src_entity_id
    FROM macrostrat_kg.relationship r
  ),

  e0 AS (
    SELECT
      e.model_run,
      e.id,
      jsonb_strip_nulls(
        to_jsonb(e.*) - 'model_run' - 'source'
      ) AS tree,
      (e.match IS NOT NULL)::integer AS n_matches
    FROM macrostrat_api.kg_entities e
  ),

  tree AS (
    SELECT
      e0.model_run,
      r.src_entity_id AS parent_id,
      se.id AS entity_id,
      e0.tree,
      0 AS depth,
      1 AS n_entities,
      e0.n_matches
    FROM e0
    JOIN start_entities se
    ON se.id = e0.id
    LEFT JOIN macrostrat_kg.relationship r
    ON r.dst_entity_id = se.id

    UNION

    SELECT
      a.model_run,
      a.src_entity_id,
      a.parent_id,
      e0.tree ||
      jsonb_build_object(
        'children',
        jsonb_agg(a.tree)
      ),
      a.depth + 1,
      sum(a.n_entities)::integer + 1,
      sum(a.n_matches)::integer + e0.n_matches
    FROM (
      SELECT
        t.model_run,
        r.src_entity_id,
        t.parent_id,
        t.tree,
        t.depth,
        t.n_entities,
        t.n_matches
      FROM tree t
      LEFT JOIN macrostrat_kg.relationship r
      ON r.dst_entity_id = t.parent_id
    ) a
    JOIN e0
    ON e0.id = a.parent_id
    GROUP BY
      a.model_run,
      a.depth,
      e0.tree,
      e0.n_matches,
      a.src_entity_id,
      a.parent_id
  ),

  root_rows AS (
    SELECT
      t.model_run,
      t.entity_id AS entity,
      t.tree,
      t.depth,
      t.n_entities,
      t.n_matches
    FROM tree t
    WHERE t.parent_id IS NULL
  ),

  root_children AS (
    SELECT
      rr.model_run,
      rr.entity,
      jsonb_agg(
        child.value
        ORDER BY (child.value ->> 'id')::bigint
      ) AS children
    FROM root_rows rr
    CROSS JOIN LATERAL jsonb_array_elements(
      COALESCE(rr.tree -> 'children', '[]'::jsonb)
                       ) AS child(value)
    GROUP BY
      rr.model_run,
      rr.entity
  ),

  merged_roots AS (
    SELECT
      rr.model_run,
      rr.entity,

      (
        (array_agg(
          rr.tree - 'children'
          ORDER BY rr.depth DESC
         ))[1]
          ||
        CASE
          WHEN rc.children IS NOT NULL
            THEN jsonb_build_object(
            'children',
            rc.children
                 )
          ELSE '{}'::jsonb
          END
        ) AS tree,

      (
        sum(rr.n_entities) - (count(*) - 1)
        )::integer AS n_entities,

      (
        sum(rr.n_matches)
          - root_entity.n_matches * (count(*) - 1)
        )::integer AS n_matches,

      max(rr.depth) AS depth

    FROM root_rows rr

    JOIN e0 root_entity
    ON root_entity.model_run = rr.model_run
      AND root_entity.id = rr.entity

    LEFT JOIN root_children rc
    ON rc.model_run = rr.model_run
      AND rc.entity = rr.entity

    GROUP BY
      rr.model_run,
      rr.entity,
      root_entity.n_matches,
      rc.children
  )

SELECT
  st.paper_id,
  merged.model_run,
  merged.entity,
  merged.tree ->> 'type' AS type,
  mr.source_text_id AS source_text,
  merged.n_entities,
  merged.n_matches,
  merged.tree,
  merged.depth
FROM merged_roots merged
JOIN macrostrat_kg.model_run mr
ON mr.id = merged.model_run
JOIN macrostrat_kg.source_text st
ON st.id = mr.source_text_id;

CREATE VIEW macrostrat_api.kg_entity_type AS
SELECT entity_type.id,
  entity_type.name,
  entity_type.description,
  entity_type.color
FROM macrostrat_kg.entity_type;

CREATE VIEW macrostrat_api.kg_extraction_feedback_type AS
SELECT extraction_feedback_type.type_id,
  extraction_feedback_type.type
FROM macrostrat_kg.extraction_feedback_type;

CREATE VIEW macrostrat_api.kg_source_text AS
WITH stats AS (
  SELECT mr.source_text_id,
    count(DISTINCT mr.id) AS n_runs,
    count(DISTINCT e.id) AS n_entities,
    count((COALESCE(e.strat_name_id, e.lith_id, e.lith_att_id))::boolean) AS n_matches,
    count((e.strat_name_id)::boolean) AS n_strat_names,
    min(mr."timestamp") AS created,
    max(mr."timestamp") AS last_update
  FROM (macrostrat_kg.model_run mr
    LEFT JOIN macrostrat_kg.entity e ON ((e.run_id = mr.id)))
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
FROM (macrostrat_kg.source_text st
  JOIN stats s ON ((s.source_text_id = st.id)));

CREATE VIEW macrostrat_api.kg_matches AS
WITH all_lith_ids AS (
  SELECT (liths.id)::text AS lith_id,
    NULL::text AS lith_att_id
  FROM macrostrat.liths
  UNION ALL
  SELECT NULL::text AS lith_id,
    (lith_atts.id)::text AS lith_att_id
  FROM macrostrat.lith_atts
), parsed_kg_entities AS (
  SELECT kg_entities.id,
    (kg_entities.match)::jsonb AS match,
    kg_entities.source,
    kg_entities.indices,
    ((kg_entities.match)::jsonb ->> 'lith_id'::text) AS lith_id,
    ((kg_entities.match)::jsonb ->> 'lith_att_id'::text) AS lith_att_id
  FROM macrostrat_api.kg_entities
)
SELECT a.lith_id,
  a.lith_att_id,
  k.match,
  k.source,
  k.indices,
  s.paragraph_text AS context_text
FROM ((all_lith_ids a
  LEFT JOIN parsed_kg_entities k ON ((((a.lith_id IS NOT NULL) AND (k.lith_id = a.lith_id)) OR ((a.lith_att_id IS NOT NULL) AND (k.lith_att_id = a.lith_att_id)))))
  LEFT JOIN macrostrat_api.kg_source_text s ON ((k.source = s.id)));

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
FROM ((macrostrat_kg.model m
  LEFT JOIN macrostrat_kg.model_run mr ON ((mr.model_id = m.id)))
  LEFT JOIN macrostrat_kg.entity e ON ((e.run_id = mr.id)))
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
FROM (((macrostrat_kg.model_run mr
  LEFT JOIN macrostrat_kg.model_run mr1 ON ((mr1.supersedes = mr.id)))
  JOIN macrostrat_kg.model m ON ((m.id = mr.model_id)))
  JOIN macrostrat_kg.source_text st ON ((st.id = mr.source_text_id)))
ORDER BY mr.id;

CREATE VIEW macrostrat_api.kg_publication_entities AS
WITH paper_strat_names AS (
  SELECT p_1.paper_id,
    array_agg(DISTINCT mr.model_id) AS models,
    array_agg(DISTINCT e_1.strat_name_id) AS strat_name_matches,
    count(DISTINCT e_1.strat_name_id) AS n_matches
  FROM (((macrostrat_kg.publication p_1
    JOIN macrostrat_kg.source_text st ON ((st.paper_id = p_1.paper_id)))
    JOIN macrostrat_kg.model_run mr ON ((mr.source_text_id = st.id)))
    JOIN macrostrat_kg.entity e_1 ON ((mr.id = e_1.run_id)))
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
  e.entities
FROM ((macrostrat_kg.publication pub
  LEFT JOIN paper_strat_names p ON ((pub.paper_id = p.paper_id)))
  LEFT JOIN entities e ON ((p.paper_id = e.paper_id)))
ORDER BY p.n_matches DESC;

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


CREATE OR REPLACE VIEW macrostrat_api.kg_context_entities AS
WITH entities AS (
  SELECT
    et.source_text,
    et.paper_id,
    et.model_run,
    jsonb_agg(
      et.tree
      ORDER BY et.entity
    ) AS entities
  FROM macrostrat_api.kg_entity_tree et
  GROUP BY
    et.source_text,
    et.paper_id,
    et.model_run
)
SELECT
  st.id AS source_text,
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
FROM macrostrat_kg.source_text st
LEFT JOIN macrostrat_kg.model_run mr
ON mr.source_text_id = st.id
LEFT JOIN entities e
ON e.source_text = st.id
  AND e.paper_id = st.paper_id
  AND e.model_run = mr.id;
