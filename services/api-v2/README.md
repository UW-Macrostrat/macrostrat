# Macrostrat API

The API for SCIENCE

## About

The Macrostrat API provides diverse macrostratigraphic and geologic data in a
concise, queryable format.

## Prerequisites

#### Software

MariaDB, PostgreSQL, Nodejs, and the
[Macrostrat system](https://github.com/UW-Macrostrat/macrostrat) are required.
Redis is optional. When the API starts requests for all columns and all units
are cached. If Redis is available it will be used, otherwise they are cached in
the application memory.

The API requires `node` v20 or to run.

## Data

The `macrostrat` PostgreSQL database must be available.

## Setup

First clone the repo:

```
git clone https://github.com/UW-Macrostrat/macrostrat-api.git
cd macrostrat-api
```

Next, install dependencies:

```
yarn install
```

## Running the API

Add environment variables to your shell or `.env` file. The
`MACROSTRAT_DATABASE_URL` variable is required.

To start the API run `npm start <port|5000>`. This will start the API on the
specified port (default 5000).

## Running tests

Tests can be run with `yarn test`. Currently, you must have a local instance of the
API running separately (e.g., `yarn start` or `yarn run dev`). You can also set
the `TEST_API_URL` variable to a different URL if you want to test a
different instance.

Additionally, you can set a `TEST_PRODUCTION_API_URL` to run comparisons against
another running instance of the API (e.g., production). This is useful for
ensuring that new versions of the API return the same results as older versions.

## Generating a release

Update the version string in `package.json` and run:

```
make release
```

This will simply add a tag that can be picked up by the CI/CD system to deploy
the application.

**Old config below. We now use env variables specifying which db and environment
to connect to.** For `credentials.ts` fill in your MariaDB and PostgreSQL user
information, update the port for Redis if necessary, and follow the inline
instructions for generating a cache refresh key. The cache refresh key is used
as a secret parameter to programmatically refresh the column cache, such as in
situations in which the underlying data has been changed (editing, adding, etc).

## Data

Required databases (version 1):

- MariaDB - macrostrat
- Postgres - burwell, alice, wof, elevation

## Running

To start the API simply run `npm start` which will start a process on port 5050.
Note that the default port was changed from 5000 to 5050 to avoid a port
conflict introduced in recent versions of commonly used OSs. To use a different
port, you can specify it during startup as so: `node server.js 5151`.

For production use `pm2` is recommended. To start as a single process:

```
pm2 start server.js --name macrostrat-api
```

or, to start in a load balanced mode with two processes:

```
pm2 start server.js --name macrostrat-api -i 2
```

For more information about managing processes with pm2 see the
[Macrostrat Wiki](https://github.com/UW-Macrostrat/lab/wiki/Nodejs-based-application-management)

## Other useful things

#### Caching

The Macrostrat API caches three specific request responses:

- All columns with geometry (`/columns?all&format=geojson_bare`)
- All columns without geometry (`/columns?all`)
- The summary of all units used in the response of the above routes

To refresh this cache without restarting the API you can make an HTTP GET
request to `/api/v2/columns/refresh-cache?cacheRefreshKey=<cacheRefreshKey>`
where `<cacheRefreshKey>` refers to the valuable of the variable with the same
name found in `./credentials.js`.

This is primarily used by scripts in the Macrostrat CLI to ensure that the API
is reporting the most recent data after columns have been added, removed, or
otherwise edited.

### Test

```
yarn test
```

### Organization

Each version of the API functions as a self-contained module, and therefore has
its own `package.json` and dependencies.

### Authors

[John J Czaplewski](https://github.com/jczaplew) and
[Shanan E Peters](http://strata.geoglogy.wisc.edu)

### License

CC0 for all code unique to this API.
