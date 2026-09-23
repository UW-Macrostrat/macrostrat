# AGENTS.md

Conventions for the `macrostrat` monorepo — the core database management and web
services codebase.

## Database schema changes — ask first

**Never apply a schema change to a database without explicit review.** This
covers creating, altering or dropping tables, views, indexes, extensions and
functions, and running migrations — in **any** environment, local included.

Write the DDL, migration or schema chunk, explain what it will do, and **wait for
approval before applying it.** An instruction to make a specific change is
approval for that change, not standing permission for the next one.

Verifying SQL against a live database is fine when it is genuinely read-only, or
wrapped in a transaction that is rolled back — but **confirm the rollback
actually took effect.** `Database.run_sql()` executes through the `Database`
object's own session and ignores a `connection=` kwarg passed by the caller, so
wrapping it in an external transaction does not roll it back.

## Where the schema lives

- `schema/core/` — the foundational build, applied in filename order.
  `0000-globals.sql` creates **extensions** and runs as the connector
  (superuser); application chunks run as the `macrostrat` role and cannot create
  extensions.
- `schema/_definitions/`, `schema/_dev_definitions/` — subsystems discovered by
  frontmatter.
- `schema/_migrations/` — condition-based migrations. Each is a directory with an
  `__init__.py` defining a `Migration` subclass plus its SQL; discovery is by
  import, and application is decided by `preconditions` / `postconditions`
  rather than a linear version ledger. Directories without an `__init__.py` are
  inert.
- Some py-modules contribute their own chunks via `build_schema_config()` — see
  `py-modules/usage-stats` — collected in
  `py-modules/schema-management/.../chunks.py`.

**Seed data needs a file-backed provider.** `macrostrat schema sync` re-applies
the content a schema diff cannot manage — views, procedures, `INSERT`/`UPDATE`
seed rows, grants — by scanning each chunk's `Path` providers.
**Function-backed providers are skipped by design** (they manage their own
objects), so seed rows reachable *only* through a callable are invisible to
`sync`, and a diff-based deploy lands the table empty. `map-topology` is the one
chunk with a callable provider — topology setup is not plain SQL — so it lists
its fixture file as an additional `Path` provider too.

Seed statements **belong beside the tables they populate**, not in a separate
file: `sync` pre-filters each file to data statements (`INSERT`/`UPDATE`/
`DELETE`/`MERGE`), so surrounding DDL is ignored. Keep them idempotent
(`ON CONFLICT DO NOTHING`); `sync` warns about an `INSERT` without one.

Design migrations to be **order-independent and re-runnable**, and key
postconditions on something that only becomes true once the migration has
actually run (not on a state the declarative chunk could also produce).

**Compactness and clarity are explicit goals.** A migration should be readable
at a glance: plain `ALTER` statements over generated SQL, an `apply()` method
over a SQL file when it is only a few statements, and no defensive machinery for
states that will not occur in practice. Rationale and history belong in the
relevant `Feature areas` doc, not in the migration's docstring. Migrations are
also housed **with the code they touch** where a subsystem owns the schema (e.g.
`map_topology/migrations/`) rather than in the central tree; discovery is by
`Migration.__subclasses__()`, so importing the package from the subsystem is what
registers them.

**Running SQL by hand is fine for one-offs**, especially in local development —
not everything needs a migration. Reach for one when a change must reach other
environments or be reproducible; otherwise a direct statement is often the right
tool, and the condition-based design means a hand-applied change and a
migration-applied one converge on the same `APPLIED` state.

## SQL gotchas

- **No bare `%` in SQL that runs through SQLAlchemy** — including inside
  comments. The driver reads it as a bind parameter and fails with
  `incomplete placeholder`. Build dynamic SQL with `||` and `quote_ident()`
  rather than `format()`, and raise messages with `RAISE … USING MESSAGE =`
  rather than a `%`-format string.
- Similarly, a literal `:` in SQL (e.g. in a regex like `(?:www\.)`) trips
  SQLAlchemy's bind-parameter parsing and must be escaped as `\:`.
- **`OVERLAPS` is a reserved keyword** (the SQL period-overlap operator), so a
  CTE or alias cannot be named `overlaps` without quoting. The parse error names
  the CTE and gives no reason.
- **A bind parameter cannot be followed by a `::` cast.** SQLAlchemy's parameter
  regex refuses a name followed by `:`, so `:lng::float` is left in the statement
  as literal text and Postgres fails with `syntax error at or near ":"`. Write
  `CAST(:lng AS float)`. A cast on a *column* (`ma.area_km::float`) is fine.
- **Don't rewrite a spatial query without benchmarking it.** This has now gone
  wrong twice: a query over the map topology was restructured into a shape that
  cannot reach a spatial index, and in both cases the rewrite returned identical
  rows, passed every test, and was only caught by someone reading it. The map
  topology exists to make these queries cheap — `map_face` is a non-overlapping
  coverage per layer, so a location resolves to a few faces and each face is one
  indexed lookup against one map's polygons. Composing over something that hides
  that access path (a view over a `STABLE` function, a set-returning function in
  a `LATERAL`) reintroduces the full scan the coverage was built to avoid.
  Before and after any such change, run `EXPLAIN (ANALYZE, BUFFERS)` and check
  for a `Seq Scan` on a `maps.polygons` partition; a cost that does not vary with
  how much the request actually covers is the tell. See
  `Incidents/2026-09-20 Spatial queries rewritten past their indexes.md` in the
  workbench vault.
- **`map_bounds.polygons_of` is for one map and one envelope.** It bundles the
  mosaic walk (`content_of`) with the polygon lookup, which is right for the
  single-map tile query. `CROSS JOIN LATERAL`-ing it per face is not: the planner
  re-runs the mosaic walk per output row and loses the constant envelope it needs
  for the GiST index. Resolve `content_of` once per face, then join
  `maps.polygons` on `source_id` + `scale` directly.
- **Don't guard against "already exists".** Schema application tolerates errors,
  so state objects declaratively and let a duplicate raise, get noted, and be
  stepped over — existence pre-checks and `IF NOT EXISTS` scaffolding cost more
  than they buy. Classify such an error by SQLSTATE off the wrapped driver
  exception (`err.orig`), reading psycopg 3's `sqlstate` **or** psycopg 2's
  `pgcode` — both drivers are installed.
- **Never wrap an error-tolerating sweep in `db.transaction`.** `run_sql` gives
  each statement its own transaction *only* when the session isn't already in
  one; inside `db.transaction` a failed statement rolls back the caller's
  transaction instead, and the fixture's own rollback then fails.

## Environments and write safety

Read **`docs/Environment configuration and write safety.md`** before running
anything against a non-local environment. In short:

- Every environment in `macrostrat.toml` declares an `env_class`
  (`local` / `development` / `staging` / `production`), which selects a gate on
  `data` and `schema` writes. **An environment that declares no class is
  treated as `production`.**
- Mutating commands are gated. The levels are `none`, `prompt`,
  `environment-name` and `reauthorize`; `staging` and `production` defaults
  **cannot be satisfied without an interactive terminal** — there is no flag or
  environment variable that bypasses them, by design. An environment may also
  ask before *reads* (`confirm = { read = "prompt" }`). Do not try to work
  around a refusal; it is the intended behaviour.
- `macrostrat env <name>` lapses after a per-class TTL (8 h development, 1 h
  staging, 15 min production; `active_ttl` overrides). A lapsed environment is
  kept and confirmed interactively before use; without a terminal it is
  refused. Use `--env` for a single command. The pointer applies only to the
  config file it was set against.
- Credentials may be literals or references (`op://`, `env://`, `file://`,
  `keychain://`). An environment using references gets **no ambient `PG*` /
  `STORAGE_*` / `SECRET_KEY`** variables — reach credentials through
  `settings.database_url(role=...)` / `settings.storage_endpoint(...)`.
- Commands that print config redact by default; `--reveal` is refused without a
  terminal. Do not add a command that prints a credential unredacted.
- A `macrostrat.toml` beginning with `config_version = 2` is read by the
  schema-validated loader in `macrostrat.core.config_loader` (model in
  `config_model`); `macrostrat config schema` prints its schema. Files without
  the key use Dynaconf. Both yield the same `settings` surface; do not add a
  consumer that depends on which loader produced it.

## Running things

- `macrostrat up` rebuilds the docker-compose stack. Python and SQL changes in
  the tileserver/API do **not** hot-reload — they need a stack rebuild.
- The local database image is built from `base-images/database/Dockerfile`.
  Extensions added there (h3, pgvector, pgaudit, safeupdate) require a rebuild
  and restart before any schema depending on them can be applied.
- Tests: `macrostrat test all` (pulls config from the local DB, avoiding cert
  issues).
- **Use the shared testing cluster.** Build on the session-scoped `schema_harness`
  / `empty_db` fixtures (a rollback transaction for writes, as `test_audit_triggers`
  does) rather than standing up a `temporary_database_cluster` per module — a new
  cluster costs CI minutes. Spin one up only when a test genuinely needs its own
  (e.g. the unoptimized drift build).

## Python

- The workspace is `uv`-managed; py-modules are editable path dependencies wired
  in `py-modules/cli/pyproject.toml` and the root `pyproject.toml`.
- Format with **ruff**: `make format` runs `ruff format .` then
  `ruff check --fix .`. Configured in the root `pyproject.toml`
  (`line-length = 88`, `lint.select = ["I"]` for import sorting,
  `lint.isort.known-first-party = ["macrostrat"]`, and
  `extend-exclude = ["__archive*", "submodules"]`). CI runs `make format` on
  every pull request and commits the result, so formatting with anything else
  produces churn. The `[tool.black]` / `[tool.isort]` blocks left in
  `py-modules/core/pyproject.toml` are vestigial — black and isort are not
  installed as dev dependencies and disagree with ruff on import grouping.
- CLI subsystems are Typer apps registered through the
  `macrostrat.subsystems` entry-point group, plus explicit `add_typer` calls in
  `py-modules/cli/macrostrat/cli/entrypoint.py`.
- Prefer `db.run_query()` (which accepts a list of param dicts for executemany)
  over raw SQLAlchemy connections.

### Libraries take a database; only the CLI resolves one

`get_database()` belongs in the **command layer and nowhere else**. Every function
beneath it takes an explicit `db` (or engine / sessionmaker / connection), so it
can be called from a notebook, a test, or a pipeline in a separate virtualenv that
never loads Macrostrat's config. Keep heavy imports inside the command body rather
than at module scope, so importing a subsystem stays cheap.

`column-ingestion` is the model — `get_database()` appears only in its
`__init__.py`, and commands are three lines:

```python
@app.command(name="ingest")
def ingest_command(data_file: Path = Argument(...)):
    from .ingest import ingest_columns_from_file   # lazy
    db = get_database()                            # only here
    ingest_columns_from_file(db, data_file)        # library takes it
```

This is the same rule the API v3 work settled from the other direction: utilities
take a concrete engine, sessionmaker or connection, never the manager.

`map-integration` predates the convention and is the outlier (21 files resolve
their own database, e.g. `match/liths.py`, whose `get_lith_count` calls
`get_database()` under the comment *"Not sure where this gets created to be
honest..."*). Move a function to the convention when you touch it.
