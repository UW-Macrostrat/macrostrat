from dotenv import load_dotenv
from pathlib import Path
from os import environ
from sys import stderr, argv
from rich import print
from subprocess import run
from typing import Optional
import typer

# Load config before we do anything else
def find_config(start_dir: Path):
    """Find the macrostrat.toml config file"""

    next_dir = start_dir.resolve()
    while next_dir != next_dir.parent:
        if (next_dir / "macrostrat.toml").exists():
            return next_dir
        next_dir = next_dir.parent
    return None


macrostrat_root = None
# Find root dir upwards
macrostrat_root = find_config(Path.cwd())
if macrostrat_root is None:
    # Find user-specific config in home dir
    macrostrat_root = find_config(Path.home() / ".config" / "macrostrat")

# Find config upwards from utils installation
if macrostrat_root is None:
    macrostrat_root = find_config(Path(__file__).parent)

if macrostrat_root is None:
    raise RuntimeError("Could not find macrostrat.toml")

env = environ.get("MACROSTRAT_ENV", "dev")
environments = ["dev", "testing", "chtc"]
if env not in environments:
    print(f"Unknown environment {env}", file=stderr)
    print(f"Valid environments are: {environments}", file=stderr)
    exit(1)
else:
    print(
        f"Using environment [bold cyan]{env}[/] [dim](from MACROSTRAT_ENV)[/]",
        file=stderr,
    )

# Right now, the root dir must be manually edited here!
root_dir = macrostrat_root / "server-configs" / f"{env}-server"
dotenv_file = root_dir / ".env"

if dotenv_file.exists():
    load_dotenv(root_dir / ".env")

from macrostrat.app_frame import Application, compose

from .v1_entrypoint import v1_cli
from .v2_commands import app as v2_app
from sys import exit

# settings = Dynaconf(settings_files=[root_dir/"macrostrat.toml", root_dir/".secrets.toml"])

compose_file = root_dir / "docker-compose.yaml"
env_file = root_dir / ".env"

app = Application(
    "Macrostrat",
    root_dir=root_dir,
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
    from .config import PG_DATABASE
    from macrostrat.database import Database

    """Create schema additions"""
    schema_dir = macrostrat_root / "schema"

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

@main.command(context_settings={"allow_extra_args": True, "ignore_unknown_options": True})
def psql(ctx: typer.Context):
    """Run psql in the database container"""
    from .config import PG_DATABASE
    flags =[ "-i", "--rm", "--network", "host", ]
    if len(ctx.args) == 0:
        flags.append("-t")

    run(["docker", "run", *flags, "postgres:15", "psql", PG_DATABASE, *ctx.args, *cmd])

@main.command(name="tables")
def list_tables():
    """List all tables in the database"""
    from .config import PG_DATABASE
    # We could probably do this with the inspector too
    run(["docker", "run", "-i", "--rm", "--network", "host", "postgres:15", "psql", PG_DATABASE, "-c", "\dt *.*"])


@main.command()
def config():
    """Print all configuration values"""
    from . import config as cfg

    for k, v in cfg.__dict__.items():
        # Only print uppercase values
        if k.isupper():
            print(f"{k}: {v}")


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
        context_settings={"allow_extra_args": True, "ignore_unknown_options": True}
    )
    def rast(ctx: typer.Context):
        run(["poetry", "run", "macrostrat-raster", *ctx.args], cwd="/data/macrostrat/tools/raster-cli")
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

main.add_click_command(v1_cli, name="v1")
