# Utility scripts

To run all scripts except `unit_boundaries_gplates` and `getOutputFields`:

````
./rebuild
````

#### getOutputFields
*Not part of rebuild.* Documentation validation script. Determines which fields are missing from the documentation on specific routes.

#### unit_boundaries_gplates
*Not part of rebuild.* Populates the fields `paleo_lat` and `paleo_lng` in the table `unit_boundaries` by hitting the GPlates API. These coordinates are used for reporting the paleocoordinates of units (`t/b_plat/lng`).

#### update_unit_boundaries
Updates the ages in `unit_boundaries` where the boundary status is 'absolute'.

#### build_pbdb_matches
Updates `collection_name`, `occs`, and `release_date` in `pbdb_matches` from the tables `collections`, `coll_matrix`, and `collections` in the PBDB MySQL database.

#### build_lookup_unit_intervals
Rebuilds the table `lookup_unit_intervals`, which maps `unit_id`s to ages and time intervals.

#### build_lookup_unit_attrs_api
Rebuilds the table `lookup_unit_attrs_api`, which is a mapping between `unit_id`s and JSON blobs of corresponding `lith`, `environ`, `econ`, `measure_short`, and `measure_long` attributes that are used in the API.

#### build_lookup_strat_names
Rebuilds the table `lookup_strat_names`, which maps `strat_name_id`s to their hierarchy.

#### build_autocomplete
Rebuilds the table `autocomplete`, which is used for the route `/api/defs/autocomplete`.
