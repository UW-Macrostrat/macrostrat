INSERT INTO macrostrat.measuremeta_new (
  id,
  sample_name,
  lat,
  lng,
  sample_geo_unit,
  sample_lith,
  lith_id,
  lith_att_id,
  age,
  early_id,
  late_id,
  sample_descrip,
  ref,
  ref_id
)
VALUES (
  %(id)s,
  %(sample_name)s,
  %(lat)s,
  %(lng)s,
  %(sample_geo_unit)s,
  %(sample_lith)s,
  %(lith_id)s,
  %(lith_att_id)s,
  %(age)s,
  %(early_id)s,
  %(late_id)s,
  %(sample_descrip)s,
  %(ref)s,
  %(ref_id)s
)

