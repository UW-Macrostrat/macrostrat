

/** Entities that can be used to filter columns */
CREATE VIEW macrostrat_api.col_filter AS
SELECT row_number() AS id,
       combined.name,
       combined.color,
       combined.lex_id,
       combined.type
FROM ( SELECT liths.lith AS name,
              liths.lith_color AS color,
              liths.id AS lex_id,
              'lithology'::text AS type
       FROM macrostrat.liths
       UNION ALL
       SELECT strat_names.strat_name AS name,
              NULL::character varying AS color,
              strat_names.id AS lex_id,
              'strat name'::text AS type
       FROM macrostrat.strat_names
       UNION ALL
       SELECT intervals.interval_name AS name,
              intervals.interval_color AS color,
              intervals.id AS lex_id,
              'interval'::text AS type
       FROM macrostrat.intervals
       UNION ALL
       SELECT units.strat_name AS name,
              NULL::character varying AS color,
              units.id AS lex_id,
              'unit'::text AS type
       FROM macrostrat.units) combined;
