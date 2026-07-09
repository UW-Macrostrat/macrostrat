# Macrostrat schema management utilities

This module contains utilities for managing Macrostrat's database schema.
It includes tools for dealing with both a stateless, diff-based schema migration
approach and stateful tools for handling specific schema changes that need to occur.

See the [`schema`](https://github.com/UW-Macrostrat/macrostrat/tree/main/schema) directory for more information.

## Composition

The declarative schema is assembled from **chunks** (`macrostrat.core.SchemaDefinition`)
ordered by a dependency graph, rather than by filename:

- `chunks.py` — the explicit list of chunks and their `depends_on` edges. Each
  chunk `provides` a `.sql` directory, a single file, or a function (e.g. the
  colocated `TopologySchema`).
- `composer.py` — `build_schema(db, env, target=…)` topologically sorts and applies
  chunks. `target` is a **subsystem/chunk name**; only that chunk and its
  transitive dependencies are built.
- `test_harness.py` — `DatabaseTestHarness` builds progressively, chunk by chunk,
  skipping already-applied chunks, with an `optimize` transform for fast test builds.

`macrostrat schema graph` lists the chunks and order; `macrostrat schema provision [TARGET]`
builds them.

## Other capabilities

- **Two migration models.** A stateless, diff-based flow (`macrostrat schema plan` / `apply`,
  backed by `migra`) reconciles structure against the composed ideal; stateful `Migration`
  classes (`macrostrat schema migrate`) handle transitions the diff can't express — renames,
  backfills, data-dependent changes — gated by pre/postconditions.
- **`macrostrat schema sync`** re-applies everything a schema diff *can't* manage on its own —
  **views**, **procedures/functions**, idempotent **seed data**, and **grants** — so that
  **`provision` ≡ `diff` + `sync`** (same schema *and* seed data either way). These are idempotent
  and often interleaved with other DDL. Select a subset with `--no-views` / `--no-procedures` /
  `--no-data` / `--no-permissions`, and restrict to a subsystem with the shared
  `--target` / `--no-dependents` option block (see below). Per category:
    - *views* (`views.py`) — `CREATE OR REPLACE` by default; drop-and-recreate (restoring grants)
      only on a signature change (SQLSTATE 42P16), via the `macrostrat.database` `on_error` hook.
    - *procedures* (`procedures.py`) — `CREATE OR REPLACE FUNCTION`/`PROCEDURE`; signature changes
      are left to the diff.
    - *seed* (`seed.py`) — re-run the data-writing statements (`INSERT`/`UPDATE`/`DELETE`/`MERGE`,
      including `WITH … INSERT`), detected by `sqlparse` statement type. These must be idempotent;
      an `INSERT` without `ON CONFLICT` is warned about.
    - *grants* (`grants.py`) — re-run every `GRANT` / `REVOKE` / `ALTER DEFAULT PRIVILEGES`.

  Structure (tables, columns, constraints, views, functions, triggers) otherwise stays
  diff-managed (migra sequences view/table drop-recreate); `sync` re-asserts the re-runnable
  content the diff is blind to (especially data).
- **Shared `--target` / `--no-dependents` option block** (`rebuild.py`) — reused by `sync` and
  `provision`. `--target NAME` restricts to a subsystem; its dependency closure is included unless
  `--no-dependents`. Resolved by `composer.selected_chunks`.
- **Enforced read-only access** (`readonly.py`) — `readonly_login` mints an ephemeral,
  privilege-limited login role (`pg_read_all_data` plus optional impersonation roles) so tests
  against a live database genuinely cannot write; `assert_read_only` fails closed, and
  `as_role` runs reads as a specific role for grant / RLS testing.
- **Testing** — `DatabaseTestHarness` builds schema progressively; a drift test asserts the
  declarative build has an empty `plan` against its own freshly-built ideal.

## Direction

The composer is in place, but the reorientation to fully modular subsystems is **not finished**.
Intended next steps:

- **Colocate** each subsystem's `.sql` with its owning module (as `map-topology` already does
  with `TopologySchema`), and *discover* chunks rather than listing them centrally in `chunks.py`.
- **Decompose `core`** (today `public → macrostrat → core`-remainder) into finer named subsystems
  with real `depends_on` edges.
- **Unify migrations into the chunk graph** so a `SchemaDefinition` owns both its declarative
  providers and its condition-gated `Migration`s — a subsystem's structure, transitions, and seed
  data in one place.
- **Template-database isolation** for faster, hermetic test databases.
