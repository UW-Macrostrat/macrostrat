from macrostrat.app_frame import Application
from pathlib import Path
from .v1_entrypoint import v1_cli
from .v2_commands import app as v2_app
from dynaconf import Dynaconf

root_dir = None
# Find root dir upwards
next_dir = Path.cwd().resolve()
while next_dir != next_dir.parent:
    if (next_dir/"macrostrat.toml").exists():
        root_dir = next_dir
        break
    next_dir = next_dir.parent
if root_dir is None:
    raise RuntimeError("Could not find macrostrat.toml")

settings = Dynaconf(settings_files=[root_dir/"macrostrat.toml", root_dir/".secrets.toml"])

app = Application("Macrostrat", root_dir=root_dir, load_dotenv=False, app_module="macrostrat")

main = app.control_command()

main.add_typer(v2_app, name="v2")

# Add subsystems if they are available.
# This organization is a bit awkward, and we may change it eventually.
try:
    from macrostrat.map_integration import app as map_app
    main.add_typer(map_app, name="maps", rich_help_panel="Subsystems", short_help="Map integration system (partial overlap with v1 commands)")
except ImportError as err:
    pass

try:
    from digitalcrust.weaver.cli import app as weaver_app
    main.add_typer(weaver_app, name="weaver", rich_help_panel="Subsystems", short_help="Prototype geochemical data management system")
except ImportError as err:
    pass

main.add_click_command(v1_cli, name="v1")