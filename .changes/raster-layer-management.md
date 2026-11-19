---
tileserver: minor
api-v3: minor
worker: minor
---

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
