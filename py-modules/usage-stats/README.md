# Usage stats

Harvests Macrostrat and Rockd usage statistics out of the Traefik access-log
dumps in object storage, and aggregates them into the `usage_stats` schema of
the core Macrostrat database.

Log objects are zstd-compressed JSONL, date-partitioned under `prod/YYYY/MM/DD/`
in the `access-logs` bucket — one Traefik access-log record per line.

## Pipelines

Each pipeline picks its own records out of the shared log stream and maintains
its own tables:

- **`tileserver`** — tile requests, aggregated into `tileserver_day_index`
  (per layer/day/referrer/cache-status) and `tileserver_location_index`
  (z≤8 spatial cells) for the request-density heatmap.
- **`rockd-dashboard`** — Rockd app dashboard loads, stored raw with the
  GPS coordinates the app reported.

A single `capture` run streams each log object **once** and feeds every pipeline
that hasn't yet processed it — a full backfill moves ~15–20 GB, so re-reading
the objects per pipeline is not affordable.

## Usage

```bash
# Ingest all log objects not yet seen (all pipelines)
macrostrat usage-stats capture

# Backfill a single pipeline over history
macrostrat usage-stats capture --pipeline rockd-dashboard

# Try a few objects first
macrostrat usage-stats capture --limit 5
```

`capture` is idempotent and resumable: each object is recorded in
`usage_stats.processed_logs` per pipeline, written last within the object's
transaction, so an interrupted run re-processes only the object it died on.

See the `Usage stats` feature-area document for the design and the dated
progress log.
