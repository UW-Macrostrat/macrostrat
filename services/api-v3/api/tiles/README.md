# Tile routes

Vector, map, raster and elevation tiles, served by API v3 at its root. This was
the standalone tileserver until it merged into API v3; its history is in
`CHANGELOG.md` here and in the `tileserver-v*` tags. Image (PNG) tiles stay in
`services/legacy-tileserver`.

- Built from PostGIS functions (the design began from
  [TimVT](https://github.com/developmentseed/timvt)), with a database tile cache
  (L2) behind Varnish (L1).
- `register_tile_routes` mounts every route after API v3's own, since the layer
  catalog's `/{layer}/{z}/{x}/{y}` is the widest route in the table.
  `tile_lifespan` owns the asyncpg pool the routes share.

## Accessing tiles

Under `/api/v3`. The tile host (`tiles.macrostrat.local`, `tiles.macrostrat.org`)
rewrites these routes to `/api/v3` in the gateway's `tiles.caddy`, an allowlist
that shrinks toward `carto` and `carto-slim` as clients move to `/api/v3`.

- `/map/{slug}/{z}/{x}/{y}` — any source by slug or id, drawn through the
  compilation system; `carto` is the served map (`/dev/carto` is its deprecated
  alias) and `sys:carto-legacy` the materialized build. Every slug other than
  those two needs a delegated token with the `tiles:map` scope
  (`macrostrat auth create-token --scope tiles:map`) in `Authorization: Bearer`.
- `/carto-slim/{z}/{x}/{y}`, `/carto/{z}/{x}/{y}`
- `/map/{z}/{x}/{y}?source_id=<source_id>`
- `/all-maps/{z}/{x}/{y}` _(for development purposes only)_
- `/<layer>/tilejson.json` for any catalog layer

## Defining new layers

Layers are SQL or PL/pgSQL functions, registered in `_stored_function_layers`
in `__init__.py`.

## Testing

The tests restore a small dump into a throwaway PostGIS container (or
`TEST_DATABASE_URL`). From `services/api-v3`:

```
make test-tiles
```

`--skip-legacy-raster` omits the Mapnik test.
