/** Useful queries to assess database structure for the Macrostrat schema */

/** Find units that are replicated elsewhere... */
SELECT * FROM macrostrat.units
WHERE id NOT IN (SELECT unit_id FROM macrostrat.units_sections)
  AND section_id NOT IN (SELECT id FROM macrostrat.sections);

/** Find units in multiple sections */
SELECT * FROM macrostrat.units
WHERE id IN (SELECT unit_id FROM macrostrat.units_sections
  GROUP BY unit_id
  HAVING COUNT(unit_id) > 1);



/** Find units_sections entries correlated to units direct links to sections */
SELECT u.id, u.section_id, us.section_id, u.col_id, us.col_id
FROM macrostrat.units u
JOIN macrostrat.units_sections us
  ON u.id = us.unit_id
WHERE u.section_id != us.section_id
  OR u.col_id != us.col_id;

/** 258 units are in more than one section/column
  TODO: we should decide if this will be allowed (i.e., do we put a unique constraint in units_sections?)
  */

SELECT unit_id, array_agg(col_id), array_agg(section_id) FROM macrostrat.units_sections
GROUP BY unit_id
HAVING COUNT(unit_id) > 1;

-- Find units that reference an invalid section
SELECT * FROM macrostrat.units
WHERE section_id NOT IN (SELECT id FROM macrostrat.sections);


