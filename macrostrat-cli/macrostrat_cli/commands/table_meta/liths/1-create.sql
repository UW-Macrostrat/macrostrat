
CREATE TABLE macrostrat.liths_new (
  id integer PRIMARY KEY NOT NULL,
  lith character varying(75),
  lith_group text,
  lith_type character varying(50),
  lith_class character varying(50),
  lith_equiv integer,
  lith_fill integer,
  comp_coef numeric,
  initial_porosity numeric,
  bulk_density numeric,
  lith_color character varying(12)
);

