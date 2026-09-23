/** Units matching a legend entry's name exactly, without walking the rank tree.

  The first and strongest pass. See `match-units-down.sql` for `{column_geom}`.
*/
INSERT INTO maps.map_units (map_id, unit_id, basis_col)
WITH a AS (
    SELECT DISTINCT ON (m.map_id, concept_id) m.map_id, concept_id, map_strat_names.strat_name_id, intervals_top.age_top, intervals_bottom.age_bottom, geom
    FROM {scale_table} m
    JOIN macrostrat.intervals intervals_top on m.t_interval = intervals_top.id
    JOIN macrostrat.intervals intervals_bottom on m.b_interval = intervals_bottom.id
    JOIN maps.map_strat_names ON m.map_id = map_strat_names.map_id
    JOIN macrostrat.lookup_strat_names on map_strat_names.strat_name_id = lookup_strat_names.strat_name_id
    WHERE m.source_id = :source_id
    AND basis_col = :match_type
    AND NOT EXISTS (
      SELECT 1
      FROM maps.map_units x
      WHERE x.map_id = m.map_id
    )
),
    b AS (
      SELECT unit_strat_names.strat_name_id, unit_strat_names.unit_id, lookup_unit_intervals.t_age, lookup_unit_intervals.b_age, {column_geom} AS geom
      FROM macrostrat.unit_strat_names
      JOIN macrostrat.units_sections ON unit_strat_names.unit_id = units_sections.unit_id
      JOIN macrostrat.cols ON units_sections.col_id = cols.id
      JOIN macrostrat.lookup_unit_intervals ON unit_strat_names.unit_id = lookup_unit_intervals.unit_id
      WHERE strat_name_id IN (SELECT DISTINCT strat_name_id FROM a) AND cols.status_code='active'
    )
SELECT DISTINCT ON (map_id, b.unit_id) map_id, b.unit_id AS units, :match_type
FROM a
JOIN b ON a.strat_name_id = b.strat_name_id
WHERE ST_Intersects(a.geom, b.geom)
    AND ((b.t_age) < (a.age_bottom + :time_fuzz))
    AND ((b.b_age) > (a.age_top - :time_fuzz));
