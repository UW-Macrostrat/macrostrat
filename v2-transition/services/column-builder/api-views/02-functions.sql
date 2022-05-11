/* 
    Creates the view for a col and sections, Not scaleable as a view, but runs quickly 
    for each column.

    Returns the top interval and bottom interval of each section in the column.
    Top interval is defined as unit.lo where unit.position_bottom is smallest.
    Likewise bottom interval is unit.fo where unit.position_bottom is greatest! 
 */
DROP FUNCTION macrostrat_api.get_col_section_data(int);
CREATE OR REPLACE FUNCTION macrostrat_api.get_col_section_data(column_id INT) 
RETURNS TABLE (
    id INT, 
    unit_count BIGINT, 
    top varchar(200), 
    bottom varchar(200)) 
AS
$$
BEGIN 
RETURN QUERY
    SELECT 
        s.id,
        COUNT(uc) as unit_count,
        lo.interval_name as top,
        fo.interval_name as bottom
    FROM macrostrat.sections s 
    JOIN macrostrat.units uc 
      ON uc.section_id = s.id
    JOIN macrostrat.units u 
      ON u.section_id = s.id
    JOIN macrostrat.units un
      ON un.section_id = s.id
    JOIN macrostrat.intervals fo
      ON un.fo = fo.id
    JOIN macrostrat.intervals lo
      ON u.lo = lo.id
    WHERE u.position_bottom = (
        SELECT MIN(position_bottom) FROM macrostrat.units WHERE section_id = u.section_id
    ) AND un.position_bottom = (
        SELECT MAX(position_bottom) FROM macrostrat.units WHERE section_id = un.section_id
    ) AND s.col_id = column_id
    GROUP BY s.id, lo.interval_name, fo.interval_name, fo.age_bottom ORDER BY fo.age_bottom
    ;
END
$$ LANGUAGE plpgsql;

DROP FUNCTION IF EXISTS macrostrat_api.get_units_with_collections(int);
CREATE OR REPLACE FUNCTION macrostrat_api.get_units_with_collections(column_id int)
RETURNS TABLE(
	id int,
	unit_strat_name varchar(150),
	strat_name jsonb,
	color varchar(20),
	outcrop varchar(20),
	fo int,
	lo int,
	position_bottom numeric,
	position_top numeric,
	max_thick numeric,
	min_thick numeric,
	section_id int,
	col_id int,
	notes text,
	name_fo varchar(200),
	age_bottom numeric,
	name_lo varchar(200),
	age_top numeric,
	lith_unit jsonb,
	environ_unit jsonb
) AS
$$
BEGIN
RETURN QUERY
	SELECT 
		u.*, 
		COALESCE(jsonb_agg(lu.*) FILTER (WHERE lu.unit_id IS NOT NULL), '[]') as lith_unit, 
		COALESCE(jsonb_agg(eu.*) FILTER (WHERE eu.unit_id IS NOT NULL),'[]') as environ_unit 
	FROM macrostrat_api.unit_strat_name_expanded u
	LEFT JOIN macrostrat_api.lith_unit lu
	 ON lu.unit_id = u.id
	LEFT JOIN macrostrat_api.environ_unit eu
	 ON eu.unit_id = u.id
	WHERE u.col_id = column_id
	GROUP BY u.id, u.unit_strat_name,u.strat_name, u.color,u.outcrop, u.fo, u.lo,u.position_bottom, u.position_top, u.max_thick, u.min_thick, u.section_id, u.col_id, u.notes, u.name_fo, u.age_bottom, u.name_lo, u.age_top
  ORDER BY u.position_bottom;
END
$$ LANGUAGE plpgsql;

/* 
Functions for Combing and Splitting Sections!
*/
CREATE OR REPLACE FUNCTION macrostrat_api.split_section(unit_ids int[])
RETURNS VOID AS
$$
DECLARE
  _col_id integer;
  _section_id integer;
BEGIN
  SELECT col_id FROM macrostrat.units WHERE id = unit_ids[0] INTO _col_id;
  INSERT INTO macrostrat.sections(col_id) VALUES (_col_id) RETURNING id INTO _section_id;
  UPDATE macrostrat.units
    SET 
      section_id = _section_id
    WHERE id = ANY(unit_ids); 
END
$$ language plpgsql;

/* 
Combine 2 or more sections
*/
CREATE OR REPLACE FUNCTION macrostrat_api.combine_sections(section_ids int[])
RETURNS VOID AS
$$
BEGIN
  IF array_length(section_ids, 1) < 2 THEN
    RAISE EXCEPTION 'Not enough section_ids';
  END IF;
  -- arbitrarily choose first section_id to combine into
  UPDATE macrostrat.units
  SET
    section_id = section_ids[1]
  WHERE section_id = ANY(section_ids);
  -- delete from sections table for rest of ids
  DELETE FROM macrostrat.sections
  WHERE id = ANY(section_ids[2:]);
END
$$ language plpgsql;