# Macrostrat tileserver — conventions

FastAPI service serving Mapbox Vector Tiles (MVT) and related JSON. Each sub-feature
is an `APIRouter` in `macrostrat/tileserver/<feature>/`, mounted with a prefix in
`macrostrat/tileserver/__init__.py` (e.g. `topology` → `/dev/topology`).

## Tile endpoints

- SQL lives in `<feature>/queries/*.sql`, loaded via `get_query(name)` / `get_sql(...)`.
- Render with **buildpg**: `query, params = render(sql, **kwargs)`, then
  `await con.fetch(query, *params)` (or `fetchval`); wrap MVT bytes in
  `VectorTileResponse`. See the `_render_tile` helper in `topology/`.
- **asyncpg takes positional args only.** Never `con.fetch(query, lng=..., lat=...)`
  — that raises `TypeError`. Bind values as buildpg `:name` placeholders and let
  `render` position them.
- Placeholders: buildpg `:name` is a bound value. A `::name` slot (double colon) is a
  *raw template* filled by `str.replace` BEFORE `render` (e.g. `::where_clauses`),
  not a bound value.

## MVT generation

- `SELECT ST_AsMVT(<rel>, '<layer-name>', 4096, 'geom') FROM <rel>` — the first arg
  MUST name the relation in the `FROM` clause. A mismatch errors at runtime with
  *"missing FROM-clause entry for table <rel>"*.
- **`'<layer-name>'` is a contract with the web client**: it becomes the Mapbox
  `"source-layer"`. Renaming it, or adding a new tile route, requires a matching
  change in `web` (`pages/dev/map/topology` for topology layers).
- Tile geometry helpers: `ST_TileEnvelope(:z,:x,:y)`,
  `tile_layers.geographic_envelope(:x,:y,:z, buffer)`,
  `tile_layers.tile_geom(geom, mercator_bbox)`.

## FastAPI parameters

- A bare Pydantic model as a GET parameter is interpreted as a request **body**,
  which is unusable from a tile/`fetch` GET. Use scalar query params instead
  (`lng: float, lat: float, map_layer: str = None`).

## Running

- Changes here are Python/SQL and do **not** hot-reload. Rebuild the stack with
  `macrostrat up` (docker compose) to pick them up.
