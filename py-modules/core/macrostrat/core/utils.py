from os import environ
from pathlib import Path


# Load config before we do anything else
def find_config(start_dir: Path):
    """Find the macrostrat.toml config file"""

    next_dir = start_dir.resolve()
    while next_dir != next_dir.parent:
        if (next_dir / "macrostrat.toml").exists():
            return next_dir
        next_dir = next_dir.parent
    return None


def find_macrostrat_config() -> Path:
    """Find the macrostrat.toml config file"""
    # If the MACROSTRAT_CONFIG env var is set, use that
    if "MACROSTRAT_CONFIG" in environ:
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
