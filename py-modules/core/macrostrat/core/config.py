from enum import Enum
from os import environ, getenv
from pathlib import Path

from dotenv import load_dotenv
from dynaconf import Dynaconf, Validator
from sqlalchemy.engine import make_url
from sqlalchemy.engine.url import URL
from toml import load as load_toml

from macrostrat.utils import get_logger

from .connections import DEFAULT_DATABASE, DatabaseRole, connection_for, connections_for
from .environment import DEFAULT_ENV, policy_from_settings
from .resolvers import cast_sources, setup_source_roots_environment
from .secrets import as_secret, is_secret_ref, reveal
from .storage import (
    DEFAULT_ENDPOINT,
    buckets_for,
    endpoints_for,
    token_signing_key_value,
)
from .utils import (
    convert_to_string,
    find_macrostrat_config,
    normalize_macrostrat_env,
    path_list_resolver,
)

log = get_logger(__name__)


class BackendType(str, Enum):
    Kubernetes = "kubernetes"
    DockerCompose = "docker-compose"


def get_default_environment():
    cfg = find_macrostrat_config()
    if cfg is None:
        return None
    return _all_environments(cfg)[0]


class MacrostratConfig(Dynaconf):
    """Macrostrat config manager that reads from a TOML file"""

    config_file: Path
    srcroot: Path

    def __init__(self):

        cfg = find_macrostrat_config()
        settings_files = []
        should_load_environments = False

        if cfg is not None:
            settings_files.append(cfg)
            env = normalize_macrostrat_env()
            if env is not None:
                should_load_environments = True

        env_kwargs = dict()
        if should_load_environments:
            env_kwargs = dict(
                environments=True,
                env_switcher="MACROSTRAT_ENV",
            )

        super().__init__(
            envvar_prefix="MACROSTRAT",
            settings_files=settings_files,
            # We load dotenv files on our own
            load_dotenv=False,
            **env_kwargs,
        )
        if not hasattr(self, "env") or not should_load_environments:
            self.env = None

        self._connections = None
        self._endpoints = None

        self.config_file = None
        if cfg is not None:
            self.config_file = Path(cfg)

        # TODO: this enables sketchy behavior and tight coupling and should be removed.
        # However it is a useful hack for now
        self.srcroot = Path(__file__).parent.parent.parent.parent.parent

    def all_environments(self):
        # Parse out top-level headers from TOML file
        return _all_environments(self.config_file)

    def database_connections(self):
        """Every database configured for the active environment, by name.

        A method rather than an attribute because the credentials these name
        may live in a password manager: building this must not fetch anything,
        and exposing it as a settings *value* would invite eager resolution.
        """
        if self._connections is None:
            self._connections = connections_for(self)
        return self._connections

    def database_connection(self, name: str = DEFAULT_DATABASE):
        """One named database, composed but not yet resolved."""
        return self.database_connections().get(name, None)

    def database_url(self, role=DatabaseRole.Reader, name: str = DEFAULT_DATABASE):
        """A connection URL for *role* of *name*, resolving its credential now."""
        conn = self.database_connection(name)
        if conn is None:
            return None
        return conn.url(role)

    def storage_endpoints(self):
        """Every storage endpoint for the active environment, by name."""
        if self._endpoints is None:
            self._endpoints = endpoints_for(self)
        return self._endpoints

    def storage_endpoint(self, name: str = DEFAULT_ENDPOINT):
        """One named storage endpoint, credentials unresolved."""
        return self.storage_endpoints().get(name, None)

    def buckets(self):
        """The environment's logical-name to bucket-name mapping."""
        return buckets_for(self)

    def resolve_token_signing_key(self):
        """The JWT signing key, resolving it now if it names a secret.

        Named `resolve_…` rather than `token_signing_key` deliberately: the
        latter is the config key's own name, and Dynaconf resolves keys through
        attribute access, so a method by that name shadows the value it reads.

        Separate from every other accessor because of what it grants: a JWT
        signed with this and carrying `role: web_admin` is honoured by
        PostgREST, so this value is equivalent to unrestricted write access.
        Callers should be countable.
        """
        return reveal(as_secret(token_signing_key_value(self)))

    def get(self, key, default=None):
        if not "." in key:
            return getattr(self, key, default)

        keys = key.split(".")
        for k in keys:
            if k not in self:
                return default
            self = getattr(self, k)
        return self


def _all_environments(config_file: Path):
    """The selectable environments in a config file.

    `default` is Dynaconf's shared base layer rather than an environment, so it
    is excluded by name. It used to be skipped by *position*, which silently
    dropped the first real environment from any file that did not happen to
    lead with `[default]`.
    """
    with open(config_file, "r") as f:
        cfg = load_toml(f)
        return [k for k in cfg.keys() if k != DEFAULT_ENV]


settings = MacrostratConfig()

settings.validators.register(
    # `must_exist` is causing huge problems
    Validator("COMPOSE_ROOT", cast=Path),
    Validator(
        "env_files", cast=path_list_resolver(settings, require_file=True), default=None
    ),
    Validator(
        "script_dirs",
        cast=path_list_resolver(settings, require_directory=True),
        default=None,
    ),
    Validator("pg_database", cast=convert_to_string, default=None),
    # Backend information. We could potentially infer this from other environment variables
    Validator("backend", default="kubernetes", cast=BackendType),
    Validator("sources", cast=cast_sources, default=None),
    # Settings to control the location of arbitrary named databases
    Validator("databases", default={}),
    Validator("log_modules", cast=list, default=["macrostrat"]),
    Validator("base_url", cast=convert_to_string, default="https://macrostrat.org"),
)

macrostrat_env = getattr(settings, "env", "default")

if env_files := getattr(settings, "env_files", None):
    for env in env_files:
        log.info(f"Loading environment variables from {env}")
        # Resolve env file from settings path
        if not Path(env).is_absolute():
            env = settings.config_file.parent / env
        load_dotenv(env)

# Validate settings
settings.validators.validate()


# Settings for storage, if provided.
#
# As with `pg_database`, an environment whose storage credentials *name* secrets
# gets no ambient STORAGE_* variables: resolving them here would fetch on every
# invocation and hand the pair to every subprocess. Reach them through
# settings.storage_endpoint(...).credentials() instead.
if storage := getattr(settings, "storage", None):
    access_key = storage.get("access_key", None)
    secret_key = storage.get("secret_key", None)
    if is_secret_ref(access_key) or is_secret_ref(secret_key):
        log.info(
            "Storage credentials for this environment name secrets; deferring "
            "resolution and skipping the STORAGE_* environment export."
        )
    else:
        if access_key is None or secret_key is None:
            raise ValueError("Access key and secret key must be provided for storage")

        environ["STORAGE_ACCESS_KEY"] = access_key
        environ["STORAGE_SECRET_KEY"] = secret_key

# A database connection string for PostgreSQL
PG_DATABASE = getattr(settings, "pg_database", None)
url = None
# Not sure why this happens
if PG_DATABASE == "None":
    PG_DATABASE = None
# environ.get("MACROSTRAT_PG_DATABASE", None)

# A `pg_database` that *names* a secret rather than containing one cannot take
# the eager path below: resolving it here would put a password-manager prompt in
# front of every `macrostrat` invocation, and would export the credential into
# the environment of every subprocess — which is the leak this indirection
# exists to close. Such an environment gets no ambient PG* variables at all;
# callers reach the credential through `settings.database_url(role=...)`, and
# commands that genuinely need PG* for a subprocess ask for it explicitly.
#
# Adopting a secret reference is therefore also how an environment opts out of
# ambient credentials. Configs holding literals are untouched.
if PG_DATABASE is not None and is_secret_ref(PG_DATABASE):
    log.info(
        "pg_database for this environment names a secret (%s); deferring "
        "resolution and skipping the PG* environment export.",
        PG_DATABASE.split("://")[0] + "://…",
    )
    PG_DATABASE = None
elif PG_DATABASE is not None:
    # On mac and windows, we need to use the docker host `host.docker.internal` or `host.lima.internal`, etc.
    docker_localhost = getattr(settings, "docker_localhost", "localhost")
    PG_DATABASE_DOCKER = PG_DATABASE.replace("localhost", docker_localhost)

    # add this to the settings.databases mapping
    settings.databases["macrostrat"] = PG_DATABASE

    # Set environment variables
    url = make_url(PG_DATABASE)

    environ["PGHOST"] = url.host
    environ["PGPORT"] = str(url.port)

    for v in ("PGPASSWORD", "POSTGRES_PASSWORD"):
        environ[v] = url.password

    for v in ("PGUSER", "POSTGRES_USER"):
        environ[v] = url.username

    for v in ("PGDATABASE", "POSTGRES_DB"):
        environ[v] = url.database

    # Used for local running of Macrostrat
    environ["MACROSTRAT_DB_PORT"] = str(url.port)

    environ["MACROSTRAT_DATABASE_URL"] = PG_DATABASE

mysql_database = getattr(settings, "mysql_database", None)
if mysql_database is not None:
    mysql_database: URL = make_url(mysql_database).set(drivername="mysql+pymysql")
    # TODO: handle this more intelligently


if elevation_database := getattr(settings, "elevation_database", None):
    environ["ELEVATION_DATABASE_URL"] = elevation_database


environ["PG_DATABASE_CONTAINER"] = getattr(
    settings, "pg_database_container", "postgis/postgis:15-3.4"
)

# The active environment's safety policy: its class, and the gate guarding each
# scope of write. Resolved eagerly so that a fail-closed inference warns once
# per invocation rather than at some arbitrary later point.
settings.policy = policy_from_settings(settings)

# Note: the database connection is deliberately *not* materialised here. Use
# settings.database_connection() / settings.database_url(role=...).

# Set defaults
# Ideally we should be able to do this in the settings object
settings.offline = getattr(settings, "offline", False)

project_name = "macrostrat"
if macrostrat_env is not None:
    project_name = "macrostrat_" + macrostrat_env

environ["COMPOSE_PROJECT_NAME"] = project_name
settings.project_name = environ["COMPOSE_PROJECT_NAME"]

# Docker compose file
compose_file = getattr(settings, "compose_file", None)
if compose_file is None:
    root = getattr(settings, "compose_root", None)
    if root is not None:
        compose_root = Path(root).expanduser()
        environ["COMPOSE_ROOT"] = str(compose_root)
        compose_file = compose_root / "docker-compose.yaml"
if compose_file is not None:
    environ["COMPOSE_FILE"] = str(compose_file)


# A database connection string for MySQL
# This should eventually become optional if it isn't already
MYSQL_DATABASE = getattr(settings, "mysql_database", None)

if mapbox_token := getattr(settings, "mapbox_token", None):
    environ["MAPBOX_TOKEN"] = mapbox_token

# The *top-level* `secret_key` is the JWT signing key for api-v3 and, through
# `PGRST_JWT_SECRET`, for PostgREST — not a storage credential despite sharing
# the name with `[<env>.storage].secret_key`.
#
# It is the highest-privilege value in the config: signing `role: web_admin`
# mints a session that PostgREST honours, so holding it confers full write
# capability without touching a database password or passing any write gate.
# Exporting it at import put it in the environment of every subprocess of every
# command, and in `macrostrat self printenv`. A reference is therefore deferred
# like any other credential — reach it through settings.token_signing_key().
_token_signing_key = token_signing_key_value(settings)
if is_secret_ref(_token_signing_key):
    log.info(
        "The token-signing key for this environment names a secret; deferring "
        "resolution and skipping the SECRET_KEY environment export."
    )
elif _token_signing_key is not None:
    environ["SECRET_KEY"] = _token_signing_key

environ["MACROSTRAT_ROOT"] = str(settings.srcroot)


setup_source_roots_environment(settings.sources)

# Settings for local installation
