
CREATE TABLE macrostrat.units_new (
  id integer PRIMARY KEY,
  strat_name character varying(150),
  color character varying(20),
  outcrop character varying(20),
  FO integer,
  FO_h integer,
  LO integer,
  LO_h integer,
  position_bottom numeric,
  position_top numeric,
  max_thick numeric,
  min_thick numeric,
  section_id integer,
  col_id integer,
  notes text
);

