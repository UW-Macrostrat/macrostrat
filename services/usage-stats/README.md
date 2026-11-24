# Usage stats worker

Harvests Traefik access-log dumps from object storage into the `usage_stats`
schema. Deployed as a Kubernetes CronJob.

A thin frontend over
[`macrostrat.usage_stats_capture`](../../py-modules/usage-stats-capture), which
holds the pipelines and ingest loop. This service's job is configuration: it
reads the environment and hands the library a database, storage credentials and
the hashing salt. The Macrostrat CLI is the other frontend over the same
library, configured from `macrostrat.toml`.

```bash
python -m usage_stats_service --prefix prod
```

| variable | |
|---|---|
| `USAGE_STATS_DATABASE_URL` | PostgreSQL URL (falls back to `MACROSTRAT_DATABASE_URL`, `DATABASE_URL`) |
| `USAGE_STATS_S3_ENDPOINT` / `_BUCKET` / `_ACCESS_KEY` / `_SECRET_KEY` | access-log object storage |
| `USAGE_STATS_CLIENT_SALT` | secret used to pseudonymize client addresses |
| `USAGE_STATS_TILE_HOSTS` | comma-separated hosts whose tile requests count (default `tiles.macrostrat.org`) |
| `USAGE_STATS_API_HOSTS` | comma-separated hosts whose Rockd dashboard loads count (default `macrostrat.org`) |

The salt must be **secret and stable**: a bare digest of an IPv4 address inverts
by brute force in seconds, and changing it forks `client_id`, silently breaking
deduplication against everything already ingested. Treat it like a database
credential.

Missing configuration exits `2` with a line naming the variables to set, so a
failing CronJob says why in its logs.

## Catching up

`capture` lists everything under the prefix, skips what is already recorded in
`usage_stats.processed_logs`, and processes the rest — there is no date window,
so the first run simply ingests the backlog. Set no `activeDeadlineSeconds` that
could kill it, and use `concurrencyPolicy: Forbid` so later ticks skip while it
runs. It is safely resumable: the `processed_logs` row is written last within
each object's transaction, so an eviction costs only the object in flight.

## Counting an instance's own traffic

By default every instance harvests production traffic. To count its own
instead, change its CronJob in `tiger-macrostrat-config` to read its Traefik's
prefix and hosts. The `macrostrat-dev` Traefik writes both development and
staging traffic under `dev`:

```yaml
args: ["--prefix", "dev"]
env:
  - name: USAGE_STATS_TILE_HOSTS
    value: tiles.dev.macrostrat.org,tiles.staging.macrostrat.org
  - name: USAGE_STATS_API_HOSTS
    value: dev.macrostrat.org,staging.macrostrat.org
```

Once that is applied, and no job from the old configuration is still running,
clear the instance's data. The ledger goes with it, so the next run backfills
the new prefix:

```sql
TRUNCATE usage_stats.processed_logs,
  usage_stats.tileserver_day_index, usage_stats.tileserver_location_index,
  usage_stats.tileserver_source_index, usage_stats.tileserver_throttled_clients,
  usage_stats.rockd_dashboard_loads;
```

This also clears the pre-switchover lineage, which is production history;
`macrostrat usage-stats import-legacy` restores it if wanted.
