
CREATE TABLE macrostrat.strat_names_new (
  id serial PRIMARY KEY NOT NULL,
  strat_name character varying(100) NOT NULL,
  rank character varying(50),
  ref_id  integer NOT NULL,
  concept_id integer
)

