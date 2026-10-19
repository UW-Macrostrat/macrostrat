# Legacy tileserver changelog

## [Unreleased]

- Image tiles draw the legacy `carto.*` build unless `LEGACY_CARTO_FROM_COMPILATION` is set; set, carto's member is resolved per render, not at startup
- `/version` reports the running build; `/health` answers 503 when the database does not. On the tiles host: `/legacy/version`, `/legacy/health`
