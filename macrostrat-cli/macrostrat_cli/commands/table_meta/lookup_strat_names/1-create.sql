
CREATE TABLE macrostrat.lookup_strat_names_new (
  strat_name_id integer,
  strat_name character varying(100),
  rank character varying(20),
  concept_id integer,
  rank_name character varying(200),
  bed_id integer,
  bed_name character varying(100),
  mbr_id integer,
  mbr_name character varying(100),
  fm_id integer,
  fm_name character varying(100),
  gp_id integer,
  gp_name character varying(100),
  sgp_id integer,
  sgp_name character varying(100),
  early_age numeric,
  late_age numeric,
  gsc_lexicon character varying(20),
  b_period character varying(100),
  t_period character varying(100),
  c_interval character varying(100),
  name_no_lith character varying(100)
);

