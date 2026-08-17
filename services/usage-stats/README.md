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
