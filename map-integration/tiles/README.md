# Tiles

## tl;dr
You just imported a new source and want to create tiles:

````
./seed
````

Follow the prompts.

## Structure
When you call `seed`, you are walked through a series of prompts to determine the parameters to be passed to the seeding scripts.
The parameters the user passes to `seed` are then passed to `seeder.js`, which uses those parameters to initialize the tile providers
defined in `tileRoller.js`. Configuration files and output tile locations are declared in `config.js`.


## setup.js
Converts the CartoCSS found in `/styles` to Mapnik XML files for each layer (`burwell_scale_style.xml`)


## tileRoller.js
An abstraction of `tilestrata-mapnik` that allows us to use it directly to create tiles instead of
through `tilestrata`. This was done to avoid `http` requests, which would sometimes time out and
interfere with the tile creation process.

It initializes tile providers for each scale, and then exposes a single method that accepts a valid
scale, a tile object (`{x: 0, y:0, z: 0}`), and a callback function.

Also checks if `redis` is available, and will update the cache as needed while creating tiles.

Used in `seeder.js`


## seeder.js
Methods for efficiently creating tiles. Primarily, it will break the target area into 16 areas in order to avoid
memory limits. Also takes care of deleting old tiles and updating any old tiles that are in a running Redis cache.


## credentials.js
Your postgres credentials for accessing the database

## config.js
Configuration options for rolling tiles
