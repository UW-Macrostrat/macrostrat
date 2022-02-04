/* Some views that may be helpful with postgrest */

CREATE SCHEMA macrostrat_api

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

CREATE OR REPLACE VIEW macrostrat_api.strat_names AS
SELECT * FROM macrostrat.strat_names;

CREATE OR REPLACE VIEW macrostrat_api.refs AS
SELECT * FROM macrostrat.refs;

CREATE OR REPLACE VIEW macrostrat_api.units AS
SELECT * FROM macrostrat.units;

CREATE OR REPLACE VIEW macrostrat_api.col_group_view AS
SELECT cg.id,
cg.col_group,
cg.col_group_long,
c.project_id,
json_agg(json_build_object('col_id', c.id, 'status_code', c.status_code, 'col_number',c.col, 'col_name', c.col_name)) AS cols
FROM macrostrat.col_groups cg
    LEFT JOIN macrostrat.cols c ON c.col_group_id = cg.id
GROUP BY cg.id, c.project_id;


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
JOIN macrostrat.unit_lith_atts ula
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
ul.prop,
ul.mod_prop,
ul.comp_prop, 
ul.ref_id,
ul.unit_id 
from macrostrat.unit_liths ul
JOIN macrostrat.liths l
ON ul.lith_id = l.id;

/*LO is top and FO is bottom*/
CREATE OR REPLACE VIEW macrostrat_api.units_view AS
SELECT 
u.*, 
fo.interval_name name_fo, 
fo.age_bottom, 
lo.interval_name name_lo, 
lo.age_top  
FROM macrostrat.units u
LEFT JOIN macrostrat.intervals fo
ON u.fo = fo.id
LEFT JOIN macrostrat.intervals lo
ON u.lo = lo.id;


CREATE OR REPLACE VIEW macrostrat_api.col_sections AS
SELECT c.id col_id, c.col_name, u.section_id, u.position_top, u.position_bottom, fo.interval_name bottom, 
lo.interval_name top FROM macrostrat.cols c
LEFT JOIN macrostrat.units u
ON u.col_id = c.id
LEFT JOIN macrostrat.intervals fo
ON u.fo = fo.id
LEFT JOIN macrostrat.intervals lo
ON u.lo = lo.id;

CREATE OR REPLACE VIEW macrostrat_api.col_form AS
SELECT 
c.id col_id, 
c.col_name, 
c.col col_number,
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