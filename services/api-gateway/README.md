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
/api ──────▶ Caddy :80 (strips /api) ─────┐
                                          ├─▶ Varnish :8000 (api.vcl) ─▶ Caddy :8080 (routes) ─▶ v2 / v3 / PostgREST / KG / legacy tileserver
tile host ─▶ Caddy :80 (tiles.caddy) ─────┘
```

The tile host is a set of rewrites in `tiles.caddy`: the tileserver's routes as
they stood before it merged into API v3 go to `/v3/…`, image tiles to
`/legacy-tiles/…`, and anything else gets a 404. A tile therefore has one cache
entry whichever host asked for it. Varnish keeps tiles and API responses in
separate storages, `tiles` and `api`, so each evicts on its own;
`ban obj.http.X-Cache-Profile != api` expires every tile. Tile rules (render
throttle, no caching above zoom 14, a one-day lifetime) follow the trailing
`/{z}/{x}/{y}`, wherever the route sits.

`tiles.vcl` is the separate tile cache the cluster runs until it moves to this
one; delete it then.

| Path | |
|---|---|
| `config/caddy/routes.caddy` | routes shared by both environments |
| `config/caddy/tiles.caddy` | the tile host: allowlist and rewrites |
| `config/caddy/Caddyfile.cluster` | `:80` and `:8080`; Traefik terminates TLS |
| `config/caddy/Caddyfile.local` | the `.local` hosts, local CORS, storage, web |
| `config/varnish/api.vcl` | the cache for /api and the tile host, in the gateway's pod |
| `config/varnish/tiles.vcl` | the separate tile cache, until the cluster retires it |
| `bin/gateway` | entrypoint: `caddy`, `varnish`, `reload-caddy`, `reload-varnish`, `validate` |

## Environment

| Variable | Container | |
|---|---|---|
| `GATEWAY_ENV` | Caddy | `cluster` (default) or `local` |
| `MACROSTRAT_API_V2_HOST`, `_API_V3_HOST`, `_API_POSTGREST_HOST`, `_TILESERVER_HOST` | Caddy | upstreams |
| `MACROSTRAT_KG_API_HOST` | Caddy | knowledge graph upstream; unset answers 502 |
| `MACROSTRAT_TILESERVER_LEGACY_HOST` | Caddy | legacy image tileserver; unset answers 502 |
| `GATEWAY_TILE_HOSTS` | Caddy, cluster | hostnames served as the tile host (`tiles.macrostrat.org`), space-separated |
| `GATEWAY_API_CACHE` | Caddy, local | `localhost:8080` skips the API cache |
| `GATEWAY_VCL` | Varnish | `api` (default) or `tiles` |
| `TILESERVER_HOST`, `TILESERVER_LEGACY_HOST` | Varnish, tiles | backend hosts of the separate tile cache; `_PORT` variants default to 80 |
| `VARNISH_HTTP_PORT`, `VARNISH_SIZE` | Varnish | listen port (8000) and API storage size (100M) |
| `VARNISH_TILE_SIZE` | Varnish, api | tile storage size (100M) |
| `TILE_THROTTLE_BURST`, `_SUSTAINED`, `_BLOCK` | Varnish | renders allowed per client in 10 s (1500) and 10 min (10000), and how long a client over either is refused (10m) |
| `TILE_THROTTLE_MODE` | Varnish | `enforce` (default) answers 429; `report` serves and marks `X-Throttle: would-deny` |

Extra arguments to `gateway varnish` pass to `varnishd`, e.g. `-p nuke_limit=500`.

The render throttle counts clients by the address Caddy writes into
`X-Gateway-Client`: the rightmost untrusted entry of `X-Forwarded-For`, trusting
private ranges (Traefik). Internal callers are exempt.

## Tests

```bash
docker compose -f tests/compose.yaml up -d --build
python3 -m unittest discover -s tests -v
```

The stack runs the cluster configuration against echoing stand-in upstreams.
`Caddyfile.local` is checked by `gateway validate` only.

The version is in `package.json`, released like the other services.
