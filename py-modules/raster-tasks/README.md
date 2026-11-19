# macrostrat.raster-tasks

Management tasks for the raster index (`macrostrat.raster_index`), registered
with `macrostrat.task-runner`.

- `rasters.scan` — register every raster under a bucket prefix. It names no
  layer: what it finds is unassigned until an administrator places it in one.

The base install is the task catalog only, which the API serves. The `index`
extra adds the libraries that read rasters, for the admin worker.
