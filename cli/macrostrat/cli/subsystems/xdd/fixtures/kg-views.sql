DROP VIEW IF EXISTS macrostrat_api.strat_names_units_kg;
DROP VIEW IF EXISTS macrostrat_api.strat_names_ext;
DROP VIEW IF EXISTS macrostrat_api.unit_liths_agg;
DROP VIEW IF EXISTS macrostrat_api.strat_name_kg_relationships;

DROP VIEW IF EXISTS macrostrat_kg.strat_name_kg_liths;
DROP VIEW IF EXISTS macrostrat_kg.relationships_meta;

DROP VIEW IF EXISTS macrostrat_api.kg_publication_entities;
DROP VIEW IF EXISTS macrostrat_api.kg_context_entities;
DROP VIEW IF EXISTS macrostrat_api.kg_entity_tree;
DROP VIEW IF EXISTS macrostrat_api.kg_relationships;
DROP VIEW IF EXISTS macrostrat_api.kg_entity_tree;
DROP VIEW IF EXISTS macrostrat_api.kg_entities;


CREATE ROLE "xdd-writer";

CREATE OR REPLACE VIEW macrostrat_api.kg_entity_type AS
SELECT id, name, description, color
FROM macrostrat_xdd.entity_type;

/** Allow entity types to be modified by administrators */
GRANT SELECT, INSERT, UPDATE, DELETE
  ON macrostrat_api.kg_entity_type TO web_admin;


CREATE OR REPLACE VIEW macrostrat_api.kg_entities AS
WITH strat_names AS (
    SELECT
        id strat_name_id,
        concept_id,
        strat_name AS name,
        rank
    FROM macrostrat.strat_names
),
liths AS (
    SELECT id lith_id,
           lith name,
           lith_color color
    FROM macrostrat.liths
),
lith_atts AS (
    SELECT id lith_att_id,
           lith_att name
    FROM macrostrat.lith_atts
)
SELECT
    e.id,
    et.id type,
    e.name,
    ARRAY[start_index, end_index] AS indices,
    mr.id model_run,
    mr.source_text_id source,
    coalesce(to_json(sn), to_json(l), to_json(la)) AS match
    -- JSON for the strat_name
FROM macrostrat_xdd.entity e
JOIN macrostrat_xdd.entity_type et
  ON et.id = e.entity_type_id
JOIN macrostrat_xdd.model_run mr
    ON mr.id = e.model_run_id
LEFT JOIN strat_names sn
    ON sn.strat_name_id = e.strat_name_id
LEFT JOIN liths l
    ON l.lith_id = e.lith_id
LEFT JOIN lith_atts la
    ON la.lith_att_id = e.lith_att_id;

CREATE OR REPLACE VIEW macrostrat_api.kg_entity_tree AS
WITH RECURSIVE start_entities AS (
    -- Entities that are not parents of any relationship
    SELECT id
    FROM macrostrat_xdd.entity
    EXCEPT
    SELECT src_entity_id
    FROM macrostrat_xdd.relationship
),
e0 AS (
    SELECT
        e.model_run,
        e.id,
        jsonb_strip_nulls(to_jsonb(e) - 'model_run' - 'source') tree,
        (e.match IS NOT null)::integer AS n_matches
    FROM macrostrat_api.kg_entities e
),
tree AS (
    /** Walk the tree of entity relationships, grouping by parent and
    aggregating as we go */
    SELECT e0.model_run,
           r.src_entity_id parent_id,
           se.id         entity_id,
           e0.tree,
           0 depth,
           1 n_entities,
           e0.n_matches
    FROM e0
    JOIN start_entities se
      ON se.id = e0.id
    LEFT JOIN macrostrat_xdd.relationship r
      ON r.dst_entity_id = se.id
    UNION
    SELECT a.model_run,
            a.src_entity_id,
            a.parent_id,
            e0.tree || jsonb_build_object('children', json_agg(a.tree)),
            a.depth + 1,
            sum(a.n_entities)::integer + 1,
            sum(a.n_matches)::integer + e0.n_matches
    FROM (
        SELECT
            tree.model_run,
            r1.src_entity_id,
            tree.parent_id,
            tree.tree,
            tree.depth,
            tree.n_entities,
            tree.n_matches
        FROM tree
        LEFT JOIN macrostrat_xdd.relationship r1
            ON r1.dst_entity_id = tree.parent_id
    ) a
    JOIN e0 ON e0.id = a.parent_id
    GROUP BY
        a.model_run,
        a.depth,
        e0.tree,
        e0.n_matches,
        a.src_entity_id,
        a.parent_id
)
SELECT
    st.paper_id,
    model_run,
    entity_id entity,
    tree ->> 'type' AS type,
    mr.source_text_id source_text,
    n_entities,
    n_matches,
    tree,
    depth
FROM tree
JOIN macrostrat_xdd.model_run mr
    ON mr.id = tree.model_run
JOIN macrostrat_xdd.source_text st
    ON st.id = mr.source_text_id
WHERE parent_id IS NULL;

CREATE OR REPLACE VIEW macrostrat_api.kg_publication_entities AS
WITH paper_strat_names AS (
    SELECT
        p.paper_id,
        array_agg(DISTINCT mr.model_id) models,
        array_agg(DISTINCT strat_name_id) strat_name_matches,
        count(DISTINCT strat_name_id) n_matches
    FROM macrostrat_xdd.publication p
    JOIN macrostrat_xdd.source_text st ON st.paper_id = p.paper_id
    JOIN macrostrat_xdd.model_run mr ON mr.source_text_id = st.id
    JOIN macrostrat_xdd.entity e ON mr.id = e.model_run_id
    WHERE e.strat_name_id IS NOT NULL
    GROUP BY p.paper_id
),
entities AS (
    SELECT
        paper_id,
        jsonb_agg(
            tree ||
            jsonb_build_object(
                'model_run', model_run,
                'depth', depth,
                'source', source_text
            )
        ) AS entities
    FROM macrostrat_api.kg_entity_tree
    GROUP BY paper_id
)
SELECT
    pub.paper_id,
    pub.citation,
    p.strat_name_matches,
    p.n_matches,
    p.models,
    e.entities
FROM macrostrat_xdd.publication pub
LEFT JOIN paper_strat_names p
  ON pub.paper_id = p.paper_id
LEFT JOIN entities e
  ON p.paper_id = e.paper_id
ORDER BY p.n_matches DESC;

CREATE OR REPLACE VIEW macrostrat_api.kg_context_entities AS
WITH entities AS (
    SELECT
        source_text,
        paper_id,
        model_run,
        jsonb_agg(tree) entities
    FROM macrostrat_api.kg_entity_tree
    GROUP BY source_text, paper_id, model_run
)
SELECT
    st.id source_text,
    st.paper_id,
    mr.id model_run,
    coalesce(e.entities, '[]'::jsonb) entities,
    st.weaviate_id,
    st.paragraph_text,
    st.hashed_text,
    st.preprocessor_id,
    mr.model_id,
    mr.version_id
FROM  macrostrat_xdd.source_text st
LEFT JOIN macrostrat_xdd.model_run mr
  ON mr.source_text_id = st.id
LEFT JOIN entities e
  ON e.model_run = mr.id;

CREATE OR REPLACE VIEW macrostrat_api.kg_model AS
SELECT
  m.id,
  m.name,
  m.description,
  m.url,
  min(mr.timestamp) first_run,
  max(mr.timestamp) last_run,
  count(distinct mr.id) n_runs,
  count(distinct e.id) n_entities,
  count((coalesce(e.strat_name_id, e.lith_id, e.lith_att_id)::boolean)) n_matches,
  count(e.strat_name_id::boolean) n_strat_names
FROM macrostrat_xdd.model m
LEFT JOIN macrostrat_xdd.model_run mr
  ON mr.model_id = m.id
LEFT JOIN macrostrat_xdd.entity e
  ON e.model_run_id = mr.id
GROUP BY m.id;

CREATE OR REPLACE VIEW macrostrat_api.kg_model_run AS
SELECT
  mr.id,
  mr.user_id,
  mr.timestamp,
  mr.model_id,
  m.name model_name,
  mr.version_id,
  mr.source_text_id,
  st.source_text_type,
  st.map_legend_id,
  st.weaviate_id,
  mr.supersedes,
  mr1.id superseded_by
FROM macrostrat_xdd.model_run mr
LEFT JOIN macrostrat_xdd.model_run mr1
  ON mr1.supersedes = mr.id
JOIN macrostrat_xdd.model m
  ON m.id = mr.model_id
JOIN macrostrat_xdd.source_text st
  ON st.id = mr.source_text_id
ORDER BY mr.id;

CREATE OR REPLACE VIEW macrostrat_api.kg_source_text AS
WITH stats AS (
  SELECT
    mr.source_text_id,
    count(distinct mr.id) n_runs,
    count(distinct e.id) n_entities,
    count((coalesce(e.strat_name_id, e.lith_id, e.lith_att_id)::boolean)) n_matches,
    count(e.strat_name_id::boolean) n_strat_names,
    min(mr.timestamp) created,
    max(mr.timestamp) last_update
  FROM macrostrat_xdd.model_run mr
         LEFT JOIN macrostrat_xdd.entity e
                   ON e.model_run_id = mr.id
  GROUP BY mr.source_text_id
)
SELECT st.*, n_runs, n_entities, n_matches, n_strat_names, created, last_update
FROM macrostrat_xdd.source_text st
JOIN stats s ON s.source_text_id = st.id;
