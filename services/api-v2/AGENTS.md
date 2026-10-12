# AGENTS.md

Conventions for `macrostrat-api`, Macrostrat's legacy v2 API: an Express app in
TypeScript, run directly with `tsx` (no build step).

## Layout

- `server.ts` starts the app; `v2/index.ts` mounts the routes. One route per file
  under `v2/`, with groups in `v2/carto/`, `v2/mobile/`, `v2/definitions/`.
- `v2/larkin.ts` is the shared toolkit: `queryPg`, `sendData`, `error`, `getRefs`
  and the capability checks. Read it before writing a route.
- `__archive/` is dead code. Don't edit it or copy from it.

## Running

- **Yarn 4 (PnP).** Use `yarn` for everything; ignore `npm` in the README.
- `yarn dev` serves with reload. Set `MACROSTRAT_DATABASE` (see `.env.example`).
- `yarn test` runs mocha against a *running* API (`TEST_API_URL`), not in-process.
- `yarn format` runs prettier.

## SQL

- All SQL is hand-written strings through `larkin.queryPg("burwell", sql, params)`.
  `"burwell"` is the `macrostrat` database under its old name.
- The schema belongs to [macrostrat](https://github.com/UW-Macrostrat/macrostrat).
  Never change it from here.
- **Capabilities** let a route use schema that not every database has yet:
  `checkCapabilities` probes at startup, and `hasCapability` gates the SQL (see
  `map-refs`). Use one rather than requiring a migration in lockstep.
- **Map tables are flat.** `maps.polygons`, `maps.lines` and `maps.lookup` are
  single tables with a `scale` column. Join them by key with `scale = ANY(…)`.
  Never `UNION ALL` the per-scale compatibility views (`maps.<scale>`,
  `lookup_<scale>`, `lines.<scale>`): the union loses the key lookup and scans
  every row of those scales (~13 s per request, 2026-10-12).
- `EXPLAIN` new joins and spatial queries against development before merging.

## Responses

`/mobile/*` and other public routes serve deployed clients. Change response
shapes additively, and keep old parameter names working (e.g. `compilation`
beside `source` on `map_query_v2`).

## Releases

CI releases on merge to `main`. A `package.json` version with no `v…` tag yet
is built, tagged and published. A stable version needs a `## [x.y.z]` heading
in `CHANGELOG.md`. Never create or push version tags by hand. Add terse,
one-line entries under `## [Unreleased]`.
