---
tileserver: minor
api-v3: minor
worker: minor
---

- `/rasters/layer/{layer}` serves any layer in the raster index by name, for tokens scoped `rasters:admin`
- `rasters.scan` task registers the rasters under a bucket prefix, without a layer
- `macrostrat.raster_index` 0.4.0
