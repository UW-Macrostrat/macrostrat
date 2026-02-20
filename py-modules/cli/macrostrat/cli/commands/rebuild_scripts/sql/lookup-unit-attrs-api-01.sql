SET SEARCH_PATH TO macrostrat, public;

DROP TABLE IF EXISTS macrostrat.lookup_unit_attrs_api_new;
DROP TABLE IF EXISTS macrostrat.lookup_unit_attrs_api_old;
CREATE TABLE macrostrat.lookup_unit_attrs_api_new (
  LIKE lookup_unit_attrs_api
);

/** Note: these comp_prop calculations are as follows:
  - For dominant liths, the comp_prop is 5 / (5 * number of dominant liths + number of subordinate liths)
  - For subordinate liths, the comp_prop is 1 / (5 * number of dominant liths + number of subordinate liths)
  - If there are no dominant liths, then the comp_prop for all liths is 1 / number of subordinate liths

  Basically, dominant props are weighted higher than subordinate liths by a factor of 5

  Note: these calculations don't appear to work correctly right now...
*/

WITH
  a AS (
    SELECT unit_id,
      count(id) adom,
      'dom' AS dom
    FROM unit_liths
    WHERE dom = 'dom'
    GROUP BY unit_id
  ),
  b AS (
    SELECT unit_id,
      count(id) bdom,
      'sub' AS dom
    FROM unit_liths
    WHERE dom = 'sub'
    GROUP BY unit_id
  ),
  d AS (
    SELECT a.unit_id,
      (5 / (coalesce(bdom, 0) + (adom * 5))) AS dom_p
    FROM a
    LEFT JOIN b ON b.unit_id = a.unit_id
  )
UPDATE unit_liths ul
SET comp_prop = d.dom_p
FROM d
WHERE d.unit_id = ul.unit_id
  AND 'dom' = ul.dom;

/** Lithologies */

WITH
  a AS (
    SELECT unit_id,
      count(id) adom,
      'dom' AS dom
    FROM unit_liths
    WHERE dom = 'dom'
    GROUP BY unit_id
  ),
  b AS (
    SELECT unit_id,
      count(id) bdom,
      'sub' AS dom
    FROM unit_liths
    WHERE dom = 'sub'
    GROUP BY unit_id
  ),
  s AS (
    SELECT a.unit_id,
      (1 / (coalesce(bdom, 0) + (adom * 5))) AS sub_p
    FROM a
    LEFT JOIN b ON b.unit_id = a.unit_id
  )
UPDATE unit_liths ul
SET comp_prop = s.sub_p
FROM s
WHERE s.unit_id = ul.unit_id
  AND 'sub' = ul.dom;

WITH
  a AS (
    SELECT unit_liths.unit_id,
      json_build_object(
        'lith_id', lith_id,
        'name', lith,
        'type', lith_type,
        'class', lith_class,
        'prop', comp_prop,
        'atts', to_json(array_remove(array_agg(lith_atts.lith_att), NULL))
      ) AS lith
    FROM units
    LEFT JOIN unit_liths ON units.id = unit_liths.unit_id
    LEFT JOIN liths ON lith_id = liths.id
    LEFT JOIN unit_liths_atts ON unit_liths.id = unit_liths_atts.unit_lith_id
    LEFT JOIN lith_atts ON unit_liths_atts.lith_att_id = lith_atts.id
    GROUP BY unit_liths.id, liths.id, liths.lith, lith_type, lith_class, comp_prop
  )
INSERT
INTO macrostrat.lookup_unit_attrs_api_new (unit_id, lith)
-- We keep this in text format for now for parallelism with v1, but we should consider
-- changing this to JSONB in the future
SELECT unit_id, json_agg(lith)::text::bytea
FROM a
GROUP BY unit_id;


/** Environments */
WITH
  unit_envs AS (
    SELECT unit_id,
      json_build_object(
        'environ_id', environ_id,
        'name', environ,
        'type', environ_type,
        'class', environ_class
      ) AS environ
      FROM unit_environs
      LEFT JOIN environs ON environ_id = environs.id
  ),
  agg_envs AS (
    SELECT unit_id, json_agg(environ) AS envs
    FROM unit_envs
    GROUP BY unit_id
  )
UPDATE macrostrat.lookup_unit_attrs_api_new lu
SET environ = agg_envs.envs::text::bytea
FROM agg_envs
WHERE lu.unit_id = agg_envs.unit_id;

-- Set rows with null environments to empty arrays for consistency with v1 structure.
UPDATE macrostrat.lookup_unit_attrs_api_new
SET environ = '[]'::bytea
WHERE environ IS NULL;

/** Econs */
SELECT unit_id, econ_id, econ, econ_type, econ_class
FROM unit_econs
LEFT JOIN econs ON econ_id = econs.id;

WITH
  unit_econs1 AS (
    SELECT unit_id,
      json_build_object(
        'econ_id', econ_id,
        'name', econ,
        'type', econ_type,
        'class', econ_class
      ) AS econ
      FROM unit_econs
      LEFT JOIN econs ON econ_id = econs.id
  ),
  agg_econs AS (
    SELECT unit_id, json_agg(econ) AS econs
    FROM unit_econs1
    GROUP BY unit_id
  )
UPDATE macrostrat.lookup_unit_attrs_api_new lu
SET econ = agg_econs.econs::text::bytea
FROM agg_econs
WHERE lu.unit_id = agg_econs.unit_id;

-- Set rows with null econs to empty arrays for consistency with v1 structure.
UPDATE macrostrat.lookup_unit_attrs_api_new
SET econ = '[]'::bytea
WHERE econ IS NULL;

/** Measurements short */
WITH a AS (
  SELECT
    unit_id,
    json_build_object(
      'measure_class', measurement_class,
      'measure_type', measurement_type
    ) measure_short
  FROM measurements
  JOIN measures ON measures.measurement_id = measurements.id
  JOIN measuremeta ON measures.measuremeta_id = measuremeta.id
  JOIN unit_measures ON measuremeta.id = unit_measures.measuremeta_id
),
agg_measures AS (
  SELECT unit_id, json_agg(measure_short) AS measure_short
  FROM a
  GROUP BY unit_id
)
UPDATE macrostrat.lookup_unit_attrs_api_new lu
SET measure_short = a.measure_short::text::bytea
FROM agg_measures a
WHERE lu.unit_id = a.unit_id;

UPDATE macrostrat.lookup_unit_attrs_api_new
SET measure_short = '[]'::bytea
WHERE measure_short IS NULL;

/** Measurements long */

WITH a AS (
  SELECT
    unit_measures.unit_id,
    measurements.id AS measure_id,
    measurement_class AS measure_class,
    measurement_type AS measure_type,
    measurement AS measure,
    round(avg(measure_value), 5) AS mean,
    round(stddev(measure_value), 5) AS stddev,
    count(unit_measures.id) AS n,
    units
  FROM measures
  JOIN measurements ON measures.measurement_id = measurements.id
  JOIN measuremeta ON measures.measuremeta_id = measuremeta.id
  JOIN unit_measures ON measuremeta.id = unit_measures.measuremeta_id
  -- Apparently there are unit measures with unit_id = 0. We filter those out here (new in v2)
  WHERE unit_measures.unit_id != 0
  GROUP BY unit_measures.unit_id, measurements.id, measurement_class, measurement_type, measurement, units
),
b AS (
  SELECT unit_id,
    json_build_object(
      'measure_id', measure_id,
      -- These class/type fields aren't included in v1 even though they could be (to extend measure_short effectively)
      -- 'measure_class', measure_class,
      -- 'measure_type', measure_type,
      'measure', measure,
      'mean', mean,
      'stddev', stddev,
      'n', n,
      'unit', units
    ) AS measure_long
  FROM a
),
agg_measures AS (
  SELECT unit_id, json_agg(measure_long) AS measure_long
  FROM b
  GROUP BY unit_id
)
UPDATE macrostrat.lookup_unit_attrs_api_new lu
SET measure_long = agg_measures.measure_long::text::bytea
FROM agg_measures
WHERE lu.unit_id = agg_measures.unit_id;

UPDATE macrostrat.lookup_unit_attrs_api_new
SET measure_long = '[]'::bytea
WHERE measure_long IS NULL;
