/* Legend with lithology information */


CREATE OR REPLACE VIEW macrostrat_api.legend AS
WITH _intervals AS (
SELECT
	id,
	json_build_object('id', id, 'name', interval_name, 'color', interval_color, 'rank', rank) _interval
FROM macrostrat.intervals
),
legend_liths AS (
SELECT
	legend_id, 
	lith_id,
	json_agg(basis_col) basis_cols
FROM maps.legend_liths
GROUP BY legend_id, lith_id
),
legend_liths2 AS (
SELECT
	legend_id,
	json_build_object(
    'lith_id', lith_id,
    'basis_col', basis_cols,
    'name', l.lith,
    'color', l.lith_color,
    'fill', l.lith_fill
  ) liths
FROM legend_liths ll
JOIN macrostrat.liths l
  ON ll.lith_id = l.id
)
SELECT
  l.legend_id,
  l.source_id,
  l.name,
  l.strat_name,
  l.age,
  l.lith,
  l.descrip,
  l.comments,
  (SELECT _interval FROM _intervals WHERE id = l.b_interval) b_interval,
  (SELECT _interval FROM _intervals WHERE id = l.t_interval) t_interval,
  l.best_age_bottom,
  l.best_age_top,
  l.color,
  l.unit_ids,
  l.concept_ids,
  l.strat_name_ids,
  l.strat_name_children,
  l.lith_ids,
  l.lith_types,
  l.lith_classes,
  l.all_lith_ids,
  l.all_lith_types,
  l.all_lith_classes,
  l.area,
	json_agg(ll.liths) liths
FROM maps.legend l
JOIN legend_liths2 ll USING (legend_id)
GROUP BY legend_id;

/* These GRANTS are duplicated elsewhere and should be simplified */
GRANT USAGE ON SCHEMA macrostrat_api TO web_anon;
GRANT USAGE ON SCHEMA macrostrat_api TO web_user;
GRANT SELECT ON ALL TABLES IN SCHEMA macrostrat_api TO web_anon;
GRANT SELECT ON ALL TABLES IN SCHEMA macrostrat_api TO web_user;