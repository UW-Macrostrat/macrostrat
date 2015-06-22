# Macrostrat API v2 Changelog

## tl;dr
+ Added ````?sample```` to every route (except ````/mobile````), which returns 5 records.
+ The input and output parameter ````id```` no longer exists. All identifiers are now descriptive, for example ````unit_id````, ````col_id````, and ````econ_id````.
+ Numerous routes have been removed (````column````, ````unit_contacts````, ````pbdb_report````, ````section_stats````, ````geologic_units/map````, ````geologic_units/intersection```` and ````geologic_units````)
+ Every route outputs JSON by default
+ ````columns```` and ````sections```` are summaries of the data returned by ````units````
+ ````lith````, ````environ```` and ````econ```` have been refactored to return valid JSON instead of pipe-delimited strings



## /column
*Removed*  - use ````/columns```` and ````/units```` instead.


## /columns
+ This route has been reworked so that it is almost identical to units, but groups by and summarizes columns
+ Format of lithology fields in CSV output has changed. Instead of "name proportion|name proportion" it is now "name - proportion|name - proportion"
+ Added ability to query to ````environ_id````, ````econ_id````, ````econ````, ````econ_type````, and ````econ_class````
+ Changes to output fields

|        old       | old example  |      new      |     new example     |
|------------------|--------------|---------------|---------------------|
| units            | [1,2,3]      | *Removed*     |  *Removed*          |
| lith_max_thick   | 1219         | *Removed*     |  *Removed*          |
| lith_min_thick   | 1001         | *Removed*     |  *Removed*          |
| pbdb_occs        | 9342         | *Removed*     |  *Removed*          |
| lith_types       | ["carbonate"] |  lith_type   |  [{"type": "carbonate", "prop": 1}] |
| sections         | [2,3,4]      | *Removed*     |  *Removed*          |
| area             | 43242.2      | col_area      |    43242.2          |
| *N/A*            | *N/A*        | group_col_id  |    2.1              |
| *N/A*            | *N/A*        | environ       | [{class: "marine", type: "siliciclastic", name: "submarine fan", environ_id: 37}] |
| lith             | "shale 0.1250| siltstone 0.1250|"  | lith  | [{atts: [ ], name: "sandstone", prop: 0.1667, lith_id: 10, type: "siliciclastic", class: "sedimentary" }] |
| *N/A*            | *N/A*        | econ       | [{type: "hydrocarbon", name: "oil reservoir", econ_id: 4, class: "energy"}]|



+ Default short and long response fields changed:
|         old short        |  new short     |
|--------------------------|----------------|
| col_id, area, units, max_thick, min_thick, lith_max_thick, lith_min_thick, lith_types |  col_id, col_name, col_group, col_group_id, col_area, project_id |

| old long (in addition to short) |  new long (in addition to short)  |
|---------------------------------|-----------------------------------|
| col_name, col_group, col_group_id, b_age, t_age, sections, pbdb_collections, pbdb_occs |  max_thick, min_thick, b_age, t_age, pbdb_collections, lith, environ, econ |


## /sections
+ Input and output parameters have changed to be identical to those of ````units````. See changes made to that route for more details.
+ Major conceptual change - now dynamically computes packages based on query (thus multiple objects may share a ````section_id````), where a package is a temporally gap bound section of units. 


## /section_stats
*Removed*  - use ````/sections```` instead.


## /fossils
+ Default output is now JSON instead of GeoJSON
+ Added CSV output
+ Changes to output field names:

|    old     |    new     |
|------------|------------|
|   collection_no       | cltn_id    |
|  occ       | pbdb_occs  |
| *N/A*      | cltn_name  |



## /units
+ Format of lithology fields in CSV output has changed. Instead of "name proportion|name proportion" it is now "name - proportion|name - proportion"
+ Empty output fields now return empty strings or arrays instead of NULLs
+ Added ability to query to ````environ_id````, ````econ_id````, ````econ````, ````econ_type````, and ````econ_class````
+ Changes to input parameter names output fields:

|    old     |    new     |
|------------|------------|
|   id       | unit_id    |
|  strat_id  | strat_name_id |
|  u_color   | *Removed* |
|  pbdb      | pbdb_collections |
|  LO_h      | *Removed* |
|  FO_h      | *Removed* |
|  position_bottom      | *Removed* |
|  t_interval      | t_int_id |
|  b_interval      | b_int_id |
|  LO_interval     | t_int_name |
|  FO_interval     | b_int_name |
|  LO_age          | t_int_age |
|  FO_age          | b_int_age |
|  *N/A*     | econ[]    |



+ Changes to the format of output fields:

|    old     |    new     |
|------------|------------|
|  lith (string), lith_class (string), lith_type (string)  | lith (array of objects) |
|  environ (string), environ_class (string), environ_type (string)  | environ (array of objects) |



## /unit_contacts
*Removed*  - use ````/units```` instead.


## /pbdb_report
*Removed*


## /defs/lithologies
+ input and output parameter ````id```` is now ````lith_id````
+ Multiple input ````lith_id```` now accepted


## /defs/lithology_attributes
+ input and output parameter ````id```` is now ````lith_att_id````
+ Multiple input ````lith_att_id```` now accepted


## /defs/columns
+ input parameters ````col_id```` and ````col_group_id```` now accept multiple ids


## /defs/environments
+   input and output parameter ````id```` is now ````environ_id````


## /defs/intervals
+ Can now specify a ````name```` query parameter
+ Changes to input and output parameters:

|   old    |   new   |
|----------|---------|
|  id      | int_id  |
| late_age | t_age   |
| early_age| b_age   |
| type     | int_type  |



## /defs/strat_names
+ parameter ````id```` is now ````strat_name_id````
+ parameter ````name```` is now ````strat_name````
+ parameter ````name_like```` is now ````strat_name_like````
+ parameter ````early_age```` is now ````b_age````
+ parameter ````late_age```` is now ````t_age````
+ The ````rank```` parameter can be used with ````strat_name````, ````strat_name_like````, ````strat_name_id````, and ````all````
+ By default, requesting a ````strat_name```` or ````strat_name_id```` will only return the matching name. Previously this would also return all associated children
+ A parameter ````rule```` was added. To return a strat name and all associated children, use ````rule=down````, and to return the entire hierarchy of a given strat name use ````rule=all````.


## /defs/measurements
+ input and output parameter ````id```` is now ````measure_id````


## /defs/projects
+ Output paramter ````id```` is now ````project_id````


## /defs/timescales
+ Output paramter ````id```` is now ````timescale_id````


## /defs/refs
+ Route added for fetching reference definitions.


## /geologic_units/map
*Removed* - use ````/geologic_units/gmus```` and ````/geologic_units/gmna```` instead.


## /geologic_units/intersection
*Removed* - use ````/geologic_units/gmus```` and ````/geologic_units/gmna```` instead.


## /geologic_units
*Removed* - use ````/geologic_units/gmus```` and ````/geologic_units/gmna```` instead.



## /geologic_units/gmna (formerly /geologic_units?type=gmna)
+ Added CSV output
+ Added input variable ````shape````, which accepts a valid WKT polygon. If used, a ````buffer```` in km2 can also be specified.
+ Output parameter names and data types have changed:

| old  | new  |
|---|---|
| min_age  | t_interval  |
|  age_top (string) | t_age (float) |
|  max_age | b_interval  |
| age_bottom (string) | b_age (float) |
| interval_name | containing_interval |
| *N/A*    | color |


The following output fields have been added:
````lith_type````, ````lith_class````, and ````gid````



## /geologic_units/gmus (formerly /geologic_units?type=gmus)
+ Added CSV output
+ Added input variable ````shape````, which accepts a valid WKT polygon. If used, a ````buffer```` in km2 can also be specified.
+ Input value ````unit_name```` is now ````search````
+ Added input variable ````strat_name_id````, which allows direct querying of Macrostrat stratigraphic names that have been matched to GMUS. Example ````/api/v2/geologic_units/gmus?strat_name_id=1,2,3````
+ Added input variable ````unit_id````, which allows direct querying of GMUS units matched to Macrostrat units.
+ Adding ````adjacents=true```` now allowed when specifying a gid
+ Improved the handling of ````adjacents=true```` when specifying a latitude and longitude
+ Output parameter names and data types have changed:

| old  | new  |
|---|---|
| lith1, lith2, lith3, lith4, lith5 (strings) | lithology (array)  |
|  rt1, rt2, rt2 (strings) | rocktype (array) |
|  min_age | t_interval  |
| age_top (string) | t_age (float) |
| max_age | b_interval |
| age_bottom (string) | b_age (float) |
| unit_age |  containing_interval |
| *N/A*    | color |


## /mobile/fossils
+ Changed output ````id```` to ````cltn_id````
+ Changed output ````name```` to ````cltn_name````


## /mobile/point_details
+ Under ````gmus````, ````rocktype1````, ````rocktype2````, and ````rocktype3```` have been collapsed into ````rocktype````, which is an array
+ Under ````column````, ````id```` has been renamed ````col_id````
+ Under ````units````, ````id```` has been renamed ````unit_id````, and ````pbdb```` has been renamed ````pbdb_cltns````, and ````lith```` is now an array of objects, with each object having a ````type```` and ````prop````, or proportion. 


