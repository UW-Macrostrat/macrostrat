SELECT
  i.id,
  i.age_bottom,
  i.age_top,
  i.interval_name,
  i.interval_abbrev,
  i.interval_type,
  i.interval_color,
  i.rank,
  jsonb_agg(
    jsonb_build_object(
      'id', t.id,
      'name', t.timescale,
      'ref_id', t.ref_id
    )
  ) FILTER (WHERE t.id IS NOT NULL) AS timescales
  -- TODO: can use jsonb_agg_strict here once we upgrade to PostgreSQL 18
FROM macrostrat.intervals i
LEFT JOIN macrostrat.timescales_intervals ti
ON i.id = ti.interval_id
LEFT JOIN macrostrat.timescales t
ON ti.timescale_id = t.id
GROUP BY
  i.id,
  i.age_bottom,
  i.age_top,
  i.interval_name,
  i.interval_abbrev,
  i.interval_type,
  i.interval_color,
  i.rank
ORDER BY i.age_top, i.age_bottom
