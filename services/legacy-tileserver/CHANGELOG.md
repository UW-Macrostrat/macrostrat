# Legacy tileserver changelog

## [Unreleased]

- The `X-Macrostrat-Sources` lookup uses the face index; it scanned every face, ~3.5 s per uncached tile
- Image tiles draw the legacy `carto.*` build unless `LEGACY_CARTO_FROM_COMPILATION` is set; set, carto's member is resolved per render, not at startup
- `/version` reports the running build; `/health` answers 503 when the database does not. On the tiles host: `/legacy/version`, `/legacy/health`
