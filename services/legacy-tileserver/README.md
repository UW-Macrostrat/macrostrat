# Macrostrat's legacy tile server

*A dynamic tile server for geologic maps*

# Version 2 changes

- Python-based instead of Node-based
- Uses PostGIS as an on-demand caching backend (i.e., no seeding)
- A "dynamic tiler" based on [Mapnik](https://mapnik.org/) and PostGIS without intermediate caching

# Version 1

This project has output compatible with Macrostrat's v1
tileserver, which was based on Node.js and TileStrata.
The legacy v1 tileserver code can be found in the
[`UW-Macrostrat/tileserver`](https://github.com/UW-Macrostrat/tileserver) repository.

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


