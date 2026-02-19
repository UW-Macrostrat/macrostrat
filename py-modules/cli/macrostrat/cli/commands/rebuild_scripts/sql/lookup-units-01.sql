SET search_path = macrostrat, public;

DROP TABLE IF EXISTS lookup_units_new;
DROP TABLE IF EXISTS lookup_units_old;

CREATE TABLE lookup_units_new (LIKE lookup_units);

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
FROM (
  SELECT
    units.id,
    (
      SELECT t1
      FROM unit_boundaries
      WHERE unit_id = units.id
      ORDER BY t1_age asc
      LIMIT 1
    ) t_int,
    (
      SELECT t1_age
      FROM unit_boundaries
      WHERE unit_id = units.id
      ORDER BY t1_age asc
      LIMIT 1
    ) t_age,
    (
      SELECT t1_prop
      FROM unit_boundaries
      WHERE unit_id = units.id
      ORDER BY t1_age asc
      LIMIT 1
    ) t_prop,
    (
      SELECT paleo_lat
      FROM unit_boundaries
      WHERE unit_id = units.id
      ORDER BY t1_age asc
      LIMIT 1
    ) t_plat,
    (
      SELECT paleo_lng
      FROM unit_boundaries
      WHERE unit_id = units.id
      ORDER BY t1_age asc
      LIMIT 1
    ) t_plng,
    (
      SELECT t1
      FROM unit_boundaries
      WHERE unit_id_2 = units.id
      ORDER BY t1_age desc
      LIMIT 1
    ) b_int,
    (
      SELECT t1_age
      FROM unit_boundaries
      WHERE unit_id_2 = units.id
      ORDER BY t1_age desc
      LIMIT 1
    ) b_age,
    (
      SELECT t1_prop
      FROM unit_boundaries
      WHERE unit_id_2 = units.id
      ORDER BY t1_age desc
      LIMIT 1
    ) b_prop,
    (
      SELECT paleo_lat
      FROM unit_boundaries
      WHERE unit_id_2 = units.id
      ORDER BY t1_age desc
      LIMIT 1
    ) b_plat,
    (
      SELECT paleo_lng
      FROM unit_boundaries
      WHERE unit_id_2 = units.id
      ORDER BY t1_age desc
      LIMIT 1
    ) b_plng,
    units.color
  FROM units
  GROUP BY
    units.id
) units
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
