/*
Macrostrat's postgrest api is expressed through the macrostrat_api schema.
Any functions, views or tables in the macrostrat_api schema can be accessed
through the postgrest api.

Below are a multitude of views that are made from the  macrostrat data schema.
Many are direct copies, however some are more customized data views for the frontend.
*/

CREATE SCHEMA IF NOT EXISTS macrostrat_api;

CREATE OR REPLACE VIEW macrostrat_api.projects AS
SELECT * FROM macrostrat.projects;

CREATE OR REPLACE VIEW macrostrat_api.cols AS
SELECT * FROM macrostrat.cols;

CREATE OR REPLACE VIEW macrostrat_api.col_groups AS
SELECT * FROM macrostrat.col_groups;

CREATE OR REPLACE VIEW macrostrat_api.environs AS
SELECT * FROM macrostrat.environs;

CREATE OR REPLACE VIEW macrostrat_api.liths AS
SELECT * FROM macrostrat.liths;

CREATE OR REPLACE VIEW macrostrat_api.intervals AS
SELECT * FROM macrostrat.intervals;

CREATE OR REPLACE VIEW macrostrat_api.timescales AS
SELECT * FROM macrostrat.timescales;

CREATE OR REPLACE VIEW macrostrat_api.strat_tree AS
SELECT * FROM macrostrat.strat_tree;

CREATE OR REPLACE VIEW macrostrat_api.refs AS
SELECT * FROM macrostrat.refs;

CREATE OR REPLACE VIEW macrostrat_api.units AS
SELECT * FROM macrostrat.units;

CREATE OR REPLACE VIEW macrostrat_api.col_refs AS
SELECT * FROM macrostrat.col_refs;

CREATE OR REPLACE VIEW macrostrat_api.unit_environs AS
SELECT * FROM macrostrat.unit_environs;

CREATE OR REPLACE VIEW macrostrat_api.unit_liths AS
SELECT * FROM macrostrat.unit_liths;

CREATE OR REPLACE VIEW macrostrat_api.sections AS
SELECT * FROM macrostrat.sections;

CREATE OR REPLACE VIEW macrostrat_api.strat_names AS
SELECT * FROM macrostrat.strat_names;

CREATE OR REPLACE VIEW macrostrat_api.unit_strat_names AS
SELECT * FROM macrostrat.unit_strat_names;

CREATE OR REPLACE VIEW macrostrat_api.strat_names_ref AS
SELECT
s.id,
s.strat_name,
s.rank,
row_to_json(r.*) ref,
row_to_json(sm.*) concept
FROM macrostrat.strat_names s
LEFT JOIN macrostrat.refs r
ON r.id = s.ref_id
LEFT JOIN macrostrat.strat_names_meta sm
ON sm.concept_id = s.concept_id;

CREATE OR REPLACE VIEW macrostrat_api.col_group_with_cols AS
SELECT
    cg.id,
    cg.col_group,
    cg.col_group_long,
    cg.project_id,
    p.project,
    COALESCE(jsonb_agg(
        jsonb_build_object(
        'col_id', c.id,
        'status_code', c.status_code,
        'col_number', c.col,
        'col_name', c.col_name))
            FILTER (WHERE c.id IS NOT NULL), '[]')
            AS cols
FROM macrostrat.col_groups cg
    LEFT JOIN macrostrat.cols c ON c.col_group_id = cg.id
    LEFT JOIN macrostrat.projects p ON p.id = cg.project_id
GROUP BY cg.id, c.project_id, p.project;


CREATE OR REPLACE VIEW macrostrat_api.environ_unit AS
SELECT e.*, ue.unit_id, ue.ref_id from macrostrat.environs e
JOIN macrostrat.unit_environs ue
ON e.id = ue.environ_id;

CREATE OR REPLACE VIEW macrostrat_api.econ_unit AS
SELECT e.*, ue.unit_id, ue.ref_id from macrostrat.econs e
JOIN macrostrat.unit_econs ue
ON e.id = ue.econ_id;

CREATE OR REPLACE VIEW macrostrat_api.lith_attr_unit AS
SELECT
la.id as lith_attr_id,
la.lith_att,
la.att_type,
la.lith_att_fill,
l.*,
ul.unit_id
from macrostrat.lith_atts la
JOIN macrostrat.unit_liths_atts ula
ON ula.lith_att_id = la.id
JOIN macrostrat.unit_liths ul
ON ul.id = ula.unit_lith_id
JOIN macrostrat.liths l
ON ul.lith_id = l.id;

CREATE OR REPLACE VIEW macrostrat_api.lith_unit AS
SELECT
l.id,
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
from macrostrat.liths l
JOIN macrostrat.unit_liths ul
ON ul.lith_id = l.id;

/*LO is top and FO is bottom*/
CREATE OR REPLACE VIEW macrostrat_api.unit_strat_name_expanded AS
SELECT
usn.id,
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
'' AS notes, -- TODO: notes are no longer part of the units table, need to remove this
fo.interval_name AS name_fo,
fo.age_bottom,
lo.interval_name AS name_lo,
lo.age_top
FROM macrostrat.unit_strat_names usn
JOIN macrostrat.units u
  ON u.id = usn.unit_id
LEFT JOIN macrostrat.strat_names sn
  ON usn.strat_name_id = sn.id
LEFT JOIN macrostrat.intervals fo ON u.fo = fo.id
LEFT JOIN macrostrat.intervals lo ON u.lo = lo.id;

CREATE OR REPLACE VIEW macrostrat_api.col_sections AS
SELECT c.id col_id, c.col_name, u.section_id, u.position_top, u.position_bottom, fo.interval_name bottom,
lo.interval_name top FROM macrostrat.cols c
LEFT JOIN macrostrat.units u
ON u.col_id = c.id
LEFT JOIN macrostrat.intervals fo
ON u.fo = fo.id
LEFT JOIN macrostrat.intervals lo
ON u.lo = lo.id;

CREATE OR REPLACE VIEW macrostrat_api.col_ref_expanded AS
SELECT
c.id col_id,
c.col_name,
c.col col_number,
'' AS notes, -- TODO: notes are no longer part of the cols table, need to remove this
c.lat,
c.lng,
json_build_object(
'id', r.id,
'pub_year', r.pub_year,
'author', r.author,
'ref', r.ref,
'doi',r.doi,
'url', r.url) ref
FROM macrostrat.cols c
LEFT JOIN macrostrat.col_refs cr
ON c.id = cr.col_id
LEFT JOIN macrostrat.refs r
ON cr.ref_id = r.id;




CREATE OR REPLACE VIEW macrostrat_api.strat_names_meta AS
SELECT * FROM macrostrat.strat_names_meta;

CREATE OR REPLACE VIEW macrostrat_api.unit_boundaries AS
SELECT * FROM macrostrat.unit_boundaries;
