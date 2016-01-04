# burwell
Multiscale geologic map integration

## Setup
+ Edit ````setup/credentials.example.py```` with your credentials and rename to ````credentials.py````
+ Run ````cd setup && ./setup.sh````
+ Permissions for MariaDB to write files to repo directory must be in place

## import
To import a new dataset, you can use ````./import```` which reprojects a dataset to EPSG 4326 and imports it into PostGIS.

It requires two parameters, a dataset name and a path to a shapefile, and accepts two optional parameters - append and encoding. If the dataset is spread out over multiple files, set append (the third positional parameter) to ````false```` or leave it blank for the first shapefile, and set it to ````true```` for subsequent shapefiles. If you see an encoding error, try the suggested encoding (usually ````LATIN1````).

##### Parameters:
+ ````dataset_name```` - Name of the dataset. The data will be inserted into a table with this name in the schema ````sources````
+ ````shapefile_path```` - The path to the shapefile you would like to insert
+ ````append (optional)```` - Boolean ````true```` or ````false````, default is ````false````. If ````true````, will append the data to an existing table specified with ````dataset_name````.
+ ````encoding (optional)```` - Default is ````UTF-8````. Often times shapefiles will have ````LATIN1```` encoding, and will throw an encoding error if ````UTF-8```` is used. If that happens, explicitly use the requested encoding.

##### Examples:

_Import a single shapefile:_
````
./import france ~/Downloads/france/france.shp
````

 _Import a dataset with same data structure spread out over two shapefiles with ````LATIN1```` encoding (note the use of ````false```` on the first command and ````true```` on the second!):_
````
./import ontario ~/Downloads/ontario/Canada.shp false LATIN1
./import ontario ~/Downloads/ontario/Greenland.shp true LATIN1
````

## Matching
There are three matching operations available - make matches, manually add a match, and manually delete a match.

#### Making matches
After a new dataset has been imported a broad set of matches should be made. To do this, run

````
python matching/match_parallel.py --source_id **source id**
````

The script `matching/match_parallel.py` takes one argument, a `source_id`, which is the new unique source ID of the dataset
you would like to create matches for (`maps.sources.source_id`). This script could take a long time time run, but will
populate `maps.map_units` and `maps.map_strat_names`.


#### Manually adding matches
Often times the automated matching script produces invalid results, or personal knowledge is better than what can be inferred from
the automated search. To manually make a match, use `matching/add_match.py`.

#### Manually deleting matches
`matching/remove_match.py`


## Rebuilding lookup tables
After creating initial matches, the lookup table for the scale of the target source should be rebuilt.

````
python setup/build_lookup.py **scale**
````




## tiles
This directory contains scripts for the creation and modification of map tiles. Very much a work in progress and subject to change.

To get started, ````cd tiles````, then:
````
npm install
git clone https://github.com/TileStache/TileStache.git
cp tilestache.cfg TileStache/tilestache.cfg
psql -U john burwell < setup_new.sql
````

This will install [kosmtik](https://github.com/kosmtik/kosmtik) and [TileStache](https://github.com/TileStache/TileStache), which are used to create a Mapnik XML file and create tiles, respectively.
It will then build the materialized views ````small_map````, ````medium_map````, and ````large_map````, which are used
for styling and grouping. Finally, it will create a CartoCSS style sheet, the Mapnik XML file, and move it into place.

#### refresh.py
This script is for refreshing the materialized views with any new source data (see ````--help```` for more info). Example: ````python refresh.py large````

#### generate.py
This abstraction of TileStache's ````tilestache-clean.py```` and ````tilestache-seed.py```` assists in the creation of tiles.
It allows you to clean and seed a cache by ````source_id````, scale, or all. Use this if you want to generate tiles for a new source, or want to regenerate for any reason, such as an update to Macrostrat matches. It also creates CartoCSS based on the contents of the table ````macrostrat.intervals````, constructs a Tilemill project file (````burwell_configured.mml````) which contains style and layer information, and then uses kosmtik to convert that file to a Mapnik XML file that can be used by TileStache.


#### setup_new.sql
The beast. Creates the  materialized views ````small_map````, ````medium_map````, and ````large_map````. It has two primary functions:
+ Assign "best" ````unit_ids```` and ````strat_name_ids```` to burwell units, if possible
+ Assign an arbitrary ````group_id```` to each burwell unit at each scale

The purpose of the ````group_id```` is to aid in the generation of tiles. Instead of generating tiles for the bounding box
of a scale, it allows us to generate tiles only for groups of adjacent sources. This means if generating tiles for BC, Ontario, GMUS, and Australia, instead of generating tiles for the whole world, the majority of which will be empty, we instead generate
two groups - North America, and Australia.

The grouping algorithm works by taking the bounding box of each source, and creating groups of touching bounding boxes.
