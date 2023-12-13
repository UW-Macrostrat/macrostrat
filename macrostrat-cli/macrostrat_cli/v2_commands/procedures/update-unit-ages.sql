/** Select all legend entries linked to units and
  update for latest timescale updates.
*/
WITH a AS (
SELECT
	legend_id, unnest(unit_ids) unit_id
FROM maps.legend
WHERE unit_ids IS NOT null
)
SELECT
  legend_id,
  max(u.b_age) best_age_bottom_new,
  min(u.t_age) best_age_top_new
FROM a
JOIN macrostrat.lookup_units u
  ON a.unit_id = u.unit_id
GROUP BY legend_id;

/** Same query but for units with only an interval */
SELECT
	legend_id, b.age_bottom best_age_bottom_new, t.age_top best_age_top_new
FROM maps.legend l
JOIN macrostrat.intervals b
  ON l.b_interval = b.id
JOIN macrostrat.intervals t
  ON l.t_interval = t.id
WHERE l.unit_ids IS null