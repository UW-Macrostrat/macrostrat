/** Units matching a legend entry's name, or any name *above* it in the rank tree.

  A map naming a member matches the units of its formation, group and supergroup.
  Unlike the descendant direction this never walked the lexicon -- a name's
  parent ids are columns on its own row -- so there is no lookup table here.
  `0` is how `lookup_strat_names` spells "no parent at this rank".

  See `match-units-down.sql` for `{column_geom}`.
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
  flattened AS (
    /* The ranks *above* this name, one row per ancestor.

       Unlike the descendant direction, this never walked the lexicon:
       a name's member, formation, group and supergroup ids are columns
       on its own row, so there was no subquery to remove. `0` is how
       `lookup_strat_names` spells "no parent at this rank". */
    SELECT lsn.strat_name_id, lsn.strat_name, lsn.rank, u AS up_names
    FROM macrostrat.lookup_strat_names lsn
    CROSS JOIN LATERAL unnest(
      CASE lsn.rank
        WHEN 'Bed' THEN ARRAY[lsn.mbr_id, lsn.fm_id, lsn.gp_id, lsn.sgp_id]
        WHEN 'Mbr' THEN ARRAY[lsn.fm_id, lsn.gp_id, lsn.sgp_id]
        WHEN 'Fm'  THEN ARRAY[lsn.gp_id, lsn.sgp_id]
        WHEN 'Gp'  THEN ARRAY[lsn.sgp_id]
        ELSE ARRAY[]::integer[]
      END
    ) AS u
    WHERE u IS NOT NULL AND u <> 0
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
  JOIN flattened ON flattened.up_names = unit_strat_names.strat_name_id
  JOIN macrostrat.lookup_strat_names ON flattened.up_names = lookup_strat_names.strat_name_id
  WHERE cols.status_code='active'
  )
  SELECT DISTINCT ON (map_id, b.unit_id) map_id, b.unit_id AS units, :match_type
  FROM a
  JOIN b ON a.strat_name_id = b.match_strat_name_id
  WHERE ST_Intersects(a.geom, b.geom)
      AND ((b.t_age) < (a.age_bottom + :time_fuzz))
      AND ((b.b_age) > (a.age_top - :time_fuzz));
