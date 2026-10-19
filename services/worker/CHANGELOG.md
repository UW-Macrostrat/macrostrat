# Worker changelog

## [Unreleased]

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
