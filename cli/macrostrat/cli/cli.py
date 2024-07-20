import json
from asyncio import run as asyncio_run
from os import environ
from pathlib import Path
from typing import Optional

import typer
from macrostrat.utils.shell import run
from rich import print
from rich.traceback import install
from typer import Argument, Option, Typer

from macrostrat.core import app
from macrostrat.core.exc import MacrostratError, setup_exception_handling
from macrostrat.core.main import env_text, set_app_state

from .database import db_app, db_subsystem, get_db
from .kubernetes import get_secret
from .v1_entrypoint import v1_cli
from .v2_commands import app as v2_app
from .subsystems.paleogeography import load_paleogeography_subsystem

__here__ = Path(__file__).parent
fixtures_dir = __here__ / "fixtures"

install(show_locals=False)


app.subsystems.add(db_subsystem)

# Manage as a docker-compose application

settings = app.settings

help_text = f"""[bold]Macrostrat[/] control interface

Active environment: [bold cyan]{environ.get('MACROSTRAT_ENV') or 'None'}[/]
"""

main = app.control_command(add_completion=True, rich_markup_mode="rich", help=help_text)


main.add_typer(db_app, name="db", short_help="Manage the Macrostrat database")


@main.command()
def secrets(secret_name: Optional[str] = Argument(None), *, key: str = Option(None)):
    """Get a secret from the Kubernetes cluster"""

    print(json.dumps(get_secret(settings, secret_name, secret_key=key), indent=4))


@main.command()
def shell():
    """Start an IPython shell"""
    import IPython

    IPython.embed()


@main.command(name="env")
def set_env(env: str = Argument(None), unset: bool = False):
    """Set the active environment"""
    try:
        current_env = app.settings.env
    except AttributeError:
        current_env = None
    if env is None:
        if current_env is None:
            raise MacrostratError("No environment set")
        print(current_env)
        return
    if unset:
        set_app_state("active_env", None, wipe_others=True)
        return
    environments = app.settings.all_environments()
    if env not in environments:
        raise MacrostratError(
            f"Environment [item]{env}[/item] is not valid",
            details=_available_environments(environments),
        )
    should_wipe = current_env != env
    set_app_state("active_env", env, wipe_others=should_wipe)
    environ["MACROSTRAT_ENV"] = env
    print(f"Activated {env_text()}")


def _available_environments(environments):
    res = "Available environments:\n"
    for k in environments:
        res += f"- [item]{k}[/item]\n"
    return res


def local_install(path: Path, lock: bool = False):
    kwargs = dict(
        cwd=path.expanduser().resolve(),
        env={**environ, "POETRY_VIRTUALENVS_CREATE": "False"},
    )

    if lock:
        run("poetry", "lock", "--no-update", **kwargs)

    run("poetry", "install", **kwargs)


@main.command()
def install(lock: bool = False):
    """Install Macrostrat subsystems into the Python root.

    This is currently hard-coded for development purposes, but
    this will be changed in the future.
    """
    local_install(Path(settings.srcroot) / "py-root", lock=lock)


cfg_app = Typer(name="config", short_help="Manage configuration")


@cfg_app.command(name="edit")
def edit_cfg():
    """Open config file in editor"""
    from subprocess import run

    from macrostrat.core.config import macrostrat_config_file

    run(["open", str(macrostrat_config_file)])


@cfg_app.command(name="environments")
def environments():
    """Get all available environments."""
    envs = app.settings.all_environments()
    app_console.print(_available_environments(envs))


main.add_typer(cfg_app)


main.add_typer(v2_app, name="v2")

from .criticalmaas.importer import import_criticalmaas


@main.command(name="import-criticalmaas")
def _import_criticalmaas(file: Path):
    asyncio_run(import_criticalmaas(file))


@main.command(
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
    name="run",
)
def _run(
    ctx: typer.Context, command: str = Argument(help="Command to run", default=None)
):
    """Run a command in the Macrostrat command-line context"""

    bindir = Path(settings.srcroot) / "bin"

    if command is None:
        # List available commands
        print("Available commands:")
        for f in bindir.iterdir():
            if f.is_file() and f.name != "macrostrat":
                print(f.name)
        return

    cmd = bindir / command
    run(str(cmd), *ctx.args)


# Add subsystems if they are available.
# This organization is a bit awkward, and we may change it eventually.
try:
    from macrostrat.map_integration import cli as map_app

    @map_app.command(name="write-criticalmaas")
    def write_map_geopackage(
        map: str = Argument(...), filename: Path = None, overwrite: bool = False
    ):
        """Write a geopackage from a map"""
        from .io.criticalmaas import write_map_geopackage

        db = get_db()
        write_map_geopackage(db, map, filename, overwrite=overwrite)

    main.add_typer(
        map_app,
        name="maps",
        rich_help_panel="Subsystems",
        short_help="Map integration system (partial overlap with v1 commands)",
    )
except ImportError as err:
    print("Could not import map integration subsystem", err)

try:
    raster_app = typer.Typer()

    @main.command(
        name="raster",
        rich_help_panel="Subsystems",
        short_help="Raster data integration",
        context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
    )
    def rast(ctx: typer.Context):
        run(
            ["poetry", "run", "macrostrat-raster", *ctx.args],
            cwd="/data/macrostrat/tools/raster-cli",
        )

except ImportError as err:
    pass

# Add weaver subsystem if available
try:
    from digitalcrust.weaver.cli import app as weaver_app
    from digitalcrust.weaver.cli import create_models

    main.add_typer(
        weaver_app,
        name="weaver",
        rich_help_panel="Subsystems",
        short_help="Prototype geochemical data management system",
    )

    def update_weaver(db):
        print("Creating models for [bold cyan]weaver[/] subsystem")
        create_models()

    db_subsystem.register_schema_part(name="weaver", callback=update_weaver)

except ImportError as err:
    pass


# TODO: consider removing tileserver config - or adjusting, as fixtures
# are now run automatically on tileserver startup.
try:
    from macrostrat_tileserver.cli import _cli as tileserver_cli
    from macrostrat_tileserver.cli import create_fixtures

    environ["DATABASE_URL"] = app.settings.pg_database
    main.add_typer(
        tileserver_cli,
        name="tileserver",
        rich_help_panel="Subsystems",
        short_help="Control Macrostrat's tileserver",
    )

    def update_tileserver(db):
        print("Creating models for [bold cyan]tileserver[/] subsystem")
        create_fixtures()

    db_subsystem.register_schema_part(name="tileserver", callback=update_tileserver)

except ImportError as err:
    print("Could not import tileserver subsystem")

app = load_paleogeography_subsystem(app, main, db_subsystem)


# Add other subsystems (temporary)
from .subsystems.mapboard import MapboardSubsystem

if mapboard_url := getattr(settings, "mapboard_database", None):
    app.subsystems.add(MapboardSubsystem(app))

app.finish_loading_subsystems()


# Commands to manage this command-line interface
self_app = typer.Typer()


@self_app.command()
def inspect():
    import IPython

    IPython.embed()


main.add_typer(
    self_app,
    name="self",
    rich_help_panel="Subsystems",
    short_help="Manage the Macrostrat CLI itself",
)

app.subsystems.run_hook("add-commands", main)


main.add_click_command(v1_cli, name="v1")


@self_app.command(name="settings-dir")
def show_app_dir():
    """Show the configuration directory"""
    print(app.app_dir)


main = setup_exception_handling(main)


@self_app.command()
def state():
    """Show the current state of the application"""
    app.console.print(app.state.get())


# Add basic schema hunks
from .subsystems.knowledge_graph import kg_schema
from .subsystems.legend_api import legend_api
from .subsystems.macrostrat_api import macrostrat_api

db_subsystem.schema_hunks.append(kg_schema)
db_subsystem.schema_hunks.append(legend_api)
db_subsystem.schema_hunks.append(macrostrat_api)
