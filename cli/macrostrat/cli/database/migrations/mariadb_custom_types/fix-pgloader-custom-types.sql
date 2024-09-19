create type macrostrat.colors_color as enum ('', 'blue', 'blue dark', 'blue green', 'black', 'yellow', 'orange', 'brown dark', 'brown light', 'tan', 'green dark', 'green light', 'gray dark', 'gray light', 'pink', 'purple', 'red', 'gray', 'green', 'brown', 'steel blue', 'white');


create type macrostrat.cols_status_code as enum ('', 'active', 'in process', 'obsolete');


create type macrostrat.cols_col_type as enum ('column', 'section');


create type macrostrat.cols_col_position as enum ('', 'onshore', 'offshore');


create type macrostrat.econs_econ_type as enum ('', 'mineral', 'hydrocarbon', 'construction', 'nuclear', 'coal', 'aquifer');


create type macrostrat.econs_econ_class as enum ('', 'energy', 'material', 'precious commodity', 'water');


create type macrostrat.environs_environ_type as enum ('', 'carbonate', 'siliciclastic', 'fluvial', 'lacustrine', 'landscape', 'glacial', 'eolian');


create type macrostrat.environs_environ_class as enum ('', 'marine', 'non-marine');


create type macrostrat.intervals_interval_type as enum ('supereon', 'eon', 'era', 'period', 'superepoch', 'epoch', 'sub-epoch', 'age', 'chron', 'zone', 'bin', 'sub-age', 'subchron', 'subzone');


create type macrostrat.interval_boundaries_boundary_status as enum ('', 'modeled', 'relative', 'absolute', 'spike');


create type macrostrat.interval_boundaries_scratch_boundary_status as enum ('', 'modeled', 'relative', 'absolute', 'spike');


create type macrostrat.liths_lith_group as enum ('sandstones', 'mudrocks', 'conglomerates', 'unconsolidated', 'Folk', 'Dunham', 'felsic', 'mafic', 'ultramafic');


create type macrostrat.liths_lith_type as enum ('', 'carbonate', 'siliciclastic', 'evaporite', 'organic', 'chemical', 'volcanic', 'plutonic', 'metamorphic', 'sedimentary', 'igneous', 'metasedimentary', 'metaigneous', 'metavolcanic', 'regolith', 'cataclastic');


create type macrostrat.liths_lith_class as enum ('', 'sedimentary', 'igneous', 'metamorphic');


create type macrostrat.lith_atts_att_type as enum ('', 'bedform', 'sed structure', 'grains', 'color', 'lithology', 'structure');


create type macrostrat.lookup_measurements_measurement_class as enum ('', 'geophysical', 'geochemical', 'sedimentological');


create type macrostrat.lookup_measurements_measurement_type as enum ('', 'material properties', 'geochronological', 'major elements', 'minor elements', 'radiogenic isotopes', 'stable isotopes', 'petrologic', 'environmental');


create type macrostrat.lookup_strat_names_rank as enum ('', 'SGp', 'Gp', 'SubGp', 'Fm', 'Mbr', 'Bed');


create type macrostrat.measurements_measurement_class as enum ('', 'geophysical', 'geochemical', 'sedimentological');


create type macrostrat.measurements_measurement_type as enum ('', 'material properties', 'geochronological', 'major elements', 'minor elements', 'radiogenic isotopes', 'stable isotopes', 'petrologic', 'environmental');


create type macrostrat.pbdb_intervals_interval_type as enum ('supereon', 'eon', 'era', 'period', 'superepoch', 'epoch', 'sub-epoch', 'age', 'chron', 'zone', 'bin', 'sub-age', 'subchron', 'subzone');


create type macrostrat.projects_project as enum ('', 'North America', 'New Zealand', 'Deep Sea', 'Australia', 'Caribbean', 'South America', 'Africa', 'North American Ediacaran', 'North American Cretaceous', 'Indonesia', 'eODP', 'Northern Eurasia');


create type macrostrat.refs_compilation_code as enum ('', 'COSUNA', 'COSUNA II', 'Canada', 'GNS Folio Series 1');


create type macrostrat.rockd_features_feature_type as enum ('', 'fault', 'glacial', 'deformation');


create type macrostrat.rockd_features_feature_class as enum ('', 'structure', 'geomorphology');


create type macrostrat.stats_project as enum ('', 'North America', 'New Zealand', 'Deep Sea', 'Australia', 'Caribbean', 'South America', 'Africa', 'North American Ediacaran', 'North American Cretaceous', 'Indonesia', 'eODP', 'Northern Eurasia');


create type macrostrat.strat_names_rank as enum ('', 'SGp', 'Gp', 'SubGp', 'Fm', 'Mbr', 'Bed');


create type macrostrat.strat_names_lookup_rank as enum ('', 'SGp', 'Gp', 'Fm', 'Mbr', 'Bed');


create type macrostrat.strat_tree_rel as enum ('', 'parent', 'synonym');


create type macrostrat.structures_structure_group as enum();


create type macrostrat.structures_structure_type as enum ('', 'fault', 'fold', 'foliation', 'lineation', 'paleocurrent', 'fracture', 'bedding', 'contact', 'intrusion');


create type macrostrat.structures_structure_class as enum ('', 'fracture', 'structure', 'fabric', 'sedimentology', 'igneous');


create type macrostrat.structure_atts_att_type as enum();


create type macrostrat.structure_atts_att_class as enum();


create type macrostrat.tectonics_basin_setting as enum ('', 'divergent', 'intraplate', 'convergent', 'transform', 'hybrid');


create type macrostrat.units_color as enum ('', 'blue', 'blue dark', 'blue green', 'black', 'yellow', 'orange', 'brown dark', 'brown light', 'tan', 'green dark', 'green light', 'gray dark', 'gray light', 'pink', 'purple', 'red', 'gray', 'green', 'brown', 'steel blue', 'white');


create type macrostrat.units_outcrop as enum ('', 'surface', 'subsurface', 'both');


-- create type macrostrat.unit_boundaries_boundary_type as enum ('', 'unconformity', 'conformity', 'fault', 'disconformity', 'non-conformity', 'angular unconformity');
-- create type macrostrat.unit_boundaries_boundary_status as enum ('', 'modeled', 'relative', 'absolute', 'spike');

alter type macrostrat.unit_boundaries_boundary_type rename to boundary_type;
alter type macrostrat.unit_boundaries_boundary_status rename to boundary_status;



create type macrostrat.unit_boundaries_backup_boundary_type as enum ('', 'unconformity', 'conformity', 'fault', 'disconformity', 'non-conformity', 'angular unconformity');


create type macrostrat.unit_boundaries_backup_boundary_status as enum ('', 'modeled', 'relative', 'absolute', 'spike');


create type macrostrat.unit_boundaries_scratch_boundary_type as enum ('', 'unconformity', 'conformity', 'fault', 'disconformity', 'non-conformity', 'angular unconformity');


create type macrostrat.unit_boundaries_scratch_boundary_status as enum ('', 'modeled', 'relative', 'absolute', 'spike');


create type macrostrat.unit_boundaries_scratch_old_boundary_type as enum ('', 'unconformity', 'conformity', 'fault', 'disconformity', 'non-conformity', 'angular unconformity');


create type macrostrat.unit_boundaries_scratch_old_boundary_status as enum ('', 'modeled', 'relative', 'absolute', 'spike');


create type macrostrat.unit_contacts_old_contact as enum ('above', 'below', 'lateral', 'lateral-bottom', 'lateral-top', 'within');


create type macrostrat.unit_contacts_contact as enum ('above', 'below', 'lateral', 'lateral-bottom', 'lateral-top', 'within');


create type macrostrat.unit_dates_system as enum ('', 'U/Pb', 'Rb/Sr', 'Ar/Ar', 'C14', 'Re/Os', 'K/Ar', 'Pb/Pb', 'Fission Track', 'Amino Acid', 'Ur-Series');


create type macrostrat.unit_liths_dom as enum ('', 'dom', 'sub');


create type macrostrat.unit_seq_strat_seq_strat as enum ('', 'TST', 'HST', 'FSST', 'LST', 'SQ');


create type macrostrat.unit_seq_strat_seq_order as enum ('', '2nd', '3rd', '4th', '5th', '6th');


