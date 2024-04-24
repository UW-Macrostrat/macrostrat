/* Legend with lithology information */

CREATE OR REPLACE VIEW macrostrat_api.legend AS
WITH legend_liths AS (
SELECT
	legend_id,
	json_build_object(
    'lith_id', lith_id,
    'basis_col', basis_col,
    'name', l.lith,
    'color', l.lith_color,
    'fill', l.lith_fill
  ) liths
FROM maps.legend_liths ll
JOIN macrostrat.liths l ON ll.lith_id = l.id
)
SELECT l.*, jsonb_agg(liths) liths FROM maps.legend l
JOIN legend_liths ll USING (legend_id)
GROUP BY legend_id;