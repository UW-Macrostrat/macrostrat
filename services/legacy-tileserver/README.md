# Macrostrat's legacy tile server

*A dynamic tile server for geologic maps*

# Version 2 changes

- Python-based instead of Node-based
- A "dynamic tiler" based on [Mapnik](https://mapnik.org/) and PostGIS
- Uses a PostgreSQL caching backend
- Optionally, can use Varnish as a "L2" API cache

# Installing

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

## Testing

Testing is done with `pytest`. To run the tests, use:

```make test```.

To omit legacy raster tests, use

  ```make test-dev```.

