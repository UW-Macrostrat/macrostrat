# API v3 changelog

## [Unreleased]

- `POST /columns/ingest` and `POST /columns/submit` take `project_id`, `col_group_id` and `col_group` to place columns, overriding the workbook's project
- `PATCH /columns/{col_id}/placement` moves a column to a project and group (administrators)
- Update callback url variable to `REDIRECT_URI`
- `/version` reports the running build; `/health` answers 503 when the database does not
