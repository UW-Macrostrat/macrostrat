from os import environ
from pathlib import Path

import typer
from rich import print
from rich.traceback import install
from typer import Argument, Option, Typer

from macrostrat.app_frame import CommandBase, SubsystemManager
from macrostrat.core import app
from macrostrat.core.environment import declared_policy_for
from macrostrat.core.exc import MacrostratError
from macrostrat.core.secrets import redact_mapping, refuse_non_interactive_reveal
from macrostrat.core.utils import (
    NON_LOCAL_TTL,
    active_env_remaining,
    env_text,
    set_active_env,
)
from macrostrat.schema_management import schema_app
from macrostrat.usage_stats import app as usage_stats_app
from macrostrat.utils import get_logger
from macrostrat.utils.shell import run

from .database import db_app, db_subsystem
from .subsystems.dev import dev_app
from .subsystems.paleogeography import (
    SubsystemLoadError,
    build_paleogeography_subsystem,
)
from .subsystems.rebuild import cli as rebuild_cli
from .subsystems.rockd import cli as rockd_cli
from .utils import run_user_command_if_provided
from .v1_entrypoint import v1_cli

__here__ = Path(__file__).parent
fixtures_dir = __here__ / "fixtures"

log = get_logger(__name__)

app.warnings = []
app.info_messages = []

install(show_locals=False)


# Manage as a docker-compose application


def initialize(app):
    pass


app.subsystems = SubsystemManager()


settings = app.settings
rockd_url = settings.get("ROCKD_DATABASE") or settings.get("rockd_database")
if rockd_url and "ROCKD_DATABASE" not in environ:
    environ["ROCKD_DATABASE"] = rockd_url

# Patch to ensure weird out-of-order loading still works.
db_subsystem.app = app
app.subsystems.add(db_subsystem)
# app.subsystems.add(rockd_subsystem)

_env_text = app.settings.env
if _env_text is None:
    _env_text = "None"

help_text = f"""[bold]Macrostrat[/] control interface

"""

app.info_messages.append(f"Active environment: [bold cyan]{_env_text}[/]")

if not settings.pg_database:
    app.warnings.append("No database URL found in settings")
reinstall_warning = environ.get("MACROSTRAT_SHOULD_REINSTALL")
if reinstall_warning is not None:
    if len(reinstall_warning) < 2:
        reinstall_warning = "Macrostrat needs to be reinstalled."
    app.warnings.append(
        f"{reinstall_warning} Please run [bold cyan]macrostrat install[/]."
    )
if environ.get("MACROSTRAT_PYROOT") is not None:
    app.warnings.append(
        "Using a custom [bold cyan]MACROSTRAT_PYROOT[/]\n  [dim]This is not recommended for normal operation."
    )

# TODO: load all subsystems before rendering help so that warnings can be shown

subsystem_commands = []
try:
    pcli = build_paleogeography_subsystem(app, db_subsystem)
    subsystem_commands.append(pcli)
except SubsystemLoadError as err:
    app.warnings.append(str(err))

# If the user has macrostrat-<command> on their path, we want to run it as a subprocess
# and return the output, instead of continuing with the CLI.
# TODO: integrate this more with the typer app so that user commands cannot override
# existing commands.
run_user_command_if_provided(*settings.script_dirs)

if app.info_messages:
    help_text += "\n".join([f"- {w}" for w in app.info_messages]) + "\n"

# Now, we render the warnings in the CLI help text
if app.warnings:
    help_text += "\n".join([f"- [yellow]{w}[/]" for w in app.warnings]) + "\n"

main = app.control_command(
    add_completion=True,
    rich_markup_mode="rich",
    help=help_text,
    backend=app.settings.backend,
)

main.add_typer(
    schema_app,
    name="schema",
    short_help="Schema management and migrations",
)

main.add_typer(
    db_app,
    name="database",
    short_help="Database utilities",
    aliases=["db"],
)

main.add_typer(
    rockd_cli,
    name="rockd-db",  # command group name
    short_help="Rockd database",  # shows in --help
    rich_help_panel="Subsystems",
)

main.add_typer(
    rebuild_cli,
    name="rebuild",  # command group name
    short_help="Rebuild scripts",  # shows in --help
    rich_help_panel="Subsystems",
)

main.add_typer(
    usage_stats_app,
    name="usage-stats",
    short_help="Usage stats",
    rich_help_panel="Subsystems",
)


for sub in subsystem_commands:
    main.add_typer(sub, rich_help_panel="Subsystems")


@main.command(name="env")
def set_env(
    env: str = Argument(None),
    unset: bool = False,
    shell: bool = Option(
        False,
        "--shell",
        help="Print an export line instead of remembering the environment. "
        'Use as: eval "$(macrostrat env --shell staging)"',
    ),
):
    """Set the active environment

    A `local`-class environment is remembered indefinitely. Anything else is
    remembered for 15 minutes, because a persisted pointer at a remote database
    that outlives the task is the sticky-global-state problem this guards
    against: a different terminal, a subagent's shell or a cron job days later
    would otherwise silently target it.

    For a longer session that ends when the terminal does, use `--shell`.
    """
    try:
        current_env = app.settings.env
    except AttributeError:
        current_env = None

    if env is None:
        if current_env is None:
            raise MacrostratError("No environment set")
        remaining = active_env_remaining()
        if remaining is None:
            print(current_env)
        else:
            minutes = max(0, int(remaining.total_seconds() // 60))
            print(f"{current_env} [dim](lapses in {minutes} min)[/dim]")
        return

    if unset:
        set_active_env(None)
        return

    environments = app.settings.all_environments()
    if env not in environments:
        raise MacrostratError(
            f"Environment [item]{env}[/item] is not valid",
            details=_available_environments(environments),
        )

    policy = declared_policy_for(app.settings.config_file, env)

    if shell:
        # Nothing is persisted: the environment lives in the shell that
        # evaluates this and dies with it.
        print(f"export MACROSTRAT_ENV={env}")
        return

    expires_in = None if policy.is_local else NON_LOCAL_TTL
    expires = set_active_env(env, expires_in=expires_in)
    environ["MACROSTRAT_ENV"] = env

    if expires is None:
        print(f"Activated {env_text()}")
    else:
        minutes = int(NON_LOCAL_TTL.total_seconds() // 60)
        print(
            f"Activated {env_text()} [bold yellow]({policy.env_class.value})[/] "
            f"[dim]for {minutes} min, until {expires:%H:%M}[/dim]"
        )
        print(
            "[dim]Use --env for a single command, or "
            f'eval "$(macrostrat env --shell {env})" for a shell session.[/dim]'
        )


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

from macrostrat.map_topology import cli as topo_cli

main.add_typer(
    topo_cli,
    name="topo",
    rich_help_panel="Subsystems",
    short_help="Manage the Macrostrat maps topology",
)

from .cache import cli as cache_cli

main.add_typer(cache_cli, name="cache", rich_help_panel="Subsystems")

from .auth import cli as auth_cli

main.add_typer(auth_cli, name="auth", rich_help_panel="Subsystems")


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

    from .commands.export import export_map

    map_app.command("export", short_help="Export map data")(export_map)

    main.add_typer(
        map_app,
        name="maps",
        rich_help_panel="Subsystems",
        short_help="Map integration system",
    )

except ImportError as err:
    app.console.print("Could not import map integration subsystem", err)

try:
    from .rasters import build_raster_cli

    main.add_typer(
        build_raster_cli(),
        name="raster",
        rich_help_panel="Subsystems",
        short_help="Raster data integration",
    )
except ImportError as err:
    # The raster libraries live in the Python-libraries monorepo and are not yet
    # released; the subsystem is optional until they are.
    log.debug("Raster subsystem unavailable: %s", err)

# Add weaver subsystem if available
try:
    from digitalcrust.weaver.cli import app as weaver_app
    from digitalcrust.weaver.cli import create_models

    main.add_typer(
        weaver_app,
        name="weaver",
        rich_help_panel="Integrations",
        short_help="Prototype geochemical data management system",
    )

    def update_weaver(db):
        app.console.print("Creating models for [bold cyan]weaver[/] subsystem")
        create_models()

    db_subsystem.register_schema_part(name="weaver", callback=update_weaver)

except ImportError as err:
    pass

try:
    from macrostrat.column_ingestion import app as column_app

    main.add_typer(
        column_app,
        name="columns",
        rich_help_panel="Subsystems",
        short_help="Column data ingestion subsystem",
    )
except ImportError as err:
    pass


# Get subsystems config
subsystems = getattr(settings, "subsystems", {})

# CRITICALMAAS subsystem depends on outdated python package. We could update this to re-enable
# if subsystems.get("criticalmaas", False):
#     # TODO: add a hint somewhere for which subsystems are disabled
#     # - This could also provide ways to dynamically load them and report
#     #   errors etc.
#     from .subsystems.criticalmaas import app as criticalmaas_app
#
#     main.add_typer(
#         criticalmaas_app,
#         name="criticalmaas",
#         rich_help_panel="Integrations",
#         short_help="Tools for the CriticalMAAS program",
#         deprecated=True,
#     )


if kube_namespace := getattr(settings, "kube_namespace", None):
    from .kubernetes import app as kube_app

    main.add_typer(
        kube_app,
        name="kube",
        short_help="Kubernetes utilities",
        rich_help_panel="Subsystems",
        deprecated=True,
    )

from .subsystems.storage import app as storage_app

main.add_typer(
    storage_app,
    name="storage",
    short_help="Manage storage buckets",
    rich_help_panel="Subsystems",
)


from macrostrat.integrations import app as integrations_app

main.add_typer(
    integrations_app,
    name="integrations",
    short_help="Integrations with other data systems",
    rich_help_panel="Integrations",
)


if sgp_url := getattr(settings, "sgp_database", None):
    from macrostrat.integrations.sgp import sgp

    main.add_typer(sgp, rich_help_panel="Integrations")

# Knowledge graph CLI
from .subsystems.xdd import cli as kg_cli

main.add_typer(
    kg_cli,
    name="xdd",
    rich_help_panel="Integrations",
    short_help="Manage xDD integration",
)

## Testing subsystem
from .test_runner import cli as test_app

main.add_typer(test_app, name="test", rich_help_panel="Subsystems")

# TODO: disable dev app in some cases
main.add_typer(dev_app, name="dev", rich_help_panel="Subsystems")


app.subsystems.finalize(app)


# Commands to manage this command-line interface
self_app = CommandBase()


@self_app.command()
def inspect():
    """Run a IPython shell in the application context"""

    import IPython

    IPython.embed()


# Print the environment variables
@self_app.command()
def printenv(
    reveal: bool = Option(
        False, "--reveal", help="Show credential values in plain text"
    ),
):
    """Print the environment variables

    Values whose name looks like a credential — and any value containing a
    secret resolved in this process — are redacted unless --reveal is passed.
    This command used to print PGPASSWORD and SECRET_KEY verbatim.
    """
    if reveal:
        refuse_non_interactive_reveal("environment variables")

    items = environ.items() if reveal else redact_mapping(environ).items()
    for k, v in items:
        print(f"[bold cyan]{k}[/]: {v}")


main.add_typer(
    self_app,
    name="self",
    short_help="Manage the Macrostrat CLI itself",
    rich_help_panel="Meta",
)

app.subsystems.run_hook("add-commands", main)


@main.command(rich_help_panel="Meta")
def uv():
    """[cyan]uv[/] CLI wrapper"""
    raise RuntimeError(
        "This is a placeholder for a command implemented in a wrapping script."
    )


@main.command(rich_help_panel="Meta")
def install():
    """Install Macrostrat dependencies"""
    raise RuntimeError("This command is currently implemented in a wrapping script")


# Add the v1 CLI
main.add_click_command(v1_cli, name="v1", deprecated=True, rich_help_panel="Legacy")


# main.add_click_command(v1_cli, name="v1")


@self_app.command(name="settings-dir")
def show_app_dir():
    """Show the configuration directory"""
    app.console.print(app.app_dir)


@self_app.command()
def state(clear: bool = False):
    if clear:
        app.state.clear()

    """Show the current state of the application"""
    app.console.print(app.state.get())


# TODO: subsystem dependencies
from .subsystems.core import core_schema

# Add basic schema hunks
from .subsystems.xdd import text_vector_schema

# TODO: move these into the migrations system
db_subsystem.schema_hunks.append(core_schema)
db_subsystem.schema_hunks.append(text_vector_schema)

# Discover subsystems in third-party packages
# https://packaging.python.org/en/latest/guides/creating-and-discovering-plugins/

from importlib.metadata import entry_points

discovered_plugins = entry_points(group="macrostrat.subsystems")
for entry_point in discovered_plugins:
    plugin = entry_point.load()
    if isinstance(plugin, typer.Typer):
        main.add_typer(plugin, name=entry_point.name, rich_help_panel="Extensions")

# main = setup_exception_handling(main)
