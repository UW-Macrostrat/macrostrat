# Macrostrat's v2 tile server

- Python-based instead of Node-based
- A "dynamic tiler" based heavily on [TimVT](https://github.com/developmentseed/timvt)
- Uses a PostgreSQL caching backend (this is the primary simplification)
- Uses Mapnik for legacy image-tile generation
- Optionally, can use Varnish as a "L2" API cache

# Installing

This module depends on tile utilities[UW-Macrostrat/postgis-tile-utils](https://github.com/UW-Macrostrat/postgis-tile-utils).
This dependency is packaged as a git submodule. To install it, run:

> git submodule update --init

The module can be run locally using Poetry, but there may be problems with Mapnik.
We're working on simplifying this process and making Mapnik optional.

To install in Docker (preferred), build the image:

> docker build -t macrostrat/tileserver .

## Running the tile server

Then run it with the appropriate environment variables and port bindings:

> docker run macrostrat/tileserver \
>   -e POSTGRES_DB=postgresql://user:password@db.server:5432 \
>   -p 8000:8000

To serve tile layers, the fixtures (housed in `macrostrat_tileserver/fixtures`) must be created on the database.
There is a bundled `tileserver` CLI that will create the layers. In Docker:

> docker run macrostrat/tileserver \
>   -e POSTGRES_DB=postgresql://user:password@db.server:5432 \
>   tileserver create-fixtures  

Or in the running docker container:

> docker exec <container-id> tileserver create-fixtures

## Accessing tiles

Once the tileserver is running, you should be able to access docs:

> curl localhost:8000/docs

And tiles:

> curl localhost:8000/<layer-id>/{z}/{x}/{y}

Macrostrat core layers:

- https://localhost:8000/carto-slim/{z}/{x}/{y}
- https://localhost:8000/carto/{z}/{x}/{y}
- https://localhost:8000/map/{z}/{x}/{y}?source_id=<source_id>
- https://localhost:8000/all-maps/{z}/{x}/{y} _(for development purposes only)_


## Defining new layers

- New layers can be defined using SQL or PL/PGSQL functions.
- Currently, layers must be initialized by editing the `macrostrat_tileserver/main.py` file to
  add the appropriate initialization function. This will be improved in the future.