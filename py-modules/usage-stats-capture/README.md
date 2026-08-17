# macrostrat.usage_stats_capture

Log-harvesting pipelines for Macrostrat usage statistics: reads Traefik
access-log dumps from object storage and aggregates them into the `usage_stats`
schema.

**A pure library.** It holds no configuration, no CLI and no Dockerfile — callers
pass in a database, storage credentials, and (for the Rockd pipeline) the salt
used to pseudonymize client addresses. Two frontends build on it:

- [`services/usage-stats`](../../services/usage-stats) — the deployed worker,
  configured from environment variables.
- [`py-modules/usage-stats`](../usage-stats) — the Macrostrat CLI subsystem,
  configured from `macrostrat.toml`, plus reporting.

```python
from macrostrat.usage_stats_capture import S3Params, capture, get_pipelines

capture(db, S3Params(...), get_pipelines(client_salt=salt), prefix="prod")
```

## Pipelines

Each picks its own records out of the shared log stream and owns its tables:

- **`tileserver`** — tile requests, aggregated into day and z<=8 location indexes.
- **`rockd-dashboard`** — Rockd app dashboard loads, stored raw with the GPS
  coordinates the app reported.

One `capture` run streams each object **once** and feeds every pipeline that
hasn't processed it — a full backfill moves 15-20 GB, so re-reading per pipeline
is not affordable. Idempotent and resumable: each object is recorded per pipeline
in `usage_stats.processed_logs`, written last within the object's transaction.

The schema SQL lives here too, beside the pipelines that write those tables; it
is registered with the schema builder by the CLI package.
