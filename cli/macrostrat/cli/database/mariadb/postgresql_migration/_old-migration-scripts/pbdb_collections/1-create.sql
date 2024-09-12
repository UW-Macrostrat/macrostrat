
CREATE TABLE macrostrat.pbdb_collections_new (
  collection_no integer NOT NULL,
  name text,
  early_age numeric,
  late_age numeric,
  grp text,
  grp_clean text,
  formation text,
  formation_clean text,
  member text,
  member_clean text,
  lithologies text[],
  environment text,
  reference_no integer,
  n_occs integer,
  geom geometry
);

