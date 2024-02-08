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
 AND r.run_id = s.run_id