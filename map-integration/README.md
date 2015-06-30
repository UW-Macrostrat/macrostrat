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

 _Import a dataset spread out over two shapefiles with ````LATIN1```` encoding (note the use of ````false```` on the first command and ````true```` on the second!):_
````
./import ontario ~/Downloads/ontario/Canada.shp false LATIN1
./import ontario ~/Downloads/ontario/Greenland.shp true LATIN1
````
