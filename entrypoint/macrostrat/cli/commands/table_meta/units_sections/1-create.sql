
CREATE TABLE macrostrat.units_sections_new (
  id serial PRIMARY KEY NOT NULL,
  unit_id integer NOT NULL,
  section_id integer NOT NULL,
  col_id integer NOT NULL
);

