import json
from os import environ
from pathlib import Path
from sys import exit, stderr
from typing import Optional

import typer
from macrostrat.utils.shell import run
from rich import print
from toml import load as load_toml
from typer import Argument, Option, Typer

from macrostrat.core import app
from macrostrat.core.main import env_text, get_app_env_file

from .database import db_app, db_subsystem, get_db
from .kubernetes import get_secret
from .v1_entrypoint import v1_cli
from .v2_commands import app as v2_app

__here__ = Path(__file__).parent
fixtures_dir = __here__ / "fixtures"


app.subsystems.add(db_subsystem)

# Manage as a docker-compose application

settings = app.settings

main = app.control_command()
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
    active_env = get_app_env_file()
    if env is None:
        e = app.settings.env
        if e is None:
            print("No environment set", file=stderr)
            exit(1)
        print(e)
        return
    if unset:
        active_env.unlink()
        return
    environ["MACROSTRAT_ENV"] = env
    active_env.parent.mkdir(exist_ok=True)
    active_env.write_text(env)
    print(f"Activated {env_text()}")


def local_install(path: Path):
    run(
        "poetry",
        "install",
        cwd=path.expanduser().resolve(),
        env={**environ, "POETRY_VIRTUALENVS_CREATE": "False"},
    )


@main.command()
def install():
    """Install Macrostrat subsystems into the Python root.

    This is currently hard-coded for development purposes, but
    this will be changed in the future.
    """
    local_install(Path(settings.srcroot) / "py-root")


cfg_app = Typer(name="config", short_help="Manage configuration")


@cfg_app.command(name="edit")
def edit_cfg():
    """Open config file in editor"""
    from subprocess import run

    from macrostrat.core.config import macrostrat_config_file

    run(["open", str(macrostrat_config_file)])


@cfg_app.command(name="environments")
def edit_cfg():
    """Open config file in editor"""
    from subprocess import run

    from macrostrat.core.config import macrostrat_config_file

    # Parse out top-level headers from TOML file
    with open(macrostrat_config_file, "r") as f:
        cfg = load_toml(f)
        keys = iter(cfg.keys())
        print("Available environments:")
        next(keys)
        for k in keys:
            print("- [bold cyan]" + k)


main.add_typer(cfg_app)


main.add_typer(v2_app, name="v2")


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
    from macrostrat.map_integration import app as map_app

    @map_app.command(name="write-geopackage")
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

    def update_weaver():
        print("Creating models for [bold cyan]weaver[/] subsystem")
        create_models()

    db_subsystem._queued_updates.append(update_weaver)

except ImportError as err:
    pass

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

    def update_tileserver():
        print("Creating models for [bold cyan]tileserver[/] subsystem")
        create_fixtures()

    db_subsystem._queued_updates.append(update_tileserver)

except ImportError as err:
    print("Could not import tileserver subsystem")

try:
    environ["CORELLE_DB"] = app.settings.pg_database
    from corelle.engine import cli as corelle_cli
    from corelle.engine.database import initialize

    corelle_cli.name = "corelle"
    corelle_cli.help = "Manage plate rotation models"

    main.add_click_command(
        corelle_cli,
        "corelle",
        rich_help_panel="Subsystems",
    )

    def update_corelle():
        print("Creating models for [bold cyan]corelle[/] subsystem")
        initialize(drop=False)

    db_subsystem._queued_updates.append(update_corelle)

except ImportError as err:
    pass


app.finish_loading_subsystems()


@main.command(name="carto-plate-index")
def build_carto_plate_index():
    """Build a representation of the Carto map layers, split by plate polygons"""
    from .corelle import build_carto_plate_index

    db = get_db()
    build_carto_plate_index(db)


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


main.add_click_command(v1_cli, name="v1")
