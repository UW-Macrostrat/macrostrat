# Macrostrat API v2 Changelog

## /column
*Removed*  - use ````/columns```` and ````/units```` instead.

## /fossils
+ Default output is now JSON instead of GeoJSON
+ Added CSV output

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