from importlib import import_module
from pathlib import Path

from macrostrat.core.migrations import Migration

__dir__ = Path(__file__).parent

# Import all submodules within this directory using importlib


def _all_subclasses(cls):
    seen = set()
    stack = [cls]
    while stack:
        c = stack.pop()
        for sc in c.__subclasses__():
            if sc not in seen:
                seen.add(sc)
                yield sc
                stack.append(sc)


def load_migrations():
    for module in __dir__.iterdir():
        if module.is_file() and module.suffix == ".py" and module.stem != "__init__":
            import_module(f".{module.stem}", package=__name__)
        elif module.is_dir() and (module / "__init__.py").exists():
            import_module(f".{module.stem}", package=__name__)
