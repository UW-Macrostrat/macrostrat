CREATE TABLE macrostrat.measures_new (
  id serial,
  measuremeta_id integer NOT NULL REFERENCES macrostrat.measuremeta(id),
  measurement_id integer NOT NULL REFERENCES macrostrat.measurements(id),
  sample_no varchar(50),
  measure_phase varchar(100) NOT NULL,
  method varchar(100) NOT NULL,
  units varchar(25) NOT NULL,
  measure_value decimal(10,5),
  v_error decimal(10,5),
  v_error_units varchar(25),
  v_type varchar(100),
  v_n integer
)
