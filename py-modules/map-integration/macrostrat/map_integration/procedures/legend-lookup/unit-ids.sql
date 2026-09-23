/** Each legend entry's unit matches, at the strongest `basis_col` any of its
  polygons reached.

  Ranked per legend entry, across all its polygons -- and 5,571 of 20,130
  entries carry more than one `basis_col`, so unlike the per-polygon lookup
  table this ladder resolves a real tie. `matched` is read twice, once for each
  entry's bases and once for the units at the chosen one; as a CTE it is
  scanned once where it was two joins of `map_units` against every polygon.
*/
WITH matched AS (
  SELECT ml.legend_id, mu.unit_id, mu.basis_col
  FROM {scale_table} q
  JOIN maps.map_legend ml ON ml.map_id = q.map_id
  JOIN maps.map_units mu ON mu.map_id = q.map_id
  WHERE q.source_id = :source_id
),

unit_bases AS (
  SELECT legend_id, array_agg(DISTINCT basis_col) AS bases
  FROM matched
  GROUP BY legend_id
),

units AS (
  SELECT m.legend_id, array_agg(DISTINCT m.unit_id) AS unit_ids
  FROM matched m
  JOIN unit_bases b ON b.legend_id = m.legend_id
  WHERE m.basis_col = ANY(
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
  GROUP BY m.legend_id
)

UPDATE maps.legend
SET unit_ids = units.unit_ids
FROM units
WHERE units.legend_id = legend.legend_id
