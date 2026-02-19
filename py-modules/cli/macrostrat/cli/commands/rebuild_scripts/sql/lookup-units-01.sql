SET search_path = macrostrat, public;

DROP TABLE IF EXISTS lookup_units_new;
DROP TABLE IF EXISTS lookup_units_old;

CREATE TABLE lookup_units_new (LIKE lookup_units);

INSERT INTO lookup_units_new (unit_id, col_area, project_id, t_int, t_int_name, t_int_age, t_age, t_prop, t_plat, t_plng, b_int, b_int_name, b_int_age, b_age, b_prop, b_plat, b_plng, clat,  clng, color, text_color, units_above, units_below, pbdb_collections, pbdb_occurrences)
SELECT
  units.id AS unit_id,
  cols.col_area,
  cols.project_id,
  t_int,
  tint.interval_name AS t_int_name,
  tint.age_top AS t_int_age,
  t_age,
  t_prop,
  IFNULL(t_plat, '') AS t_plat,
  IFNULL(t_plng, '') AS t_plng,
  b_int,
  bint.interval_name AS b_int_name,
  bint.age_bottom AS b_int_age,
  b_age,
  b_prop,
  IFNULL(b_plat, '') AS b_plat,
  IFNULL(b_plng, '') AS b_plng,
  cols.lat AS clat,
  cols.lng AS clng,
  colors.unit_hex AS color,
  colors.text_hex AS text_color,
  GROUP_CONCAT(distinct ubt.unit_id_2 SEPARATOR '|') AS units_above,
  GROUP_CONCAT(distinct ubb.unit_id SEPARATOR '|') AS units_below,
  COUNT(DISTINCT pbdb_matches.collection_no) AS pbdb_collections,
  SUM(pbdb_matches.occs) AS pbdb_occurrences
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
  GROUP BY units.id
) units
LEFT JOIN intervals tint ON tint.id = units.t_int
LEFT JOIN intervals bint ON bint.id = units.b_int
LEFT JOIN colors ON units.color = colors.color
LEFT JOIN pbdb_matches ON pbdb_matches.unit_id = units.id
LEFT JOIN units_sections ON units.id = units_sections.unit_id
LEFT JOIN cols ON cols.id = units_sections.col_id
LEFT JOIN unit_boundaries ubb ON ubb.unit_id_2 = units.id
LEFT JOIN unit_boundaries ubt ON ubt.unit_id = units.id
GROUP BY units.id;
