# MariaDB CLI — archived

The `macrostrat mariadb` subsystem: dump, restore, and the one-time
MariaDB → PostgreSQL migration. Moved here from
`py-modules/cli/macrostrat/cli/database/mariadb/` and **not wired up** — the
registration in `entrypoint.py` is gone, so the commands no longer exist.

| Was | Did |
| --- | --- |
| `macrostrat mariadb dump` | `mysqldump` of the v1 database |
| `macrostrat mariadb restore` | Load a gzipped MariaDB dump |
| `postgresql_migration/` | The one-time v1 → v3 migration, plus `_old-migration-scripts/` |

It was already registered `deprecated=True` under a "Legacy" help panel and
only appeared at all when `mysql_database` was set in `macrostrat.toml`, so
archiving is the next step on a path it was already on rather than a new
decision. The v1 → PostgreSQL migration has happened; a one-time migration
kept as a live command is a footgun and nothing else.

## What was deliberately left in place

MariaDB has a wider footprint than this directory, and the rest is **not**
dead:

- **`macrostrat.core.config`'s `mysql_database` / `MYSQL_DATABASE`** — still
  read by `py-modules/cli/macrostrat/cli/database/_legacy.py`, which
  `schema_management/migrations.py` imports for `get_db`. Removing it would
  break migrations.
- **`local-root/docker-compose.yaml`'s `mariadb` service** — infrastructure
  config, and whether the local stack still needs it is a separate call.
- **The v1 command framework** (`cli/commands/process_scripts/*`, which pass a
  `mariadb` connection around) — a different legacy layer, untouched here.
- **`"macrostrat-mariadb"` in `schema/_migrations/*/depends_on`** — historical
  migration *identifiers*. Renaming them would change which migrations are
  considered applied. Do not touch.

## If this is revived

It was on the list of commands to put behind Stage 2's write gate
(`require_write_access(WriteScope.Data)`) and never got there, because
archiving it was the better answer. Anything revived from here needs that gate
before it runs against a non-local environment.
