/*
    Creates the view for a col and sections, Not scaleable as a view, but runs quickly
    for each column.

    Returns the top interval and bottom interval of each section in the column.
    Top interval is defined as unit.lo where unit.position_bottom is smallest.
    Likewise bottom interval is unit.fo where unit.position_bottom is greatest!
 */
DROP FUNCTION IF EXISTS macrostrat_api.get_col_section_data(int);
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
	strat_name varchar(150),
	strat_name_data jsonb,
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
	GROUP BY u.id, u.strat_name,u.strat_name, u.color,u.outcrop, u.fo, u.lo,u.position_bottom, u.position_top, u.max_thick, u.min_thick, u.section_id, u.col_id, u.notes, u.name_fo, u.age_bottom, u.name_lo, u.age_top
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

/*
sophisticated ways of fetching related strat_names
Returns only strat_name_records where it's connected to a
concept and that concept ref contains the point geom for the
column.

Unions searches for strat_names in column, ones in col-group, and geographically
representative lexicon
*/
CREATE OR REPLACE FUNCTION macrostrat_api.get_col_strat_names(_col_id int)
RETURNS TABLE(
  id integer,
  strat_name VARCHAR(100),
  rank VARCHAR(50),
  ref_id integer,
  concept_id integer,
  author VARCHAR(255),
  source text
) AS
$$
BEGIN
  RETURN QUERY
  WITH a AS(
SELECT cc.*, ST_Distance(
	ST_Transform(c.coordinate, 3857),
	ST_Transform(cc.coordinate, 3857)
	)
	as distance FROM macrostrat.cols c
JOIN macrostrat.cols cc
	ON c.col_group_id = cc.col_group_id
WHERE c.id = _col_id
), b AS(
  SELECT c.col_name from macrostrat.cols c WHERE c.id = _col_id
)
SELECT sn.*, r.author, b.col_name::text as source from b,macrostrat_api.units u
JOIN macrostrat_api.unit_strat_names usn
 ON u.id = usn.unit_id
JOIN macrostrat_api.strat_names sn
 ON usn.strat_name_id = sn.id
JOIN macrostrat_api.refs r
  ON r.id = sn.ref_id
WHERE u.col_id = _col_id
AND sn.concept_id IS NULL
UNION ALL
SELECT DISTINCT ON(sn.id) sn.*, r.author, a.col_name::text as source
FROM a, macrostrat_api.units u
JOIN macrostrat_api.unit_strat_names usn
 ON u.id = usn.unit_id
JOIN macrostrat_api.strat_names sn
 ON usn.strat_name_id = sn.id
JOIN macrostrat_api.refs r
  ON r.id = sn.ref_id
WHERE u.col_id = _col_id AND sn.concept_id IS NULL or u.col_id = a.id
AND sn.concept_id IS NULL
UNION ALL
SELECT DISTINCT ON(sn.id) sn.*, r.author, 'nearby' as source FROM macrostrat.strat_names sn
  LEFT JOIN macrostrat.strat_names_meta snm
  ON sn.concept_id = snm.concept_id
  LEFT JOIN macrostrat.refs r
  ON r.id = snm.ref_id
  WHERE ST_Intersects(r.rgeom, (
  	select ST_SetSrid((coordinate)::geometry, 4326)
  	from macrostrat.cols c where c.id = _col_id
  	)
)
UNION ALL
SELECT DISTINCT ON(sn.id) sn.*, r.author, 'unrelated' as source
FROM macrostrat_api.units u
JOIN macrostrat_api.unit_strat_names usn
 ON u.id = usn.unit_id
JOIN macrostrat_api.strat_names sn
 ON usn.strat_name_id = sn.id
JOIN macrostrat_api.refs r
  ON r.id = sn.ref_id
WHERE u.col_id NOT IN (SELECT a.id FROM a)
	AND sn.concept_id IS NULL
	AND r.rgeom IS NULL
;
END
$$ language plpgsql;

CREATE OR REPLACE FUNCTION macrostrat_api.get_strat_names_col_priority(_col_id int)
RETURNS TABLE(
  id integer,
  strat_name VARCHAR(100),
  rank VARCHAR(50),
  ref_id integer,
  concept_id integer,
  author VARCHAR(255),
  source text,
  parent text

) AS
$$
BEGIN
  RETURN QUERY
    SELECT
    gc.*,
    st.strat_name ||' '|| st.rank as parent
    FROM macrostrat_api.get_col_strat_names(_col_id) gc
    LEFT JOIN macrostrat.strat_tree tree
    ON tree.child = gc.id
    LEFT JOIN macrostrat.strat_names st
    ON st.id = tree.parent
    ;
END
$$ language plpgsql;

CREATE OR REPLACE FUNCTION macrostrat_api.get_strat_name_info(strat_name_id int)
RETURNS TABLE(
  id integer,
  strat_name VARCHAR(100),
  rank VARCHAR(50),
  author VARCHAR(255),
  parent text
)AS
$$
BEGIN
RETURN QUERY
  SELECT
  sn.id,
  sn.strat_name,
  sn.rank,
  sn.concept_id,
  r.author,
  st.strat_name ||' '|| st.rank as parent
  FROM macrostrat.strat_names sn
  JOIN macrostrat.strat_names_meta snm
    ON sn.concept_id = snm.concept_id
  JOIN macrostrat.refs r
    ON r.id = snm.ref_id
  JOIN macrostrat.strat_tree tree
    ON tree.child = sn.id
  JOIN macrostrat.strat_names st
    ON st.id = tree.parent
  WHERE sn.id = strat_name_id
    ;
END
$$ language plpgsql;

/* function that calculates proportions of lithologies based on
subdom and dom props.

happens here: https://github.com/UW-Macrostrat/utils/blob/bba082956cc611af8458cf234c160b05e1cb3794/cli/commands/rebuild_scripts/lookup_unit_attrs_api.py#L40
but as two separate queries. Makes more sense to make a function that calculates both sub and dom comp_prop for
a unit and returns that for a update query
*/
CREATE OR REPLACE FUNCTION macrostrat.get_lith_comp_prop(_unit_id integer)
RETURNS TABLE(
  dom_prop numeric,
  sub_prop numeric
) AS $$
BEGIN
  RETURN QUERY
    WITH dom as (
        SELECT
            unit_id,
            count(id) count,
            'dom' AS dom
        FROM macrostrat.unit_liths
        WHERE dom = 'dom' and unit_id = _unit_id
        GROUP BY unit_id
      ), sub as(
        SELECT
          unit_id,
          count(id) count,
          'sub' AS dom
        FROM macrostrat.unit_liths
        WHERE dom = 'sub' and unit_id = _unit_id
        GROUP BY unit_id
      )
    SELECT
      -- need at least one float to prevent truncating to 0
      ROUND((5.0 / (COALESCE(sub.count, 0) + (dom.count * 5))),4) AS dom_prop,
      ROUND((1.0 / (COALESCE(sub.count, 0) + (dom.count * 5))),4) AS sub_prop
    FROM sub
    JOIN dom
    ON dom.unit_id = sub.unit_id;
END
$$ language plpgsql;

/* updates the comp_prop for unit_liths */
CREATE OR REPLACE FUNCTION macrostrat.update_unit_lith_comp_props(_unit_id integer)
RETURNS VOID as
$$
BEGIN
  UPDATE macrostrat.unit_liths ul
  SET
    comp_prop = (CASE WHEN ul.dom = 'sub' THEN prop.sub_prop ELSE prop.dom_prop END)
  FROM (SELECT * FROM macrostrat.get_lith_comp_prop(_unit_id)) as prop
  WHERE ul.unit_id = _unit_id;
END
$$ language plpgsql;

/*
  a insert or update trigger for cols.

  If a lat and long are passed but NOT a wkt or coordinate,
  we want to create those two columns and insert them as well
 */
CREATE OR REPLACE FUNCTION macrostrat.lng_lat_insert_trigger()
RETURNS TRIGGER AS $$
DECLARE
BEGIN
  IF tg_op = 'INSERT' OR new.lat <> old.lat OR new.lng <> old.lng THEN
    new.wkt := ST_AsText(ST_MakePoint(new.lng, new.lat));
    new.coordinate := ST_SetSrid(new.wkt, 4326);
  END IF;
  RETURN new;
END;
$$ language plpgsql;

DROP TRIGGER IF EXISTS lng_lat_insert ON macrostrat.cols;
CREATE TRIGGER lng_lat_insert_trigger
  BEFORE INSERT OR UPDATE ON macrostrat.cols
  FOR EACH ROW
  EXECUTE PROCEDURE macrostrat.lng_lat_insert_trigger();


