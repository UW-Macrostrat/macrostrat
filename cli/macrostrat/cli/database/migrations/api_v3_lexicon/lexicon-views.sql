/** Entities that can be used to filter columns */
CREATE OR REPLACE VIEW macrostrat_api.col_filter AS
SELECT
  concat('lith:', l.id::text) AS uid,
  l.lith AS name,
  l.lith_color AS color,
  l.id AS lex_id,
  'lithology'::text AS type
FROM macrostrat.liths l
UNION ALL
SELECT
  concat('int:', i.id::text) AS uid,
  i.interval_name AS name,
  i.interval_color AS color,
  i.id AS lex_id,
  'interval'::text AS type
FROM macrostrat.intervals i
UNION ALL
SELECT
  concat('env:', e.id::text) AS uid,
  e.environ AS name,
  e.environ_color AS color,
  e.id AS lex_id,
  'environment'::text AS type
FROM macrostrat.environs e
UNION ALL
SELECT
  concat('concept:', c.concept_id::text) AS uid,
  c.name AS name,
  NULL::character varying AS color,
  c.concept_id AS lex_id,
  'concept'::text AS type
FROM macrostrat.strat_names_meta c
UNION ALL
SELECT
  concat('strat_name:', sn.id::text) AS uid,
  sn.strat_name AS name,
  NULL::character varying AS color,
  sn.id AS lex_id,
  'strat name'::text AS type
FROM macrostrat.strat_names sn;
