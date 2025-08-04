from importlib import import_module
from pathlib import Path

__dir__ = Path(__file__).parent

# Import all submodules within this directory using importlib


def load_migrations():
    for module in __dir__.iterdir():
        if module.is_file() and module.suffix == ".py" and module.stem != "__init__":
            import_module(f".{module.stem}", package=__name__)
        elif module.is_dir() and (module / "__init__.py").exists():
            import_module(f".{module.stem}", package=__name__)
