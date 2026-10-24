# Worker changelog

## [Unreleased]

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
