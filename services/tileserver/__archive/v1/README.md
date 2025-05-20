# Macrostrat Tile Server

For all your geologic map needs

## Installation
````
npm install && cp credentials.example.js credentials.js
````

Enter your Postgres credentials in `credentials.js`

## Starting

For development:
````
npm start
````

For production:
````
pm2 start server.js -i 2 --name tileserver
````

## Troubleshooting
Seeing blank tiles, empty polygons, or other oddities? Try the following:

1. Clear your browser cache

2. Clear the tile cache:
````
redis-cli flushdb
````

3. Restart the tileserver:
````
pm2 restart tileserver
````

4a. If the problem is with raster tiles....
````
macrostrat seed <source_id>
````

4b. If the problem is with vector tiles...
````
macrostrat seed carto && macrostrat seed carto-vector
````

## Layers
The following tilesets are available:
+ `/carto/<z>/<x>/<y>.mvt`
+ `/carto/<z>/<x>/<y>.png`
+ `/carto-slim/<z>/<x>/<y>.mvt`


## Schema
All tilesets contain two layers - `units` and `lines`. Units are the geologic map polygons, and lines are geologic line features such as faults, anticlines, and moraines.

##### Units
| field  |  description |
|--------|--------------|
|  `map_id`  |  The unique identifier for a polygon  |
|  `source_id`  |  An integer that corresponds to the original map sources that can be found at https://macrostrat.org/api/v2/defs/sources  |
|  `name`  | The name of the polygon. Usually either a stratigraphic name or lithological description |
|  `strat_name` | The stratigraphic name of the polygon |
|  `age`   | The age indicated by the map author. |
|  `lith`  | Lithology |
|  `descrip`  | A description of the map unit |
|  `comments` | Comments about the map unit |
|  `t_int`    | The Macrostrat interval ID associated with the top age of the map unit |
|  `t_int_name` | The name of the Macrostrat interval associated with the top age of the map unit |
|  `best_t_age` | The best top age that Macrostrat can assign to the unit based on linked resources |
|  `b_int`    | The Macrostrat interval ID associated with the bottom age of the map unit |
|  `b_int_name` | The name of the Macrostrat interval associated with the bottom age of the map unit |
|  `best_b_age` | The best bottom age that Macrostrat can assign to the unit based on linked resources |
|  `color`   | A hex code associated with the best containing time interval for the map unit |


##### Lines
| field  |  description |
|--------|--------------|
|  `line_id` | The unique identifier for a line feature |
|  `sources_id` | An integer that corresponds to the original map sources that can be found at https://macrostrat.org/api/v2/defs/sources  |
|  `name`  | The name of the line, if available |
|  `descrip` | A description of the line |
|  `type`    | A normalized line type (fault, fold, anticline, etc) |
|  `direction`  | A normalized direction of the line. Not commonly available. |
