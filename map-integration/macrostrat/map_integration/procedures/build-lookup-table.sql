INSERT INTO lookup_%(scale)s (
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

  -- Find unique match types for units
  WITH unit_bases AS (
    SELECT array_agg(distinct basis_col) bases, q.map_id
    FROM maps.map_units
    JOIN maps.%(scale)s q ON map_units.map_id = q.map_id
    WHERE source_id = %(source_id)s
    GROUP BY q.map_id
    ORDER BY q.map_id
  ),

  -- Find and aggregate best unit_ids for each map_id
  unit_ids AS (
    SELECT q.map_id, array_agg(DISTINCT unit_id) AS unit_ids
    FROM maps.%(scale)s q
    JOIN maps.map_units ON q.map_id = map_units.map_id
    JOIN unit_bases ON unit_bases.map_id = q.map_id

    WHERE source_id = %(source_id)s AND map_units.basis_col = ANY(
      CASE
        WHEN 'manual' = ANY(bases)
          THEN array['manual']

        WHEN 'strat_name' = ANY(bases)
        THEN array['strat_name', 'manual']

        WHEN 'strat_name_fname' = ANY(bases)
          THEN array['strat_name_fname', 'manual']

        WHEN 'strat_name_fspace' = ANY(bases)
          THEN array['strat_name_fspace', 'manual']

        WHEN 'strat_name_ftime' = ANY(bases)
          THEN array['strat_name_ftime', 'manual']

        WHEN 'strat_name_fname_fspace' = ANY(bases)
          THEN array['strat_name_fname_fspace', 'manual']

        WHEN 'strat_name_fspace_ftime' = ANY(bases)
          THEN array['strat_name_fspace_ftime', 'manual']

        WHEN 'strat_name_fname_ftime' = ANY(bases)
          THEN array['strat_name_fname_ftime', 'manual']

        WHEN 'strat_name_fname_fspace_ftime' = ANY(bases)
          THEN array['strat_name_fname_fspace_ftime', 'manual']

--------------------------------------------------------------------------------------------
        WHEN 'name' = ANY(bases)
        THEN array['name', 'manual']

        WHEN 'name_fname' = ANY(bases)
        THEN array['name_fname', 'manual']

        WHEN 'name_fspace' = ANY(bases)
        THEN array['name_fspace', 'manual']

        WHEN 'name_ftime' = ANY(bases)
        THEN array['name_ftime', 'manual']

        WHEN 'name_fname_fspace' = ANY(bases)
          THEN array['name_fname_fspace', 'manual']

        WHEN 'name_fspace_ftime' = ANY(bases)
          THEN array['name_fspace_ftime', 'manual']

        WHEN 'name_fname_ftime' = ANY(bases)
          THEN array['name_fname_ftime', 'manual']

        WHEN 'name_fname_fspace_ftime' = ANY(bases)
          THEN array['name_fname_fspace_ftime', 'manual']

--------------------------------------------------------------------------------------------
        WHEN ('descrip' = ANY(bases) OR 'comments' = ANY(bases))
        THEN array['descrip', 'comments', 'manual']

        WHEN ('descrip_fname' = ANY(bases) OR 'comments_fname' = ANY(bases))
        THEN array['descrip_fname', 'comments_fname', 'manual']

        WHEN ('descrip_fspace' = ANY(bases) OR 'comments_fspace' = ANY(bases))
        THEN array['descrip_fspace', 'comments_fspace', 'manual']

        WHEN ('descrip_ftime' = ANY(bases) OR 'comments_ftime' = ANY(bases))
        THEN array['descrip_ftime', 'comments_ftime', 'manual']

        WHEN ('descrip_fname_fspace' = ANY(bases) OR 'comments_fname_fspace' = ANY(bases))
          THEN array['descrip_fname_fspace', 'comments_fname_fspace', 'manual']

        WHEN ('descrip_fspace_ftime' = ANY(bases) OR 'comments_fspace_ftime' = ANY(bases))
          THEN array['descrip_fspace_ftime', 'comments_fspace_ftime', 'manual']

        WHEN ('descrip_fname_ftime' = ANY(bases) OR 'comments_fname_ftime' = ANY(bases))
          THEN array['descrip_fname_ftime', 'comments_fname_ftime', 'manual']

        WHEN ('descrip_fname_fspace_ftime' = ANY(bases) OR 'comments_fname_fspace_ftime' = ANY(bases))
          THEN array['descrip_fname_fspace_ftime', 'comments_fname_fspace_ftime', 'manual']

        ELSE
        array['unknown', 'manual']
        END
    )
    GROUP BY q.map_id
  ),

  -- Find unique match types of strat_names
  strat_name_bases AS (
    SELECT array_agg(distinct basis_col) bases, q.map_id
    FROM maps.map_strat_names
    JOIN maps.%(scale)s q ON map_strat_names.map_id = q.map_id
    WHERE source_id = %(source_id)s
    GROUP BY q.map_id
    ORDER BY q.map_id
  ),

  -- Find and aggregate best strat_name_ids for each map_id
  strat_name_ids AS (
    SELECT q.map_id, array_agg(DISTINCT strat_name_id) AS strat_name_ids
    FROM maps.%(scale)s q
    JOIN maps.map_strat_names ON q.map_id = map_strat_names.map_id
    JOIN strat_name_bases ON strat_name_bases.map_id = q.map_id
    WHERE source_id = %(source_id)s AND map_strat_names.basis_col = ANY(
      CASE
        WHEN 'manual' = ANY(bases)
          THEN array['manual']

        WHEN 'strat_name' = ANY(bases)
        THEN array['strat_name', 'manual']

        WHEN 'strat_name_fspace' = ANY(bases)
          THEN array['strat_name_fspace', 'manual']

        WHEN 'strat_name_ftime' = ANY(bases)
          THEN array['strat_name_ftime', 'manual']

        WHEN 'strat_name_fspace_ftime' = ANY(bases)
          THEN array['strat_name_fspace_ftime', 'manual']

        WHEN 'strat_name_ntime' = ANY(bases)
          THEN array['strat_name_ntime', 'manual']

        WHEN 'strat_name_fspace_ntime' = ANY(bases)
          THEN array['strat_name_fspace_ntime', 'manual']

        WHEN 'strat_name_fname' = ANY(bases)
          THEN array['strat_name_fname', 'manual']

        WHEN 'strat_name_fname_fspace' = ANY(bases)
          THEN array['strat_name_fname_fspace', 'manual']

        WHEN 'strat_name_fname_ftime' = ANY(bases)
          THEN array['strat_name_fname_ftime', 'manual']

        WHEN 'strat_name_fname_fspace_ftime' = ANY(bases)
          THEN array['strat_name_fname_fspace_ftime', 'manual']

        WHEN 'strat_name_fname_ftime' = ANY(bases)
          THEN array['strat_name_fname_ftime', 'manual']

        WHEN 'strat_name_fname_fspace_ntime' = ANY(bases)
          THEN array['strat_name_fname_fspace_ntime', 'manual']

--------------------------------------------------------------------------------------------
        WHEN 'name' = ANY(bases)
        THEN array['name', 'manual']

        WHEN 'name_fname' = ANY(bases)
        THEN array['name_fname', 'manual']

        WHEN 'name_fspace' = ANY(bases)
        THEN array['name_fspace', 'manual']

        WHEN 'name_ftime' = ANY(bases)
        THEN array['name_ftime', 'manual']

        WHEN 'name_fname_fspace' = ANY(bases)
          THEN array['name_fname_fspace', 'manual']

        WHEN 'name_fspace_ftime' = ANY(bases)
          THEN array['name_fspace_ftime', 'manual']

        WHEN 'name_fname_ftime' = ANY(bases)
          THEN array['name_fname_ftime', 'manual']

        WHEN 'name_fname_fspace_ftime' = ANY(bases)
          THEN array['name_fname_fspace_ftime', 'manual']

--------------------------------------------------------------------------------------------
        WHEN ('descrip' = ANY(bases) OR 'comments' = ANY(bases))
        THEN array['descrip', 'comments', 'manual']

        WHEN ('descrip_fname' = ANY(bases) OR 'comments_fname' = ANY(bases))
        THEN array['descrip_fname', 'comments_fname', 'manual']

        WHEN ('descrip_fspace' = ANY(bases) OR 'comments_fspace' = ANY(bases))
        THEN array['descrip_fspace', 'comments_fspace', 'manual']

        WHEN ('descrip_ftime' = ANY(bases) OR 'comments_ftime' = ANY(bases))
        THEN array['descrip_ftime', 'comments_ftime', 'manual']

        WHEN ('descrip_fname_fspace' = ANY(bases) OR 'comments_fname_fspace' = ANY(bases))
          THEN array['descrip_fname_fspace', 'comments_fname_fspace', 'manual']

        WHEN ('descrip_fspace_ftime' = ANY(bases) OR 'comments_fspace_ftime' = ANY(bases))
          THEN array['descrip_fspace_ftime', 'comments_fspace_ftime', 'manual']

        WHEN ('descrip_fname_ftime' = ANY(bases) OR 'comments_fname_ftime' = ANY(bases))
          THEN array['descrip_fname_ftime', 'comments_fname_ftime', 'manual']

        WHEN ('descrip_fname_fspace_ftime' = ANY(bases) OR 'comments_fname_fspace_ftime' = ANY(bases))
          THEN array['descrip_fname_fspace_ftime', 'comments_fname_fspace_ftime', 'manual']

        ELSE
        array['unknown', 'manual']
        END
    )
    GROUP BY q.map_id
  ),

  lith_bases AS (
        SELECT array_agg(distinct basis_col) bases, q.legend_id
        FROM maps.legend_liths
        JOIN maps.legend q ON legend_liths.legend_id = q.legend_id
        WHERE source_id = %(source_id)s
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
        WHERE source_id = %(source_id)s
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
    JOIN maps.%(scale)s q ON q.map_id = map_legend.map_id
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
        FROM maps.%(scale)s q
        JOIN strat_name_ids sni ON sni.map_id = q.map_id
        JOIN macrostrat.lookup_strat_names lsn ON lsn.strat_name_id = ANY(sni.strat_name_ids)
        WHERE source_id = %(source_id)s
        GROUP BY q.map_id
    ) sub
    JOIN strat_name_ids sni ON sni.map_id = sub.map_id
  ),

  -- Group all the previous matches, and select the top and bottom interval for each map_id
  match_summary AS (
    SELECT
      q.map_id,
      q.name,
      COALESCE(unit_ids.unit_ids, '{}') unit_ids,
      COALESCE(strat_name_ids.strat_name_ids, '{}') strat_name_ids,
      COALESCE(more_strat_names.concept_ids, '{}') concept_ids,
      COALESCE(more_strat_names.strat_name_children, '{}') strat_name_children,
      COALESCE(lith_ids.lith_ids, '{}') lith_ids,
      COALESCE(lith_ids.lith_types, '{}') lith_types,
      COALESCE(lith_ids.lith_classes, '{}') lith_classes,
      t_interval,
      b_interval
    FROM maps.%(scale)s q
    LEFT JOIN unit_ids ON q.map_id = unit_ids.map_id
    LEFT JOIN strat_name_ids ON q.map_id = strat_name_ids.map_id
    LEFT JOIN more_strat_names ON more_strat_names.map_id = q.map_id
    LEFT JOIN lith_ids ON q.map_id = lith_ids.map_id
    WHERE source_id = %(source_id)s
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