# burwell
Multiscale geologic map integration

## TL;DR
1. `./import tataouine ~/Downloads/tataouine.shp`
2. `python process_source.py --source_id 1234`


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
+ ````encoding (optional)```` - REQUIRES ````true```` or ````false```` to be specified, otherwise ignored. Default is ````UTF-8````. Often times shapefiles will have ````LATIN1```` encoding, and will throw an encoding error if ````UTF-8```` is used. If that happens, explicitly use the requested encoding. Must also include "false", even if adding one file, otherwise the encoding will be ignored.

##### Examples:

_Import a single shapefile:_
````
./import france ~/Downloads/france/france.shp false
````

 _Import a dataset with same data structure spread out over two shapefiles with ````LATIN1```` encoding (note the use of ````false```` on the first command and ````true```` on the second!):_
````
./import ontario ~/Downloads/ontario/Canada.shp false LATIN1
./import ontario ~/Downloads/ontario/Greenland.shp true LATIN1
````


## processing
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
There are three matching operations available - make matches, manually add a match, and manually delete a match.

#### Making matches
After a new dataset has been imported a broad set of matches should be made. To do this, run

````
python matching/match_parallel.py --source_id **source id**
````

The script `matching/match_parallel.py` takes one argument, a `source_id`, which is the new unique source ID of the dataset
you would like to create matches for (`maps.sources.source_id`). This script could take a long time time run, but will
populate `maps.map_units` and `maps.map_strat_names`, as well as update the proper lookup table.


#### Manually adding matches
Often times the automated matching script produces invalid results, or personal knowledge is better than what can be inferred from
the automated search. To manually make a match, use `matching/add_match.py`.

#### Manually deleting matches
`matching/remove_match.py --help`



## Rebuilding lookup tables
The lookup tables are automatically rebuilt after running `match_parallel.py`, but you can manually refresh them as well.

````
python setup/refresh_lookup.py **scale or source_id**
````



## tiles
See `tiles/README.md`


## Import raster

````
raster2pgsql -s 4326 -c -I -t 30x30 n42_w090_1arc_v2.tif sources.srtm | psql -U john elevation

````
