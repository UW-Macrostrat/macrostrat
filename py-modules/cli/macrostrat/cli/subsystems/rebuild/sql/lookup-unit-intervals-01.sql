SET SEARCH_PATH to macrostrat;

DROP TABLE IF EXISTS lookup_unit_intervals_new;
DROP TABLE IF EXISTS lookup_unit_intervals_old;

CREATE TABLE lookup_unit_intervals_new (LIKE lookup_unit_intervals);

/** We restructure the query to work in bulk */
INSERT INTO lookup_unit_intervals_new (
  unit_id,
  fo_age, -- fo.age_bottom
  b_age,
  fo_interval, --fname
  lo_age, -- lo.age_top
  t_age,
  lo_interval, --lname
  -- uninitaialized
  epoch,
  epoch_id,
  period,
  period_id,
  age,
  age_id,
  era,
  era_id,
  eon,
  eon_id,
  fo_period,
  lo_period
)
SELECT
  u.id unit_id,
  fo.age_bottom, -- lower interval max age
  max(u2.t1_age) AS b_age,
  fo.interval_name fname,
  lo.age_top, -- upper interval min age
  min(u1.t1_age) AS t_age,
  lo.interval_name lname,
  -- uninitialized
  '' epoch,
  0 epoch_id,
  '' period,
  0 period_id,
  '' age,
  0 age_id,
  '' era,
  0 era_id,
  '' eon,
  0 eon_id,
  '' fo_period,
  '' lo_period
FROM units u
JOIN intervals fo on u.fo = fo.id
JOIN intervals lo ON u.lo = lo.id
LEFT JOIN unit_boundaries u1 ON u1.unit_id = u.id
LEFT JOIN unit_boundaries u2 ON u2.unit_id_2 = u.id
GROUP BY u.id, fo.age_bottom, fo.interval_name, lo.age_top, lo.interval_name;
