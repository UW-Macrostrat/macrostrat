---
api-gateway: minor
---

- One cache for `/api` and the tile host, with separate `tiles` and `api` storages (`VARNISH_TILE_SIZE`)
- The tile host is rewritten to API v3 in `tiles.caddy`, so a tile has one cache entry across both hosts; only the tileserver's routes are served there, other paths get a 404
- Render throttle, high-zoom bypass and tile lifetime apply to tile routes under `/api/v3` too
- The throttle counts the client Caddy names in `X-Gateway-Client` (`trusted_proxies`, strict)
- New `MACROSTRAT_TILESERVER_LEGACY_HOST` and `GATEWAY_TILE_HOSTS`; `tiles.vcl` stays until the cluster retires the separate tile cache
