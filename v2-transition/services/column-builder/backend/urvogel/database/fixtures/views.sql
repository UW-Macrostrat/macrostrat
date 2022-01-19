/* Some views that may be helpful with postgrest */

CREATE OR REPLACE VIEW macrostrat.environ_unit AS
SELECT e.*, ue.unit_id, ue.ref_id from macrostrat.environs e
JOIN macrostrat.unit_environs ue
ON e.id = ue.environ_id;


CREATE OR REPLACE VIEW macrostrat.econ_unit AS
SELECT e.*, ue.unit_id, ue.ref_id from macrostrat.econs e
JOIN macrostrat.unit_econs ue
ON e.id = ue.econ_id;

CREATE OR REPLACE VIEW macrostrat.lith_attr_unit AS
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

CREATE OR REPLACE VIEW macrostrat.lith_unit AS
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
CREATE OR REPLACE VIEW macrostrat.units_view AS
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
