
CREATE TABLE macrostrat.unit_liths_new (
  id integer NOT NULL PRIMARY KEY,
  lith_id integer,
  unit_id integer,
  prop text,
  dom text,
  comp_prop numeric,
  mod_prop numeric,
  toc numeric,
  ref_id integer,
  date_mod text
);

