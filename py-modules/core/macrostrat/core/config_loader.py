"""The opt-in, schema-validated configuration loader (config version 2).

A ``macrostrat.toml`` opts in with a top-level ``config_version = 2`` (or the
environment sets ``MACROSTRAT_CONFIG_VERSION=2``). :mod:`macrostrat.core.config`
then builds its ``settings`` object here instead of through Dynaconf. Nothing
else in the CLI changes: :class:`MacrostratSettings` presents the surface the
Dynaconf object had — attribute access, dotted ``get()``, the registry methods,
and the legacy read-only keys consumers still ask for — so a file can move to
the new format one environment file at a time, without touching consumers.

What the new loader does differently:

- **Validates against a schema** (:mod:`config_model`), so a mistyped key is
  reported, a removed key is an error naming its replacement, and
  ``env_class`` is required.
- **Layers the whole ``[default]`` section** under the selected environment,
  not only the database and storage tables.
- **Applies ``MACROSTRAT_*`` environment overrides** deliberately:
  ``MACROSTRAT_BASE_URL``, ``MACROSTRAT_DATABASE__HOST``; the variables the
  CLI uses for its own control (``MACROSTRAT_ENV``, ``MACROSTRAT_CONFIG``, …)
  are never mistaken for settings.
- **Points ``op`` at an account** from ``op_account``.
"""

import tomllib
from copy import deepcopy
from os import environ
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Union

from pydantic import ConfigDict, Field, PrivateAttr, ValidationError

from macrostrat.utils import get_logger

from .config_model import EnvironmentSettings, RemovedKeys
from .connections import (
    DEFAULT_DATABASE,
    DatabaseRole,
    MissingCredential,
    connections_for,
)
from .environment import DEFAULT_ENV, EnvironmentPolicy, policy_from_settings
from .exc import ConfigError, UnknownEnvironment
from .secrets import as_secret, configure_onepassword, reveal
from .storage import DEFAULT_ENDPOINT, buckets_for, endpoints_for

log = get_logger(__name__)

#: Top-level key in the file that selects this loader.
CONFIG_VERSION_KEY = "config_version"
#: Environment variable that does the same, for a file that cannot be edited.
CONFIG_VERSION_VAR = "MACROSTRAT_CONFIG_VERSION"
#: The version this module implements.
CONFIG_VERSION = 2

#: Prefix of environment variables that override settings.
ENV_PREFIX = "MACROSTRAT_"
#: Separator for nested keys: ``MACROSTRAT_DATABASE__HOST`` → ``database.host``.
ENV_NESTING = "__"
#: ``MACROSTRAT_*`` variables the CLI uses for itself; never settings.
CONTROL_VARIABLES = frozenset(
    {
        "ENV",
        "ENV_EXPIRES",
        "CONFIG",
        "CONFIG_VERSION",
        "ROOT",
        "PYROOT",
        "SHOULD_REINSTALL",
        "INSTALL_PATH",
        "DATABASE_URL",
        "DB_PORT",
    }
)


# ---------------------------------------------------------------------------
# Reading and layering the file
# ---------------------------------------------------------------------------


def read_config_file(path: Optional[Path]) -> dict:
    """The parsed TOML, or ``{}`` when there is no file."""
    if path is None:
        return {}
    try:
        with open(path, "rb") as f:
            return tomllib.load(f)
    except OSError as err:
        raise ConfigError(f"Could not read {path}", err.strerror) from None
    except tomllib.TOMLDecodeError as err:
        raise ConfigError(f"{path} is not valid TOML", str(err)) from None


def config_version(path: Optional[Path], raw: Optional[Mapping] = None) -> int:
    """Which loader a config file asks for. Defaults to 1 (Dynaconf)."""
    # An empty variable is the same as an unset one: the file decides.
    declared = environ.get(CONFIG_VERSION_VAR) or None
    if declared is None and path is not None:
        if raw is None:
            try:
                raw = read_config_file(path)
            except ConfigError:
                return 1
        declared = raw.get(CONFIG_VERSION_KEY)
    if declared in (None, ""):
        return 1
    try:
        return int(str(declared).strip())
    except ValueError:
        raise ConfigError(
            f"{CONFIG_VERSION_KEY} must be an integer, got {declared!r}",
            f"Write {CONFIG_VERSION_KEY} = {CONFIG_VERSION} to use the new loader.",
        ) from None


def environment_names(raw: Mapping) -> List[str]:
    """The selectable environments: every table except ``[default]``."""
    return [k for k, v in raw.items() if isinstance(v, Mapping) and k != DEFAULT_ENV]


def deep_merge(base: Optional[Mapping], override: Optional[Mapping]) -> dict:
    """*override* on top of *base*, recursing into tables. Lists replace."""
    out = deepcopy(dict(base or {}))
    for key, value in dict(override or {}).items():
        if isinstance(value, Mapping) and isinstance(out.get(key), Mapping):
            out[key] = deep_merge(out[key], value)
        else:
            out[key] = deepcopy(value)
    return out


def merged_environment(raw: Mapping, env: Optional[str]) -> dict:
    """The table to validate: top-level keys, then ``[default]``, then ``[env]``."""
    top = {
        k: v
        for k, v in raw.items()
        if not isinstance(v, Mapping) and k != CONFIG_VERSION_KEY
    }
    merged = deep_merge(top, raw.get(DEFAULT_ENV, {}))
    if env is not None:
        merged = deep_merge(merged, raw.get(env, {}))
    return merged


# ---------------------------------------------------------------------------
# Environment-variable overrides
# ---------------------------------------------------------------------------


def _parse_env_value(text: str) -> Any:
    """A TOML-typed value if *text* parses as one, else the string itself.

    ``MACROSTRAT_OFFLINE=true`` becomes a bool and ``MACROSTRAT_DATABASE__PORT=5433``
    an int, while ``MACROSTRAT_BACKEND=docker-compose`` stays a string.
    """
    try:
        return tomllib.loads(f"v = {text}")["v"]
    except (tomllib.TOMLDecodeError, KeyError):
        return text


def environment_overrides(env: Mapping[str, str] = environ) -> dict:
    """``MACROSTRAT_*`` variables as a nested settings table."""
    out: dict = {}
    for name, value in env.items():
        if not name.startswith(ENV_PREFIX):
            continue
        rest = name[len(ENV_PREFIX) :]
        if rest in CONTROL_VARIABLES or rest.endswith("_SRC") or not rest:
            continue
        path = [p.lower() for p in rest.split(ENV_NESTING) if p]
        if not path:
            continue
        node = out
        for part in path[:-1]:
            node = node.setdefault(part, {})
            if not isinstance(node, dict):
                break
        else:
            node[path[-1]] = _parse_env_value(value)
    return out


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def _clean_loc(loc) -> str:
    """A dotted key path without pydantic's union-branch tags.

    A `str | DatabaseTable` field reports its location as
    `database.DatabaseTable.port`; the reader wrote `database.port`.
    """
    parts = []
    for p in loc:
        text = str(p)
        if text == "__root__" or "[" in text:
            continue
        if text in ("str", "int", "float", "bool", "dict", "list"):
            continue
        if text[:1].isupper() and text.isidentifier():
            continue
        parts.append(text)
    return ".".join(parts)


def _render_validation_error(err: ValidationError, env: Optional[str]) -> str:
    entries = []
    for item in err.errors():
        msg = item.get("msg", "")
        if msg.startswith("Value error, "):
            msg = msg[len("Value error, ") :]
        entries.append((_clean_loc(item.get("loc", ())), msg))
    # A union that failed on its `str` branch also reports a real problem on
    # the table branch; the "should be a string" line is noise beside it.
    locs = {loc for loc, _ in entries}
    lines = []
    for loc, msg in entries:
        if msg == "Input should be a valid string" and any(
            other != loc and other.startswith(loc) for other in locs
        ):
            continue
        line = f"{loc}: {msg}" if loc else msg
        if line not in lines:
            lines.append(line)
    return "\n".join(lines)


def validate_environment(table: Mapping, env: Optional[str]) -> EnvironmentSettings:
    """Validate a merged table, rendering failures as one :class:`ConfigError`."""
    try:
        return EnvironmentSettings.model_validate(dict(table), context={"env": env})
    except ValidationError as err:
        where = f"environment '{env}'" if env else "the configuration"
        raise ConfigError(
            f"macrostrat.toml: {where} is not valid",
            _render_validation_error(err, env),
        ) from None


# ---------------------------------------------------------------------------
# The settings object
# ---------------------------------------------------------------------------


class _AttrDict(dict):
    """A dict that also answers to attribute access, like Dynaconf's boxes.

    Consumers written against Dynaconf do ``settings.get("storage.admin").type``;
    this keeps that working for values that come back from :meth:`get`.
    """

    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            raise AttributeError(name) from None


def _boxed(value):
    if isinstance(value, Mapping) and not isinstance(value, _AttrDict):
        return _AttrDict({k: _boxed(v) for k, v in value.items()})
    return value


class _DatabasesView(dict):
    """``settings.databases`` with the legacy reading semantics.

    Under Dynaconf this key held whole connection URLs, and consumers still do
    ``settings.databases["test"]`` expecting one. The registry composes each
    entry, so a literal entry is handed back as a URL string; a vaulted one is
    handed back as written, since composing it would fetch the credential.
    Iteration and ``model_dump`` still see the raw specs.
    """

    def __init__(self, specs: Mapping, owner: "MacrostratSettings"):
        super().__init__(specs)
        self._owner = owner

    def _compat(self, name, raw):
        conn = self._owner.database_connection(name)
        if conn is None or conn.requires_resolution(DatabaseRole.Writer):
            return raw
        try:
            return self._owner._exported_url(conn)
        except MissingCredential:
            return raw

    def __getitem__(self, name):
        return self._compat(name, super().__getitem__(name))

    def get(self, name, default=None):
        if name not in self:
            return default
        return self[name]


#: Config keys that read as *absent* (AttributeError) when unset, matching
#: Dynaconf. Every optional key of the file schema; none of the runtime ones.
_ABSENT_WHEN_NONE = frozenset(
    name
    for name, field in EnvironmentSettings.model_fields.items()
    if field.default is None and field.default_factory is None
)

#: Legacy single-URL keys, and the registry entry each one reads as.
LEGACY_DATABASE_KEYS = {
    "pg_database": DEFAULT_DATABASE,
    "rockd_database": "rockd",
    "sgp_database": "sgp",
    "elevation_database": "elevation",
    "mapboard_database": "mapboard",
}


class MacrostratSettings(EnvironmentSettings):
    """The settings object for a version-2 config: schema-typed, Dynaconf-shaped.

    Attributes are typed (``settings.compose_root`` is a :class:`~pathlib.Path`,
    ``settings.backend`` a :class:`BackendType`). :meth:`get` returns plain
    values — strings, numbers, dicts — the way the Dynaconf object did, and
    accepts dotted keys. The legacy single-URL keys (``pg_database``,
    ``rockd_database``, …) read as composed URLs when the login is literal, so
    consumers written against them keep working on a literal config.
    """

    model_config = ConfigDict(extra="allow", arbitrary_types_allowed=True)

    env: Optional[str] = Field(None, description="The active environment.")
    config_file: Optional[Path] = None
    srcroot: Path = Field(default_factory=lambda: Path(__file__).parents[4])
    policy: Optional[EnvironmentPolicy] = None
    project_name: str = "macrostrat"

    _connections: Optional[dict] = PrivateAttr(default=None)
    _endpoints: Optional[dict] = PrivateAttr(default=None)
    _dump: Optional[dict] = PrivateAttr(default=None)
    #: True while the registry is being composed. The registry asks for the
    #: legacy `pg_database` key as a fallback, and the legacy key is answered
    #: *from* the registry — so during composition it must read as absent.
    _composing: bool = PrivateAttr(default=False)

    def model_post_init(self, __context) -> None:
        # `databases` keeps its raw specs for the registry, but answers legacy
        # subscript reads with composed URLs.
        object.__setattr__(self, "databases", _DatabasesView(self.databases, self))

    def __getattribute__(self, name):
        # Dynaconf raised AttributeError for a key the file did not set, and
        # consumers lean on that: `getattr(settings, "storage", {})`. A typed
        # field that is None is therefore reported as absent. The runtime
        # fields (`env`, `policy`, …) are legitimately None and are exempt.
        value = object.__getattribute__(self, name)
        if value is None and name in _ABSENT_WHEN_NONE:
            raise AttributeError(name)
        return value

    # -- the raw view -------------------------------------------------------

    def _raw(self) -> dict:
        if self._dump is None:
            self._dump = self.model_dump(
                mode="json",
                exclude_none=True,
                exclude={"policy", "srcroot", "config_file", "project_name"},
            )
        return self._dump

    def get(self, key: str, default=None):
        """A setting by (possibly dotted) name, as a plain value.

        Case-insensitive on the first segment, as Dynaconf was, so
        ``settings.get("ROCKD_DATABASE")`` still finds ``rockd_database``.
        """
        parts = str(key).split(".")
        head, rest = parts[0], parts[1:]
        value = self._top_level(head)
        if value is _MISSING:
            return default
        for part in rest:
            value = _lookup(value, part)
            if value is _MISSING:
                return default
        return _boxed(value)

    def _top_level(self, name: str):
        for candidate in (name, name.lower()):
            if candidate in LEGACY_DATABASE_KEYS:
                if self._composing:
                    return _MISSING
                return self._legacy_database_url(LEGACY_DATABASE_KEYS[candidate])
            if candidate == "secret_key":
                return self.__dict__.get("token_signing_key")
            raw = self._raw()
            if candidate in raw:
                return raw[candidate]
            if candidate in ("env", "config_file", "srcroot", "policy", "project_name"):
                return getattr(self, candidate)
        return _MISSING

    def __contains__(self, key) -> bool:
        return self.get(key, _MISSING) is not _MISSING

    def __getitem__(self, key):
        value = self.get(key, _MISSING)
        if value is _MISSING:
            raise KeyError(key)
        return value

    def __getattr__(self, name):
        # Pydantic serves fields and extras; this handles the legacy keys.
        if name in LEGACY_DATABASE_KEYS:
            return self._legacy_database_url(LEGACY_DATABASE_KEYS[name])
        if name == "secret_key":
            return self.__dict__.get("token_signing_key")
        return super().__getattr__(name)

    # -- legacy URL compatibility -------------------------------------------

    def _exported_url(self, conn, role=DatabaseRole.Writer) -> str:
        """A URL string for another process: resolved, without CLI attribution."""
        url = conn.url(role)
        configured = getattr(conn, "options", None) or {}
        if "application_name" not in configured:
            query = {k: v for k, v in url.query.items() if k != "application_name"}
            url = url.set(query=query)
        return url.render_as_string(hide_password=False)

    def _legacy_database_url(self, name: str) -> Optional[str]:
        """The old whole-URL reading of a database, when it costs no fetch."""
        conn = self.database_connection(name)
        if conn is None or conn.requires_resolution(DatabaseRole.Writer):
            return None
        try:
            return self._exported_url(conn)
        except MissingCredential:
            return None

    # -- the registry --------------------------------------------------------

    def all_environments(self) -> List[str]:
        return environment_names(read_config_file(self.config_file))

    def database_connections(self):
        if self._connections is None:
            self._composing = True
            try:
                self._connections = connections_for(self)
            finally:
                self._composing = False
        return self._connections

    def database_connection(self, name: str = DEFAULT_DATABASE):
        return self.database_connections().get(name, None)

    def database_url(self, role=DatabaseRole.Reader, name: str = DEFAULT_DATABASE):
        conn = self.database_connection(name)
        if conn is None:
            return None
        return conn.url(role)

    def storage_endpoints(self):
        if self._endpoints is None:
            self._endpoints = endpoints_for(self)
        return self._endpoints

    def storage_endpoint(self, name: str = DEFAULT_ENDPOINT):
        return self.storage_endpoints().get(name, None)

    def buckets(self):
        return buckets_for(self)

    def resolve_token_signing_key(self):
        return reveal(as_secret(self.__dict__.get("token_signing_key")))


class _Missing:
    def __repr__(self):
        return "<missing>"


_MISSING = _Missing()


def _lookup(value, key: str):
    """One step of a dotted lookup over dicts and models."""
    if isinstance(value, Mapping):
        if key in value:
            return value[key]
        lowered = {str(k).lower(): k for k in value}
        if key.lower() in lowered:
            return value[lowered[key.lower()]]
        return _MISSING
    if hasattr(value, key):
        return getattr(value, key)
    return _MISSING


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------


def _resolve_paths(settings: MacrostratSettings) -> None:
    """Expand ``~`` and resolve file lists relative to the config file."""
    base = settings.config_file.parent if settings.config_file else Path.cwd()

    def one(p: Path) -> Path:
        p = Path(p).expanduser()
        if not p.is_absolute():
            p = base / p
        return p

    for name, kind in (("env_files", "file"), ("script_dirs", "directory")):
        resolved = []
        for p in getattr(settings, name):
            p = one(p)
            if not p.exists():
                raise ConfigError(
                    f"{name} names a {kind} that does not exist: {p}",
                    f"Fix or remove it in {settings.config_file}.",
                )
            resolved.append(p.resolve())
        setattr(settings, name, resolved)

    for name in ("compose_root", "compose_file"):
        value = getattr(settings, name, None)
        if value is not None:
            setattr(settings, name, one(value))

    sources = settings.sources
    for field in list(type(sources).model_fields) + list(sources.model_extra or {}):
        value = getattr(sources, field, None)
        if value is not None:
            setattr(sources, field, Path(value).expanduser())
    settings._dump = None


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def load_settings_v2(
    config_file: Optional[Path],
    env: Optional[str],
    *,
    environ: Mapping[str, str] = environ,
) -> MacrostratSettings:
    """Build the settings object for *env* from *config_file*.

    *env* has already been decided by :func:`~macrostrat.core.utils.normalize_macrostrat_env`.
    An *env* the file does not define is refused with the list it does.
    """
    raw = read_config_file(config_file)
    available = environment_names(raw)
    if env is not None and env not in available:
        raise UnknownEnvironment(env, available, config_file)

    table = deep_merge(merged_environment(raw, env), environment_overrides(environ))
    validated = validate_environment(table, env)

    # model_dump carries the extras along, so unknown keys survive the copy.
    settings = MacrostratSettings(
        **validated.model_dump(exclude_unset=True),
        env=env,
        config_file=Path(config_file) if config_file else None,
    )
    _resolve_paths(settings)

    unknown = settings.unknown_keys()
    if unknown:
        log.warning(
            "macrostrat.toml: %s has keys the schema does not know: %s. "
            "Check the spelling; `macrostrat config schema` lists the keys.",
            f"environment '{env}'" if env else "the configuration",
            ", ".join(unknown),
        )

    configure_onepassword(settings.get("op_account"))
    settings.policy = policy_from_settings(settings)
    return settings


__all__ = [
    "CONFIG_VERSION",
    "CONFIG_VERSION_KEY",
    "CONFIG_VERSION_VAR",
    "MacrostratSettings",
    "RemovedKeys",
    "config_version",
    "deep_merge",
    "environment_names",
    "environment_overrides",
    "load_settings_v2",
    "merged_environment",
    "read_config_file",
    "validate_environment",
]
