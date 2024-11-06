/** Useful queries to assess database structure for the Macrostrat schema */

/** Find units that are replicated elsewhere... */
SELECT * FROM macrostrat.units
WHERE id NOT IN (SELECT unit_id FROM macrostrat.units_sections)
  AND section_id NOT IN (SELECT id FROM macrostrat.sections);

/** Find units_sections entries correlated to units direct links to sections */
SELECT u.id, u.section_id, us.section_id, u.col_id, us.col_id
FROM macrostrat.units u
JOIN macrostrat.units_sections us
  ON u.id = us.unit_id;
