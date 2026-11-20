# API v3 changelog

## [Unreleased]

## [3.2.0] - 2026-11-19

- `/refs` and `/refs/{id}` return references with geometry diagnostics; `/refs.geojson` returns them with their geometries
- Regions (the `geologic_boundaries` tables): `/regions`, `/regions/sources`
  and `/regions/{region_id}` in the API, and `/regions/tiles/{z}/{x}/{y}` tiles
- Updated Dockerfiles for quicker cached rebuilds
- `PATCH /security/users/{id}` also changes display name and email; an admin may edit their own record but not their own role
- `DELETE /security/users/{id}` deletes a user; tokens delegated to them are expired and kept
- `PATCH /security/tokens/{id}` replaces a token's scopes
- `GET /security/tokens` names the delegated user (`user_name`)
- `/security/login`, `/security/callback` and `/security/refresh` come from `macrostrat.auth_system` 1.2.0
- Sign-in checks a state nonce, and returns only to the API's own origin or one listed in `AUTH_RETURN_ORIGINS`
- A refresh token is no longer accepted as a session
- FastAPI 0.136 and Starlette 1
- `GET /columns/{col_id}/nearby` lists the columns, in any project, that overlap or lie within a kilometre of a column
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

## [3.1.2] - 2026-11-03

- `Sources` drops `rgeom`; `/sources?include_geom=true` no longer returns it

## [3.1.1] - 2026-10-24

- `/workers/version` lists the build each Celery worker reports; 503 when the broker is unreachable

## [3.1.0]

- Authentication cookie fixes, so that `dev` and production environments are not mixed.
- `/tasks`: start, watch (Server-Sent Events), cancel and kill runs of registered
  management tasks, recorded in `macrostrat_meta.task_run`. Admin only.

## [3.0.0] - 2026-10-19

- Removed `POST /security/token` and `GET /security/groups`; delegated tokens are issued at `POST /security/tokens`, listed at `GET /security/tokens` and revoked at `POST /security/tokens/{token_id}/revoke`
- `POST /columns/ingest` and `POST /columns/submit` take `project_id`, `col_group_id` and `col_group` to place columns, overriding the workbook's project
- `PATCH /columns/{col_id}/placement` moves a column to a project and group (administrators)
- Update callback url variable to `REDIRECT_URI` (`REDIRECT_URI_ENV` is still read)
- `/version` reports the running build; `/health` answers 503 when the database does not
- `GET /security/users`, `PATCH /security/users/{user_id}`, `GET /security/roles` and `GET /security/history` administer users
- `POST /security/role` switches the session to a lower role
- An `authorized` role, between `user` and `admin`, may view everything and edit nothing
- `/compilations` serves the compilation graph, each node with its members and neighbors, and batch edits (`PATCH`, administrators)
- `/bounds/{ident}/operations` and `/bounds/{ident}/build` edit and rebuild map boundaries
- `POST /cache/flush` and `POST /cache/refresh/carto` manage the tile cache
- `POST /columns/ingest`, `POST /columns/submit` and `GET /columns/ingest/{task_id}` ingest column workbooks through the worker; `GET /columns/examples` lists the example workbooks
- `PATCH /columns/{col_id}/geometry` sets a column's point and area
