set SEARCH_PATH to macrostrat, public;

DROP TABLE IF EXISTS macrostrat.lookup_strat_names_new;
DROP TABLE IF EXISTS macrostrat.lookup_strat_names_old;

CREATE TABLE macrostrat.lookup_strat_names (
  strat_name_id integer NOT NULL PRIMARY KEY,
  strat_name    varchar(100) NOT NULL,
  rank          macrostrat.lookup_strat_names_rank,
  concept_id    integer      NOT NULL,
  rank_name     varchar(100) NOT NULL,
  bed_id        integer      NOT NULL,
  bed_name      varchar(100)  DEFAULT NULL::character varying,
  mbr_id        integer      NOT NULL,
  mbr_name      varchar(100)  DEFAULT NULL::character varying,
  fm_id         integer      NOT NULL,
  fm_name       varchar(100)  DEFAULT NULL::character varying,
  subgp_id      integer      NOT NULL,
  subgp_name    varchar(100)  DEFAULT NULL::character varying,
  gp_id         integer      NOT NULL,
  gp_name       varchar(100)  DEFAULT NULL::character varying,
  sgp_id        integer      NOT NULL,
  sgp_name      varchar(100)  DEFAULT NULL::character varying,
  early_age     numeric(8, 4) DEFAULT NULL::numeric,
  late_age      numeric(8, 4) DEFAULT NULL::numeric,
  gsc_lexicon   char(15)      DEFAULT NULL::bpchar,
  parent        integer      NOT NULL,
  tree          integer      NOT NULL,
  t_units       integer      NOT NULL,
  b_period      varchar(100)  DEFAULT NULL::character varying,
  t_period      varchar(100)  DEFAULT NULL::character varying,
  name_no_lith  varchar(100)  DEFAULT NULL::character varying,
  ref_id        integer      NOT NULL,
  c_interval    varchar(100)  DEFAULT NULL::character varying
);

/** Indexes; may be auto-generated?
CREATE INDEX idx_lookup_strat_names_bed_id
  ON lookup_strat_names (bed_id);

CREATE INDEX idx_lookup_strat_names_concept_id
  ON lookup_strat_names (concept_id);

CREATE INDEX idx_lookup_strat_names_fm_id
  ON lookup_strat_names (fm_id);

CREATE INDEX idx_lookup_strat_names_gp_id
  ON lookup_strat_names (gp_id);

CREATE INDEX idx_lookup_strat_names_mbr_id
  ON lookup_strat_names (mbr_id);

CREATE INDEX idx_lookup_strat_names_parent
  ON lookup_strat_names (parent);

CREATE INDEX idx_lookup_strat_names_rank
  ON lookup_strat_names (rank);

CREATE INDEX idx_lookup_strat_names_ref_id
  ON lookup_strat_names (ref_id);

CREATE INDEX idx_lookup_strat_names_sgp_id
  ON lookup_strat_names (sgp_id);

CREATE INDEX idx_lookup_strat_names_strat_name
  ON lookup_strat_names (strat_name);

CREATE INDEX idx_lookup_strat_names_subgp_id
  ON lookup_strat_names (subgp_id);

CREATE INDEX idx_lookup_strat_names_tree
  ON lookup_strat_names (tree);

CREATE INDEX lookup_strat_names_new_bed_id_idx
  ON lookup_strat_names (bed_id);

CREATE INDEX lookup_strat_names_new_concept_id_idx
  ON lookup_strat_names (concept_id);

CREATE INDEX lookup_strat_names_new_fm_id_idx
  ON lookup_strat_names (fm_id);

CREATE INDEX lookup_strat_names_new_gp_id_idx
  ON lookup_strat_names (gp_id);

CREATE INDEX lookup_strat_names_new_mbr_id_idx
  ON lookup_strat_names (mbr_id);

CREATE INDEX lookup_strat_names_new_sgp_id_idx
  ON lookup_strat_names (sgp_id);

CREATE INDEX lookup_strat_names_new_strat_name_id_idx
  ON lookup_strat_names (strat_name_id);

CREATE INDEX lookup_strat_names_new_strat_name_idx
  ON lookup_strat_names (strat_name);
*/
