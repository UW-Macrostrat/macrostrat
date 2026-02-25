set SEARCH_PATH to macrostrat;

UPDATE unit_boundaries ub
SET t1_age = i.age_bottom - ((i.age_bottom - i.age_top) * ub.t1_prop)
FROM intervals i
WHERE ub.t1 = i.id
  AND ub.boundary_status != 'absolute';

UPDATE unit_boundaries_scratch ub
SET t1_age = i.age_bottom - ((i.age_bottom - i.age_top) * ub.t1_prop)
FROM intervals i
WHERE ub.t1 = i.id
  AND ub.boundary_status != 'absolute';

UPDATE unit_boundaries ub
SET t1_prop = (i.age_bottom - ub.t1_age) / (i.age_bottom - i.age_top)
FROM intervals i
WHERE ub.t1 = i.id
  AND ub.boundary_status = 'absolute';

UPDATE unit_boundaries_scratch ub
SET t1_prop = (i.age_bottom - ub.t1_age) / (i.age_bottom - i.age_top)
FROM intervals i
WHERE ub.t1 = i.id
  AND ub.boundary_status = 'absolute';

