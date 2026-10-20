"""Refresh the derived lookup tables for the units an ingest writes.

The v2 API (and so the website) reads a unit's lithologies and environments from
`lookup_unit_attrs_api`, and its ages, interval names and colour from `lookup_units`.
Both are otherwise only built by `macrostrat rebuild lookup-unit-attrs-api` and
`macrostrat rebuild lookup-units`, which recreate the whole tables. These statements
follow those scripts' SQL, limited to a set of units, so an ingested column displays
straight away.

One deliberate difference: the rebuild first overwrites `unit_liths.comp_prop` with a
fixed 5:1 dominant/subordinate weighting. That step is skipped here, so the lookup
carries the proportions the ingester wrote (stated ones kept, the rest shared).
"""

from __future__ import annotations

from collections.abc import Iterable

_UNITS = "CAST(:unit_ids AS integer[])"

_ATTRS_API = f"""
INSERT INTO macrostrat.lookup_unit_attrs_api
  (unit_id, lith, environ, econ, measure_short, measure_long)
SELECT
  u.id,
  coalesce((
    SELECT json_agg(json_build_object(
      'lith_id', ul.lith_id,
      'name', l.lith,
      'type', l.lith_type,
      'class', l.lith_class,
      'prop', ul.comp_prop,
      'atts', to_json(array_remove(array(
        SELECT la.lith_att
        FROM macrostrat.unit_liths_atts ula
        JOIN macrostrat.lith_atts la ON la.id = ula.lith_att_id
        WHERE ula.unit_lith_id = ul.id
      ), NULL))
    ))
    FROM macrostrat.unit_liths ul
    LEFT JOIN macrostrat.liths l ON l.id = ul.lith_id
    WHERE ul.unit_id = u.id
  ), '[]'::json)::text::bytea,
  coalesce((
    SELECT json_agg(json_build_object(
      'environ_id', ue.environ_id,
      'name', e.environ,
      'type', e.environ_type,
      'class', e.environ_class
    ))
    FROM macrostrat.unit_environs ue
    LEFT JOIN macrostrat.environs e ON e.id = ue.environ_id
    WHERE ue.unit_id = u.id
  ), '[]'::json)::text::bytea,
  coalesce((
    SELECT json_agg(json_build_object(
      'econ_id', uc.econ_id,
      'name', c.econ,
      'type', c.econ_type,
      'class', c.econ_class
    ))
    FROM macrostrat.unit_econs uc
    LEFT JOIN macrostrat.econs c ON c.id = uc.econ_id
    WHERE uc.unit_id = u.id
  ), '[]'::json)::text::bytea,
  coalesce((
    SELECT json_agg(json_build_object(
      'measure_class', m.measurement_class,
      'measure_type', m.measurement_type
    ))
    FROM macrostrat.unit_measures um
    JOIN macrostrat.measuremeta mm ON mm.id = um.measuremeta_id
    JOIN macrostrat.measures ms ON ms.measuremeta_id = mm.id
    JOIN macrostrat.measurements m ON m.id = ms.measurement_id
    WHERE um.unit_id = u.id
  ), '[]'::json)::text::bytea,
  coalesce((
    SELECT json_agg(json_build_object(
      'measure_id', a.measure_id,
      'measure', a.measure,
      'mean', a.mean,
      'stddev', a.stddev,
      'n', a.n,
      'unit', a.units
    ))
    FROM (
      SELECT m.id AS measure_id, m.measurement AS measure,
        round(avg(ms.measure_value), 5) AS mean,
        round(stddev(ms.measure_value), 5) AS stddev,
        count(um.id) AS n,
        ms.units
      FROM macrostrat.unit_measures um
      JOIN macrostrat.measuremeta mm ON mm.id = um.measuremeta_id
      JOIN macrostrat.measures ms ON ms.measuremeta_id = mm.id
      JOIN macrostrat.measurements m ON m.id = ms.measurement_id
      WHERE um.unit_id = u.id
      GROUP BY m.id, m.measurement, ms.units
    ) a
  ), '[]'::json)::text::bytea
FROM macrostrat.units u
WHERE u.id = ANY({_UNITS})
"""

_LOOKUP_UNITS = f"""
WITH top_bound AS (
  SELECT DISTINCT ON (unit_id) unit_id, t1, t1_age, t1_prop, paleo_lat, paleo_lng
  FROM macrostrat.unit_boundaries
  WHERE t1 IS NOT NULL AND unit_id = ANY({_UNITS})
  ORDER BY unit_id, t1_age ASC
),
bottom_bound AS (
  SELECT DISTINCT ON (unit_id_2) unit_id_2, t1, t1_age, t1_prop, paleo_lat, paleo_lng
  FROM macrostrat.unit_boundaries
  WHERE t1 IS NOT NULL AND unit_id_2 = ANY({_UNITS})
  ORDER BY unit_id_2, t1_age DESC
),
units_ext AS (
  SELECT units.id, tb.t1 t_int, tb.t1_age t_age, tb.t1_prop t_prop,
    tb.paleo_lat t_plat, tb.paleo_lng t_plng,
    bb.t1 b_int, bb.t1_age b_age, bb.t1_prop b_prop,
    bb.paleo_lat b_plat, bb.paleo_lng b_plng, units.color
  FROM macrostrat.units
  LEFT JOIN top_bound tb ON tb.unit_id = units.id
  LEFT JOIN bottom_bound bb ON bb.unit_id_2 = units.id
  WHERE units.id = ANY({_UNITS})
)
INSERT INTO macrostrat.lookup_units (unit_id, col_area, project_id, t_int, t_int_name,
  t_int_age, t_age, t_prop, t_plat, t_plng, b_int, b_int_name, b_int_age, b_age, b_prop,
  b_plat, b_plng, clat, clng, color, text_color, units_above, units_below,
  pbdb_collections, pbdb_occurrences)
SELECT
  units.id, coalesce(cols.col_area, 0), cols.project_id,
  t_int, tint.interval_name, tint.age_top, t_age, t_prop,
  coalesce(t_plat, 0), coalesce(t_plng, 0),
  b_int, bint.interval_name, bint.age_bottom, b_age, b_prop,
  coalesce(b_plat, 0), coalesce(b_plng, 0),
  cols.lat, cols.lng,
  coalesce(colors.unit_hex, '#888888'), coalesce(colors.text_hex, '#000000'),
  string_agg(DISTINCT ubt.unit_id_2::text, '|'),
  string_agg(DISTINCT ubb.unit_id::text, '|'),
  count(DISTINCT pbdb_matches.collection_no),
  coalesce(sum(pbdb_matches.occs), 0)
FROM units_ext units
LEFT JOIN macrostrat.intervals tint ON tint.id = units.t_int
LEFT JOIN macrostrat.intervals bint ON bint.id = units.b_int
LEFT JOIN macrostrat.colors ON units.color::text = colors.color::text
LEFT JOIN macrostrat.pbdb_matches ON pbdb_matches.unit_id = units.id
LEFT JOIN macrostrat.units_sections ON units.id = units_sections.unit_id
LEFT JOIN macrostrat.cols ON cols.id = units_sections.col_id
LEFT JOIN macrostrat.unit_boundaries ubb ON ubb.unit_id_2 = units.id
LEFT JOIN macrostrat.unit_boundaries ubt ON ubt.unit_id = units.id
GROUP BY units.id, cols.col_area, cols.project_id, t_int, tint.interval_name,
  tint.age_top, t_age, t_prop, t_plat, t_plng, b_int, bint.interval_name,
  bint.age_bottom, b_age, b_prop, b_plat, b_plng, cols.lat, cols.lng,
  colors.unit_hex, colors.text_hex
"""

# A top at the base of an interval reads as the top of the one before it, and a base at
# the top of an interval as the base of the one after (as in `lookup-units-01.sql`).
_EDGE_INTERVALS = [
    f"""
WITH prev_interval AS (
  SELECT DISTINCT i.id next_id, i1.interval_name, i1.id, i1.age_top
  FROM macrostrat.intervals i
  JOIN macrostrat.timescales_intervals ti ON i.id = ti.interval_id
  JOIN macrostrat.timescales_intervals ti1 ON ti.timescale_id = ti1.timescale_id
  JOIN macrostrat.intervals i1 ON i1.age_top = i.age_bottom AND i1.id = ti1.interval_id
)
UPDATE macrostrat.lookup_units lu
SET t_int = p.id, t_int_age = p.age_top, t_int_name = p.interval_name, t_prop = 1
FROM prev_interval p
WHERE lu.t_prop = 0 AND lu.t_int = p.next_id AND lu.unit_id = ANY({_UNITS})
""",
    f"""
WITH next_interval AS (
  SELECT DISTINCT i.id prev_id, i1.interval_name, i1.id, i1.age_bottom
  FROM macrostrat.intervals i
  JOIN macrostrat.timescales_intervals ti ON i.id = ti.interval_id
  JOIN macrostrat.timescales_intervals ti1 ON ti.timescale_id = ti1.timescale_id
  JOIN macrostrat.intervals i1 ON i1.age_bottom = i.age_top AND i1.id = ti1.interval_id
)
UPDATE macrostrat.lookup_units lu
SET b_int = n.id, b_int_age = n.age_bottom, b_int_name = n.interval_name, b_prop = 0
FROM next_interval n
WHERE lu.b_prop = 1 AND lu.b_int = n.prev_id AND lu.unit_id = ANY({_UNITS})
""",
]

#: The `lookup_units` name/id columns filled from each international timescale.
_TIME_RANGES = ("age", "epoch", "period", "era", "eon")


def _time_range_statements(field: str) -> list[str]:
    # Identifiers come from `_TIME_RANGES`, never from input
    return [
        f"""
WITH ints AS (
  SELECT i.id, interval_name, age_bottom, age_top
  FROM macrostrat.intervals i
  JOIN macrostrat.timescales_intervals ON i.id = interval_id
  JOIN macrostrat.timescales ON timescale_id = macrostrat.timescales.id
  WHERE timescale = 'international {field}s'
)
UPDATE macrostrat.lookup_units t SET {field} = i.interval_name, {field}_id = i.id
FROM ints i
WHERE t.b_age > i.age_top AND t.b_age <= i.age_bottom
  AND t.t_age < i.age_bottom AND t.t_age >= i.age_top
  AND t.unit_id = ANY({_UNITS})
""",
        f"""
UPDATE macrostrat.lookup_units SET {field}_id = 0, {field} = ''
WHERE {field}_id IS NULL AND unit_id = ANY({_UNITS})
""",
    ]


# As in `lookup-units-02.sql`: names for units that no single period contains
_PERIOD_FIXES = [
    f"""
UPDATE macrostrat.lookup_units SET period = eon
WHERE period = '' AND eon = 'Archean' AND unit_id = ANY({_UNITS})
""",
    f"""
UPDATE macrostrat.lookup_units SET period = 'Precambrian'
WHERE period = '' AND t_age >= 541 AND unit_id = ANY({_UNITS})
""",
    f"""
UPDATE macrostrat.lookup_units SET period = concat_ws('-', (
    SELECT intervals.interval_name FROM macrostrat.intervals
    JOIN macrostrat.timescales_intervals ON intervals.id = interval_id
    JOIN macrostrat.timescales ON timescale_id = timescales.id
    WHERE timescale = 'international periods'
      AND age_top <= (SELECT age_top FROM macrostrat.intervals WHERE id = b_int)
      AND age_bottom >= (SELECT age_bottom FROM macrostrat.intervals WHERE id = b_int)
  ), (
    SELECT intervals.interval_name FROM macrostrat.intervals
    JOIN macrostrat.timescales_intervals ON intervals.id = interval_id
    JOIN macrostrat.timescales ON timescale_id = timescales.id
    WHERE timescale = 'international periods'
      AND age_top <= (SELECT age_top FROM macrostrat.intervals WHERE id = t_int)
      AND age_bottom >= (SELECT age_bottom FROM macrostrat.intervals WHERE id = t_int)
  ))
WHERE period = '' AND unit_id = ANY({_UNITS})
""",
]


def group_unit_ids(db, col_group_id: int) -> set[int]:
    """The units currently in a column group's columns."""
    rows = db.run_query(
        "SELECT us.unit_id FROM macrostrat.units_sections us"
        " JOIN macrostrat.cols c ON c.id = us.col_id"
        " WHERE c.col_group_id = :col_group_id",
        dict(col_group_id=col_group_id),
    )
    return {row[0] for row in rows}


def refresh_unit_lookups(
    db, unit_ids: Iterable[int], *, removed: Iterable[int] = ()
) -> None:
    """Rebuild the lookup rows of `unit_ids`, and drop those of `removed` units."""
    unit_ids = sorted(set(unit_ids))
    stale = sorted(set(removed) | set(unit_ids))
    for table in ("lookup_unit_attrs_api", "lookup_units"):
        db.run_query(
            f"DELETE FROM macrostrat.{table} WHERE unit_id = ANY({_UNITS})",
            dict(unit_ids=stale),
        )
    if not unit_ids:
        return
    params = dict(unit_ids=unit_ids)
    statements = [_ATTRS_API, _LOOKUP_UNITS, *_EDGE_INTERVALS]
    for field in _TIME_RANGES:
        statements += _time_range_statements(field)
    statements += _PERIOD_FIXES
    for sql in statements:
        db.run_query(sql, params)
