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

## Environments and write safety

Read **`docs/Environment configuration and write safety.md`** before running
anything against a non-local environment. In short:

- Every environment in `macrostrat.toml` declares an `env_class`
  (`local` / `development` / `staging` / `production`), which selects a gate on
  `data` and `schema` writes. **An environment that declares no class is
  treated as `production`.**
- Mutating commands are gated. `staging` and `production` gates **cannot be
  satisfied without an interactive terminal** — there is no flag or environment
  variable that bypasses them, by design. Do not try to work around a refusal;
  it is the intended behaviour.
- `macrostrat env <name>` expires after 15 minutes for any non-`local`
  environment. Use `--env` for a single command.
- Credentials may be literals or references (`op://`, `env://`, `file://`,
  `keychain://`). An environment using references gets **no ambient `PG*` /
  `STORAGE_*` / `SECRET_KEY`** variables — reach credentials through
  `settings.database_url(role=...)` / `settings.storage_endpoint(...)`.
- Commands that print config redact by default; `--reveal` is refused without a
  terminal. Do not add a command that prints a credential unredacted.

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
