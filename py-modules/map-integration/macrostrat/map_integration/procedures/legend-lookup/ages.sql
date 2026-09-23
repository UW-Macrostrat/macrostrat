/** Each legend entry's best age and base colour.

  The age is its matched units' range where it has any, and its own intervals'
  otherwise. The colour is that of the tightest interval bracketing the age,
  excluding the New Zealand timescale; `legend_lookup.py` then nudges it to a
  variant. Reads `unit_ids`, so it runs after they are set.

  Colours are looked up once per distinct age range, as `build-lookup-table.sql`
  does. A range with a null end matches no interval and gets no colour.
*/
WITH unit_ages AS (
  SELECT l.legend_id, min(ui.t_age) AS t_age, max(ui.b_age) AS b_age
  FROM maps.legend l
  JOIN macrostrat.lookup_unit_intervals ui ON ui.unit_id = ANY(l.unit_ids)
  WHERE l.source_id = :source_id
  GROUP BY l.legend_id
),

ages AS (
  SELECT
    l.legend_id,
    coalesce(u.t_age, ti.age_top) AS best_age_top,
    coalesce(u.b_age, tb.age_bottom) AS best_age_bottom
  FROM maps.legend l
  LEFT JOIN unit_ages u ON u.legend_id = l.legend_id
  LEFT JOIN macrostrat.intervals ti ON ti.id = l.t_interval
  LEFT JOIN macrostrat.intervals tb ON tb.id = l.b_interval
  WHERE l.source_id = :source_id
),

colors AS (
  SELECT
    a.best_age_top,
    a.best_age_bottom,
    (
      SELECT i.interval_color
      FROM macrostrat.intervals i
      WHERE i.age_top <= a.best_age_top
        AND i.age_bottom >= a.best_age_bottom
        AND i.id NOT IN (
          SELECT interval_id FROM macrostrat.timescales_intervals
          WHERE timescale_id = 6
        )
      ORDER BY i.age_bottom - i.age_top
      LIMIT 1
    ) AS color
  FROM (SELECT DISTINCT best_age_top, best_age_bottom FROM ages) a
)

UPDATE maps.legend
SET
  best_age_top = ages.best_age_top,
  best_age_bottom = ages.best_age_bottom,
  color = CASE WHEN legend.name ILIKE 'water' THEN '' ELSE colors.color END
FROM ages
LEFT JOIN colors
  ON colors.best_age_top = ages.best_age_top
  AND colors.best_age_bottom = ages.best_age_bottom
WHERE ages.legend_id = legend.legend_id
