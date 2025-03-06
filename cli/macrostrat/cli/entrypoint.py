from os import environ
from pathlib import Path

import typer
from macrostrat.app_frame import CommandBase
from macrostrat.utils.shell import run
from rich import print
from rich.traceback import install
from typer import Argument, Typer

from macrostrat.core import app
from macrostrat.core.exc import MacrostratError
from macrostrat.core.main import env_text, set_app_state
from .database import db_app, db_subsystem
from .subsystems.macrostrat_api import MacrostratAPISubsystem
from .subsystems.paleogeography import build_paleogeography_subsystem, SubsystemLoadError
from .v1_entrypoint import v1_cli
from .v2_commands import app as v2_app

__here__ = Path(__file__).parent
fixtures_dir = __here__ / "fixtures"

install(show_locals=False)


app.subsystems.add(db_subsystem)

# Manage as a docker-compose application

settings = app.settings

help_text = f"""[bold]Macrostrat[/] control interface


Active environment: [bold cyan]{environ.get('MACROSTRAT_ENV') or 'None'}[/]
"""


warnings = []
if not settings.pg_database:
    warnings.append("No database URL found in settings")
reinstall_warning = environ.get("MACROSTRAT_SHOULD_REINSTALL")
if reinstall_warning is not None:
    if len(reinstall_warning) < 2:
        reinstall_warning = "Macrostrat needs to be reinstalled."
    warnings.append(f"{reinstall_warning} Please run [bold cyan]macrostrat install[/].")
if environ.get("MACROSTRAT_PYROOT") is not None:
    warnings.append(
        "Using a custom [bold cyan]MACROSTRAT_PYROOT[/]. This is not recommended for normal operation."
    )

# TODO: load all subsystems before rendering help so that warnings can be shown

subsystem_commands = []
try:
    pcli = build_paleogeography_subsystem(app, db_subsystem)
    subsystem_commands.append(pcli)
except SubsystemLoadError as err:
    warnings.append(str(err))


# Now, we render the warnings in the CLI help text
if warnings:
    help_text += "\n[bold yellow]Warnings[/]:\n"
    help_text += "\n".join([f"- [yellow]{w}[/]" for w in warnings]) + "\n"

main = app.control_command(
    add_completion=True,
    rich_markup_mode="rich",
    help=help_text,
    backend=app.settings.backend,
)

main.add_typer(
    db_app,
    name="database",
    short_help="Manage the Macrostrat database",
    aliases=["db"],
)

for sub in subsystem_commands:
    main.add_typer(sub, name=sub.name, rich_help_panel="Subsystems")


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


cfg_app = Typer(name="config", short_help="Manage configuration")


@cfg_app.command(name="show")
def show_cfg():
    """Show the current configuration"""
    from macrostrat.core.config import settings

    print(str(settings.config_file))


@cfg_app.command(name="edit")
def edit_cfg():
    """Open config file in editor"""
    from subprocess import run

    from macrostrat.core.config import settings

    editor = environ.get("EDITOR", "open")
    run([editor, str(settings.config_file)])


@cfg_app.command(name="environments")
def environments():
    """Get all available environments."""
    envs = app.settings.all_environments()
    app.console.print(_available_environments(envs))


main.add_typer(cfg_app)

from .cache import cli as cache_cli

main.add_typer(cache_cli, name="cache", rich_help_panel="Subsystems")


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

    main.add_typer(
        map_app,
        name="maps",
        rich_help_panel="Subsystems",
        short_help="Map integration system (partial overlap with v1 commands)",
    )
except ImportError as err:
    app.console.print("Could not import map integration subsystem", err)

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
        app.console.print("Creating models for [bold cyan]weaver[/] subsystem")
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
        app.console.print("Creating models for [bold cyan]tileserver[/] subsystem")
        create_fixtures()

    db_subsystem.register_schema_part(name="tileserver", callback=update_tileserver)

except ImportError as err:
    pass
    # app.console.print("Could not import tileserver subsystem")

# Get subsystems config
subsystems = getattr(settings, "subsystems", {})
if subsystems.get("criticalmaas", False):
    # TODO: add a hint somewhere for which subsystems are disabled
    # - This could also provide ways to dynamically load them and report
    #   errors etc.
    from .subsystems.criticalmaas import app as criticalmaas_app

    main.add_typer(
        criticalmaas_app,
        name="criticalmaas",
        rich_help_panel="Integrations",
        short_help="Tools for the CriticalMAAS program",
        deprecated=True,
    )


if kube_namespace := getattr(settings, "kube_namespace", None):
    from .kubernetes import app as kube_app

    main.add_typer(
        kube_app,
        name="kube",
        short_help="Kubernetes utilities",
        rich_help_panel="Subsystems",
    )


from .subsystems.storage import app as storage_app

main.add_typer(
    storage_app,
    name="storage",
    short_help="Manage storage buckets",
    rich_help_panel="Subsystems",
)


from .subsystems.mapboard import MapboardSubsystem

if subsystems.get("mapboard", False):
    if mapboard_url := getattr(settings, "mapboard_database", None):
        app.subsystems.add(MapboardSubsystem(app))
    else:
        app.console.print(
            "Mapboard subsystem enabled, but no mapboard_database setting found"
        )

from macrostrat.integrations import app as integrations_app

main.add_typer(
    integrations_app,
    name="integrations",
    short_help="Integrations with other data systems",
    rich_help_panel="Subsystems",
)


app.subsystems.add(MacrostratAPISubsystem(app))

if sgp_url := getattr(settings, "sgp_database", None):
    from .subsystems.sgp import sgp

    main.add_typer(sgp, rich_help_panel="Integrations")

# Mariadb CLI
if mariadb_url := getattr(settings, "mysql_database", None):
    from .database.mariadb import app as mariadb_app

    main.add_typer(
        mariadb_app,
        name="mariadb",
        rich_help_panel="Subsystems",
        short_help="Manage the MariaDB database",
    )

# Knowledge graph CLI
from .subsystems.xdd import cli as kg_cli

main.add_typer(
    kg_cli,
    name="xdd",
    rich_help_panel="Integrations",
    short_help="Manage xDD integration",
)

## Testing subsystem
from .subsystems.test import cli as test_app

main.add_typer(test_app, name="test", rich_help_panel="Subsystems")


app.finish_loading_subsystems()


# Commands to manage this command-line interface
self_app = CommandBase()


@self_app.command()
def inspect():
    """Run a IPython shell in the application context"""

    import IPython

    IPython.embed()


main.add_typer(
    self_app,
    name="self",
    short_help="Manage the Macrostrat CLI itself",
    rich_help_panel="Meta",
)

app.subsystems.run_hook("add-commands", main)


@main.command(rich_help_panel="Meta")
def poetry():
    """[cyan]poetry[/] CLI wrapper"""
    raise RuntimeError("This command is currently implemented in a wrapping script")


@main.command(rich_help_panel="Meta")
def install():
    """Install Macrostrat dependencies"""
    raise RuntimeError("This command is currently implemented in a wrapping script")


# Add the v1 CLI
main.add_click_command(v1_cli, name="v1", deprecated=True, rich_help_panel="Legacy")
main.add_typer(v2_app, name="v2", deprecated=True, rich_help_panel="Legacy")


# main.add_click_command(v1_cli, name="v1")


@self_app.command(name="settings-dir")
def show_app_dir():
    """Show the configuration directory"""
    app.console.print(app.app_dir)


@self_app.command()
def state():
    """Show the current state of the application"""
    app.console.print(app.state.get())


# TODO: subsystem dependencies
from .subsystems.core import core_schema
from .subsystems.legend_api import legend_api
from .subsystems.macrostrat_api import macrostrat_api

# Add basic schema hunks
from .subsystems.xdd import text_vector_schema, xdd_schema

# TODO: move these into the migrations system
db_subsystem.schema_hunks.append(core_schema)
db_subsystem.schema_hunks.append(xdd_schema)
db_subsystem.schema_hunks.append(text_vector_schema)
db_subsystem.schema_hunks.append(legend_api)
db_subsystem.schema_hunks.append(macrostrat_api)

# Discover subsystems in third-party packages
# https://packaging.python.org/en/latest/guides/creating-and-discovering-plugins/

from importlib.metadata import entry_points

discovered_plugins = entry_points(group="macrostrat.subsystems")
for entry_point in discovered_plugins:
    plugin = entry_point.load()
    if isinstance(plugin, typer.Typer):
        main.add_typer(plugin, name=entry_point.name, rich_help_panel="Subsystems")

# main = setup_exception_handling(main)
