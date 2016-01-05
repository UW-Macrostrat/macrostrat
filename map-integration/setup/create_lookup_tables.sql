DROP TABLE IF EXISTS public.lookup_tiny;
DROP TABLE IF EXISTS public.lookup_small;
DROP TABLE IF EXISTS public.lookup_medium;
DROP TABLE IF EXISTS public.lookup_large;

CREATE TABLE public.lookup_tiny (
  map_id integer,
  unit_ids integer[],
  strat_name_ids integer[],
  lith_ids integer[],
  best_age_top numeric,
  best_age_bottom numeric,
  color character varying(20)
);

CREATE INDEX ON public.lookup_tiny (map_id);

CREATE TABLE public.lookup_small (
  map_id integer,
  unit_ids integer[],
  strat_name_ids integer[],
  lith_ids integer[],
  best_age_top numeric,
  best_age_bottom numeric,
  color character varying(20)
);

CREATE INDEX ON public.lookup_small (map_id);

CREATE TABLE public.lookup_medium (
  map_id integer,
  unit_ids integer[],
  strat_name_ids integer[],
  lith_ids integer[],
  best_age_top numeric,
  best_age_bottom numeric,
  color character varying(20)
);

CREATE INDEX ON public.lookup_medium (map_id);

CREATE TABLE public.lookup_large (
  map_id integer,
  unit_ids integer[],
  strat_name_ids integer[],
  lith_ids integer[],
  best_age_top numeric,
  best_age_bottom numeric,
  color character varying(20)
);

CREATE INDEX ON public.lookup_large (map_id);
