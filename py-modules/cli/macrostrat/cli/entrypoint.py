from datetime import datetime, timezone
from os import environ
from pathlib import Path

import typer
from rich import print
from rich.traceback import install
from typer import Argument, Option, Typer

from macrostrat.app_frame import CommandBase, SubsystemManager
from macrostrat.core import app
from macrostrat.core.environment import (
    WriteScope,
    declared_policy_for,
    format_duration,
)
from macrostrat.core.exc import MacrostratError
from macrostrat.core.secrets import redact_mapping, refuse_non_interactive_reveal
from macrostrat.core.utils import (
    ENV_EXPIRES_VAR,
    ENV_VAR,
    active_environment,
    env_text,
    remembered_environment,
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

# Asks the connection registry, which composes without fetching: a structured
# `[<env>.database]` table and a vaulted URL both count as configured.
if settings.database_connection() is None:
    app.warnings.append("No database configured for this environment")
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
    unset: bool = Option(False, "--unset", help="Forget the remembered environment"),
    shell: bool = Option(
        False,
        "--shell",
        help="Print export lines instead of remembering the environment. "
        'Use as: eval "$(macrostrat env --shell staging)"',
    ),
):
    """Set the active environment

    A `local`-class environment is remembered indefinitely. Anything else is
    remembered for its class's time-to-live (8 h development, 1 h staging,
    15 min production; `active_ttl` in the environment's section overrides it).
    A lapsed environment is kept, and you are asked before the next command
    that would use it — a persisted pointer at a remote database that outlives
    the task is the sticky-global-state problem this guards against.

    The pointer applies only to the config file it was set against, so a
    directory with a different `macrostrat.toml` is unaffected.

    For a session that ends when the terminal does, use `--shell`.
    """
    if unset:
        set_active_env(None)
        print("Forgot the remembered environment.")
        return

    if env is None:
        _report_active_environment()
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
        # evaluates this and dies with it. The expiry makes it lapse the same
        # way a remembered one does, so an exported variable is not a way
        # around the TTL.
        print(f"export {ENV_VAR}={env}")
        if policy.ttl is not None:
            expires = datetime.now(timezone.utc) + policy.ttl
            print(f"export {ENV_EXPIRES_VAR}={expires.isoformat()}")
        return

    expires = set_active_env(
        env, expires_in=policy.ttl, config_file=app.settings.config_file
    )
    environ[ENV_VAR] = env

    if expires is None:
        print(f"Activated {env_text()}")
    else:
        print(
            f"Activated {env_text()} [bold yellow]({policy.env_class.value})[/] "
            f"[dim]for {format_duration(policy.ttl)}, "
            f"until {expires.astimezone():%H:%M}[/dim]"
        )
        print(
            "[dim]Use --env for a single command, or "
            f'eval "$(macrostrat env --shell {env})" for a shell session.[/dim]'
        )


def _report_active_environment():
    """`macrostrat env` with no argument: what is active, from where, how fresh."""
    state = active_environment()
    if state is None:
        remembered = remembered_environment()
        if remembered is not None:
            where = remembered.config_file or "another config file"
            print(
                f"No environment applies here. The remembered environment "
                f"[bold cyan]{remembered.name}[/] was set for [dim]{where}[/dim]."
            )
            return
        print(
            "No environment set. Run [bold]macrostrat env <name>[/] to activate "
            "one; [bold]macrostrat config environments[/] lists them."
        )
        return

    policy = declared_policy_for(app.settings.config_file, state.name)
    line = f"[bold cyan]{state.name}[/] [bold yellow]({policy.env_class.value})[/]"
    if state.source == "explicit":
        line += " [dim](--env, this command only)[/dim]"
    elif state.expires is None:
        line += " [dim](does not lapse)[/dim]"
    elif state.lapsed:
        ago = format_duration(-state.remaining)
        line += (
            f" [yellow]lapsed {ago} ago[/yellow] [dim]— you will be asked before "
            "it is used; `macrostrat env "
            f"{state.name}` re-activates it[/dim]"
        )
    else:
        left = format_duration(state.remaining)
        via = "shell session" if state.source == "shell" else "remembered"
        line += f" [dim]({via}, lapses in {left})[/dim]"
    print(line)


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


@cfg_app.command(name="schema")
def config_schema():
    """Print the JSON Schema of a config environment (config_version = 2)

    The schema is the reference for every key the new loader reads. Point an
    editor at it for completion, or read it to see what a key means.
    """
    from json import dumps

    from macrostrat.core.config_model import config_json_schema

    typer.echo(dumps(config_json_schema(), indent=2))


@cfg_app.command(name="environments")
def environments():
    """List the environments in the config file, with class, confirmations and TTL.

    One look answers the questions that otherwise surface one refusal at a
    time: which environments are still *inferred* as production because they
    declare no `env_class`, what each kind of access will ask of you (`read`,
    `data`, `schema`), and how long `macrostrat env <name>` keeps each one
    active.
    """
    from rich.table import Table

    active = active_environment()
    table = Table(title=str(app.settings.config_file), title_justify="left")
    table.add_column("environment")
    table.add_column("class")
    table.add_column("read")
    table.add_column("data")
    table.add_column("schema")
    table.add_column("active for")
    for name in app.settings.all_environments():
        policy = declared_policy_for(app.settings.config_file, name)
        label = f"[bold cyan]{name}[/]"
        if active is not None and active.name == name:
            label += " [green]●[/]"
        klass = policy.env_class.value
        if policy.inferred and not policy.is_local:
            klass = f"[yellow]{klass}[/] [dim](inferred)[/dim]"
        table.add_row(
            label,
            klass,
            policy.gate_for(WriteScope.Read).value,
            policy.gate_for(WriteScope.Data).value,
            policy.gate_for(WriteScope.Schema).value,
            format_duration(policy.ttl),
        )
    app.console.print(table)
    inferred = [
        n
        for n in app.settings.all_environments()
        if (p := declared_policy_for(app.settings.config_file, n)).inferred
        and not p.is_local
    ]
    if inferred:
        app.console.print(
            '[dim]"inferred" means the section declares no env_class = "…", so it '
            "is gated as production. Declare one to say what it really is.[/dim]"
        )


main.add_typer(cfg_app)

from macrostrat.map_topology import cli as topo_cli

main.add_typer(
    topo_cli,
    name="topo",
    rich_help_panel="Maps",
    short_help="Manage the Macrostrat maps topology",
)

from macrostrat.map_topology.bounds import cli as bounds_cli

main.add_typer(
    bounds_cli,
    name="bounds",
    rich_help_panel="Maps",
    short_help="Compose and edit map boundaries",
)

from macrostrat.map_topology.compilations import cli as compilations_cli

main.add_typer(
    compilations_cli,
    name="compilations",
    rich_help_panel="Maps",
    short_help="Assemble maps out of other maps",
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
    ctx: typer.Context,
    command: str = Argument(help="Command to run", default=None),
):
    """Run a data pipeline, or a script from `bin/`, with the environment resolved.

    A **pipeline** is a directory holding a Typer app named `cli.py` or a Makefile,
    in a workbook such as `data-integration`. Name one by its directory, from
    anywhere inside the workbook, or give a path from anywhere at all:

        macrostrat run                       list the pipelines here
        macrostrat run ngs sources --apply   Maps/NGS/cli.py sources --apply
        macrostrat --env test run Stratigraphy/GBDB ingest

    It is *executed, not imported*, in its own virtualenv, and receives the
    resolved environment as MACROSTRAT_ENV and MACROSTRAT_DATABASE_URL. Anything
    that is neither a pipeline nor a path is looked up in `srcroot/bin`.
    """
    from . import pipelines

    bindir = Path(settings.srcroot) / "bin"

    if command is None:
        root = pipelines.workbook_root()
        if root is not None:
            pipelines.list_pipelines(root)
        print("[bold]Scripts in bin/[/bold]")
        for f in sorted(bindir.iterdir()):
            if f.is_file() and f.name != "macrostrat":
                print(f"  {f.name}")
        return

    target = pipelines.resolve(command)
    if target is not None:
        raise typer.Exit(pipelines.run_pipeline(target, ctx.args))

    cmd = bindir / command
    if not cmd.is_file():
        root = pipelines.workbook_root()
        where = (
            f"the pipelines in {root.name}"
            if root
            else "any workbook (no .dvc above here)"
        )
        raise MacrostratError(
            f"[item]{command}[/item] is not a pipeline, a path, or a script in bin/",
            details=f"Looked in {where} and {bindir}. `macrostrat run` alone lists both.",
        )
    run(str(cmd), *ctx.args)


# Add subsystems if they are available.
# This organization is a bit awkward, and we may change it eventually.
try:
    from macrostrat.map_integration.cli import cli as map_app

    from .commands.export import export_map

    map_app.command("export", short_help="Export map data")(export_map)

    main.add_typer(
        map_app,
        name="maps",
        rich_help_panel="Maps",
        short_help="Map integration system",
    )

except ImportError as err:
    app.console.print("Could not import map integration subsystem", err)

try:
    from .rasters import build_raster_cli

    main.add_typer(
        build_raster_cli(),
        name="raster",
        rich_help_panel="Maps",
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
