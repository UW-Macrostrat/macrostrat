from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from os import environ, unsetenv
from pathlib import Path
from sys import argv
from typing import Optional

import toml
from click import get_app_dir

from macrostrat.utils import get_logger

log = get_logger(__name__)


# Load config before we do anything else
def find_config(start_dir: Path):
    """Find the macrostrat.toml config file"""

    next_dir = start_dir.resolve()
    while next_dir != next_dir.parent:
        if (next_dir / "macrostrat.toml").exists():
            return next_dir
        next_dir = next_dir.parent
    return None


def env_text():
    return f"environment [bold cyan]{environ.get('MACROSTRAT_ENV')}[/]"


#: App-state keys holding the remembered environment, when it lapses, and
#: which config file it was set against.
ACTIVE_ENV_KEY = "active_env"
ACTIVE_ENV_EXPIRES_KEY = "active_env_expires"
ACTIVE_ENV_CONFIG_KEY = "active_env_config"

#: Environment variables carrying a per-shell environment (`macrostrat env
#: --shell`). The second is optional and makes a shell session lapse the same
#: way a remembered one does.
ENV_VAR = "MACROSTRAT_ENV"
ENV_EXPIRES_VAR = "MACROSTRAT_ENV_EXPIRES"


def extract_env_from_argv(args=None) -> Optional[str]:
    """Pull `--env`/`-e` out of *args*, removing both tokens. Mutates in place.

    The single place this happens. It used to be scraped in
    `Macrostrat.__init__` *and* set again in `MacrostratControlCommand.callback`
    — the latter, by its own comment, too late to affect config. Two parsers for
    one flag is how they drift.

    Scraping is still necessary rather than ugly: config is loaded while the
    application is constructed, which is before Typer has parsed anything.
    """
    argv_list = argv if args is None else args
    for i, arg in enumerate(argv_list):
        if arg in ("--env", "-e") and i + 1 < len(argv_list):
            value = argv_list[i + 1]
            argv_list.pop(i + 1)
            argv_list.pop(i)
            return value
        if arg.startswith("--env="):
            argv_list.pop(i)
            return arg.split("=", 1)[1]
    return None


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_timestamp(raw) -> Optional[datetime]:
    """An aware UTC datetime from a stored value, or `datetime.min` if corrupt.

    A corrupt timestamp means *already lapsed*, never *never lapses*: failing
    closed here is what keeps a damaged state file from granting a permanent
    environment.
    """
    if raw is None:
        return None
    if isinstance(raw, datetime):
        value = raw
    else:
        try:
            value = datetime.fromisoformat(str(raw))
        except ValueError:
            return datetime.min.replace(tzinfo=timezone.utc)
    if value.tzinfo is None:
        # Timestamps written before expiries were stored aware were local time.
        value = value.astimezone()
    return value.astimezone(timezone.utc)


@dataclass
class ActiveEnvironment:
    """How this invocation came to have an environment, and whether it is fresh.

    Resolved once, while config loads, and consulted later by whatever decides
    that the environment is about to be *used* — so that a lapsed pointer is
    kept and questioned rather than silently dropped.
    """

    name: str
    #: ``explicit`` (`--env`), ``shell`` (an exported variable), or
    #: ``remembered`` (`macrostrat env <name>`).
    source: str
    #: When it lapses, or None if it does not.
    expires: Optional[datetime] = None
    #: The config file a remembered environment was set against.
    config_file: Optional[Path] = None
    #: Set once the operator has agreed to keep using a lapsed environment for
    #: this invocation, so they are asked at most once.
    approved: bool = False

    @property
    def remaining(self) -> Optional[timedelta]:
        if self.expires is None:
            return None
        return self.expires - _now()

    @property
    def lapsed(self) -> bool:
        remaining = self.remaining
        return remaining is not None and remaining <= timedelta(0)

    @property
    def needs_approval(self) -> bool:
        return self.lapsed and not self.approved


_ACTIVE: Optional[ActiveEnvironment] = None


def active_environment() -> Optional[ActiveEnvironment]:
    """The environment this invocation resolved, or None if there is none."""
    return _ACTIVE


def _set_active(state: Optional[ActiveEnvironment]) -> None:
    global _ACTIVE
    _ACTIVE = state


def environments_in(config_file) -> list:
    """The selectable environments in a config file.

    `default` is Dynaconf's shared base layer rather than an environment, so it
    is excluded by name. It used to be skipped by *position*, which silently
    dropped the first real environment from any file that did not happen to
    lead with `[default]`.
    """
    if config_file is None:
        return []
    try:
        with open(config_file, "r") as f:
            cfg = toml.load(f)
    except (OSError, ValueError, TypeError):
        return []
    return [k for k in cfg.keys() if k != "default"]


def active_env_expiry() -> Optional[datetime]:
    """When the remembered environment lapses, or None if it does not."""
    return _parse_timestamp(get_app_state(ACTIVE_ENV_EXPIRES_KEY))


def active_env_remaining() -> Optional[timedelta]:
    """Time left on the remembered environment, or None if it does not expire."""
    expires = active_env_expiry()
    if expires is None:
        return None
    return expires - _now()


def remembered_environment() -> Optional[ActiveEnvironment]:
    """The pointer in app state as written, whether or not it applies here."""
    if not get_app_state_file().exists():
        return None
    env = get_app_state(ACTIVE_ENV_KEY)
    if env is None:
        return None
    config = get_app_state(ACTIVE_ENV_CONFIG_KEY)
    return ActiveEnvironment(
        name=str(env),
        source="remembered",
        expires=active_env_expiry(),
        config_file=Path(config) if config else None,
    )


def set_active_env(
    env: Optional[str],
    *,
    expires_in: Optional[timedelta] = None,
    config_file: Optional[Path] = None,
):
    """Remember *env*, with an expiry unless it is exempt, for *config_file*.

    The pointer is scoped to the config file it was set against: app state is
    per user while the config file is found per directory, and applying a
    pointer set for one file to another is how a remembered `development` met a
    config that had never heard of it.
    """
    if env is None:
        set_app_state(ACTIVE_ENV_KEY, None, wipe_others=True)
        _set_active(None)
        return None
    set_app_state(ACTIVE_ENV_KEY, env, wipe_others=True)
    if config_file is not None:
        set_app_state(ACTIVE_ENV_CONFIG_KEY, str(Path(config_file).resolve()))
    expires = None
    if expires_in is not None:
        expires = _now() + expires_in
        set_app_state(ACTIVE_ENV_EXPIRES_KEY, expires.isoformat())
    _set_active(
        ActiveEnvironment(
            name=env, source="remembered", expires=expires, config_file=config_file
        )
    )
    return expires


def renew_active_env(expires_in: Optional[timedelta]):
    """Re-stamp the remembered environment's expiry from now.

    The operator has just agreed to keep using it, so this is the same act as
    `macrostrat env <name>` — a fresh, bounded grant.
    """
    state = _ACTIVE
    if state is None:
        return None
    expires = None
    if expires_in is not None:
        expires = _now() + expires_in
    if state.source == "remembered":
        if expires is None:
            set_app_state(ACTIVE_ENV_EXPIRES_KEY, None)
        else:
            set_app_state(ACTIVE_ENV_EXPIRES_KEY, expires.isoformat())
    state.expires = expires
    state.approved = True
    return expires


def _same_file(a: Optional[Path], b: Optional[Path]) -> bool:
    if a is None or b is None:
        return True
    try:
        return Path(a).resolve() == Path(b).resolve()
    except OSError:
        return str(a) == str(b)


def normalize_macrostrat_env(config_file: Optional[Path] = None) -> Optional[str]:
    """The active environment for this invocation, or None.

    Order: an explicit `MACROSTRAT_ENV` (which `--env` has already been folded
    into) always wins. It lapses only if a `MACROSTRAT_ENV_EXPIRES` from
    `macrostrat env --shell` says so. A *remembered* environment applies only
    if it was set against this config file and names an environment the file
    has; a lapsed one is **kept**, and whoever is about to use it asks first
    (see `macrostrat.core.safety.require_environment`).

    Deliberately writes nothing: this runs while config loads, for every
    invocation including `--help`, and a load must not edit state.
    """
    _set_active(None)

    if ENV_VAR in environ:
        env = environ[ENV_VAR]
        if env in ("", "none", "None"):
            unsetenv(ENV_VAR)
            environ.pop(ENV_VAR, None)
            return None
        expires = _parse_timestamp(environ.get(ENV_EXPIRES_VAR) or None)
        source = "shell" if expires is not None else "explicit"
        _set_active(ActiveEnvironment(name=env, source=source, expires=expires))
        log.info("active environment: %s", env_text())
        return env

    state = remembered_environment()
    if state is None:
        return None

    if config_file is None:
        config_file = find_macrostrat_config()

    if not _same_file(state.config_file, config_file):
        log.info(
            "The remembered environment %r was set for %s and does not apply "
            "to %s; ignoring it here.",
            state.name,
            state.config_file,
            config_file,
        )
        return None

    if config_file is not None and state.name not in environments_in(config_file):
        log.warning(
            "The remembered environment %r is not defined in %s; ignoring it. "
            "Run `macrostrat env <name>` to pick one of its environments, or "
            "`macrostrat env --unset` to forget it.",
            state.name,
            config_file,
        )
        return None

    if state.lapsed:
        log.debug(
            "The remembered environment %r has lapsed; it will be confirmed "
            "before it is used.",
            state.name,
        )

    state.config_file = config_file
    _set_active(state)
    environ[ENV_VAR] = state.name
    log.info("active environment: %s", env_text())
    return state.name


def find_macrostrat_config() -> Optional[Path]:
    """Find the macrostrat.toml config file"""
    # If the MACROSTRAT_CONFIG env var is set, use that
    if "MACROSTRAT_CONFIG" in environ:
        # Handle special values signifying no config
        if environ["MACROSTRAT_CONFIG"] in ("", "none", "None"):
            return None

        return Path(environ["MACROSTRAT_CONFIG"])

    # Find root dir upwards
    macrostrat_root = find_config(Path.cwd())
    if macrostrat_root is None:
        # Find user-specific config in home dir
        macrostrat_root = find_config(Path.home() / ".config" / "macrostrat")

    # Find config upwards from utils installation
    if macrostrat_root is None:
        macrostrat_root = find_config(Path(__file__).parent)

    if macrostrat_root is None:
        return None
        # raise RuntimeError("Could not find macrostrat.toml")

    return macrostrat_root / "macrostrat.toml"


def is_pg_url(url):
    return (url.startswith("postgres") or url.startswith("postgresql")) and "://" in url


def convert_to_string(value):
    if value is None:
        return None
    return str(value)


def list_of_paths(value):
    if value is None:
        return []
    if isinstance(value, str):
        return [Path(value)]
    if isinstance(value, list):
        return [Path(v) for v in value]
    raise ValueError(f"Expected a string or list of strings, got {type(value)}")


def path_list_resolver(settings, *, require_directory=False, require_file=False):
    element_type = "file or directory"
    if require_directory and require_file:
        raise ValueError("Cannot require both files and directories")
    if require_directory:
        element_type = "directory"
    if require_file:
        element_type = "file"

    def resolve_paths(value):
        _paths = list_of_paths(value)
        for p in _paths:
            p1 = p.expanduser()
            if not p1.is_absolute():
                # Resolve relative to config file
                if settings.config_file is not None:
                    p1 = settings.config_file.parent / p1
            if not p1.exists():
                raise ValueError(f"{p1} is not a valid {element_type}")
            if require_directory and not p1.is_dir():
                raise ValueError(f"{p1} is not a {element_type}")
            if require_file and not p1.is_file():
                raise ValueError(f"{p1} is not a {element_type}")
            yield p1.resolve()

    return lambda x: list(resolve_paths(x))


def get_app_state_file() -> Path:
    APP_NAME = "macrostrat"
    app_dir = Path(get_app_dir(APP_NAME))
    return app_dir / "app-state.toml"


def get_app_state(key: str = None) -> str:
    state_file = get_app_state_file()
    if not state_file.exists():
        return None
    with state_file.open() as f:
        state = toml.load(f)
    if key is None:
        return state
    return state.get(key, None)


def set_app_state(key: str, value: str, wipe_others: bool = False):
    state_file = get_app_state_file()
    state_file.parent.mkdir(exist_ok=True)
    state = get_app_state()
    if state is None or wipe_others:
        state = {}
    state[key] = value
    with state_file.open("w") as f:
        toml.dump(state, f)
