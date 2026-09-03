"""Database connections composed from plaintext topology plus a named secret.

An environment can describe its database structurally, naming one credential
per role, instead of carrying a whole connection URL with a password in it:

.. code-block:: toml

    [production.database]
    host     = "db.production.svc.macrostrat.org"
    port     = 5432
    database = "macrostrat"
    reader   = "op://Macrostrat Prod/macrostrat-db/reader/password"
    writer   = "op://Macrostrat Prod/macrostrat-db/admin/password"

Composing the URL from parts, rather than storing whole URLs, buys three things:

- Hosts and database names stay visible and greppable — the half of the config
  that is genuinely useful context, and harmless to commit.
- There is one credential per *role*, so a caller has to say which one it wants.
  A read path can no longer accidentally hold write capability.
- The password is quoted by SQLAlchemy's ``URL.create`` rather than pasted into
  a string, so a credential containing ``@``, ``/`` or ``:`` composes correctly.
  Hand-written URLs get this wrong silently.

An environment usually has **several** databases — `macrostrat` is the default,
but `rockd`, `sgp`, an elevation database and others live alongside it, mostly on
the same server. Restating a host, port and credential pair for each one would be
worse than the whole-URL form it replaces, so the general case is kept short in
two ways:

.. code-block:: toml

    # Written once, inherited by every environment.
    [default.database]
    port = 5432
    [default.database.options]
    sslmode = "require"

    [production.database]
    host   = "db.production.svc.macrostrat.org"
    database = "macrostrat"
    reader = "op://Macrostrat Prod/macrostrat-db/reader/password"
    writer = "op://Macrostrat Prod/macrostrat-db/admin/password"

    [production.databases]
    rockd     = "rockd"                                    # same server
    sgp       = "sgp"
    elevation = { host = "elev.svc.macrostrat.org", database = "elevation" }
    burwell   = "postgresql://u:p@legacy:5432/burwell"     # still works

A bare string is a database *name* on the environment's default server, so an
extra database costs one line. A table states only its differences. And
`[default.database]` is inherited, so a shared port, TLS mode or reader
credential is written once rather than once per tier.

**The legacy path is untouched.** ``pg_database`` keeps working exactly as it
does today, and :func:`connection_for` prefers a ``[env.database]`` table only
when one is present. A config that has never heard of this module behaves
identically; adopting it is per-environment and reversible. ``pg_database``
itself may also be a secret reference, which is the smallest possible adoption
step — a whole URL in the vault, no structural change at all.
"""

from enum import Enum
from os import environ
from typing import Any, Dict, Mapping, Optional, Union

from pydantic import BaseModel, ConfigDict
from sqlalchemy.engine import make_url
from sqlalchemy.engine.url import URL
from sqlalchemy.exc import ArgumentError

from macrostrat.utils import get_logger

from .environment import DEFAULT_ENV
from .secrets import Secret, as_secret, is_secret_ref, reveal

log = get_logger(__name__)

#: TOML key holding an environment's structured database description.
DATABASE_KEY = "database"

#: The legacy key: a whole connection URL, password included.
LEGACY_URL_KEY = "pg_database"

#: TOML key holding the environment's *additional* named databases. This key
#: already exists — `config.py` injects `databases["macrostrat"]` and the test
#: suite reads `databases["test"]` — so named databases extend it rather than
#: introducing a second, competing mapping.
NAMED_KEY = "databases"

#: The name of the database an unqualified request resolves to.
DEFAULT_DATABASE = "macrostrat"

DEFAULT_DRIVER = "postgresql"
DEFAULT_PORT = 5432
DEFAULT_USER = "macrostrat"


class DatabaseRole(str, Enum):
    """Which credential a caller is asking for.

    The distinction is the point: `reader` is cheap to resolve and safe to hand
    to an agent or a log; `writer` is the privileged credential and should be
    resolved as late as possible, by as few callers as possible.
    """

    Reader = "reader"
    Writer = "writer"


class MissingCredential(RuntimeError):
    """No credential is configured for the requested role."""


class DatabaseConnection(BaseModel):
    """One environment's database, with a credential per role."""

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    host: str
    database: str
    port: int = DEFAULT_PORT
    driver: str = DEFAULT_DRIVER
    #: Per-role login user. Falls back to :attr:`user` when unset.
    reader_user: Optional[str] = None
    writer_user: Optional[str] = None
    user: str = DEFAULT_USER
    #: Per-role credential: a literal, or a :class:`Secret` naming one.
    reader: Union[str, Secret, None] = None
    writer: Union[str, Secret, None] = None
    #: Connection parameters carried as URL query string — `sslmode`,
    #: `connect_timeout`, and friends. Decomposing a URL and rebuilding it
    #: drops these unless they are modelled explicitly, and `sslmode` in
    #: particular is security-relevant: silently losing it downgrades a
    #: required-TLS connection.
    options: Dict[str, str] = {}

    def user_for(self, role: DatabaseRole) -> str:
        specific = self.reader_user if role == DatabaseRole.Reader else self.writer_user
        return specific or self.user

    def credential_for(self, role: DatabaseRole) -> Union[str, Secret]:
        """The unresolved credential for *role*."""
        role = DatabaseRole(role)
        value = self.reader if role == DatabaseRole.Reader else self.writer
        if value is None:
            raise MissingCredential(
                f"No {role.value!r} credential is configured for "
                f"{self.user_for(role)}@{self.host}:{self.port}/{self.database}. "
                f'Add {role.value} = "op://..." (or a literal) to its '
                f"[<env>.{DATABASE_KEY}] table."
            )
        return value

    def _query_for(self, role: DatabaseRole) -> dict:
        """Connection parameters, with an attributing `application_name`.

        pgaudit and `pg_stat_activity` record `application_name`, so setting it
        to `macrostrat-cli/<user>@<env>/<role>` is what makes a write in the log
        attributable to a person, an environment and a privilege level rather
        than to "some client of the admin role". An explicitly configured
        `application_name` is left alone.
        """
        query = dict(self.options)
        query.setdefault("application_name", _application_name(role))
        return query

    def url(self, role: DatabaseRole = DatabaseRole.Reader) -> URL:
        """A connection URL for *role*, resolving its credential now.

        Returns a SQLAlchemy :class:`~sqlalchemy.engine.url.URL`, whose ``str``
        already masks the password — use
        ``url.render_as_string(hide_password=False)`` to get a usable DSN, and
        treat every call site that does so as a disclosure point.
        """
        role = DatabaseRole(role)
        return URL.create(
            drivername=self.driver,
            username=self.user_for(role),
            password=reveal(self.credential_for(role)),
            host=self.host,
            port=self.port,
            database=self.database,
            query=self._query_for(role),
        )

    @classmethod
    def parse(cls, value: Mapping[str, Any]) -> "DatabaseConnection":
        """Build from a ``[env.database]`` table."""
        if not hasattr(value, "get"):
            raise ValueError(
                f"[<env>.{DATABASE_KEY}] must be a table, got {type(value).__name__}"
            )

        def field(*names):
            for name in names:
                got = value.get(name, None)
                if got is not None:
                    return got
            return None

        host = field("host")
        database = field("database", "dbname")
        if host is None or database is None:
            raise ValueError(
                f"[<env>.{DATABASE_KEY}] needs at least `host` and `database`"
            )

        # A single `password` applies to both roles — the shape a
        # single-credential environment (local, development) wants.
        shared = field("password")
        reader = field("reader", "reader_password")
        writer = field("writer", "writer_password")

        options = field("options", "query") or {}
        if not hasattr(options, "items"):
            raise ValueError(
                f"[<env>.{DATABASE_KEY}.options] must be a table, "
                f"got {type(options).__name__}"
            )

        return cls(
            host=str(host),
            database=str(database),
            options={str(k): str(v) for k, v in options.items()},
            port=int(field("port") or DEFAULT_PORT),
            driver=str(field("driver") or DEFAULT_DRIVER),
            user=str(field("user", "username") or DEFAULT_USER),
            reader_user=_opt_str(field("reader_user")),
            writer_user=_opt_str(field("writer_user")),
            reader=as_secret(reader if reader is not None else shared),
            writer=as_secret(writer if writer is not None else shared),
        )

    @classmethod
    def from_url(cls, url: Union[str, URL]) -> "DatabaseConnection":
        """Build from a whole connection URL — the legacy `pg_database` shape.

        The URL's single credential serves both roles, because that is what it
        actually is today: one admin login used for everything.
        """
        parsed = make_url(url) if isinstance(url, str) else url
        if parsed.host is None or parsed.database is None:
            raise ValueError(f"{LEGACY_URL_KEY} is missing a host or database name")
        return cls(
            host=parsed.host,
            database=parsed.database,
            port=parsed.port or DEFAULT_PORT,
            driver=parsed.drivername or DEFAULT_DRIVER,
            user=parsed.username or DEFAULT_USER,
            reader=parsed.password,
            writer=parsed.password,
            # Round-tripping a URL must not quietly drop `?sslmode=require`.
            options={k: str(v) for k, v in (parsed.query or {}).items()},
        )


def _opt_str(value) -> Optional[str]:
    return None if value is None else str(value)


def _application_name(role: DatabaseRole) -> str:
    """`macrostrat-cli/<user>@<env>/<role>`, truncated to what libpq accepts.

    Postgres silently truncates `application_name` past NAMEDATALEN-1 (63), so
    truncate deliberately and keep the *role* — the most security-relevant
    part — rather than letting it fall off the end.
    """
    user = environ.get("USER") or environ.get("USERNAME") or "unknown"
    env = environ.get("MACROSTRAT_ENV") or "no-env"
    suffix = f"@{env}/{DatabaseRole(role).value}"
    prefix = "macrostrat-cli/"
    budget = 63 - len(prefix) - len(suffix)
    if budget < 1:
        # Pathological env/role names: drop the user rather than the role.
        return (prefix + suffix)[:63]
    return prefix + user[:budget] + suffix


def merge_tables(base: Optional[Mapping], override: Optional[Mapping]) -> dict:
    """Overlay *override* on *base*, merging the nested `options` table.

    Deliberately hand-rolled rather than switching Dynaconf to
    ``merge_enabled=True``: that flag changes how *every* setting merges across
    environments — lists like `log_modules`, tables like `sources` — and would
    silently alter the behaviour of configs that exist today. This merges only
    what the database layer owns.
    """
    out = dict(base or {})
    for key, value in dict(override or {}).items():
        if (
            key in ("options", "query")
            and hasattr(value, "items")
            and hasattr(out.get(key), "items")
        ):
            merged = dict(out[key])
            merged.update(dict(value))
            out[key] = merged
        else:
            out[key] = value
    return out


def _base_table(settings) -> dict:
    """The environment's default database table, with `[default]` underneath.

    Dynaconf replaces a nested table wholesale when an environment declares it,
    so `[default.database]` is silently discarded today. Reading the default
    layer explicitly is what lets shared settings — a port, a `sslmode`, a
    reader reference used by every tier — be written once.
    """
    inherited = None
    from_env = getattr(settings, "from_env", None)
    if callable(from_env):
        try:
            inherited = from_env(DEFAULT_ENV).get(DATABASE_KEY, None)
        except Exception:  # pragma: no cover - Dynaconf raises variously here
            inherited = None
    return merge_tables(inherited, settings.get(DATABASE_KEY, None))


def _legacy_connection(settings) -> Optional[DatabaseConnection]:
    """The `pg_database` fallback, which may itself be a secret reference."""
    legacy = settings.get(LEGACY_URL_KEY, None)
    if legacy in (None, "None", ""):
        return None
    resolved = reveal(as_secret(legacy))
    try:
        return DatabaseConnection.from_url(resolved)
    except (ValueError, ArgumentError) as err:
        log.warning("Could not parse %s: %s", LEGACY_URL_KEY, err)
        return None


def _named_connection(name, spec, base: dict) -> Optional[DatabaseConnection]:
    """Resolve one entry of the `databases` table.

    Three accepted shapes, in the order they are distinguished:

    ``"postgresql://…"`` / ``"op://…"``
        A whole connection URL — what this key holds today, so existing
        entries keep working. A secret reference is resolved here.

    ``"rockd"``
        Just a database name. Everything else — host, port, credentials,
        options — comes from the environment's default database. This is the
        shape that keeps the general case from being unbearable: one line per
        database, no repetition of the server it lives on.

    ``{ host = "…", database = "…" }``
        A table, overlaid on the environment's default. Only the differences
        need stating.
    """
    if hasattr(spec, "items"):
        return DatabaseConnection.parse(merge_tables(base, spec))

    if not isinstance(spec, str) or not spec.strip():
        log.warning("Ignoring database %r: expected a name, URL or table.", name)
        return None

    if is_secret_ref(spec) or "://" in spec:
        try:
            return DatabaseConnection.from_url(reveal(as_secret(spec)))
        except (ValueError, ArgumentError) as err:
            log.warning("Could not parse the URL for database %r: %s", name, err)
            return None

    # A bare database name on the environment's default server.
    if not base:
        log.warning(
            "Database %r names %r but this environment has no [%s] table to "
            "inherit a host from.",
            name,
            spec,
            DATABASE_KEY,
        )
        return None
    return DatabaseConnection.parse(merge_tables(base, {"database": spec}))


def connections_for(settings) -> Dict[str, DatabaseConnection]:
    """Every database configured for the active environment, by name."""
    base = _base_table(settings)
    out: Dict[str, DatabaseConnection] = {}

    default = None
    if base:
        try:
            default = DatabaseConnection.parse(base)
        except ValueError as err:
            log.warning(
                "Ignoring the [%s] table for this environment (%s); "
                "falling back to %s.",
                DATABASE_KEY,
                err,
                LEGACY_URL_KEY,
            )
    if default is None:
        default = _legacy_connection(settings)
    if default is not None:
        out[DEFAULT_DATABASE] = default

    for name, spec in dict(settings.get(NAMED_KEY, None) or {}).items():
        if name == DEFAULT_DATABASE and name in out:
            # An explicit [<env>.database] table outranks the URL that
            # config.py injects into `databases` from `pg_database`.
            continue
        conn = _named_connection(name, spec, base)
        if conn is not None:
            out[str(name)] = conn

    return out


def connection_for(settings, name: str = DEFAULT_DATABASE):
    """One named database for the active environment, or None if unconfigured.

    Resolution order for the default name, chosen so that no existing config
    changes behaviour:

    1. a ``[<env>.database]`` table (with ``[default.database]`` underneath),
       when present;
    2. otherwise ``pg_database`` — which may itself be a secret reference,
       making "put the whole URL in the vault" a valid first migration step.
    """
    return connections_for(settings).get(name, None)
