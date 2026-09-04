
CREATE TABLE macrostrat.intervals_new (
  id serial NOT NULL,
  age_bottom numeric,
  age_top numeric,
  interval_name character varying(200),
  interval_abbrev character varying(50),
  interval_type character varying(50),
  interval_color character varying(20),
  rank integer DEFAULT NULL
);

