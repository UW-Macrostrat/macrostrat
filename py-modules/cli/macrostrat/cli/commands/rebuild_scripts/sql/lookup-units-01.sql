SET search_path = macrostrat, public;

DROP TABLE IF EXISTS lookup_units_new;
DROP TABLE IF EXISTS lookup_units_old;

CREATE TABLE lookup_units_new (LIKE lookup_units);

WITH top_bound AS (
  SELECT DISTINCT ON (unit_id) unit_id, t1, t1_age, t1_prop, paleo_lat, paleo_lng
  FROM unit_boundaries
  WHERE t1 IS NOT NULL
  ORDER BY unit_id, t1_age ASC
),
bottom_bound AS (
  SELECT DISTINCT ON (unit_id_2) unit_id_2, t1, t1_age, t1_prop, paleo_lat, paleo_lng
  FROM unit_boundaries
  WHERE t1 IS NOT NULL
  ORDER BY unit_id_2, t1_age DESC
),
units_ext AS (
  SELECT
    units.id,
    tb.t1 t_int,
    tb.t1_age t_age,
    tb.t1_prop t_prop,
    tb.paleo_lat t_plat,
    tb.paleo_lng t_plng,
    bb.t1 b_int,
    bb.t1_age b_age,
    bb.t1_prop b_prop,
    bb.paleo_lat b_plat,
    bb.paleo_lng b_plng,
    units.color
  FROM units
  LEFT JOIN top_bound tb ON tb.unit_id = units.id
  LEFT JOIN bottom_bound bb ON bb.unit_id_2 = units.id
)
INSERT INTO lookup_units_new (unit_id, col_area, project_id, t_int, t_int_name, t_int_age, t_age, t_prop, t_plat, t_plng, b_int, b_int_name, b_int_age, b_age, b_prop, b_plat, b_plng, clat,  clng, color, text_color, units_above, units_below, pbdb_collections, pbdb_occurrences)
SELECT
  units.id AS unit_id,
  coalesce(cols.col_area, 0) col_area,
  cols.project_id,
  t_int,
  tint.interval_name AS t_int_name,
  tint.age_top AS t_int_age,
  t_age,
  t_prop,
  /** Note: t_plat, t_plng, b_plat, and b_plng were all constructed with
    ifnull(<col>, '') in MariaDB, which does not work in PostgreSQL
    because the column type is numeric. If we want to have the old handling
    (empty strings instead of nulls) we will have to make the column type text,
    however, using nulls specifically is better anyway.
   */
  t_plat,
  t_plng,
  b_int,
  bint.interval_name AS b_int_name,
  bint.age_bottom AS b_int_age,
  b_age,
  b_prop,
  b_plat,
  b_plng,
  cols.lat AS clat,
  cols.lng AS clng,
  coalesce(colors.unit_hex, '#888888') AS color,
  coalesce(colors.text_hex, '#000000') text_color,
  string_agg(distinct ubt.unit_id_2::text, '|') AS units_above,
  string_agg(distinct ubb.unit_id::text, '|') AS units_below,
  COUNT(DISTINCT pbdb_matches.collection_no) AS pbdb_collections,
  coalesce(SUM(pbdb_matches.occs), 0) AS pbdb_occurrences
FROM units_ext units
LEFT JOIN intervals tint ON tint.id = units.t_int
LEFT JOIN intervals bint ON bint.id = units.b_int
LEFT JOIN colors ON units.color::text = colors.color::text
LEFT JOIN pbdb_matches ON pbdb_matches.unit_id = units.id
-- Had to convert units_sections and cols joins from left joins
JOIN units_sections ON units.id = units_sections.unit_id
JOIN cols ON cols.id = units_sections.col_id
LEFT JOIN unit_boundaries ubb ON ubb.unit_id_2 = units.id
LEFT JOIN unit_boundaries ubt ON ubt.unit_id = units.id
GROUP BY units.id,
  cols.col_area,
  cols.project_id,
  t_int,
  tint.interval_name,
  tint.age_top,
  t_age,
  t_prop,
  t_plat,
  t_plng,
  b_int,
  bint.interval_name,
  bint.age_bottom,
  b_age,
  b_prop,
  b_plat,
  b_plng,
  cols.lat,
  cols.lng,
  colors.unit_hex,
  colors.text_hex;
