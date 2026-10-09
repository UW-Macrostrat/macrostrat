# Worker changelog

## [Unreleased]

- `macrostrat.tasks.run` executes registered management tasks (`topology.update`, `maps.process-pipeline`)
  on the `admin` queue, with live terminal output and Ctrl-C-style cancel (`tasks` extra)
- The image carries its build in `MACROSTRAT_*` environment variables
