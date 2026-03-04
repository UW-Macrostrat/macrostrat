CREATE EXTENSION IF NOT EXISTS postgres_fdw;
DROP FOREIGN TABLE IF EXISTS public.lookup_large;
DROP FOREIGN TABLE IF EXISTS public.lookup_medium;
DROP FOREIGN TABLE IF EXISTS public.lookup_small;
DROP FOREIGN TABLE IF EXISTS public.lookup_tiny;
DROP FOREIGN TABLE IF EXISTS public.intervals;
DROP FOREIGN TABLE IF EXISTS public.lookup_strat_names;
DROP SERVER IF EXISTS macrostrat CASCADE;
DROP USER MAPPING IF EXISTS FOR rockd SERVER macrostrat;


CREATE SERVER macrostrat
FOREIGN DATA WRAPPER postgres_fdw
OPTIONS (
  host '{fdw_host}',
  dbname 'macrostrat',
  port '5432'
);

CREATE USER MAPPING FOR rockd
SERVER macrostrat
OPTIONS (
  user '{fdw_user}',
  password '{fdw_password}'
);


CREATE FOREIGN TABLE public.lookup_strat_names (
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
)
SERVER macrostrat
OPTIONS (schema_name 'macrostrat', table_name 'lookup_strat_names');

CREATE FOREIGN TABLE public.intervals (
  id integer NOT NULL,
  age_bottom numeric,
  age_top numeric,
  interval_name character varying(200),
  interval_abbrev character varying(50),
  interval_type character varying(50),
  interval_color character varying(20),
  rank integer
)
SERVER macrostrat
OPTIONS (schema_name 'macrostrat', table_name 'intervals');

CREATE FOREIGN TABLE public.lookup_tiny (
  map_id integer,
  unit_ids integer[],
  strat_name_ids integer[],
  lith_ids integer[],
  best_age_top numeric,
  best_age_bottom numeric,
  color character varying(20)
)
SERVER macrostrat
OPTIONS (schema_name 'public', table_name 'lookup_tiny');

CREATE FOREIGN TABLE public.lookup_small (
  map_id integer,
  unit_ids integer[],
  strat_name_ids integer[],
  lith_ids integer[],
  best_age_top numeric,
  best_age_bottom numeric,
  color character varying(20)
)
SERVER macrostrat
OPTIONS (schema_name 'public', table_name 'lookup_small');

CREATE FOREIGN TABLE public.lookup_medium (
  map_id integer,
  unit_ids integer[],
  strat_name_ids integer[],
  lith_ids integer[],
  best_age_top numeric,
  best_age_bottom numeric,
  color character varying(20)
)
SERVER macrostrat
OPTIONS (schema_name 'public', table_name 'lookup_medium');

CREATE FOREIGN TABLE public.lookup_large (
  map_id integer,
  unit_ids integer[],
  strat_name_ids integer[],
  lith_ids integer[],
  best_age_top numeric,
  best_age_bottom numeric,
  color character varying(20)
)
SERVER macrostrat
OPTIONS (schema_name 'public', table_name 'lookup_large');