# Macrostrat API v2 Changelog



## /column
*Removed*  - use ````/columns```` and ````/units```` instead.


## /columns
+ This route has been reworked so that it is almost identical to units, but groups by and summarizes columns
+ Format of lithology fields in CSV output has changed. Instead of "name proportion|name proportion" it is now "name - proportion|name - proportion"
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
| *N/A*            | *N/A*        | environ_class | ["marine"]          |
| *N/A*            | *N/A*        | environ_type  | ["glacial", "fluvial"] |
| *N/A*            | *N/A*        | environ       | ["loess", "glacial indet."]|
| *N/A*            | *N/A*        | lith_class    | [{"type": "sedimentary", "prop": 0.5}, {"type": "metamorphic", "prop": 0.5}] |
| *N/A*            | *N/A*        | lith          | [{"type": "organic", "prop": 0.75}, {"type": "siliciclastic", "prop": 0.25}] |


+ Default short and long response fields changed:
|         old short        |  new short     |
|--------------------------|----------------|
| col_id, area, units, max_thick, min_thick, lith_max_thick, lith_min_thick, lith_types |  col_id, col_name, col_group, col_group_id, col_area, project_id |

| old long (in addition to short) |  new long (in addition to short)  |
|---------------------------------|-----------------------------------|
| col_name, col_group, col_group_id, b_age, t_age, sections, pbdb_collections, pbdb_occs |  max_thick, min_thick, b_age, t_age, pbdb_collections, environ_class, environ_type,  environ, lith, lith_class, lith_type |



## /fossils
+ Default output is now JSON instead of GeoJSON
+ Added CSV output


## /units
+ Format of lithology fields in CSV output has changed. Instead of "name proportion|name proportion" it is now "name - proportion|name - proportion"
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


+ Changes to the format of output fields:

|    old     |    new     |
|------------|------------|
|  lith (string)  | lith (array of objects) |
|  lith_class (string)  | lith_class (array of objects) |
|  lith_type (string)  | lith_type (array of objects) |



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
+ Changes to input and output parameters:

|   old    |   new   |
|----------|---------|
|  id      | int_id  |
| late_age | t_age   |
| early_age| b_age   |



## /defs/strat_names
+ parameter ````id```` is now ````strat_name_id````
+ parameter ````name```` is now ````strat_name````
+ parameter ````name_like```` is now ````strat_name_like````
+ parameter ````early_age```` is now ````b_age````
+ parameter ````late_age```` is now ````t_age````
+ The ````rank```` parameter can be used with ````strat_name````, ````strat_name_like````, ````strat_name_id````, and ````all````


## /geologic_units/map
*Removed* - use ````/geologic_units/gmus```` and ````/geologic_units/gmna```` instead.



## /geologic_units
*Removed* - use ````/geologic_units/gmus```` and ````/geologic_units/gmna```` instead.



## /geologic_units/gmna (formerly /geologic_units?type=gmna)
+ Added CSV output
+ Output parameter names and data types have changed:

| old  | new  |
|---|---|
| min_age  | t_interval  |
|  age_top (string) | t_age (float) |
|  max_age | b_interval  |
| age_bottom (string) | b_age (float) |
| interval_name | containing_interval |


The following output fields have been added:
````lith_type````, ````lith_class````, and ````gid````



## /geologic_units/gmus (formerly /geologic_units?type=gmus)
+ Added CSV output
+ Output parameter names and data types have changed:

| old  | new  |
|---|---|
| lith1, lith2, lith3, lith4, lith5 (strings) | lithology (array)  |
|  rt1, rt2, rt2 (strings) | rocktype (array) |
|  min_age | t_interval  |
| age_top (string) | t_age (float) |
| max_age | b_interval |
| age_bottom (string) | b_age (float) |
| unit_age |  containing_interval

