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

## Running things

- `macrostrat up` rebuilds the docker-compose stack. Python and SQL changes in
  the tileserver/API do **not** hot-reload — they need a stack rebuild.
- The local database image is built from `base-images/database/Dockerfile`.
  Extensions added there (h3, pgvector, pgaudit, safeupdate) require a rebuild
  and restart before any schema depending on them can be applied.
- Tests: `macrostrat test all` (pulls config from the local DB, avoiding cert
  issues).

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
