"""Database connections composed from plaintext topology plus a named secret.

An environment can describe its database structurally, naming a login per
role, instead of carrying a whole connection URL with a password in it:

.. code-block:: toml

    [production.database]
    host           = "db.production.svc.macrostrat.org"
    port           = 5432
    database       = "macrostrat"
    read_user      = "macrostrat_reader"
    read_password  = "op://Macrostrat Prod/macrostrat-db/reader/password"
    write_user     = "op://Macrostrat Prod/macrostrat-db/admin/username"
    write_password = "op://Macrostrat Prod/macrostrat-db/admin/password"

Each role has a ``<role>_user`` and a ``<role>_password``; ``user`` and
``password`` stand in for whichever role does not declare its own, so a
single-login environment writes just those two. **Any of the four may be a
literal or a secret reference** — a username is topology when it is a role name
like ``macrostrat_reader``, and a secret when it is the generated login a
password manager stores beside its password.

Composing the URL from parts, rather than storing whole URLs, buys three things:

- Hosts and database names stay visible and greppable — the half of the config
  that is genuinely useful context, and harmless to commit.
- There is one login per *role*, so a caller has to say which one it wants.
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
    host           = "db.production.svc.macrostrat.org"
    database       = "macrostrat"
    read_password  = "op://Macrostrat Prod/macrostrat-db/reader/password"
    write_password = "op://Macrostrat Prod/macrostrat-db/admin/password"

    [production.databases]
    rockd     = "rockd"                                    # same server
    sgp       = "sgp"
    elevation = { host = "elev.svc.macrostrat.org", database = "elevation" }
    burwell   = "postgresql://u:p@legacy:5432/burwell"     # still works

A bare string is a database *name* on the environment's default server, so an
extra database costs one line. A table states only its differences. And
`[default.database]` is inherited, so a shared port, TLS mode or read login is
written once rather than once per tier.

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
from .secrets import Secret, SecretResolutionError, as_secret, is_secret_ref, reveal

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


class DatabaseRole(str, Enum):
    """Which credential a caller is asking for.

    The distinction is the point: `reader` is cheap to resolve and safe to hand
    to an agent or a log; `writer` is the privileged credential and should be
    resolved as late as possible, by as few callers as possible.
    """

    Reader = "reader"
    Writer = "writer"


DEFAULT_DRIVER = "postgresql"
DEFAULT_PORT = 5432
DEFAULT_USER = "macrostrat"

#: Config keys per role, in the order they are consulted. The first name is the
#: documented one; the rest are earlier spellings, still honoured so a config
#: written against them keeps working (a config file and the CLI reading it are
#: deployed separately).
USER_KEYS = {
    DatabaseRole.Reader: ("read_user", "reader_user"),
    DatabaseRole.Writer: ("write_user", "writer_user"),
}
PASSWORD_KEYS = {
    DatabaseRole.Reader: ("read_password", "reader", "reader_password"),
    DatabaseRole.Writer: ("write_password", "writer", "writer_password"),
}
#: Role-agnostic keys, standing in for whichever role declares nothing.
SHARED_USER_KEYS = ("user", "username")
SHARED_PASSWORD_KEYS = ("password",)


class MissingCredential(RuntimeError):
    """No credential is configured for the requested role."""


#: A config value that may name a secret rather than contain one.
Credential = Union[str, Secret, None]


class DatabaseConnection(BaseModel):
    """One environment's database, with a login per role.

    Each role resolves its user and password independently: the role-specific
    field if declared, else the shared one, else — for the user only — the
    default. A password has no default; a role with none configured raises
    :class:`MissingCredential` when asked, and never before.
    """

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    host: str
    database: str
    port: int = DEFAULT_PORT
    driver: str = DEFAULT_DRIVER
    #: Shared login, standing in for whichever role declares none of its own.
    user: Credential = None
    password: Credential = None
    #: Per-role login. Any of these may be a literal or a :class:`Secret`.
    read_user: Credential = None
    write_user: Credential = None
    read_password: Credential = None
    write_password: Credential = None
    #: Connection parameters carried as URL query string — `sslmode`,
    #: `connect_timeout`, and friends. Decomposing a URL and rebuilding it
    #: drops these unless they are modelled explicitly, and `sslmode` in
    #: particular is security-relevant: silently losing it downgrades a
    #: required-TLS connection.
    options: Dict[str, str] = {}

    def user_for(self, role: DatabaseRole) -> Union[str, Secret]:
        """The unresolved login user for *role*: specific, shared, or default."""
        role = DatabaseRole(role)
        specific = self.read_user if role == DatabaseRole.Reader else self.write_user
        if specific is not None:
            return specific
        if self.user is not None:
            return self.user
        return DEFAULT_USER

    def credential_for(self, role: DatabaseRole) -> Union[str, Secret]:
        """The unresolved password for *role*: specific, else shared, else raise."""
        role = DatabaseRole(role)
        specific = (
            self.read_password if role == DatabaseRole.Reader else self.write_password
        )
        value = specific if specific is not None else self.password
        if value is None:
            key = PASSWORD_KEYS[role][0]
            raise MissingCredential(
                f"No {role.value} password is configured for "
                f"{self.location(role)}. "
                f'Add {key} = "op://..." (or a literal) to its '
                f"[<env>.{DATABASE_KEY}] table."
            )
        return value

    def location(self, role: DatabaseRole) -> str:
        """`user@host:port/database` for messages, without resolving anything.

        A username held in a secret manager is shown by its reference, not
        fetched: an error about a missing password must not itself prompt for
        a username.
        """
        user = self.user_for(role)
        label = user.ref if isinstance(user, Secret) else str(user)
        return f"{label}@{self.host}:{self.port}/{self.database}"

    def requires_resolution(self, role: DatabaseRole = DatabaseRole.Reader) -> bool:
        """Whether composing this role's URL would fetch from a secret manager.

        For a caller that wants to export a URL eagerly — the corelle subsystem
        must set ``CORELLE_DB`` before importing corelle — this says whether it
        may do so now (a literal config, or an already-fetched secret) or has
        to wait for command time. A role with no password configured fetches
        nothing, so it reports False; :meth:`url` raises for it regardless.
        """
        role = DatabaseRole(role)
        try:
            values = (self.user_for(role), self.credential_for(role))
        except MissingCredential:
            return False
        return any(isinstance(v, Secret) and not v.is_resolved for v in values)

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
        # Password first: if none is configured, fail before fetching a
        # username that may itself live in the secret manager.
        password = reveal(self.credential_for(role))
        username = reveal(self.user_for(role))
        return URL.create(
            drivername=self.driver,
            username=username,
            password=password,
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
            for i, name in enumerate(names):
                got = value.get(name, None)
                if got is not None:
                    if i > 0 and names[0] not in _LEGACY_WARNED:
                        _LEGACY_WARNED.add(names[0])
                        log.warning(
                            "[<env>.%s] key %r is an old spelling; write %r.",
                            DATABASE_KEY,
                            name,
                            names[0],
                        )
                    return got
            return None

        host = field("host")
        database = field("database", "dbname")
        if host is None or database is None:
            raise ValueError(
                f"[<env>.{DATABASE_KEY}] needs at least `host` and `database`"
            )

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
            # The shared pair stands in for whichever role declares nothing;
            # `user_for` / `credential_for` apply that rule, so it lives in one
            # place rather than being baked in here.
            user=_credential(field(*SHARED_USER_KEYS)),
            password=_credential(field(*SHARED_PASSWORD_KEYS)),
            read_user=_credential(field(*USER_KEYS[DatabaseRole.Reader])),
            write_user=_credential(field(*USER_KEYS[DatabaseRole.Writer])),
            read_password=_credential(field(*PASSWORD_KEYS[DatabaseRole.Reader])),
            write_password=_credential(field(*PASSWORD_KEYS[DatabaseRole.Writer])),
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
            user=parsed.username,
            password=parsed.password,
            # Round-tripping a URL must not quietly drop `?sslmode=require`.
            options={k: str(v) for k, v in (parsed.query or {}).items()},
        )


class DeferredUrlConnection:
    """A whole connection URL held by a secret manager, decomposed on first use.

    Composing the registry must not fetch anything. A reference that cannot
    resolve right now — the wrong 1Password account, no ``op`` on PATH, a cloud
    session without the variable — has to fail when *that* database is used,
    not take every database in the environment offline the moment anything
    asks for the default one. So the reference is kept as it is, and the URL is
    fetched and parsed the first time a role's URL is asked for.

    Presents the same surface as :class:`DatabaseConnection` where the
    distinction does not matter: :meth:`url`, :meth:`location`,
    :meth:`credential_for`, :meth:`requires_resolution`. It deliberately has no
    ``host`` / ``database`` attributes — reading topology off it would have to
    fetch, and an attribute that fetches is exactly what this class exists to
    avoid. Call :meth:`connection` for the parsed form when you mean to.
    """

    def __init__(self, secret: Secret, name: str = DEFAULT_DATABASE):
        self.secret = secret
        self.name = name

    @property
    def ref(self) -> str:
        """The reference. Safe to print — it names the URL, isn't it."""
        return self.secret.ref

    def connection(self) -> DatabaseConnection:
        """Fetch the URL and decompose it. This is the disclosure point."""
        raw = reveal(self.secret)
        try:
            return DatabaseConnection.from_url(raw)
        except (ValueError, ArgumentError):
            # Neither the URL nor the driver's message (which quotes the URL,
            # password included) may reach the caller.
            raise SecretResolutionError(
                f"{self.ref} did not resolve to a usable connection URL for "
                f"database {self.name!r}. Expected postgresql://user:pass@host/db."
            ) from None

    def url(self, role: DatabaseRole = DatabaseRole.Reader) -> URL:
        return self.connection().url(role)

    def user_for(self, role: DatabaseRole):
        """The login user for *role*. Fetches — there is no other way to know."""
        return self.connection().user_for(role)

    def credential_for(self, role: DatabaseRole) -> Secret:
        """The credential for *role* is the URL reference itself.

        The URL carries one login that serves both roles, so re-authorizing
        the writer (what an ``escalate`` gate does) means re-fetching the URL.
        """
        return self.secret

    def requires_resolution(self, role: DatabaseRole = DatabaseRole.Reader) -> bool:
        return not self.secret.is_resolved

    def location(self, role: DatabaseRole = DatabaseRole.Reader) -> str:
        """The reference, never the URL: this must not fetch."""
        return self.ref

    def __repr__(self) -> str:
        return f"DeferredUrlConnection({self.ref!r})"


#: Either kind of registry entry. Both compose a URL per role on demand.
AnyConnection = Union[DatabaseConnection, DeferredUrlConnection]


#: Old key spellings already warned about in this process, so a config that
#: still uses them draws one line per key rather than one per database.
_LEGACY_WARNED: set = set()


def _credential(value) -> Credential:
    """A config value as a login field: None, a :class:`Secret`, or a string."""
    if value is None:
        return None
    return as_secret(value if isinstance(value, str) else str(value))


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
    merged = merge_tables(inherited, settings.get(DATABASE_KEY, None))
    # The environment's default database is `macrostrat` unless it says
    # otherwise: a `[<env>.database]` table that names only a host means the
    # Macrostrat database on that host. Named databases built on this table
    # override the name (a bare name replaces it; a table may restate it).
    if merged.get("host") is not None and not any(
        merged.get(k) is not None for k in ("database", "dbname")
    ):
        merged["database"] = DEFAULT_DATABASE
    return merged


def _legacy_connection(settings) -> Optional[AnyConnection]:
    """The `pg_database` fallback, which may itself be a secret reference.

    A literal URL is parsed now, so a malformed one is reported at config load
    as it always was. A reference is *not* fetched here — see
    :class:`DeferredUrlConnection`.
    """
    legacy = settings.get(LEGACY_URL_KEY, None)
    if legacy in (None, "None", ""):
        return None
    if is_secret_ref(legacy):
        return DeferredUrlConnection(as_secret(legacy), DEFAULT_DATABASE)
    try:
        return DatabaseConnection.from_url(legacy)
    except (ValueError, ArgumentError) as err:
        log.warning("Could not parse %s: %s", LEGACY_URL_KEY, _parse_problem(err))
        return None


def _parse_problem(err: Exception) -> str:
    """Why a URL failed to parse, without the URL.

    SQLAlchemy's `ArgumentError` quotes the whole string it could not parse,
    password included, and this text ends up in the CLI's help banner.
    """
    if isinstance(err, ArgumentError):
        return "malformed connection URL"
    return str(err)


def _named_connection(name, spec, base: dict) -> Optional[AnyConnection]:
    """Resolve one entry of the `databases` table.

    Three accepted shapes, in the order they are distinguished:

    ``"postgresql://…"`` / ``"op://…"``
        A whole connection URL — what this key holds today, so existing
        entries keep working. A secret reference is kept unresolved until the
        database is used, so one unreachable reference cannot take the rest
        of the environment offline.

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
    spec = spec.strip()

    if is_secret_ref(spec):
        return DeferredUrlConnection(as_secret(spec), str(name))
    if "://" in spec:
        try:
            return DatabaseConnection.from_url(spec)
        except (ValueError, ArgumentError) as err:
            log.warning(
                "Could not parse the URL for database %r: %s",
                name,
                _parse_problem(err),
            )
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


def connections_for(settings) -> Dict[str, AnyConnection]:
    """Every database configured for the active environment, by name.

    Composes without fetching: no secret is resolved by building this map,
    whatever shape the entries take.
    """
    base = _base_table(settings)
    out: Dict[str, AnyConnection] = {}

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
