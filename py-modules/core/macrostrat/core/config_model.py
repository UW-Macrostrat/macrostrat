"""The schema of ``macrostrat.toml``.

One environment section of the file, fully described. The model is the
documentation: ``EnvironmentSettings.model_json_schema()`` is what
``macrostrat config schema`` prints, and every field's description is the
reference text for that key.

.. code-block:: toml

    [default]                        # inherited by every environment
    pg_database_container = "imresamu/postgis:15-3.4"
    [default.database]
    port = 5432

    [local]
    env_class    = "local"
    backend      = "docker-compose"
    compose_root = "./local-root"
    token_signing_key = "a-random-string"
    [local.database]
    host     = "localhost"
    port     = 5433
    user     = "macrostrat-admin"
    password = "a-local-password"
    [local.databases]
    rockd = "rockd"
    test  = "macrostrat_test"

    [production]
    env_class = "production"
    token_signing_key = "op://Macrostrat Prod/api-v3/jwt/secret_key"
    [production.database]
    host           = "db.production.svc.macrostrat.org"
    read_password  = "op://Macrostrat Prod/macrostrat-db/reader/password"
    write_user     = "op://Macrostrat Prod/macrostrat-db/admin/username"
    write_password = "op://Macrostrat Prod/macrostrat-db/admin/password"

Three rules keep the surface small:

- **One shape per thing.** A database is a URL *or* a table of components; a
  credential is a literal *or* a reference. There are no synonyms.
- **A removed key is an error, not a silent no-op.** :data:`REMOVED_KEYS` names
  each one and its replacement; the loader refuses a file that still uses one.
- **Unknown keys are reported.** A typo in a key name is the classic silent
  config failure, so the loader warns about top-level keys it does not know.
  Nested tables that subsystems extend (``storage``) accept extra keys.

Validation happens on the *merged* environment — ``[default]`` overlaid with
the selected section, then ``MACROSTRAT_*`` environment variables — so a
section in the file may be partial. ``env_class`` is required once merged.
"""

from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, model_validator

from .environment import EnvironmentClass

#: Config keys this CLI no longer reads, each with what replaces it. The loader
#: raises for any of these rather than ignoring them: a key that silently stops
#: working is how an environment ends up pointed at the wrong database.
REMOVED_KEYS: Dict[str, str] = {
    "pg_database": 'database = "postgresql://…" or a [<env>.database] table',
    "rockd_database": 'an entry in [<env>.databases], e.g. rockd = "rockd"',
    "sgp_database": 'an entry in [<env>.databases], e.g. sgp = "sgp"',
    "elevation_database": "an entry in [<env>.databases] named elevation",
    "mapboard_database": "an entry in [<env>.databases] named mapboard",
    "mysql_database": "nothing; MySQL access was retired with the v1 migration",
    "mysql_pod": "nothing; MySQL access was retired",
    "pg_database_pod": "nothing; unused",
    "proxy_command": "nothing; unused",
    "docker_base_url": "nothing; unused",
    "secret_key": "token_signing_key (the storage table keeps its own secret_key)",
}

#: Removed spellings inside a database table.
REMOVED_DATABASE_KEYS: Dict[str, str] = {
    "dbname": "database",
    "query": "options",
    "username": "user",
    "reader": "read_password",
    "writer": "write_password",
    "reader_user": "read_user",
    "writer_user": "write_user",
    "reader_password": "read_password",
    "writer_password": "write_password",
}


class RemovedKeys(ValueError):
    """One or more removed keys were found. Rendered by the loader."""

    def __init__(self, where: str, found: Mapping[str, str]):
        self.where = where
        self.found = dict(found)
        lines = [f"{where} uses keys this CLI no longer reads:"]
        for key, replacement in self.found.items():
            lines.append(f"  {key}  ->  {replacement}")
        super().__init__("\n".join(lines))


class _TableCompat:
    """Dict-style reads on a table model, as Dynaconf's boxes allowed.

    Consumers do ``settings.storage.get("endpoint")`` and
    ``"buckets" in settings.storage``; fields and extra keys both answer.
    """

    def get(self, key, default=None):
        if key in self:
            return getattr(self, key)
        return default

    def __getitem__(self, key):
        if key in self:
            return getattr(self, key)
        raise KeyError(key)

    def __contains__(self, key) -> bool:
        if key in type(self).model_fields:
            return getattr(self, key) is not None
        return key in (self.model_extra or {})

    def keys(self):
        return [
            k
            for k in list(type(self).model_fields) + list(self.model_extra or {})
            if k in self
        ]

    def items(self):
        return [(k, getattr(self, k)) for k in self.keys()]


def _check_removed(where: str, data: Any, table: Mapping[str, str]) -> None:
    if not isinstance(data, Mapping):
        return
    found = {k: table[k] for k in data if k in table}
    if found:
        raise RemovedKeys(where, found)


class BackendType(str, Enum):
    """How the environment's services are run."""

    Kubernetes = "kubernetes"
    DockerCompose = "docker-compose"


class DatabaseTable(_TableCompat, BaseModel):
    """A database described by its parts, with one login per role.

    ``user`` / ``password`` serve whichever role declares nothing of its own.
    Any login field may be a literal or a secret reference (``op://…``,
    ``env://…``, ``file://…``, ``keychain://…``); a reference is fetched when
    the credential is first used, never when config loads.
    """

    model_config = ConfigDict(extra="forbid")

    host: Optional[str] = Field(None, description="Server host name.")
    port: Optional[int] = Field(None, description="Server port. Default 5432.")
    database: Optional[str] = Field(
        None,
        description=(
            "Database name. The environment's default database is `macrostrat` "
            "when this is omitted."
        ),
    )
    driver: Optional[str] = Field(
        None, description="SQLAlchemy driver name. Default `postgresql`."
    )
    user: Optional[str] = Field(
        None,
        description="Login user for any role without its own. Default `macrostrat`.",
    )
    password: Optional[str] = Field(
        None, description="Password for any role without its own. Literal or reference."
    )
    read_user: Optional[str] = Field(None, description="Login user for the read role.")
    read_password: Optional[str] = Field(
        None, description="Password for the read role. Literal or reference."
    )
    write_user: Optional[str] = Field(
        None, description="Login user for the write role."
    )
    write_password: Optional[str] = Field(
        None, description="Password for the write role. Literal or reference."
    )
    item: Optional[str] = Field(
        None,
        description=(
            "A 1Password item, `op://<vault>/<item>`, whose `username` and "
            "`password` fields are the shared login. Sugar for writing "
            '`user = "op://…/username"` and `password = "op://…/password"`; '
            "either may still be given explicitly to override."
        ),
    )
    options: Dict[str, str] = Field(
        default_factory=dict,
        description=(
            "Connection parameters carried as the URL query string: `sslmode`, "
            "`connect_timeout`, `application_name`, and friends."
        ),
    )

    @model_validator(mode="before")
    @classmethod
    def _normalise(cls, data: Any) -> Any:
        if not isinstance(data, Mapping):
            return data
        _check_removed("a database table", data, REMOVED_DATABASE_KEYS)
        data = dict(data)
        item = data.get("item")
        if item:
            item = str(item).rstrip("/")
            data.setdefault("user", f"{item}/username")
            data.setdefault("password", f"{item}/password")
        if "options" in data and data["options"] is not None:
            data["options"] = {str(k): str(v) for k, v in dict(data["options"]).items()}
        return data


#: How a database may be written: a whole connection URL (or a reference to
#: one), or a table of parts.
DatabaseSpec = Union[str, DatabaseTable]


class StorageTable(_TableCompat, BaseModel):
    """An object-storage endpoint and its credential pair.

    Sub-tables extend it: ``buckets`` maps logical names to bucket names,
    ``admin`` is the cluster-administration endpoint kept deliberately
    separate, ``endpoints`` adds further named endpoints. Subsystems may add
    their own keys here, so unknown keys are kept rather than rejected.
    """

    model_config = ConfigDict(extra="allow")

    endpoint: Optional[str] = Field(
        None, description="Endpoint URL or host:port. `https://` implies TLS."
    )
    access_key: Optional[str] = Field(
        None, description="Access key. Literal or reference."
    )
    secret_key: Optional[str] = Field(
        None, description="Secret key. Literal or reference. Not the token-signing key."
    )
    bucket: Optional[str] = Field(None, description="Default bucket, if any.")
    type: Optional[str] = Field(
        None,
        description="`s3` (default) or `ceph-object-storage` for an admin endpoint.",
    )
    region: Optional[str] = Field(
        None, description="Region, when the endpoint needs one."
    )
    user_id: Optional[str] = Field(
        None, description="Object-storage user, for admin use."
    )
    item: Optional[str] = Field(
        None,
        description=(
            "A 1Password item, `op://<vault>/<item>`, whose `access_key` and "
            "`secret_key` fields are the credential pair. Sugar for the two "
            "explicit references; either may still be given to override."
        ),
    )
    buckets: Dict[str, str] = Field(
        default_factory=dict, description="Logical bucket name → bucket name."
    )
    admin: Optional["StorageTable"] = Field(
        None, description="The cluster-admin endpoint. Nothing resolves it by accident."
    )
    endpoints: Dict[str, Union[str, "StorageTable"]] = Field(
        default_factory=dict,
        description=(
            "Further named endpoints. A bare string is a bucket on the default "
            "endpoint; a table states only its differences."
        ),
    )

    @model_validator(mode="before")
    @classmethod
    def _normalise(cls, data: Any) -> Any:
        if not isinstance(data, Mapping):
            return data
        data = dict(data)
        item = data.get("item")
        if item:
            item = str(item).rstrip("/")
            data.setdefault("access_key", f"{item}/access_key")
            data.setdefault("secret_key", f"{item}/secret_key")
        return data


class SourceRoots(_TableCompat, BaseModel):
    """Checkouts of sibling repositories, for the local compose stack."""

    model_config = ConfigDict(extra="allow")

    api: Optional[Path] = None
    api_v3: Optional[Path] = None
    tileserver: Optional[Path] = None
    corelle: Optional[Path] = None
    web: Optional[Path] = None
    map_cache: Optional[Path] = None


class EnvironmentSettings(BaseModel):
    """One environment of ``macrostrat.toml``, after ``[default]`` is applied.

    The file's sections are partial; this is validated on the merged result.
    """

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    # -- identity and safety ------------------------------------------------
    env_class: Optional[EnvironmentClass] = Field(
        None,
        description=(
            "local | development | staging | production. Selects the default "
            "write gates and how long `macrostrat env` keeps the environment "
            "active. Required for every environment."
        ),
    )
    write_gate: Dict[str, str] = Field(
        default_factory=dict,
        description="Per-scope gate overrides: data / schema → none | confirm | typed | escalate.",
    )
    active_ttl: Optional[Union[str, int]] = Field(
        None,
        description='How long `macrostrat env <name>` stays active: "15m", "8h", "never".',
    )
    base_url: str = Field(
        "https://macrostrat.org", description="Public URL of this environment."
    )
    backend: BackendType = Field(
        BackendType.Kubernetes,
        description="`kubernetes`, or `docker-compose` for the local stack.",
    )

    # -- credentials ------------------------------------------------------------
    token_signing_key: Optional[str] = Field(
        None,
        description=(
            "Signs api-v3's JWTs and is PostgREST's `PGRST_JWT_SECRET`. The most "
            "privileged value in the file. Literal or reference."
        ),
    )
    op_account: Optional[str] = Field(
        None,
        description=(
            "1Password account (`team.1password.com`) that `op://` references "
            "resolve against. Needed on a machine signed in to more than one."
        ),
    )

    # -- databases -----------------------------------------------------------
    database: Optional[DatabaseSpec] = Field(
        None,
        description=(
            "The default database: a connection URL, a reference to one, or a "
            "table of parts."
        ),
    )
    databases: Dict[str, DatabaseSpec] = Field(
        default_factory=dict,
        description=(
            "Further databases by name. A bare string is a database name on the "
            "default server; a URL (or reference) stands alone; a table states "
            "only its differences from the default."
        ),
    )
    docker_localhost: Optional[str] = Field(
        None,
        description=(
            "What `localhost` is called from inside a container, e.g. "
            "`host.docker.internal`. Used by database tools run in Docker."
        ),
    )

    # -- storage ----------------------------------------------------------------
    storage: Optional[StorageTable] = Field(None, description="Object storage.")

    # -- local stack ------------------------------------------------------------
    compose_root: Optional[Path] = Field(
        None, description="Directory holding `docker-compose.yaml` for the local stack."
    )
    compose_file: Optional[Path] = Field(
        None,
        description="Compose file, when it is not `<compose_root>/docker-compose.yaml`.",
    )
    pg_database_container: str = Field(
        "postgis/postgis:15-3.4",
        description="Image used to run database tools (`psql`, `pg_dump`) in Docker.",
    )
    mapbox_token: Optional[str] = Field(
        None, description="Mapbox token for the web stack."
    )
    sources: SourceRoots = Field(
        default_factory=SourceRoots,
        description="Checkouts of sibling repositories the local stack builds from.",
    )

    # -- kubernetes -------------------------------------------------------------
    kube_namespace: Optional[str] = Field(
        None, description="Kubernetes namespace. Enables the `kube` commands."
    )
    kube_proxy: Optional[str] = Field(None, description="SOCKS proxy for kubectl.")

    # -- CLI behaviour ----------------------------------------------------------
    env_files: List[Path] = Field(
        default_factory=list,
        description="dotenv files loaded into the environment before anything else.",
    )
    script_dirs: List[Path] = Field(
        default_factory=list,
        description="Directories searched for `macrostrat-<command>` scripts.",
    )
    log_modules: List[str] = Field(
        default_factory=lambda: ["macrostrat"],
        description="Logger names enabled by `--verbose`.",
    )
    offline: bool = Field(
        False, description="Skip network-dependent steps where possible."
    )
    subsystems: Dict[str, Union[bool, str]] = Field(
        default_factory=dict, description="Optional subsystems to enable."
    )
    usage_stats_client_salt: Optional[str] = Field(
        None, description="Salt for hashing client identifiers in usage stats."
    )

    @model_validator(mode="before")
    @classmethod
    def _reject_removed_keys(cls, data: Any, info: ValidationInfo) -> Any:
        if not isinstance(data, Mapping):
            return data
        env = (info.context or {}).get("env")
        # Quotes, not brackets: this text is printed through Rich, which
        # would read `[local]` as a style tag and drop it.
        where = f"environment '{env}'" if env else "the configuration"
        _check_removed(where, data, REMOVED_KEYS)
        if env is not None and data.get("env_class") in (None, ""):
            raise ValueError(
                f"environment '{env}' declares no env_class. Add "
                f'env_class = "{_suggest_class(env)}" (one of '
                f"{', '.join(c.value for c in EnvironmentClass)}) to its section."
            )
        return data

    def unknown_keys(self) -> List[str]:
        """Top-level keys the schema does not know. The loader warns about them."""
        return sorted(self.model_extra or {})


def _suggest_class(env: str) -> str:
    """A plausible `env_class` for an environment name, for the error message."""
    name = env.lower()
    for klass in EnvironmentClass:
        if klass.value in name:
            return klass.value
    if name in ("dev", "local-dev"):
        return EnvironmentClass.Development.value
    if name in ("prod",):
        return EnvironmentClass.Production.value
    return EnvironmentClass.Production.value


def config_json_schema() -> dict:
    """The JSON Schema of one environment section, for editors and docs."""
    return EnvironmentSettings.model_json_schema()
