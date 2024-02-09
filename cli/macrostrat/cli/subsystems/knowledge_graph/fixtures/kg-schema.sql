CREATE SCHEMA IF NOT EXISTS macrostrat_kg;

CREATE OR REPLACE VIEW macrostrat_kg.relationships_meta AS
SELECT
	r.relationship_id id,
	r.head,
	r.tail,
	r.type,
	r.model_used model,
	r.run_id model_run,
	r.src_type head_type,
	r.dst_type tail_type,
	r.strat_name_id,
	r.lith_id,
	r.lith_att_id,
	s.src_id source_id,
	s.article_id,
	s.paragraph_txt,
	nullif(
    position(head IN lower(paragraph_txt)),
    0
  )-1 head_pos,
	nullif(
    position(tail IN lower(paragraph_txt)
  ), 0)-1 tail_pos                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       
FROM macrostrat_kg.relationships r
JOIN macrostrat_kg.relationships_extracted re
  ON r.run_id = re.run_id
 AND r.relationship_id = re.relationship_id
JOIN macrostrat_kg.sources s
  ON re.source_id = s.src_id
 AND r.run_id = s.run_id;



CREATE OR REPLACE VIEW macrostrat_api.strat_name_kg_relationships AS
SELECT DISTINCT ON (strat_name_id, lith_id, source_id)
 	r.id,
	strat_name_id,
	lith_id,
	l.lith,
	l.lith_color,
	source_id,
	article_id,
	paragraph_txt
FROM macrostrat_kg.relationships_meta r
JOIN macrostrat.liths l
  ON l.id = r.lith_id
WHERE strat_name_id IS NOT null
  AND lith_id IS NOT null;

CREATE OR REPLACE VIEW macrostrat_api.unit_liths_agg AS
WITH unit_liths AS (
  SELECT
    ul.unit_id,
    json_agg(json_build_object(
      'id', l.id,
      'name', l.lith,
      'color', l.lith_color,
      'prop', ul.comp_prop
    )) liths
  FROM macrostrat.unit_liths ul
  JOIN macrostrat.liths l
    ON l.id = ul.lith_id
  GROUP BY ul.unit_id
)
SELECT id, strat_name, section_id, col_id, liths
FROM macrostrat.units
JOIN unit_liths ul ON units.id = ul.unit_id; 