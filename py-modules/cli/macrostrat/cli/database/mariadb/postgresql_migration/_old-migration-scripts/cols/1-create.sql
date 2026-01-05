
CREATE TABLE macrostrat.cols_new (
  id integer PRIMARY KEY,
  col_group_id smallint,
  project_id smallint,
  col_type text,
  status_code character varying(25),
  col_position character varying(25),
  col numeric,
  col_name character varying(100),
  lat numeric,
  lng numeric,
  col_area numeric,
  coordinate geometry,
  wkt text,
  created text,
  poly_geom geometry,
  notes text
);
