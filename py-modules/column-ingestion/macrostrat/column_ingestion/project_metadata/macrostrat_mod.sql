-- this SQL must be executed on macrostrat before macrostrat_import_2.5.py can be successfully run
-- ALTER TABLE macrostrat.cols ALTER COLUMN col_name TYPE character varying;

-- remove NOT NULL from sections.fo_h and sections.lo_h
-- remove NOT NULL from units.max_thick, units.min_thick
-- remove NOT NULL from units.fo_h, units.lo_h, remove default

-- remove foreign key constraint on units.section_id
-- ALTER TABLE macrostrat.units DROP CONSTRAINT units_sections_fk;

-- units_sections autoincrement primary key was wonky, had to change in order to insert to: macrostrat.units_sections_id_seq

/** NOTE: we are not removing this foreign key for now, as having units depend
  on sections seems to be the right approach.
 */
ALTER TABLE "macrostrat"."units_sections" ALTER COLUMN "id" SET DEFAULT nextval('macrostrat.units_sections_id_seq'::regclass);

-- remove null constraint on obsolete fields in "macrostrat"."strat_names"

-- autoincrement primary key was wonky, had to change to insert into macrostrat.strat_names

-- strat_tree did not have primary autoincrement key
-- Added to migration
