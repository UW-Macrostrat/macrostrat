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


    # if args[0] == "maps":
    #     # Check if the macrostrat-maps command is available on the system
    #     try:
    #         run(["macrostrat-maps"] + sys.argv[2:], check=True)
    #     except FileNotFoundError:
    #         print("Error: map ingestion CLI is not installed")
    #     sys.exit()

main.add_click_command(v1_cli, name="v1")