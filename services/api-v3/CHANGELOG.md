# API v3 changelog

## [Unreleased]

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
