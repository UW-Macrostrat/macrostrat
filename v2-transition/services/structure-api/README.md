# Corelle

**Corelle** is a simple system for reconstructing the location of tectonic
plates back in geologic time. The software is compatible with **GPlates**, but it
is designed specifically to support interactive web visualizations. It is named
for the venerable dinnerware owned by everyone's grandma.

## Useful links

- [CHANGELOG](CHANGELOG.md)
- [Demo: pre-split coastline features](https://birdnest.geology.wisc.edu/corelle)
- [Demo: externally-provided features](https://davenquinn.com/viz/corelle-demo-pbdb)
- [Demo: regional rotation model](https://davenquinn.com/viz/corelle-demo-neogene-north-america)
- [Notebook: basic usage from Python](notebooks/Corelle-Basic-Usage.ipynb)
- [Notebook: advanced usage – building a paleolatitude history curve](notebooks/Corelle-Paleolatitude.ipynb)

## Corelle's goals

Corelle is designed for "simplicity", in two broad categories:

### Focused and well-defined capabilities

Corelle faithfully implements a subset of [**GPlates**](https://www.gplates.org/) functionality supporting the rotation of existing plate models.
While GPlates is a capable and complete system for building and rendering plate models,
its sophistication (and that of its [PyGPlates](https://www.gplates.org/docs/pygplates/) binding) comes at a cost of complexity
that inhibits installation, usage, and integration with other systems.

**Corelle** is primarily designed for use by geoscientists outside of the
tectonics domain, and makes it simple to achieve basic rotations. Its
client/server design allows use in "satellite" applications without the
overhead of a full GPlates system. This allows the integration of dynamic plate
reconstructions into a variety of apps and analytical processes.

### Efficiency for web visualization

Corelle's architecture balances simplicity and power — its key advance is to
calculate rotations on the server but leave the last step (rotating
paleogeographic features to their final positions) to be run separately by each
application.

The final step in plate reconstruction, applying a vector rotation to geographic
features, is mathematically simple but highly dependent on the input data —
leaving it for the client makes it _much_ quicker to rotate large amounts of
data dynamically through time, since map data doesn't have to repeatedly traverse
the network.

Some examples from the [Seton et al., 2012](https://www.sciencedirect.com/science/article/abs/pii/S0012825212000311) rotation model:

- [Global rotations at 20 Ma](https://birdnest.geology.wisc.edu/corelle/api/rotate?model=Seton2012&time=20) weigh in at 33 kB.
- [Global rotations at 1 Myr intervals from 100 Ma to the present](https://birdnest.geology.wisc.edu/corelle/api/rotate-series?model=Seton2012&time_start=100&time_end=0&interval=1) take up 2.8 MB.

Since features are rotated at the point of use, the Corelle server is only responsible for tracking the rotations themselves, allowing for much more modular and composable systems.

## Structure of the project

Corelle's plate rotation engine is built on a PostgreSQL/PostGIS database (to track the plate dependency tree and
run geospatial operations). quaternion rotation vectors are accumulated in Python.
Modeled rotation vectors are sent to be applied by separate software on the client;
simple client libraries for [Python](notebooks/corelle_helpers.py) and [Javascript](https://www.npmjs.com/package/@macrostrat/map-components)
are provided here.

Corelle's public-facing API is
in beta but will eventually be integrated with [Macrostrat](https://macrostrat.org)'s core services,
which already power plate rotations in [PBDB](https://paleobiodb.org) and other projects.
Upcoming work will focus on integrating new plate models with these applications.

This repository contains several related components:

- An API server that provides rotations from several
  GPlates `.rot` files and associated plate polygons.
- A testing suite that validates conformance to GPlates results.
- The `@macrostrat/corelle` Javascript library, which implements quaternion rotations
  to display rotations.
- An example web application that implements basic plate motions atop
  several common plate models.

## Installation

### Local development

A recent (>3.6) version of Python is required to run the backend code. A recent
version of Node.js is required to bundle the frontend. The Python module expects
to use the `postgresql:///plate-rotations` database by default, but this can be
easily changed using the `CORELLE_DB` environment variable.

To install the backend, run `make install` in this repository. The `corelle`
executable should be installed on your path. `make init` imports models and
feature datasets. Then `corelle serve` starts the testing API server.

To build (and continuously watch) the frontend, run `make dev`.
A backend API server will be started and proxied, so you don't have to run
`corelle serve`.

### Installation with Docker

Simply install Docker and run `docker-compose up --build` in the root directory.
This will build the application, install test data, and spin up the development server.

You can run a development version by creating a `.env` file containing
`COMPOSE_FILE=docker-compose.yaml:docker-compose.development.yaml` in the root
directory. This will tell Docker to spin up the frontend container using settings
for auto-rebuilding.

## Todo

- [x] Fix subtle math bugs!
- [ ] On-database cache of rotations (say, at 1 Ma increments?)
- [ ] Return pre-rotated feature datasets (rather than just modern versions)
- [x] Materialized view for split feature datasets
- [x] Allow feature datasets to be listed
- [x] Create a dockerized version
- [x] Polish the frontend demo

## API Reference

### Get valid models

Returns a list of available models

```
/api/model
```

### Rotate a point

Pass points as a URLEncoded, space-separated list of comma-separated lon-lat pairs.
E.g. `20,-20 10,10` to rotate two points becomes

```
/api/point?model=Seton2012&data=20,-20%2010,10&time=40
```

### Rotation primitives

This route gives you the axis-angle or quaternion representation of plate rotations
at the specified time, for client-side rotation of points.

#### All rotations defined by the model

```
/api/rotate?time=10&model=Seton2012&quaternion=true
```

#### Rotation for a specific plate

```
/api/rotate?time=10&model=Seton2012&plate_id=quaternion=true
```

#### Return formats

##### Axis-angle

```json
{
  "axis": [0.027206502237792123, 0.013804853692062557, -0.03262231893894808],
  "angle": 0.08936020386653408,
  "plate_id": 311
}
```

##### Quaternion

```json
{
  "quaternion": [
    0.9990020102870522,
    0.027206502237792123,
    0.013804853692062557,
    -0.03262231893894808
  ],
  "plate_id": 311
}
```

### Features for rotation

For right now, features are not returned pre-rotated, but this capability will
be added to the API. Instead, features are returned as-is, with
`plate_id`, `old_lim`, and `young_lim` properties so they can be rotated client-side.

#### A named feature dataset

Arbitrary feature datasets (imported in advance on the backend).
The datasets are returned split on plate boundaries and so they can be
rotated on the client side.
The example below fetches the `ne_110m_land` dataset.

```
/api/feature/ne_110m_land?model=Seton2012
```

TODO: allow listing of all named feature datasets.

#### Modern plate polygons

This route returns the plate polygons features themselves.

```
/api/plates?model=Seton2012
```
