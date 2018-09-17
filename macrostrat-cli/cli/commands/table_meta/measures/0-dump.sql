-- This one is executed on MariaDB
SELECT
  id,
  measuremeta_id,
  measurement_id,
  -- We had a problem with NUL characters in this column
  replace(sample_no, CHAR(0x00 using utf8), "") sample_no,
  measure_phase,
  method,
  units,
  measure_value,
  v_error,
  v_error_units,
  v_type,
  v_n
FROM measures;
