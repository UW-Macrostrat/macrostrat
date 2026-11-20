# API gateway

Caddy routing and Varnish caching for Macrostrat's API and tile hosts, in the
cluster and in the local stack. Its scope is `/api` and the tile host; the website
and other hosts are routed by Traefik in the cluster. `Caddyfile.local` also serves
the website, storage and `old.macrostrat.local` only because it stands in for
Traefik locally. One image holds both binaries and all
configuration, so a single tag guarantees the Caddyfiles and VCLs match; it runs
as separate Caddy and Varnish containers, each with its own limits, restarts and
logs.

```
/api ─▶ Caddy :80 (strips /api) ─▶ Varnish :8000 (api.vcl) ─▶ Caddy :8080 (routes) ─▶ v2 / v3 / PostgREST / knowledge graph
tiles ─▶ Varnish :8000 (tiles.vcl) ─▶ core and legacy tileservers
```

| Path | |
|---|---|
| `config/caddy/routes.caddy` | routes shared by both environments |
| `config/caddy/Caddyfile.cluster` | `:80` and `:8080`; Traefik terminates TLS |
| `config/caddy/Caddyfile.local` | the `.local` hosts, local CORS, storage, web |
| `config/varnish/api.vcl` | the API cache, in the gateway's pod |
| `config/varnish/tiles.vcl` | the tile cache; backend hosts from the environment |
| `bin/gateway` | entrypoint: `caddy`, `varnish`, `reload-caddy`, `reload-varnish`, `validate` |

## Environment

| Variable | Container | |
|---|---|---|
| `GATEWAY_ENV` | Caddy | `cluster` (default) or `local` |
| `MACROSTRAT_API_V2_HOST`, `_API_V3_HOST`, `_API_POSTGREST_HOST`, `_TILESERVER_HOST` | Caddy | upstreams |
| `MACROSTRAT_KG_API_HOST` | Caddy | knowledge graph upstream; unset answers 502 |
| `GATEWAY_API_CACHE` | Caddy, local | `localhost:8080` skips the API cache |
| `GATEWAY_VCL` | Varnish | `api` (default) or `tiles` |
| `TILESERVER_HOST`, `TILESERVER_LEGACY_HOST` | Varnish, tiles | backend hosts; `_PORT` variants default to 80 |
| `VARNISH_HTTP_PORT`, `VARNISH_SIZE` | Varnish | listen port (8000) and cache size (100M) |
| `TILE_THROTTLE_BURST`, `_SUSTAINED`, `_BLOCK` | Varnish, tiles | renders allowed per client in 10 s (300) and 10 min (3000), and how long one over either stays marked (10m) |

Extra arguments to `gateway varnish` pass to `varnishd`, e.g. `-p nuke_limit=500`.

## Tests

```bash
docker compose -f tests/compose.yaml up -d --build
python3 -m unittest discover -s tests -v
```

The stack runs the cluster configuration against echoing stand-in upstreams.
`Caddyfile.local` is checked by `gateway validate` only.

The version is in `package.json`, released like the other services.
