---
api-v2: minor
---

- `mobile/map_query` and `mobile/map_query_v2` answer from `carto` when no `source` is given and `CARTO_BUILD=compilation`; `mobile/map_query` accepts `source`
- `/geologic_units/map/legend?carto=<scale>` lists the compilation's legend for that scale under `CARTO_BUILD=compilation`
- `/geologic_units/burwell` queries `maps.polygons` once for all scales instead of a `UNION` of the per-scale views
