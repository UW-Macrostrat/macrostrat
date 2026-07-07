# macrostrat.map_utils

Lightweight map operations that work directly on the database (and object
store) — **no GIS dependencies** (no GDAL/geopandas/shapely).

This module is the single source of truth for operations like deleting a staged
map. Because its dependency footprint is small (`macrostrat.database`, `psycopg`,
`minio`), it can be imported by the Celery worker (`macrostrat.worker`), the API,
and the CLI (`macrostrat.map_integration`) alike, without any of them pulling in
the heavy GIS stack.

Configuration is **injected by the caller** — functions take a `Database` handle
and, where storage is involved, an explicit `StorageConfig` — rather than reading
global settings. This keeps the module decoupled and easy to reuse.

```python
from macrostrat.map_utils import delete_map, StorageConfig

delete_map(db, "my-map-slug")                       # DB-only
delete_map(db, "my-map-slug", storage=storage_cfg)  # also clears staged S3 objects
```
