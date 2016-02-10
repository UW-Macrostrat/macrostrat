# Tiles

## tl;dr
You just imported a new source and want to create tiles:

````
node seeder.js **source_id**
````


## setup.js
Generates the Mapnik XML files for each layer (`burwell_scale.xml`)

## seeder.js
Run this to seed the tile cache for zoom levels 1-10 (tiny - medium).

*****To seed everything:*****

````
node seeder.js
````

*****To seed a specific source:*****

````
node seeder.js 21
````

## tileRoller.js
An abstraction of `tilestrata-mapnik` that allows us to use it directly to create tiles instead of
through `tilestrata`. This was done to avoid `http` requests, which would sometimes time out and
interfere with the tile creation process.

It initializes tile providers for each scale, and then exposes a single method that accepts a valid
scale, a tile object (`{x: 0, y:0, z: 0}`), and a callback function.

Used in `seeder.js`


## credentials.js
Your postgres credentials for accessing the database

## config.js
Configuration options for rolling tiles
