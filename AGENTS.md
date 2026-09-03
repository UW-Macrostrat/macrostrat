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

Design migrations to be **order-independent and re-runnable**, and key
postconditions on something that only becomes true once the migration has
actually run (not on a state the declarative chunk could also produce).

## SQL gotchas

- **No bare `%` in SQL that runs through SQLAlchemy** — including inside
  comments. The driver reads it as a bind parameter and fails with
  `incomplete placeholder`. Build dynamic SQL with `||` and `quote_ident()`
  rather than `format()`, and raise messages with `RAISE … USING MESSAGE =`
  rather than a `%`-format string.
- Similarly, a literal `:` in SQL (e.g. in a regex like `(?:www\.)`) trips
  SQLAlchemy's bind-parameter parsing and must be escaped as `\:`.
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
- Format with `black` and `isort` (profile `black`, line length 88), configured
  in the root `pyproject.toml`.
- CLI subsystems are Typer apps registered through the
  `macrostrat.subsystems` entry-point group, plus explicit `add_typer` calls in
  `py-modules/cli/macrostrat/cli/entrypoint.py`.
- Prefer `db.run_query()` (which accepts a list of param dicts for executemany)
  over raw SQLAlchemy connections.
