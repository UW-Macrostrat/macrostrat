INSERT INTO macrostrat.measures_new (
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
)
VALUES (
  %(id)s,
  %(measuremeta_id)s,
  %(measurement_id)s,
  %(sample_no)s,
  %(measure_phase)s,
  %(method)s,
  %(units)s,
  %(measure_value)s,
  %(v_error)s,
  %(v_error_units)s,
  %(v_type)s,
  %(v_n)s
)

