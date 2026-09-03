
SELECT
  matrix.collection_no,
  collections.collection_name,
  matrix.early_age,
  matrix.late_age,
  strata.grp,
  strata.formation,
  strata.member,
  strata.lithology,
  matrix.environment,
  matrix.reference_no,
  matrix.n_occs,
  matrix.lng,
  matrix.lat
FROM pbdb.coll_matrix matrix
JOIN pbdb.coll_strata strata ON strata.collection_no = matrix.collection_no
JOIN pbdb.collections ON collections.collection_no = strata.collection_no
WHERE matrix.access_level = 0

