# Environment configuration and write safety

The `macrostrat` CLI drives several environments — your laptop, a development
cluster, staging, production — from a single `macrostrat.toml`. This describes
how an environment is selected, how each one declares how dangerous it is to
write to, and how credentials are kept out of places they should not reach.

Two goals shape the design:

- **Prevent footguns.** A mistaken environment or a fat-fingered slug should not
  be able to delete production data.
- **Keep write-capable credentials away from anything that logs.** Read-only
  access is *encouraged* — it is what makes an agent useful for diagnosing a
  live environment — but a credential that can write to staging or production
  must not end up in a log, a transcript or a subprocess environment.

Everything here is **additive**. A `macrostrat.toml` written before any of this
existed keeps working unchanged; each feature is opt-in per environment. See
[Migrating an existing config](#migrating-an-existing-config).

`macrostrat.example.toml` in the repository root is a worked example of every
shape described below.

## Selecting an environment

Three ways, in precedence order:

```bash
# 1. Per invocation. Always wins, never expires.
macrostrat --env staging db tables

# 2. A shell session. Dies when the shell does.
eval "$(macrostrat env --shell staging)"

# 3. Remembered. `local` indefinitely; anything else for 15 minutes.
macrostrat env local
macrostrat env staging        # → "Activated environment staging (staging) for 15 min, until 14:32"
macrostrat env                # → "staging (lapses in 12 min)"
```

A remembered non-`local` environment **expires**, and a lapsed one is ignored
and forgotten:

```
The remembered environment 'staging' has lapsed and is being ignored.
Pass --env staging to use it for this command, or run `macrostrat env staging`
to activate it again.
```

This is deliberate. A persisted pointer at a remote database that outlives the
task will otherwise still be in force in a different terminal, in a script, or
next week — and nothing in your working tree tells you which database you are
about to write to. `local` is exempt because local work is disposable.

## Environment classes

Every environment declares **how expensive it should be to write to it**:

```toml
[local]
env_class = "local"

[development]
env_class = "development"

[production]
env_class = "production"
```

`env_class` is one of `local`, `development`, `staging`, `production`. It
selects a default **gate** for each scope of write:

| class | `data` | `schema` |
| --- | --- | --- |
| `local` | none | none |
| `development` | confirm | confirm |
| `staging` | typed | typed |
| `production` | escalate | escalate |

- **none** — proceed.
- **confirm** — `y/N` prompt. `--yes` satisfies it non-interactively.
- **typed** — type the environment name. **No flag satisfies this**, and it
  always refuses without a terminal.
- **escalate** — `typed`, *plus* the writer credential is re-fetched from the
  secret manager for this invocation, so its approval prompt is in the path.

`data` covers row-level changes — ingestion, restores, deletions. `schema`
covers DDL. There is no `services` scope: `up`/`down`/`restart` manage the
local compose stack only.

**An environment that declares no `env_class` is treated as `production`**
unless it is named `local`, as is one declaring a class that isn't recognised.
Silence, and typos, mean the strictest gate.

Override a gate per scope where the default is wrong:

```toml
[staging.write_gate]
schema = "escalate"     # stricter than staging's default for DDL
```

### Which commands are gated

`db restore`, `db load-csv`, `maps sources delete`, `topo reset`, `topo clean`,
`topo rebuild`, `topo remove` (data); `schema apply`, `topo init` (schema);
`schema migrate` **only with `--apply`**, since without it the command is a dry
run. Read-only commands — `db dump`, `db tables`, `db credentials` — are never
gated.

Each gated command takes `--yes`/`-y`, which satisfies a `confirm` gate and
nothing stronger.

### Why a command was refused

```
╭─ Error ──────────────────────────────────────────────────────────────────╮
│ Refusing database restore in production (production)                     │
│ The 'escalate' gate guarding data writes here requires an interactive    │
│ terminal. There is no flag or environment variable that satisfies it.    │
╰──────────────────────────────────────────────────────────────────────────╯
```

The message names the environment, its class, the gate and the scope. If the
class was *inferred* it says so and why — an environment appearing as
`(production)` that you did not expect to be production is missing an
`env_class`.

There is deliberately **no bypass environment variable**. An environment
variable is ambient, inherited by every subprocess, and sticky: set once in a
deployment's configuration it would authorise writes for every later
invocation, which is the problem the expiring active environment above exists
to solve. `--yes` is per-invocation and cannot be set once and forgotten.

## Credentials

A credential may be written literally, or **name a secret** in a manager:

```toml
[production.database]
host     = "db.production.svc.macrostrat.org"
database = "macrostrat"
reader   = "op://Macrostrat Prod/macrostrat-db/reader/password"
writer   = "op://Macrostrat Prod/macrostrat-db/admin/password"
```

Supported reference schemes:

| scheme | resolved by | for |
| --- | --- | --- |
| `op://vault/item/section/field` | 1Password CLI (`op read`) | developer machines |
| `env://VAR_NAME` | the process environment | CI, cloud agents — no TTY, no `op` |
| `file:///run/secrets/name` | reading the file | Kubernetes and Docker secret mounts |
| `keychain://service/account` | macOS keychain | developer machines |

A reference resolves **when the credential is needed**, not when config loads —
otherwise every `macrostrat --help` would prompt a password manager. Only these
schemes are references: `postgresql://user:pass@host/db` is a URI too, and stays
the literal it is.

> **One behavioural change.** An environment whose credentials are *references*
> gets **no ambient `PG*`, `POSTGRES_*`, `STORAGE_*` or `SECRET_KEY`
> environment variables.** Exporting them requires resolving the secret at
> import and handing it to every subprocess — the leak this indirection exists
> to close. Adopting a reference is therefore also how an environment opts out
> of ambient credentials. Environments holding literals are unaffected.

### Reader by default

A command connects with the **reader** credential. The connection is escalated
to the writer only when a write gate passes — so write capability is *acquired*
by passing a gate rather than held by every command from the start.

```
macrostrat --env production db tables                 → resolves `reader`
macrostrat --env production db restore dump.sql       → refused; resolves nothing
macrostrat --env development db restore dump.sql --yes → gate passes; resolves `writer`
```

Note the middle case: a refused write never touches the writer credential at
all, so it cannot produce a password-manager prompt for a command that was
never going to run.

The role is decided **once per invocation** — `get_database()` caches a single
connection — so this needs no change at any call site that merely uses the
database. If a command reads before it asks to write, the reader connection is
closed and replaced when the gate passes.

This has no effect on an environment configured with a literal `pg_database`
URL: there is one credential, and the role is ignored. It also has no effect
where `reader` and `writer` resolve to the same secret. It matters only once an
environment has a genuinely distinct, restricted reader role — so it can be
adopted well before one exists.

### The token-signing key is the most sensitive value here

```toml
[production]
token_signing_key = "op://Macrostrat Prod/api-v3/jwt/secret_key"
```

This signs api-v3's JWTs and is PostgREST's `PGRST_JWT_SECRET`. A JWT signed
with it carrying `role: web_admin` is honoured by PostgREST, so holding it
confers full write access **with no database password and past every write
gate**. Treat it as the most sensitive value in the file.

`token_signing_key` is the preferred name; plain `secret_key` still works. The
new name exists because `[<env>.storage].secret_key` is an *S3 secret access
key* — unrelated, far less privileged, and one indentation level away.

## Several databases per environment

`macrostrat` is the default database, but not the only one. Restating a host
and credential pair for each would be worse than the connection URLs it
replaces, so extra databases cost one line:

```toml
[default.database]              # written once, inherited by every environment
port = 5432
[default.database.options]
sslmode = "require"

[production.database]
host     = "db.production.svc.macrostrat.org"
database = "macrostrat"
reader   = "op://Macrostrat Prod/macrostrat-db/reader/password"
writer   = "op://Macrostrat Prod/macrostrat-db/admin/password"

[production.databases]
rockd     = "rockd"                                            # same server
sgp       = "sgp"
elevation = { host = "elev.svc.macrostrat.org", database = "elevation" }
burwell   = "postgresql://u:p@old-host:5432/burwell"            # still works
```

A **bare string** is a database *name* on the environment's default server,
inheriting host, port, credentials and options. A **table** states only its
differences. A **URL** is what this key has always held. A malformed entry is
skipped with a warning rather than taking the environment offline.

`[default.database]` is inherited, so a shared port, TLS mode or reader
reference is written once rather than once per tier.

Object storage works the same way:

```toml
[default.storage]
endpoint = "https://storage.macrostrat.org"

[production.storage]
access_key = "op://Macrostrat Prod/ceph-app/access_key"
secret_key = "op://Macrostrat Prod/ceph-app/secret_key"

[production.storage.buckets]                    # logical name → bucket
map-staging = "map-staging-prod"

[production.storage.admin]                      # cluster admin, kept separate
type       = "ceph-object-storage"
access_key = "op://Macrostrat Prod/ceph-admin/access_key"
secret_key = "op://Macrostrat Prod/ceph-admin/secret_key"

[production.storage.endpoints]
access-logs = "macrostrat-access-logs"          # bucket on the default endpoint
```

The Ceph **admin** credential is a separate named endpoint on purpose:
`radosgw-admin` can create and delete users and buckets cluster-wide, so
nothing resolves it while reaching for an ordinary object credential.

## What is safe to print

Commands that print configuration redact credentials by default:

```bash
macrostrat db credentials          # password and URL redacted
macrostrat self printenv           # PGPASSWORD, SECRET_KEY, … redacted
macrostrat kubernetes secrets NAME # every value redacted, field names kept
```

Each takes `--reveal`, which is **refused when there is no terminal** — an
agent or a CI job cannot reveal a credential into a transcript. Redaction works
by variable name, by value (any secret resolved in this process), and by URL
structure, so a password embedded in something innocuously named like
`MACROSTRAT_DATABASE_URL` is masked too.

## Attribution in the database

Every connection sets `application_name` to
`macrostrat-cli/<user>@<env>/<role>`, so `pg_stat_activity` and pgaudit
attribute a query to a person, an environment and a privilege level rather than
to "some client of the admin role". Set `application_name` under
`[<env>.database.options]` to override it.

## Migrating an existing config

Nothing is required. An older CLI ignores every key below, and a config using
none of them behaves exactly as before — so these can be adopted one
environment at a time, in any order, and reverted.

**1. Declare classes. Do this first, everywhere.** One line per environment and
no other change. This is what turns the gates on, and without it every
non-`local` environment is treated as `production`.

**2. Rename the signing key.** `secret_key` → `token_signing_key`.

**3. Hoist what is shared** into `[default.database]` / `[default.storage]`.
Now that it is inherited, this is a deletion rather than an addition.

**4. Move remote credentials into a secret manager.** Smallest step first — the
whole URL in the vault, no structural change:

```toml
[production]
env_class   = "production"
pg_database = "op://Macrostrat Prod/macrostrat-db/admin/url"
```

Then the structured `[<env>.database]` form, which is where a remote
environment should end up: it keeps the credential redactable, keeps topology
reviewable in a diff, and separates reader from writer.

If the environment declares separate `reader` and `writer` references, reads
use the reader and only an authorized write reaches for the writer — see
[Reader by default](#reader-by-default).

## Retired commands

`macrostrat mariadb` (dump, restore, and the one-time MariaDB → PostgreSQL
migration) and the Minio-client S3 commands (`storage mc`, `storage mirror`)
have been moved to `__archive__/` and are no longer registered. `rclone`-based
bucket copying (`storage s3-bucket-migration`) and the `radosgw-admin`
subcommands remain. See the READMEs in `__archive__/mariadb-cli/` and
`__archive__/s3-management/` for why, and what a revival would need.
