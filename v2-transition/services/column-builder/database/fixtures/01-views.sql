/* Some views that may be helpful with postgrest */

CREATE SCHEMA IF NOT EXISTS macrostrat_api;

CREATE OR REPLACE FUNCTION
macrostrat_api.get_projects() RETURNS SETOF macrostrat.projects AS $$
BEGIN
  RETURN QUERY SELECT * FROM macrostrat.projects;
END
$$ language plpgsql SECURITY INVOKER;

CREATE OR REPLACE VIEW macrostrat_api.projects AS
SELECT * FROM macrostrat_api.get_projects();

CREATE OR REPLACE FUNCTION
macrostrat_api.get_cols() RETURNS SETOF macrostrat.cols AS $$
BEGIN
  RETURN QUERY SELECT * FROM macrostrat.cols;
END
$$ language plpgsql SECURITY INVOKER;

CREATE OR REPLACE VIEW macrostrat_api.cols AS
SELECT * FROM macrostrat_api.get_cols();

CREATE OR REPLACE FUNCTION
macrostrat_api.get_col_groups() RETURNS SETOF macrostrat.col_groups AS $$
BEGIN
  RETURN QUERY SELECT * FROM macrostrat.col_groups;
END
$$ language plpgsql SECURITY INVOKER;

CREATE OR REPLACE VIEW macrostrat_api.col_groups AS
SELECT * FROM macrostrat_api.get_col_groups();

CREATE OR REPLACE FUNCTION
macrostrat_api.get_envs() RETURNS SETOF macrostrat.environs AS $$
BEGIN
  RETURN QUERY SELECT * FROM macrostrat.environs;
END
$$ language plpgsql SECURITY INVOKER;

CREATE OR REPLACE VIEW macrostrat_api.environs AS
SELECT * FROM macrostrat_api.get_envs();

CREATE OR REPLACE FUNCTION
macrostrat_api.get_liths() RETURNS SETOF macrostrat.liths AS $$
BEGIN
  RETURN QUERY SELECT * FROM macrostrat.liths;
END
$$ language plpgsql SECURITY INVOKER;

CREATE OR REPLACE VIEW macrostrat_api.liths AS
SELECT * FROM macrostrat_api.get_liths();

CREATE OR REPLACE FUNCTION
macrostrat_api.get_intervals() RETURNS SETOF macrostrat.intervals AS $$
BEGIN
  RETURN QUERY SELECT * FROM macrostrat.intervals;
END
$$ language plpgsql SECURITY INVOKER;

CREATE OR REPLACE VIEW macrostrat_api.intervals AS
SELECT * FROM macrostrat_api.get_intervals();

CREATE OR REPLACE FUNCTION
macrostrat_api.get_timescales() RETURNS SETOF macrostrat.timescales AS $$
BEGIN
  RETURN QUERY SELECT * FROM macrostrat.timescales;
END
$$ language plpgsql SECURITY INVOKER;

CREATE OR REPLACE VIEW macrostrat_api.timescales AS
SELECT * FROM macrostrat_api.get_timescales();

CREATE OR REPLACE FUNCTION
macrostrat_api.get_strat_tree() RETURNS SETOF macrostrat.strat_tree AS $$
BEGIN
  RETURN QUERY SELECT * FROM macrostrat.strat_tree;
END
$$ language plpgsql SECURITY INVOKER;

CREATE OR REPLACE VIEW macrostrat_api.strat_tree AS
SELECT * FROM macrostrat_api.get_strat_tree();

CREATE OR REPLACE FUNCTION
macrostrat_api.get_refs() RETURNS SETOF macrostrat.refs AS $$
BEGIN
  RETURN QUERY SELECT * FROM macrostrat.refs;
END
$$ language plpgsql SECURITY INVOKER;

CREATE OR REPLACE VIEW macrostrat_api.refs AS
SELECT * FROM macrostrat_api.get_refs();

CREATE OR REPLACE FUNCTION
macrostrat_api.get_units() RETURNS SETOF macrostrat.units AS $$
BEGIN
  RETURN QUERY SELECT * FROM macrostrat.units;
END
$$ language plpgsql SECURITY INVOKER;

CREATE OR REPLACE VIEW macrostrat_api.units AS
SELECT * FROM macrostrat_api.get_units();

CREATE OR REPLACE FUNCTION
macrostrat_api.get_col_refs() RETURNS SETOF macrostrat.col_refs AS $$
BEGIN
  RETURN QUERY SELECT * FROM macrostrat.col_refs;
END
$$ language plpgsql SECURITY INVOKER;

CREATE OR REPLACE VIEW macrostrat_api.col_refs AS
SELECT * FROM macrostrat_api.get_col_refs();

CREATE OR REPLACE FUNCTION
macrostrat_api.get_unit_environs() RETURNS SETOF macrostrat.unit_environs AS $$
BEGIN
  RETURN QUERY SELECT * FROM macrostrat.unit_environs;
END
$$ language plpgsql SECURITY INVOKER;

CREATE OR REPLACE VIEW macrostrat_api.unit_environs AS
SELECT * FROM macrostrat_api.get_unit_environs();

CREATE OR REPLACE FUNCTION
macrostrat_api.get_unit_liths() RETURNS SETOF macrostrat.unit_liths AS $$
BEGIN
  RETURN QUERY SELECT * FROM macrostrat.unit_liths;
END
$$ language plpgsql SECURITY INVOKER;

CREATE OR REPLACE VIEW macrostrat_api.unit_liths AS
SELECT * FROM macrostrat_api.get_unit_liths();

CREATE OR REPLACE FUNCTION
macrostrat_api.get_sections() RETURNS SETOF macrostrat.sections AS $$
BEGIN
  RETURN QUERY SELECT * FROM macrostrat.sections;
END
$$ language plpgsql SECURITY INVOKER;

CREATE OR REPLACE VIEW macrostrat_api.sections AS
SELECT * FROM macrostrat_api.get_sections();

CREATE OR REPLACE FUNCTION
macrostrat_api.get_strat_names() RETURNS SETOF macrostrat.strat_names AS $$
BEGIN
  RETURN QUERY SELECT * FROM macrostrat.strat_names;
END
$$ language plpgsql SECURITY INVOKER;

CREATE OR REPLACE VIEW macrostrat_api.strat_names AS
SELECT * FROM macrostrat_api.get_strat_names();

CREATE OR REPLACE FUNCTION
macrostrat_api.get_strat_names_view() RETURNS VOID AS $$
BEGIN
  CREATE VIEW macrostrat_api.strat_names_view AS SELECT 
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
END
$$ language plpgsql SECURITY INVOKER;

SELECT macrostrat_api.get_strat_names_view(); 

CREATE OR REPLACE VIEW macrostrat_api.col_group_view AS
SELECT cg.id,
cg.col_group,
cg.col_group_long,
cg.project_id,
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
SELECT u.id,
u.strat_name AS unit_strat_name,
to_jsonb(s.*) as strat_name,
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
u.notes,
fo.interval_name AS name_fo,
fo.age_bottom,
lo.interval_name AS name_lo,
lo.age_top
FROM macrostrat.units u
    LEFT JOIN macrostrat.intervals fo ON u.fo = fo.id
    LEFT JOIN macrostrat.intervals lo ON u.lo = lo.id
    LEFT JOIN macrostrat.strat_names s ON u.strat_name_id = s.id;


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
c.notes,
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