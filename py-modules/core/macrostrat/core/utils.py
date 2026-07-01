from os import environ, unsetenv
from pathlib import Path
from typing import Optional
from os import environ

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


def normalize_macrostrat_env():
    if "MACROSTRAT_ENV" in environ:
        log.info("active environment: %s", env_text())
        # Check environment value
        env = environ["MACROSTRAT_ENV"]
        if env in ("", "none", "None"):
            unsetenv("MACROSTRAT_ENV")
            return None
        return env
    active_env = get_app_state_file()
    # TODO: unset env here if the config file does not contain the correct env
    if "MACROSTRAT_ENV" not in environ and active_env.exists():
        env = get_app_state("active_env")
        if env is not None:
            environ["MACROSTRAT_ENV"] = env
        log.info("active environment: %s", env_text())
        return env
    return None


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
