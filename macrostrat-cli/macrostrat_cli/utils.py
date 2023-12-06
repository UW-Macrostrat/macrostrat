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
    macrostrat_root = None
    # Find root dir upwards
    macrostrat_root = find_config(Path.cwd())
    if macrostrat_root is None:
        # Find user-specific config in home dir
        macrostrat_root = find_config(Path.home() / ".config" / "macrostrat")

    # Find config upwards from utils installation
    if macrostrat_root is None:
        macrostrat_root = find_config(Path(__file__).parent)

    if macrostrat_root is None:
        raise RuntimeError("Could not find macrostrat.toml")

    return macrostrat_root / "macrostrat.toml"


def is_pg_url(url):
    return (url.startswith("postgres") or url.startswith("postgresql")) and "://" in url
