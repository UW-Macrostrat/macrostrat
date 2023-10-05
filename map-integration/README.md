# Macrostrat's map integration system

This repository holds the core of Macrostrat's system for integrating geologic maps across many scales.
The repository contains scripts for importing maps, matching to macrostrat, creation of build tables, and tiles.

Prior to 2023, this system used to be code-named "Burwell." But we're moving towards a more functional name now that the maps
system is a central part of Macrostrat's capabilities and expansion plans.

## Ingestion

In version `2.0`, imports are now accomplished with the `macrostrat maps ingest` script, which reprojects a
dataset to EPSG 4326 and imports it into PostGIS.

It requires two parameters, a dataset name and a path to a shapefile, and accepts two optional parameters - append and encoding. If the dataset is spread out over multiple files, set append (the third positional parameter) to ````false```` or leave it blank for the first shapefile, and set it to ````true```` for subsequent shapefiles. If you see an encoding error, try the suggested encoding (usually ````LATIN1````).

##### Parameters:
+ ````dataset_name```` - Name of the dataset. The data will be inserted into a table with this name in the schema ````sources````
+ ````shapefile_path```` - The path to the shapefile you would like to insert
+ ````append (optional)```` - Boolean ````true```` or ````false````, default is ````false````. If ````true````, will append the data to an existing table specified with ````dataset_name````.
+ ````encoding (optional)```` - REQUIRES ````true```` or ````false```` to be specified, otherwise ignored. Default is ````UTF-8````. Often times shapefiles will have ````LATIN1```` encoding, and will throw an encoding error if ````UTF-8```` is used. If that happens, explicitly use the requested encoding. Must also include "false", even if adding one file, otherwise the encoding will be ignored.

##### Examples:

_Import a single shapefile:_
````
macrostrat maps ingest ~/Downloads/france/france.shp
````

 _Import a dataset with same data structure spread out over two shapefiles with ````LATIN1```` encoding (note the use of ````false```` on the first command and ````true```` on the second!):_
````
./import ontario ~/Downloads/ontario/Canada.shp false LATIN1
./import ontario ~/Downloads/ontario/Greenland.shp true LATIN1
````
Note that if this script reports an error similar to ````Unable to open unprojected.shp or unprojected.SHP.````, try moving the directory containing the .shp file into a shorter path location. Long paths can cause failure.


# Harmonization

Manual cleanup to tables to prepare them for importing. Not yet well-documented.

We will import the `<source_id>_polygons` and `<source_id>_linestrings` table.
`<source_id>_points` is ignored for now in Macrostrat's current processing, but should be
retained in case we want to track point data (especially, bedding orientations) in the future.

- Set the `ready` field to `true` for fields that have been prepared for import.
  This allows data not matching Macrostrat's current structure (especially, contacts with
  certainty information) to be retained for eventual use if desired.


# Processing
Processing a source involves matching, refreshing lookup tables, building an `rgeom`, refreshing carto tables for lines, and rolling tiles. While these steps can be done individually, they should be done all at once by using `process_source.py`.

**This should only be called after the units and lines for a given source have been imported into their respective homogenized tables!!!**

##### Parameters:
+ ````source_id```` - A valid source_id to process

##### Examples:

_Process a source:_
````
python process_source.py --source_id 1234
````


## Matching
Matching involves creating relationships between geologic map units and Macrostrat units and/or stratigraphic names.

Fundamental to this process is the table `macrostrat.strat_name_footprints` (built during the import of Macrostrat into burwell or by running the script `setup/create_strat_names_footprints.sql`). This table represents a greedy footprint for each stratigraphic name which consists of the union of units tagged to *any* name in the given name's hierarchy, the units tagged to *any* name part of the same concept, and the footprint identified by the lexicon the name belongs to.

#### Matching to stratigraphic names

````
python matching/match_names.py --source_id <source-id>
````

Geologic map units are matched to stratigraphic names on the basis of these footprints, a string match, and an overlap in time. This matching process is repeated by relaxing each of these constraints in all possible combinations and recorded in the column `basis_col` in the table `maps.map_strat_names`. The relaxation of each constraint appends `_f<name of constraint>` to the column being matched.

For example, if a geologic map source has data in the fields `name` and `descrip`, `match_names.py` will first try to match stratigraphic names using a strict time, space, and string match on each field. It will then begin to relax these constraints. A strict name match uses the field `rank_name`, and a relaxed match uses `name_no_lith`. A strict time match checks for an overlap in the range of the unit and name's ages, and a relaxed match adds 25Ma to the top age of the stratigraphic name, and subtracts 25Ma from the bottom age. A strict space match uses the footprint of the name from `strat_name_footprints`, and a relaxed match buffers the footprint of the name by 1.2 degrees.


#### Matching to Macrostrat units

````
python matching/match_units.py --source_id <source-id>
````

After geologic map units are matched to stratigraphic names, they are then matched to Macrostrat units with the script `match_units.py` and the companion script `match_units_multi.py`. While this script relaxes constraints in an identical way to `match_names.py`, it also takes into account name hierarchy. First, it uses the names matched to a given geologic map unit to find macrostrat units that are assigned to that stratigraphic name. It then goes through the constraint relaxing process. Next, it repeats the same process, but instead looks for Macrostrat units that are assigned to children of the target stratigraphic name. So, if a geologic map unit is matched to a formation, it will look for matches to Macrostrat units that are assigned to members of that formation. The same relaxation of constraints is repeated. Finally, the process is repeated but instead the script looks for Macrostrat units that are assigned to names that the target stratigraphic name *belongs to*. Again, if our target name is a formation, it will look for any Macrostrat units that assigned to the group or supergroup that this formation might belong to.


#### Manually adding matches
Often times the automated matching script produces invalid results, or personal knowledge is better than what can be inferred from
the automated search. To manually make a match, use `matching/add_match.py`.

#### Manually deleting matches
`matching/remove_match.py --help`


## Lookup Tables

````
python setup/refresh_lookup <source_id or scale>
````

After the matching process, the lookup tables for each scale are built. These tables (`public.lookup_<scale>`) contain a synthesis of the best data available for a given geologic map unit. The `strat_name_ids` amd `unit_ids` are determined based on the highest quality of match available for a polygon. To see the order in which this is determined, please see `setup/refresh.py`. This is also where a color is assigned to each polygon for tile creation.


## rgeom

````
python utils/rgeom.py <source_id>
````

The `rgeom` for each source is the convex hull for all the geometries the given source and can be found in `maps.sources`. It is used primarily in the creation of `carto` tables and tiles, and is necessary for many operations. In order to speed up the creation of this geometry, all geometries of the target source are exported to a shapefile and dissolved by Mapshaper. The result is then imported into PostGIS and processed to remove small interior rings. **Some rgeoms in burwell have been manually edited to get the desired level of simplicity**.


## carto

The schema `carto` contains geometries that are suitable for mapping purposes. In order to reconcile overlapping geometries from multiple scales, sources, and priorities, the `carto` scripts "flatten" these data into a single layer for each source with non-overlapping polygons and lines.

#### lines

````
python utils/carto_lines.py --source_id <source_id>
````

This script adds the lines from a single source to the proper `carto.lines_<scale>`. The lines of the source must be in one of the tables in the schema `lines`. It takes into the various `display_scales` and priorities of all sources.


#### units
Coming soon. Necessary for vector tiles


## tiles
See `tiles/README.md`


## tile-tester
This is a small application to make the modification of styles to the burwell tiles easier. It is identical to the tile server in the Macrostrat API except it doesn't use any caching.

#### Setup
````
cd tile-tester
npm install
````

#### Usage
````
node server.js
````

You will then be able to see a live view of the tiles at `http://localhost:5555` in your web browser. If you edit any of the styles in `./tiles/styles` and then run `node tiles/compile_styles.js` and restart the `tile-tester` server you will see the changes.


## Import raster

````
raster2pgsql -s 4326 -c -I -t 30x30 n42_w090_1arc_v2.tif sources.srtm | psql -U john elevation

````

## Fix unstyled polygons
When empty (unstyled) polygons appear do the following to fix (see https://github.com/UW-Macrostrat/burwell/issues/38)
```
sudo su jczaplewski
pm2 restart seed-server
macrostrat seed 207
```
