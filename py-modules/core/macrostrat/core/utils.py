from datetime import timedelta
from os import environ
from pathlib import Path
from typing import Optional

import toml
from click import get_app_dir

from macrostrat.app_frame.environments import (  # noqa: F401
    ActiveEnvironment,
    EnvironmentState,
    environments_in,
    extract_env_from_argv,
)
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


#: Variables carrying a per-process or per-shell environment.
ENV_VAR = "MACROSTRAT_ENV"
ENV_EXPIRES_VAR = "MACROSTRAT_ENV_EXPIRES"


class _AppState(EnvironmentState):
    """The remembered environment, kept in `app-state.toml` as it always was.

    Remembering an environment rewrites the file, which drops the rest of the
    app state (the active map) along with the environment it belonged to.
    """

    def read_state(self) -> dict:
        return get_app_state() or {}

    def write_state(self, state: dict):
        state_file = get_app_state_file()
        state_file.parent.mkdir(exist_ok=True)
        with state_file.open("w") as f:
            toml.dump(state, f)


#: Which environment this invocation uses, and the remembered pointer. The
#: mechanism is `macrostrat.app_frame.environments`; these names are Macrostrat's.
environment_state = _AppState(
    "macrostrat", env_var=ENV_VAR, expires_var=ENV_EXPIRES_VAR
)


def active_environment() -> Optional[ActiveEnvironment]:
    """The environment this invocation resolved, or None if there is none."""
    return environment_state.active


def remembered_environment() -> Optional[ActiveEnvironment]:
    """The pointer as written, whether or not it applies here."""
    return environment_state.remembered()


def set_active_env(
    env: Optional[str],
    *,
    expires_in: Optional[timedelta] = None,
    config_file: Optional[Path] = None,
):
    """Remember *env* for *config_file*; None forgets it."""
    return environment_state.remember(
        env, expires_in=expires_in, config_file=config_file
    )


def renew_active_env(expires_in: Optional[timedelta]):
    """Re-stamp the remembered environment's expiry from now."""
    return environment_state.renew(expires_in)


def normalize_macrostrat_env(config_file: Optional[Path] = None) -> Optional[str]:
    """The active environment for this invocation, or None. Writes no state."""
    if config_file is None:
        config_file = find_macrostrat_config()
    env = environment_state.resolve(config_file)
    if env is not None:
        # Dynaconf's environment switcher reads the variable.
        environ[ENV_VAR] = env
        log.info("active environment: %s", env_text())
    return env


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
