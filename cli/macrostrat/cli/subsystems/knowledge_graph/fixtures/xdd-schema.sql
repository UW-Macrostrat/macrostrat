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
    e.type,
    e.name,
    ARRAY[start_index, end_index] AS indices,
    model_run_id model_run,
    source_id source,
    coalesce(to_json(sn), to_json(l), to_json(la)) AS match
    -- JSON for the strat_name
FROM macrostrat_xdd.entity e
LEFT JOIN strat_names sn
    ON sn.strat_name_id = e.strat_name_id
LEFT JOIN liths l
    ON l.lith_id = e.lith_id
LEFT JOIN lith_atts la
    ON la.lith_att_id = e.lith_att_id;

CREATE OR REPLACE VIEW macrostrat_api.kg_relationships AS
SELECT
    id,
    type,
    model_run_id model_run,
    source_id source,
    src_entity_id src,
    dst_entity_id dst
FROM macrostrat_xdd.relationship;

CREATE OR REPLACE VIEW macrostrat_api.kg_entity_tree AS
WITH RECURSIVE start_entities AS (
    -- Entities that are not parents of any relationship
    SELECT id
    FROM macrostrat_xdd.entity
    EXCEPT
    SELECT src_entity_id
    FROM macrostrat_xdd.relationship
), e0 AS (SELECT e.source,
                 e.id,
                 jsonb_strip_nulls(to_jsonb(e) - 'model_run' - 'source') tree,
                 (e.match IS NOT null)::integer AS n_matches
          FROM macrostrat_api.kg_entities e),
    tree AS (
    -- Walk the tree of entity relationships
    SELECT e0.source,
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
    SELECT a.source,
            a.src_entity_id,
            a.parent_id,
            e0.tree || jsonb_build_object('children', json_agg(a.tree)),
            a.depth + 1,
            sum(a.n_entities)::integer + 1,
            sum(a.n_matches)::integer + e0.n_matches
     FROM (
         SELECT * FROM tree
                           LEFT JOIN macrostrat_xdd.relationship r1
                                     ON r1.dst_entity_id = tree.parent_id
          ) a
              JOIN e0
                   ON e0.id = a.parent_id
     GROUP BY a.source, a.depth, e0.tree, e0.n_matches, a.src_entity_id, a.parent_id
)
SELECT
    st.paper_id,
    source source_id,
    entity_id entity,
    tree ->> 'type' AS type,
    st.model_run_id model_run,
    n_entities,
    n_matches,
    tree,
    depth
FROM tree
JOIN macrostrat_xdd.source_text st
    ON st.id = source
WHERE parent_id IS NULL
ORDER BY n_matches DESC;

CREATE OR REPLACE VIEW macrostrat_api.kg_publication_entities AS
WITH paper_strat_names AS (SELECT p.paper_id,
                                  array_agg(DISTINCT strat_name_id) strat_name_matches,
                                  count(DISTINCT strat_name_id)                 n_matches
                           FROM macrostrat_xdd.publication p
                                    JOIN macrostrat_xdd.source_text st ON st.paper_id = p.paper_id
                                    JOIN macrostrat_xdd.entity e ON e.source_id = st.id
                           WHERE e.strat_name_id IS NOT NULL
                           GROUP BY p.paper_id),
entities AS (SELECT paper_id,
                    jsonb_agg(tree || jsonb_build_object('model_run', model_run, 'depth', depth, 'source',
                                                         source_id)) AS entities
             FROM macrostrat_api.kg_entity_tree
             GROUP BY paper_id)
SELECT e.paper_id,
         e.entities,
         p.strat_name_matches,
         p.n_matches,
        pub.citation
FROM entities e
            JOIN paper_strat_names p ON p.paper_id = e.paper_id
            JOIN macrostrat_xdd.publication pub ON pub.paper_id = e.paper_id
ORDER BY p.n_matches DESC;

CREATE VIEW macrostrat_api.kg_context_entities AS
WITH entities AS (SELECT source_id, paper_id, model_run, jsonb_agg(tree) entities
                  FROM macrostrat_api.kg_entity_tree
                  GROUP BY source_id, paper_id, model_run)
SELECT e.source_id,
         e.paper_id,
         e.model_run,
         e.entities,
         st.weaviate_id,
         st.paragraph_text,
            st.hashed_text,
            st.preprocessor_id,
            mr.model_id,
            mr.version_id
FROM entities e
JOIN macrostrat_xdd.source_text st
    ON st.id = e.source_id
JOIN macrostrat_xdd.model_run mr
  ON st.model_run_id = mr.id;

