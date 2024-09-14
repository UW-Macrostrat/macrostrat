DROP VIEW IF EXISTS macrostrat_api.strat_names_units_kg;
DROP VIEW IF EXISTS macrostrat_api.strat_names_ext;
DROP VIEW IF EXISTS macrostrat_api.unit_liths_agg;
DROP VIEW IF EXISTS macrostrat_api.strat_name_kg_relationships;

DROP VIEW IF EXISTS macrostrat_kg.strat_name_kg_liths;
DROP VIEW IF EXISTS macrostrat_kg.relationships_meta;

DROP VIEW IF EXISTS macrostrat_api.kg_entities;
CREATE OR REPLACE VIEW macrostrat_api.kg_entities AS
WITH strat_names AS (
    SELECT
        id,
        concept_id,
        strat_name AS name,
        rank
    FROM macrostrat.strat_names
),
liths AS (
    SELECT id,
           lith name,
           lith_color color
    FROM macrostrat.liths
),
lith_atts AS (
    SELECT *
    FROM macrostrat.lith_atts
)
SELECT
    e.id,
    e.type,
    e.name,
    ARRAY[start_index, end_index] AS indices,
    model_run_id model_run,
    source_id source,
    to_json(sn) AS strat_name,
    to_json(l) AS lith,
    to_json(la) AS lith_att
    -- JSON for the strat_name
FROM macrostrat_xdd.entity e
LEFT JOIN strat_names sn
    ON sn.id = e.strat_name_id
LEFT JOIN liths l
    ON l.id = e.lith_id
LEFT JOIN lith_atts la
    ON la.id = e.lith_att_id;

CREATE OR REPLACE VIEW macrostrat_api.kg_relationships AS
SELECT
    id,
    type,
    model_run_id model_run,
    source_id source,
    src_entity_id src,
    dst_entity_id dst
FROM relationship;

-- Walk the tree of entity relationships
SELECT source,
       r.dst_entity_id,
       to_json(e) entity
FROM macrostrat_api.kg_entities e
LEFT JOIN macrostrat_xdd.relationship r
    ON r.src_entity_id = e.id
EXCEPT SELECT source,
             r.dst_entity_id,
             to_json(e) entity
FROM macrostrat_api.kg_entities e
LEFT JOIN macrostrat_xdd.relationship r
    ON r.src_entity_id = e.id
WHERE r.dst_entity_id IS NULL;


--CREATE OR REPLACE VIEW macrostrat_api.kg_entity_tree AS

WITH RECURSIVE start_entities AS (
    -- Entities not parents of relationship
    SELECT id
    FROM entity
    EXCEPT
    SELECT src_entity_id
    FROM relationship
), e0 AS (SELECT e.source,
                 e.id,
                 jsonb_strip_nulls(to_jsonb(e) - 'model_run') tree
          FROM macrostrat_api.kg_entities e),
    tree AS (
    -- Walk the tree of entity relationships
    SELECT se.source_id source,
           r.src_entity_id parent_id,
           se.id         entity_id,
           e0.tree,
           0 depth
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
            a.depth + 1
     FROM (
         SELECT * FROM tree
                           LEFT JOIN macrostrat_xdd.relationship r1
                                     ON r1.dst_entity_id = tree.parent_id
          ) a
              JOIN e0
                   ON e0.id = a.parent_id
     GROUP BY a.source, a.depth, e0.tree, a.src_entity_id, a.parent_id
)
SELECT source, entity_id root_entity, tree entity_tree, depth
FROM tree
WHERE parent_id IS NULL
ORDER BY depth DESC;



WITH strat_names AS (
SELECT p.paper_id,

    e.name,
    e.type,
    strat_name_id,
    strat_name_id IS NOT null AS strat_name_present
FROM publication p
  JOIN source_text st ON st.paper_id = p.paper_id
LEFT JOIN entity e ON e.source_id = st.id
)
SELECT s.*, sn.*
FROM strat_names s
JOIN macrostrat.strat_names sn
 ON sn.id = s.strat_name_id;




SELECT count(*) FROM entity WHERE strat_name_id IS NOT null;
