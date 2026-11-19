# API gateway changelog

## [Unreleased]

## [1.0.0]

- One image holding Caddy and Varnish with all gateway configuration, replacing the
  local-root Caddyfile and VCL and the cluster's ConfigMaps
- Shared API routes for the cluster and the local stack; the local stack now runs
  the API cache
- Tile VCL backends come from the environment; local `.mvt` tiles go to the core
  tileserver, as deployed
- The PostgREST trailing-slash redirect keeps the `/api` prefix
- `/api/gateway/version` reports the build
