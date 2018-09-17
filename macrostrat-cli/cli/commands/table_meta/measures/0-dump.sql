-- This one is executed on MariaDB
SELECT
  id,
  measuremeta_id,
  measurement_id,
  sample_no,
  measure_phase,
  method,
  units,
  measure_value,
  v_error,
  v_error_units,
  v_type,
  v_n
FROM measures;
