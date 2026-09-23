INSERT INTO {lookup_table} (
  map_id,
  legend_id,
  unit_ids,
  strat_name_ids,
  concept_ids,
  strat_name_children,
  lith_ids,
  lith_types,
  lith_classes,
  best_age_top,
  best_age_bottom,
  color
) (

  /* Every unit match a polygon carries.

     No tier to choose between: `units.py` excludes a polygon from every later
     pass once it has matched, so a `map_id` holds exactly one `basis_col` --
     true of all 651,909 of them. The ladder that stood here resolved a tie that
     cannot occur. Unlike the strat-name side this stays at polygon grain, and
     correctly: units belong to columns, and 6,953 of 20,130 legend entries have
     polygons resolving to different units. */
  WITH unit_ids AS (
    SELECT q.map_id, array_agg(DISTINCT mu.unit_id) AS unit_ids
    FROM {scale_table} q
    JOIN maps.map_units mu ON mu.map_id = q.map_id
    WHERE q.source_id = :source_id
    GROUP BY q.map_id
  ),

  /* The same ranking as `legend_lookup`, joined out to the polygons that share
     each legend entry. It is decided once per entry: every polygon of an entry
     has the same matches, so ranking per `map_id` was the same answer computed
     once per polygon. */
  ranked AS (
    SELECT
      lsn.legend_id,
      lsn.strat_name_id,
      rank() OVER (
        PARTITION BY lsn.legend_id
    /* Strongest evidence first. A human assertion outranks everything;
       then the field the name was found in -- `strat_name` and `name` are
       the unit, a description is a mention; then temporal corroboration,
       then spatial. Description and comments share a rank, as the ladder
       this replaces also had them.

       This is the same order the forty `WHEN` branches expressed, including
       the part that reads oddly: a buffered footprint demotes *less* than
       fuzzed time, so `_fspace` sorted above `_ftime`. */
    ORDER BY
      lsn.is_manual DESC,
      CASE lsn.match_field
        WHEN 'strat_name' THEN 0
        WHEN 'name' THEN 1
        ELSE 2
      END,
      CASE
        WHEN lsn.age_overlaps THEN 0
        WHEN NOT lsn.age_overlaps THEN 1
        ELSE 2
      END,
      lsn.location_basis
      ) AS tier
    FROM maps.legend_strat_names lsn
    JOIN maps.legend l ON l.legend_id = lsn.legend_id
    WHERE l.source_id = :source_id
  ),

  strat_name_ids AS (
    SELECT q.map_id, array_agg(DISTINCT r.strat_name_id) AS strat_name_ids
    FROM ranked r
    JOIN maps.map_legend ml ON ml.legend_id = r.legend_id
    JOIN {scale_table} q ON q.map_id = ml.map_id
    WHERE r.tier = 1 AND q.source_id = :source_id
    GROUP BY q.map_id
  ),

  lith_bases AS (
        SELECT array_agg(distinct basis_col) bases, q.legend_id
        FROM maps.legend_liths
        JOIN maps.legend q ON legend_liths.legend_id = q.legend_id
        WHERE source_id = :source_id
        GROUP BY q.legend_id
        ORDER BY q.legend_id
  ),

  -- The following was an idea that was not implemented, but might be in the future
  ------------
  -- If there are matches on the 'lith' field, don't include macrostrat match liths
  -- if matched on `lith`
    -- if `strat_names` and all are matched
        -- Use `lith` matches AND macrostrat unit matches
    -- if `strat_names` and NOT all are matched
        -- Use `lith` matches
  -- if NOT matched on `lith` (but matched on another field)
    --
    -- if `strat_names` and all are matched
        -- Use `lith` matches AND macrostrat unit matches
    -- if `strat_names` and NOT all are matched
        -- Use `lith` matches
---------------

-- Find and aggregate best lith_ids for each map_id
-- **NB:** Only uses lith matches from the map!
--         All lithologies matches to matched units are ommitted
-- Priority: `lith`, `descrip`, `name`, `comments`

-- Find and aggregate best lith_ids for each map_id
-- **NB:** Only uses lith matches from the map!
--         All lithologies matches to matched units are ommitted
-- Priority: `lith`, `descrip`, `name`, `comments`
  lith_ids AS (
    SELECT
        q.map_id,
        array_agg(DISTINCT lith_equiv) AS lith_ids,
        array_agg(DISTINCT liths.lith_type) AS lith_types,
        array_agg(DISTINCT liths.lith_class) AS lith_classes
    FROM (
        SELECT legend_liths.legend_id, legend_liths.lith_id
        FROM maps.legend_liths
        JOIN maps.legend ON legend_liths.legend_id = legend.legend_id
        JOIN lith_bases ON lith_bases.legend_id = legend.legend_id
        WHERE source_id = :source_id
          AND legend_liths.basis_col =
              CASE
                  WHEN 'lith' = ANY(bases)
                      THEN 'lith'
                  WHEN 'descrip' = ANY(bases)
                      THEN 'descrip'
                  WHEN 'name' = ANY(bases)
                      THEN 'name'
                  WHEN 'comments' = ANY(bases)
                      THEN 'comments'
                  ELSE ''
              END
    ) sub
    JOIN maps.map_legend ON map_legend.legend_id = sub.legend_id
    JOIN {scale_table} q ON q.map_id = map_legend.map_id
    JOIN macrostrat.liths ON sub.lith_id = liths.id
    GROUP BY q.map_id
  ),

  more_strat_names AS (
    SELECT
        sub.map_id,
        concept_ids,
        (
            SELECT array_agg(DISTINCT strat_name_id)
            FROM macrostrat.lookup_strat_names
            WHERE bed_id = ANY(strat_name_ids)
                OR mbr_id = ANY(strat_name_ids)
                OR fm_id = ANY(strat_name_ids)
                OR gp_id = ANY(strat_name_ids)
                OR sgp_id = ANY(strat_name_ids)
        ) AS strat_name_children
    FROM (
        SELECT
          q.map_id,
          array_agg(DISTINCT lsn.concept_id) AS concept_ids
        FROM {scale_table} q
        JOIN strat_name_ids sni ON sni.map_id = q.map_id
        JOIN macrostrat.lookup_strat_names lsn ON lsn.strat_name_id = ANY(sni.strat_name_ids)
        WHERE source_id = :source_id
        GROUP BY q.map_id
    ) sub
    JOIN strat_name_ids sni ON sni.map_id = sub.map_id
  ),

  -- Group all the previous matches, and select the top and bottom interval for each map_id
  match_summary AS (
    SELECT
      q.map_id,
      q.name,
      COALESCE(unit_ids.unit_ids, '{{}}') unit_ids,
      COALESCE(strat_name_ids.strat_name_ids, '{{}}') strat_name_ids,
      COALESCE(more_strat_names.concept_ids, '{{}}') concept_ids,
      COALESCE(more_strat_names.strat_name_children, '{{}}') strat_name_children,
      COALESCE(lith_ids.lith_ids, '{{}}') lith_ids,
      COALESCE(lith_ids.lith_types, '{{}}') lith_types,
      COALESCE(lith_ids.lith_classes, '{{}}') lith_classes,
      t_interval,
      b_interval
    FROM {scale_table} q
    LEFT JOIN unit_ids ON q.map_id = unit_ids.map_id
    LEFT JOIN strat_name_ids ON q.map_id = strat_name_ids.map_id
    LEFT JOIN more_strat_names ON more_strat_names.map_id = q.map_id
    LEFT JOIN lith_ids ON q.map_id = lith_ids.map_id
    WHERE source_id = :source_id
  ),

  -- Get the macrostrat ages for each map_id, if possible (i.e. if it has unit_id matches)
  macro_ages AS (
    SELECT
      map_id,
      name,
      unit_ids,
      strat_name_ids,
      concept_ids,
      strat_name_children,
      lith_ids,
      lith_types,
      lith_classes,
      t_interval,
      b_interval,

      (SELECT min(t_age) AS t_age FROM macrostrat.lookup_unit_intervals WHERE unit_id = ANY(unit_ids)) t_age,
      (SELECT max(b_age) AS b_age FROM macrostrat.lookup_unit_intervals WHERE unit_id = ANY(unit_ids)) b_age
    FROM match_summary
  ),

  -- Determine the best_age_top and best_age_bottom
  best_times AS (
    SELECT
      map_id,
      name,
      unit_ids,
      strat_name_ids,
      concept_ids,
      strat_name_children,
      lith_ids,
      lith_types,
      lith_classes,

      ti.age_top,
      tb.age_bottom,

      t_age,
      b_age,

      CASE
        WHEN t_age IS NULL THEN
          ti.age_top
        ELSE
          t_age
      END best_age_top,

      CASE
        WHEN b_age IS NULL THEN
          tb.age_bottom
        ELSE
          b_age
      END best_age_bottom

  FROM macro_ages
  LEFT JOIN macrostrat.intervals ti ON ti.id = t_interval
  LEFT JOIN macrostrat.intervals tb ON tb.id = b_interval
  )
  -- Assign a color for making tiles
  SELECT best_times.map_id,
  legend_id,
  unit_ids,
  strat_name_ids,
  concept_ids,
  strat_name_children,
  lith_ids,
  lith_types,
  lith_classes,

  best_age_top,
  best_age_bottom,

  CASE
    WHEN name ilike 'water'
        THEN ''
    ELSE
      (SELECT interval_color
        FROM macrostrat.intervals
        WHERE age_top <= best_age_top AND age_bottom >= best_age_bottom
        -- Exclude New Zealand ages as possible matches
        AND intervals.id NOT IN (SELECT interval_id FROM macrostrat.timescales_intervals WHERE timescale_id = 6)
        ORDER BY age_bottom - age_top
        LIMIT 1
      )
    END AS color
  FROM best_times
  LEFT JOIN maps.map_legend ON map_legend.map_id = best_times.map_id
)