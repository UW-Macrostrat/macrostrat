import sys
from importlib import util
from pathlib import Path

from macrostrat.core.config import settings

migrations_dir = settings.srcroot / "schema" / "_migrations"


def load_migrations():
    for module in migrations_dir.iterdir():
        if module.is_file() and module.suffix == ".py" and module.stem != "__init__":
            _import_file(module)
        elif module.is_dir() and (module / "__init__.py").exists():
            _import_file(module)


def _import_file(module_path: Path):
    MODULE_NAME = module_path.stem
    if module_path.is_dir() and (module_path / "__init__.py").exists():
        module_path = module_path / "__init__.py"
    MODULE_PATH = str(module_path)

    spec = util.spec_from_file_location(MODULE_NAME, MODULE_PATH)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load module from {MODULE_PATH}")
    module = util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
