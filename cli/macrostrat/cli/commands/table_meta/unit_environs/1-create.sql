
CREATE TABLE macrostrat.unit_environs_new (
  id integer NOT NULL PRIMARY KEY,
  unit_id integer,
  environ_id integer,
  ref_id integer,
  date_mod text
);

