--Consolidating all of the schelp index scripts here from https://github.com/UW-Macrostrat/macrostrat/blob/maria-migrate/cli/macrostrat/cli/commands/table_meta/

--autocomplete
CREATE INDEX ON macrostrat.autocomplete_new (id);
CREATE INDEX ON macrostrat.autocomplete_new (name);
CREATE INDEX ON macrostrat.autocomplete_new (type);
CREATE INDEX ON macrostrat.autocomplete_new (category);

--col_areas
CREATE INDEX ON macrostrat.col_areas_new (col_id);
CREATE INDEX ON macrostrat.col_areas_new USING GIST (col_area);

--col_groups
CREATE INDEX ON macrostrat.col_groups_new (id);

--col_refs
CREATE INDEX ON macrostrat.col_refs_new (col_id);
CREATE INDEX ON macrostrat.col_refs_new (ref_id);

--cols
CREATE INDEX ON macrostrat.cols_new (project_id);
CREATE INDEX ON macrostrat.cols_new USING GIST (coordinate);
CREATE INDEX ON macrostrat.cols_new USING GIST (poly_geom);
CREATE INDEX ON macrostrat.cols_new (col_group_id);
CREATE INDEX ON macrostrat.cols_new (status_code);

--concepts_places
CREATE INDEX ON macrostrat.concepts_places_new (concept_id);
CREATE INDEX ON macrostrat.concepts_places_new (place_id);

--econs

--environs

--intervals
CREATE INDEX ON macrostrat.intervals_new (id);
CREATE INDEX ON macrostrat.intervals_new (age_top);
CREATE INDEX ON macrostrat.intervals_new (age_bottom);
CREATE INDEX ON macrostrat.intervals_new (interval_type);
CREATE INDEX ON macrostrat.intervals_new (interval_name);

--lith_atts
CREATE INDEX ON macrostrat.lith_atts_new (att_type);
CREATE INDEX ON macrostrat.lith_atts_new (lith_att);

--liths
CREATE INDEX ON macrostrat.liths_new (lith);
CREATE INDEX ON macrostrat.liths_new (lith_class);
CREATE INDEX ON macrostrat.liths_new (lith_type);

--lookup_strat_names
CREATE INDEX ON macrostrat.lookup_strat_names_new (strat_name_id);
CREATE INDEX ON macrostrat.lookup_strat_names_new (concept_id);
CREATE INDEX ON macrostrat.lookup_strat_names_new (bed_id);
CREATE INDEX ON macrostrat.lookup_strat_names_new (mbr_id);
CREATE INDEX ON macrostrat.lookup_strat_names_new (fm_id);
CREATE INDEX ON macrostrat.lookup_strat_names_new (gp_id);
CREATE INDEX ON macrostrat.lookup_strat_names_new (sgp_id);
CREATE INDEX ON macrostrat.lookup_strat_names_new (strat_name);

--lookup_unit_attrs_api
CREATE INDEX ON macrostrat.lookup_unit_attrs_api_new (unit_id);

--lookup_unit_intervals
CREATE INDEX ON macrostrat.lookup_unit_intervals_new (unit_id);
CREATE INDEX ON macrostrat.lookup_unit_intervals_new (best_interval_id);

--lookup_unit_liths
CREATE INDEX ON macrostrat.lookup_unit_liths_new (unit_id);

--lookup_units
CREATE INDEX ON macrostrat.lookup_units_new (project_id);
CREATE INDEX ON macrostrat.lookup_units_new (t_int);
CREATE INDEX ON macrostrat.lookup_units_new (b_int);

--measurements
CREATE INDEX ON macrostrat.measurements_new (id);
CREATE INDEX ON macrostrat.measurements_new (measurement_class);
CREATE INDEX ON macrostrat.measurements_new (measurement_type);

--measuremeta
CREATE INDEX ON macrostrat.measuremeta_new (lith_id);
CREATE INDEX ON macrostrat.measuremeta_new (ref_id);
CREATE INDEX ON macrostrat.measuremeta_new (lith_att_id);

--measures
CREATE INDEX ON macrostrat.measures_new (measurement_id);
CREATE INDEX ON macrostrat.measures_new (measuremeta_id);

--pbdb_collections
CREATE INDEX ON macrostrat.pbdb_collections_new (collection_no);
CREATE INDEX ON macrostrat.pbdb_collections_new (early_age);
CREATE INDEX ON macrostrat.pbdb_collections_new (late_age);
CREATE INDEX ON macrostrat.pbdb_collections_new USING GiST (geom);

--places
CREATE INDEX ON macrostrat.places_new USING GiST (geom);

--projects
CREATE INDEX ON macrostrat.projects_new (project);
CREATE INDEX ON macrostrat.projects_new (timescale_id);

--refs
CREATE INDEX ON macrostrat.refs_new USING GiST (rgeom);

--sections
CREATE INDEX ON macrostrat.sections_new(id);
CREATE INDEX ON macrostrat.sections_new(col_id);

--strat_names
CREATE INDEX ON macrostrat.strat_names_new (strat_name);
CREATE INDEX ON macrostrat.strat_names_new (rank);
CREATE INDEX ON macrostrat.strat_names_new (ref_id);
CREATE INDEX ON macrostrat.strat_names_new (concept_id);

--strat_names_meta
CREATE INDEX ON macrostrat.strat_names_meta_new (interval_id);
CREATE INDEX ON macrostrat.strat_names_meta_new (b_int);
CREATE INDEX ON macrostrat.strat_names_meta_new (t_int);
CREATE INDEX ON macrostrat.strat_names_meta_new (ref_id);

--strat_names_places
CREATE INDEX ON macrostrat.strat_names_places_new (strat_name_id);
CREATE INDEX ON macrostrat.strat_names_places_new (place_id);

--strat_tree
CREATE INDEX ON macrostrat.strat_tree_new (parent);
CREATE INDEX ON macrostrat.strat_tree_new (child);
CREATE INDEX ON macrostrat.strat_tree_new (ref_id);

--timescales
CREATE INDEX ON macrostrat.timescales_new (timescale);
CREATE INDEX ON macrostrat.timescales_new (ref_id);

--timescales_intervals
CREATE INDEX ON macrostrat.timescales_intervals_new (timescale_id);
CREATE INDEX ON macrostrat.timescales_intervals_new (interval_id);

--unit_boundaries
CREATE INDEX on macrostrat.unit_boundaries (t1);
CREATE INDEX on macrostrat.unit_boundaries (unit_id);
CREATE INDEX on macrostrat.unit_boundaries (unit_id_2);
CREATE INDEX on macrostrat.unit_boundaries (section_id);

--unit_econs
CREATE INDEX ON macrostrat.unit_econs_new (econ_id);
CREATE INDEX ON macrostrat.unit_econs_new (unit_id);
CREATE INDEX ON macrostrat.unit_econs_new (ref_id);

--unit_environs
CREATE INDEX ON macrostrat.unit_environs_new (environ_id);
CREATE INDEX ON macrostrat.unit_environs_new (unit_id);
CREATE INDEX ON macrostrat.unit_environs_new (ref_id);

--unit_lith_atts
CREATE INDEX ON macrostrat.unit_lith_atts_new (unit_lith_id);
CREATE INDEX ON macrostrat.unit_lith_atts_new (lith_att_id);
CREATE INDEX ON macrostrat.unit_lith_atts_new (ref_id);

--unit_liths
CREATE INDEX ON macrostrat.unit_liths_new (lith_id);
CREATE INDEX ON macrostrat.unit_liths_new (unit_id);
CREATE INDEX ON macrostrat.unit_liths_new (ref_id);

--unit_strat_names
CREATE INDEX ON macrostrat.unit_strat_names_new (unit_id);
CREATE INDEX ON macrostrat.unit_strat_names_new (strat_name_id);

--units
CREATE INDEX ON macrostrat.units_new (section_id);
CREATE INDEX ON macrostrat.units_new (col_id);
CREATE INDEX ON macrostrat.units_new (strat_name);
CREATE INDEX ON macrostrat.units_new (color);

--units_sections

CREATE INDEX ON macrostrat.units_sections_new (unit_id);
CREATE INDEX ON macrostrat.units_sections_new (section_id);
CREATE INDEX ON macrostrat.units_sections_new (col_id);
