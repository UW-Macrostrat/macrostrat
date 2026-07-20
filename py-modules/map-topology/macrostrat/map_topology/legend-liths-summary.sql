/** View to summarize lithologies in a single array for each legend item */
CREATE OR REPLACE VIEW maps.legend_liths_summary AS
WITH a AS (SELECT * FROM maps.legend_liths ll
                           JOIN macrostrat.liths l ON ll.lith_id = l.id
), b AS (SELECT legend_id, a.lith::text, lith_id
         FROM a
         UNION ALL
         SELECT legend_id, lith_group::text, lith_id
         FROM a
         WHERE lith_group IS NOT NULL
         UNION ALL
         SELECT legend_id, lith_type::text, lith_id
         FROM a
         UNION ALL
         SELECT legend_id, lith_class::text, lith_id
         FROM a
)
SELECT legend_id, array_agg(distinct lith) liths, array_agg(distinct lith_id) lith_ids FROM b
GROUP BY legend_id;
