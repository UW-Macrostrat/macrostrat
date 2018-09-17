CREATE TABLE macrostrat.measuremeta_new (
  id serial PRIMARY KEY,
  sample_name text NOT NULL,
  lat decimal(8,5),
  lng decimal(8,5),
  sample_geo_unit text NOT NULL,
  sample_lith text,
  lith_id integer NOT NULL,
  lith_att_id bigint NOT NULL,
  age text NOT NULL,
  early_id bigint NOT NULL,
  late_id bigint NOT NULL,
  sample_descrip text,
  ref text NOT NULL,
  ref_id bigint NOT NULL
)
