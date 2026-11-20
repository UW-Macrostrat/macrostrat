# Worker changelog

## [Unreleased]

## [1.2.0] - 2026-11-19

- Updated Dockerfiles for quicker cached rebuilds
- `/rasters/layer/{layer}` serves any layer in the raster index by name, for tokens scoped `tiles:map`
- `rasters.scan` task registers the rasters under a bucket prefix, without a layer
- `macrostrat.raster_index` 0.4.0
- `/tasks/{task}/recent/{param}` lists the values a parameter took in recent runs; the scan prefix is marked to offer them
- `/rasters/raster/{raster_id}` serves one indexed raster by id, in a layer or not, for tokens scoped `tiles:map`
- `/rasters/layer/{layer}/WMTSCapabilities.xml`: WMTS for any indexed layer, one layer per class where it has a vocabulary
- Removed the configured `/rasters/emit-minerals` mount; the layer is served at `/rasters/layer/emit-minerals`
- `/rasters/layer/{layer}` also accepts delegated tokens scoped `rasters:<layer>`, for that layer alone
- Configured raster layers are served at `/rasters/layer/<slug>`, overriding the by-name defaults for that slug; `/rasters/elevation` moves to `/rasters/layer/elevation`
- Removed the per-layer `/rasters/<slug>/refresh` routes, which never flushed; `POST /cache/refresh/rasters` does

## [1.1.3] - 2026-10-28

- `topology.update` no longer holds its first connection idle in a transaction for the whole run

## [1.1.2] - 2026-10-24

- A `build` inspect command reports the worker's build and queues over the broker

## [1.1.1] - 2026-10-23

- Fixes a bug in `macrostrat bounds build` that caused failure for global maps.

## [1.1.0] - 2026-10-23

- `macrostrat.tasks.run` executes registered management tasks (`topology.update`, `maps.process-pipeline`)
  on the `admin` queue, with live terminal output and Ctrl-C-style cancel (`tasks` extra)

## [1.0.0] - 2026-10-19

- Column ingestion takes a `placement` (project, and group by id or name) that overrides the workbook's project
- Column geometry may be a `LINESTRING` / `MULTILINESTRING` traverse; a point within 1 km of it is kept
- Units sheet: `axis_type`, and `fill_values` to carry blank cells from the previous row (`none` ends a run); missing bounds are filled from adjacent surfaces
- An optional `facies` sheet names the lithologies and environments units refer to; `environment` cells split on `,` as well as `;`
- Each section of a column is checked as its own age model
- Non-WKT geometry, unknown compilation codes, starred headers and incomplete refs are reported as notices instead of failing the write
- Lookup tables are refreshed for the units an ingest writes
- The image carries its build in `MACROSTRAT_*` environment variables
- Column ingestion writes rows in batches rather than one statement per row
