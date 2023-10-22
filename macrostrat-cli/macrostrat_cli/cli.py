from dotenv import load_dotenv
from pathlib import Path
from os import environ
from sys import stderr, argv
from rich import print
from subprocess import run
from typing import Optional
import typer

from .config import settings

# Old environments configuration
# env = environ.get("MACROSTRAT_ENV", "dev")
# environments = ["dev", "testing", "chtc"]
# if env not in environments:
#     print(f"Unknown environment {env}", file=stderr)
#     print(f"Valid environments are: {environments}", file=stderr)
#     exit(1)
# else:
#     print(
#         f"Using environment [bold cyan]{env}[/] [dim](from MACROSTRAT_ENV)[/]",
#         file=stderr,
#     )

# Right now, the root dir must be manually edited here!
# root_dir = macrostrat_root / "server-configs" / f"{env}-server"
# dotenv_file = root_dir / ".env"

# if dotenv_file.exists():
#     load_dotenv(root_dir / ".env")

from macrostrat.app_frame import Application, compose

from .v1_entrypoint import v1_cli
from .v2_commands import app as v2_app
from sys import exit

# settings = Dynaconf(settings_files=[root_dir/"macrostrat.toml", root_dir/".secrets.toml"])

__here__ = Path(__file__).parent
root_dir = __here__ / "fixtures"
# macrostrat_root = Path(settings.macrostrat_root)

compose_file = root_dir / "docker-compose.yaml"
env_file = root_dir / ".env"

# Manage as a docker-compose application
app = Application(
    "Macrostrat",
    root_dir=root_dir,
    project_prefix=settings.project_name,
    app_module="macrostrat",
    compose_files=[compose_file],
    load_dotenv=env_file,
    restart_commands={"gateway": "nginx -s reload"},
)

main = app.control_command()


def run_all_sql(db, dir: Path):
    schema_files = list(dir.glob("*.sql"))
    schema_files.sort()
    for f in schema_files:
        print(f"[cyan bold]{f}[/]")
        db.run_sql(f)
        print()


def update_schema():
    """Update the database schema"""
    from .config import PG_DATABASE
    from macrostrat.database import Database

    try:
        from corelle.engine.database import initialize

        print("Creating models for [bold cyan]corelle[/] subsystem")
        initialize(drop=False)
    except ImportError as err:
        pass

    """Create schema additions"""
    schema_dir = root_dir
    # Loaded from env file
    db = Database(PG_DATABASE)

    subdirs = [d for d in schema_dir.iterdir()]
    subdirs.sort()
    for f in subdirs:
        if f.is_file() and f.suffix == ".sql":
            print(f"[cyan bold]{f}[/]")
            db.run_sql(f)
            print()
        elif f.is_dir():
            run_all_sql(db, f)

    try:
        from digitalcrust.weaver.cli import create_models

        print("Creating models for [bold cyan]weaver[/] subsystem")
        create_models()
    except ImportError as err:
        pass

    # Reload the postgrest schema cache
    compose("kill -s SIGUSR1 postgrest")


main.command(name="update-schema")(update_schema)

# Pass through arguments


@main.command(
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True}
)
def psql(ctx: typer.Context):
    """Run psql in the database container"""
    from .config import PG_DATABASE

    flags = [
        "-i",
        "--rm",
        "--network",
        "host",
    ]
    if len(ctx.args) == 0:
        flags.append("-t")

    run(["docker", "run", *flags, "postgres:15", "psql", PG_DATABASE, *ctx.args])


@main.command(name="tables")
def list_tables():
    """List all tables in the database"""
    from .config import PG_DATABASE

    # We could probably do this with the inspector too
    run(
        [
            "docker",
            "run",
            "-i",
            "--rm",
            "--network",
            "host",
            "postgres:15",
            "psql",
            PG_DATABASE,
            "-c",
            "\dt *.*",
        ]
    )


@main.command()
def config():
    """Print all configuration values"""
    from . import config as cfg

    for k, v in cfg.__dict__.items():
        # Only print uppercase values
        if k.isupper():
            print(f"{k}: {v}")


@main.command()
def install():
    """Install Macrostrat subsystems if available."""
    if hasattr(settings, "corelle_src"):
        print("Installing corelle")
        run(
            ["poetry", "install"], cwd=Path(settings.corelle_src).expanduser().resolve()
        )


main.add_typer(v2_app, name="v2")

# Add subsystems if they are available.
# This organization is a bit awkward, and we may change it eventually.
try:
    from macrostrat.map_integration import app as map_app

    main.add_typer(
        map_app,
        name="maps",
        rich_help_panel="Subsystems",
        short_help="Map integration system (partial overlap with v1 commands)",
    )
except ImportError as err:
    pass

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


try:
    from digitalcrust.weaver.cli import app as weaver_app

    main.add_typer(
        weaver_app,
        name="weaver",
        rich_help_panel="Subsystems",
        short_help="Prototype geochemical data management system",
    )
except ImportError as err:
    pass

try:
    from macrostrat_tileserver.cli import _cli as tileserver_cli

    environ["DATABASE_URL"] = settings.pg_database
    main.add_typer(
        tileserver_cli,
        name="tileserver",
        rich_help_panel="Subsystems",
        short_help="Control Macrostrat's tileserver",
    )
except ImportError as err:
    pass

try:
    environ["CORELLE_DB"] = settings.pg_database
    from corelle.engine import cli as corelle_cli

    corelle_cli.name = "corelle"
    corelle_cli.help = "Manage plate rotation models"

    main.add_click_command(
        corelle_cli,
        "corelle",
        rich_help_panel="Subsystems",
    )
except ImportError as err:
    pass

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
