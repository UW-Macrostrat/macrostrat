-- Extraction feedback routes; before 02-api-views.sql, which reads kg_macrostrat_terms

CREATE VIEW macrostrat_api.extraction_feedback AS
 SELECT extraction_feedback.note_id,
    extraction_feedback.feedback_id,
    extraction_feedback.date,
    extraction_feedback.custom_note
   FROM macrostrat_kg.extraction_feedback;

CREATE VIEW macrostrat_api.extraction_feedback_combined AS
 SELECT f.feedback_id,
    f.date,
    f.custom_note AS note,
    COALESCE(json_agg(json_build_object('type_id', t.type_id, 'type', t.type)) FILTER (WHERE (t.type_id IS NOT NULL)), '[]'::json) AS types
   FROM ((macrostrat_kg.extraction_feedback f
     LEFT JOIN macrostrat_kg.lookup_extraction_type l ON ((l.note_id = f.note_id)))
     LEFT JOIN macrostrat_kg.extraction_feedback_type t ON ((t.type_id = l.type_id)))
  GROUP BY f.feedback_id, f.date, f.custom_note
  ORDER BY f.date DESC;

CREATE VIEW macrostrat_api.extraction_feedback_type AS
 SELECT extraction_feedback_type.type_id,
    extraction_feedback_type.type
   FROM macrostrat_kg.extraction_feedback_type;

CREATE VIEW macrostrat_api.lookup_extraction_type AS
 SELECT lookup_extraction_type.note_id,
    lookup_extraction_type.type_id
   FROM macrostrat_kg.lookup_extraction_type;

CREATE OR REPLACE VIEW macrostrat_api.feedback AS
WITH selected_runs AS (
    SELECT *
    FROM macrostrat_kg.all_runs
    WHERE user_id IS NOT NULL
),

entities AS (
    SELECT
        e.run_id,
        jsonb_agg(
            jsonb_build_object(
                'id', e.id,
                'text', e.name,
                'type', et.name,
                'start', e.start_index,
                'end', e.end_index
            )
        ) AS entities
    FROM macrostrat_kg.entity e
    JOIN selected_runs sr
        ON sr.id = e.run_id
    LEFT JOIN macrostrat_kg.entity_type et
        ON et.id = e.entity_type_id
    GROUP BY e.run_id
),

relations AS (
    SELECT
        parent.run_id,
        jsonb_agg(
            jsonb_build_object(
                'head', r.src_entity_id,
                'tail', r.dst_entity_id
            )
        ) AS relations
    FROM macrostrat_kg.relationship r
    JOIN macrostrat_kg.entity parent
        ON parent.id = r.src_entity_id
    JOIN selected_runs sr
        ON sr.id = parent.run_id
    GROUP BY parent.run_id
),

feedback_meta AS (
    SELECT
        ef.feedback_id AS run_id,
        ef.custom_note AS extraction_note,
        eft.type AS extraction_feedback_type
    FROM macrostrat_kg.extraction_feedback ef
    LEFT JOIN macrostrat_kg.lookup_extraction_type let
        ON let.note_id = ef.note_id
    LEFT JOIN macrostrat_kg.extraction_feedback_type eft
        ON eft.type_id = let.type_id
)

SELECT
    sr.*,
    mt.name AS root_entity_name,
    mt.entity_type AS root_entity_type,
    fm.extraction_note,
    fm.extraction_feedback_type,
    COALESCE(ent.entities, '[]'::jsonb) AS entities,
    COALESCE(rel.relations, '[]'::jsonb) AS relations

FROM selected_runs sr
LEFT JOIN entities ent
    ON ent.run_id = sr.id
LEFT JOIN relations rel
    ON rel.run_id = sr.id
LEFT JOIN feedback_meta fm
    ON fm.run_id = sr.id
LEFT JOIN macrostrat_kg.macrostrat_terms mt
    ON mt.id = sr.root_id;

CREATE VIEW macrostrat_api.kg_macrostrat_terms AS
    select
    id AS macrostrat_terms_id,
    entity_type,
    entity_id,
    name
FROM macrostrat_kg.macrostrat_terms;

GRANT SELECT ON TABLE macrostrat_api.extraction_feedback TO web_anon;
GRANT INSERT,DELETE,UPDATE ON TABLE macrostrat_api.extraction_feedback TO web_admin;

GRANT SELECT ON TABLE macrostrat_api.extraction_feedback_combined TO web_anon;

GRANT SELECT ON TABLE macrostrat_api.extraction_feedback_type TO web_anon;
GRANT INSERT,DELETE,UPDATE ON TABLE macrostrat_api.extraction_feedback_type TO web_admin;

GRANT SELECT ON TABLE macrostrat_api.lookup_extraction_type TO web_anon;
GRANT INSERT,DELETE,UPDATE ON TABLE macrostrat_api.lookup_extraction_type TO web_admin;
