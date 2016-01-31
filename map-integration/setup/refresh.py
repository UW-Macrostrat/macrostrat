from psycopg2.extensions import AsIs

def find_sources(cursor, scale):
    cursor.execute("SELECT source_id FROM maps.sources WHERE scale = %(scale)s", {"scale": scale})
    return cursor.fetchall()

def find_scale(cursor, source_id):
    cursor.execute("SELECT scale from maps.sources WHERE source_id = %(source_id)s", {"source_id": source_id})
    result = cursor.fetchone()[0]
    return result

def refresh(cursor, connection, scale, source_id):
    # Delete source from lookup_scale
    cursor.execute("""
    DELETE FROM lookup_%(scale)s
    WHERE map_id IN (
        SELECT map_id
        FROM maps.%(scale)s
        WHERE source_id =  %(source_id)s
    )
    """, {"scale": AsIs(scale), "source_id": source_id})

    # Insert source into lookup_scale
    cursor.execute("""
    INSERT INTO lookup_%(scale)s (map_id, unit_ids, strat_name_ids, lith_ids, best_age_top, best_age_bottom, color) (

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
           WHEN 'manual_replace' = ANY(bases)
             THEN array['manual_replace']

           WHEN 'strat_name' = ANY(bases)
            THEN array['strat_name', 'manual']
           WHEN 'name' = ANY(bases)
             THEN array['name', 'manual']
           WHEN 'descrip' = ANY(bases)
             THEN array['descrip', 'manual']
           WHEN 'comments' = ANY(bases)
             THEN array['comments', 'manual']


           WHEN 'strat_name_buffer' = ANY(bases)
            THEN array['strat_name_buffer', 'manual']
           WHEN 'name_buffer' = ANY(bases)
             THEN array['name_buffer', 'manual']
           WHEN 'descrip_buffer' = ANY(bases)
             THEN array['descrip_buffer', 'manual']
           WHEN 'comments_buffer' = ANY(bases)
             THEN array['comments_buffer', 'manual']

           WHEN 'strat_name_fname' = ANY(bases)
            THEN array['strat_name_fname', 'manual']
           WHEN 'name_fname' = ANY(bases)
             THEN array['name_fname', 'manual']
           WHEN 'descrip_fname' = ANY(bases)
             THEN array['descrip_fname', 'manual']
           WHEN 'comments_fname' = ANY(bases)
             THEN array['comments_fname', 'manual']

           WHEN 'strat_name_fname_buffer' = ANY(bases)
            THEN array['strat_name_fname_buffer', 'manual']
           WHEN 'name_fname_buffer' = ANY(bases)
             THEN array['name_fname_buffer', 'manual']
           WHEN 'descrip_fname_buffer' = ANY(bases)
             THEN array['descrip_fname_buffer', 'manual']
           WHEN 'comments_fname_buffer' = ANY(bases)
             THEN array['comments_fname_buffer', 'manual']

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
           WHEN 'manual_replace' = ANY(bases)
             THEN array['manual_replace']

           WHEN 'strat_name' = ANY(bases)
            THEN array['strat_name', 'manual']
           WHEN 'name' = ANY(bases)
             THEN array['name', 'manual']
           WHEN 'descrip' = ANY(bases)
             THEN array['descrip', 'manual']
           WHEN 'comments' = ANY(bases)
             THEN array['comments', 'manual']


           WHEN 'strat_name_buffer' = ANY(bases)
            THEN array['strat_name_buffer', 'manual']
           WHEN 'name_buffer' = ANY(bases)
             THEN array['name_buffer', 'manual']
           WHEN 'descrip_buffer' = ANY(bases)
             THEN array['descrip_buffer', 'manual']
           WHEN 'comments_buffer' = ANY(bases)
             THEN array['comments_buffer', 'manual']

           WHEN 'strat_name_fname' = ANY(bases)
            THEN array['strat_name_fname', 'manual']
           WHEN 'name_fname' = ANY(bases)
             THEN array['name_fname', 'manual']
           WHEN 'descrip_fname' = ANY(bases)
             THEN array['descrip_fname', 'manual']
           WHEN 'comments_fname' = ANY(bases)
             THEN array['comments_fname', 'manual']

           WHEN 'strat_name_fname_buffer' = ANY(bases)
            THEN array['strat_name_fname_buffer', 'manual']
           WHEN 'name_fname_buffer' = ANY(bases)
             THEN array['name_fname_buffer', 'manual']
           WHEN 'descrip_fname_buffer' = ANY(bases)
             THEN array['descrip_fname_buffer', 'manual']
           WHEN 'comments_fname_buffer' = ANY(bases)
             THEN array['comments_fname_buffer', 'manual']

           ELSE
            array['unknown', 'manual']
           END
       )
       GROUP BY q.map_id
     ),

     -- Find unique match types of lithologies
     lith_bases AS (
       SELECT array_agg(distinct basis_col) bases, q.map_id
       FROM maps.map_liths
       JOIN maps.%(scale)s q ON map_liths.map_id = q.map_id
       WHERE source_id = %(source_id)s
       GROUP BY q.map_id
       ORDER BY q.map_id
     ),

     -- Find and aggregate best lith_ids for each map_id
     lith_ids AS (
       SELECT q.map_id, array_agg(DISTINCT lith_id) AS lith_ids
       FROM maps.%(scale)s q
       JOIN maps.map_liths ON q.map_id = map_liths.map_id
       JOIN lith_bases ON lith_bases.map_id = q.map_id
       WHERE source_id = %(source_id)s AND map_liths.basis_col = ANY(
         CASE
           WHEN 'manual_replace' = ANY(bases)
             THEN array['manual_replace']

           WHEN 'strat_name' = ANY(bases)
            THEN array['strat_name', 'manual']
           WHEN 'name' = ANY(bases)
             THEN array['name', 'manual']
           WHEN 'descrip' = ANY(bases)
             THEN array['descrip', 'manual']
           WHEN 'comments' = ANY(bases)
             THEN array['comments', 'manual']


           WHEN 'strat_name_buffer' = ANY(bases)
            THEN array['strat_name_buffer', 'manual']
           WHEN 'name_buffer' = ANY(bases)
             THEN array['name_buffer', 'manual']
           WHEN 'descrip_buffer' = ANY(bases)
             THEN array['descrip_buffer', 'manual']
           WHEN 'comments_buffer' = ANY(bases)
             THEN array['comments_buffer', 'manual']

           WHEN 'strat_name_fname' = ANY(bases)
            THEN array['strat_name_fname', 'manual']
           WHEN 'name_fname' = ANY(bases)
             THEN array['name_fname', 'manual']
           WHEN 'descrip_fname' = ANY(bases)
             THEN array['descrip_fname', 'manual']
           WHEN 'comments_fname' = ANY(bases)
             THEN array['comments_fname', 'manual']

           WHEN 'strat_name_fname_buffer' = ANY(bases)
            THEN array['strat_name_fname_buffer', 'manual']
           WHEN 'name_fname_buffer' = ANY(bases)
             THEN array['name_fname_buffer', 'manual']
           WHEN 'descrip_fname_buffer' = ANY(bases)
             THEN array['descrip_fname_buffer', 'manual']
           WHEN 'comments_fname_buffer' = ANY(bases)
             THEN array['comments_fname_buffer', 'manual']

           ELSE
            array['unknown', 'manual']
           END
       )
       GROUP BY q.map_id
     ),

     -- Group all the previous matches, and select the top and bottom interval for each map_id
     match_summary AS (
       SELECT
         q.map_id,
         COALESCE(unit_ids.unit_ids, '{}') unit_ids,
         COALESCE(strat_name_ids.strat_name_ids, '{}') strat_name_ids,
         COALESCE(lith_ids.lith_ids, '{}') lith_ids,
         t_interval,
         b_interval
       FROM maps.%(scale)s q
       LEFT JOIN unit_ids ON q.map_id = unit_ids.map_id
       LEFT JOIN strat_name_ids ON q.map_id = strat_name_ids.map_id
       LEFT JOIN lith_ids ON q.map_id = lith_ids.map_id
       WHERE source_id = %(source_id)s
     ),

     -- Get the macrostrat ages for each map_id, if possible (i.e. if it has unit_id matches)
     macro_ages AS (
       SELECT
         map_id,
         unit_ids,
         strat_name_ids,
         lith_ids,
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
         unit_ids,
         strat_name_ids,
         lith_ids,

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
      JOIN macrostrat.intervals ti ON ti.id = t_interval
      JOIN macrostrat.intervals tb ON tb.id = b_interval
     )
     -- Assign a color for making tiles
     SELECT map_id,
      unit_ids,
      strat_name_ids,
      lith_ids,

      best_age_top,
      best_age_bottom,

      (SELECT interval_color
       FROM macrostrat.intervals
       WHERE age_top <= best_age_top AND age_bottom >= best_age_bottom
       ORDER BY age_bottom - age_top
       LIMIT 1
      ) AS color
      FROM best_times

    )
    """, {"scale": AsIs(scale), "source_id": source_id})
    connection.commit()

    cursor.execute("""
        DELETE FROM lookup_%(scale)s
        WHERE map_id IN (
            SELECT map_id FROM maps.%(scale)s
            WHERE name ILIKE 'water'
        );
    """)
    connection.commit()

def refresh_scale(cursor, connection, scale):
    print "--- Working on ", scale, " ---"
    source_ids = find_sources(cursor, scale)
    for idx, source in enumerate(source_ids):
        print "--- ", idx, " of ", len(source_ids), " ---"
        refresh(cursor, connection, scale, source)
