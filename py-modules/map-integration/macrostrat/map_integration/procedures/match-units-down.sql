/** Units matching a legend entry's name, or any name *below* it in the rank tree.

  A map naming a group matches the units of its formations and members. The
  descendants come from `macrostrat.lookup_strat_name_tree`, flattened once by
  the lexicon rebuild; this walked `lookup_strat_names` with four correlated
  subqueries per row on every pass, up to sixty-four full-lexicon scans for one
  source.

  `{column_geom}` is the column geometry this pass compares against -- the
  polygon itself when space is strict, a buffered envelope when it is not. Two
  different expressions rather than one with a different number, so it is
  substituted rather than bound; the distance inside it is `:space_buffer`.
*/
INSERT INTO maps.map_units (map_id, unit_id, basis_col)
  WITH a AS (
      SELECT DISTINCT ON (m.map_id, concept_id) m.map_id, concept_id, map_strat_names.strat_name_id, intervals_top.age_top, intervals_bottom.age_bottom, geom
      FROM maps.polygons m
      JOIN macrostrat.intervals intervals_top on m.t_interval = intervals_top.id
      JOIN macrostrat.intervals intervals_bottom on m.b_interval = intervals_bottom.id
      JOIN maps.map_strat_names ON m.map_id = map_strat_names.map_id
      JOIN macrostrat.lookup_strat_names on map_strat_names.strat_name_id = lookup_strat_names.strat_name_id
      WHERE m.source_id = :source_id
        AND m.scale = :scale
        AND basis_col = :match_type
        AND NOT EXISTS (
          SELECT 1
          FROM maps.map_units x
          WHERE x.map_id = m.map_id
        )
  ),
  flattened AS (
    /* The rank tree is flattened once by the lexicon rebuild. This
       walked `lookup_strat_names` with four correlated subqueries per
       row, on every matching pass -- up to sixty-four full-lexicon
       scans for one source. */
    SELECT lsn.strat_name_id, lsn.strat_name, lsn.rank,
           unnest(tree.descendant_ids) AS down_names
    FROM macrostrat.lookup_strat_names lsn
    JOIN macrostrat.lookup_strat_name_tree tree
      ON tree.strat_name_id = lsn.strat_name_id
  ),
  b AS (
  SELECT
    flattened.strat_name_id AS match_strat_name_id,
    flattened.strat_name AS match_strat_name,
    flattened.rank AS match_rank,
    lookup_strat_names.strat_name,
    unit_strat_names.strat_name_id,
    unit_strat_names.unit_id,
    lookup_unit_intervals.t_age,
    lookup_unit_intervals.b_age,
    {column_geom} AS geom
  FROM macrostrat.unit_strat_names
  JOIN macrostrat.units_sections ON unit_strat_names.unit_id = units_sections.unit_id
  JOIN macrostrat.cols ON units_sections.col_id = cols.id
  JOIN macrostrat.lookup_unit_intervals ON unit_strat_names.unit_id = lookup_unit_intervals.unit_id
  JOIN flattened ON flattened.down_names = unit_strat_names.strat_name_id
  JOIN macrostrat.lookup_strat_names ON flattened.down_names = lookup_strat_names.strat_name_id
  WHERE cols.status_code='active'
  )
  SELECT DISTINCT ON (map_id, b.unit_id) map_id, b.unit_id AS units, :match_type
  FROM a
  JOIN b ON a.strat_name_id = b.match_strat_name_id
  WHERE ST_Intersects(a.geom, b.geom)
      AND ((b.t_age) < (a.age_bottom + :time_fuzz))
      AND ((b.b_age) > (a.age_top - :time_fuzz));
