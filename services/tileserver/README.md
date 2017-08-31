# Macrostrat Tile Server

For all your geologic map needs

## Available formats
All tiles are available as both Map(nik/box) Vector Tiles (`.mvt`) and PNG (`.png`)

## Layers
The following tilesets are available:

### Carto
The carto layer is for visualization purposes, and makes many assumptions about the relative priority of each map. The layers and scales are seamlessly blended so no scale-dependent decisions can or should be made

### Tiny
All maps from the scale `tiny`. You can find a list of available maps at https://macrostrat.org/api/v2/defs/sources?scale=tiny

### Small
All maps from the scale `small`. You can find a list of available maps at https://macrostrat.org/api/v2/defs/sources?scale=small

### Tiny
All maps from the scale `medium`. You can find a list of available maps at https://macrostrat.org/api/v2/defs/sources?scale=medium

### Large
All maps from the scale `tiny`. You can find a list of available maps at https://macrostrat.org/api/v2/defs/sources?scale=large


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
