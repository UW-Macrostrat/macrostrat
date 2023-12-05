from dotenv import load_dotenv
from pathlib import Path
from os import environ
from sys import stderr, argv
from rich import print
from typing import Optional
import typer
from macrostrat.utils.shell import run
from typer import get_app_dir, Argument, Typer
from time import sleep

APP_NAME = "macrostrat"
app_dir = Path(get_app_dir(APP_NAME))
active_env = app_dir / "~active_env"
if "MACROSTAT_ENV" in environ:
    print(f"Using environment [bold cyan]{environ['MACROSTRAT_ENV']}[/]", file=stderr)
if "MACROSTRAT_ENV" not in environ and active_env.exists():
    environ["MACROSTRAT_ENV"] = active_env.read_text().strip()
    user_dir = str(Path("~").expanduser())
    dir = str(active_env).replace(user_dir, "~")
    print(
        f"Using environment [bold cyan]{environ['MACROSTRAT_ENV']}[/]\n[dim] from {dir}[/]",
        file=stderr,
    )


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
from .database import get_db
from sys import exit


# settings = Dynaconf(settings_files=[root_dir/"macrostrat.toml", root_dir/".secrets.toml"])

__here__ = Path(__file__).parent
fixtures_dir = __here__ / "fixtures"
# macrostrat_root = Path(settings.macrostrat_root)

compose_files = []
env_file = None
root_dir = None
if settings.get("compose_root", None) is not None:
    root_dir = Path(settings.compose_root).expanduser().resolve()
    compose_file = root_dir / "docker-compose.yaml"
    env_file = root_dir / ".env"
    compose_files.append(compose_file)

# Manage as a docker-compose application
app = Application(
    "Macrostrat",
    root_dir=root_dir,
    project_prefix=settings.project_name,
    app_module="macrostrat",
    compose_files=compose_files,
    load_dotenv=env_file,
    # This only applies to Docker Compose
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


# Additional functions to run when updating schema
subsystem_updates = []


def update_schema():
    """Update the database schema"""
    from .config import PG_DATABASE
    from macrostrat.database import Database

    """Create schema additions"""
    schema_dir = fixtures_dir
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

    # Run subsystem updates
    for func in subsystem_updates:
        func()

    # Reload the postgrest schema cache
    compose("kill -s SIGUSR1 postgrest")


# Commands to manage this command-line interface
db_app = typer.Typer(no_args_is_help=True)
db_app.command(name="update-schema")(update_schema)

# Pass through arguments


@db_app.command(
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True}
)
def psql(ctx: typer.Context):
    """Run psql in the database container"""
    from .config import PG_DATABASE_DOCKER

    flags = [
        "-i",
        "--rm",
        "--network",
        "host",
    ]
    if len(ctx.args) == 0:
        flags.append("-t")

    run("docker", "run", *flags, "postgres:15", "psql", PG_DATABASE_DOCKER, *ctx.args)


@db_app.command()
def restore(dumpfile: Path, database: str, create=False):
    """Restore the database from a dump file"""
    from .config import PG_DATABASE_DOCKER
    from ._dev.restore_database import pg_restore

    db_conn = PG_DATABASE_DOCKER
    # Replace the database name with the specified database

    db_container = settings.get("pg_database_container", "postgres:15")

    engine = get_db().engine

    pg_restore(
        dumpfile,
        engine,
        database,
        postgres_container=db_container,
        create=create,
    )


@db_app.command(name="tables")
def list_tables():
    """List all tables in the database"""
    from .config import PG_DATABASE_DOCKER

    # We could probably do this with the inspector too
    run(
        "docker",
        "run",
        "-i",
        "--rm",
        "--network",
        "host",
        "postgres:15",
        "psql",
        PG_DATABASE_DOCKER,
        "-c",
        "\dt *.*",
    )


@db_app.command(name="sql")
def run_migration(migration: str = Argument(None)):
    """Run an ad-hoc migration"""
    pth = Path(__file__).parent.parent / "ad-hoc-migrations"
    files = list(pth.glob("*.sql"))
    files.sort()
    if migration is None:
        print("No migration specified", file=stderr)
        print("Available migrations:", file=stderr)
        for f in files:
            print(f"  {f.stem}", file=stderr)
        exit(1)
    migration = pth / (migration + ".sql")
    if not migration.exists():
        print(f"Migration {migration} does not exist", file=stderr)
        exit(1)

    db = get_db()
    db.run_sql(migration)


@db_app.command(name="tunnel")
def db_tunnel():
    """Create a Kubernetes port-forward to the remote database"""

    pod = getattr(settings, "pg_database_pod", None)
    if pod is None:
        raise Exception("No pod specified.")
    port = environ.get("PGPORT", "5432")
    run("kubectl", "port-forward", pod, f"{port}:5432")


main.add_typer(db_app, name="db", short_help="Manage the database")


@main.command()
def config():
    """Print all configuration values"""
    from . import config as cfg

    for k, v in cfg.__dict__.items():
        # Only print uppercase values
        if k.isupper():
            print(f"{k}: {v}")


@main.command()
def shell():
    """Start an IPython shell"""
    import IPython

    IPython.embed()


@main.command(name="env")
def set_env(env: str = Argument(None), unset: bool = False):
    """Set the active environment"""
    if env is None:
        e = environ.get("MACROSTRAT_ENV")
        if e is None:
            print("No environment set", file=stderr)
            exit(1)
        print(e)
        return
    if unset:
        active_env.unlink()
    else:
        active_env.parent.mkdir(exist_ok=True)
        active_env.write_text(env)


def local_install(path: Path):
    run(
        ["poetry", "install"],
        cwd=path.expanduser().resolve(),
        env={**environ, "POETRY_VIRTUALENVS_CREATE": "False"},
    )


@main.command()
def install():
    """Install Macrostrat subsystems if available."""
    if hasattr(settings, "corelle_src"):
        print("Installing corelle")
        local_install(Path(settings.corelle_src))

    # TODO: move map integration subsystem into this repository
    if hasattr(settings, "map_integration_src"):
        print("Installing map integration subsystem")
        local_install(Path(settings.map_integration_src))


cfg_app = Typer(name="config")


@cfg_app.command(name="edit")
def edit_cfg():
    """Open config file in editor"""
    from subprocess import run
    from .config import macrostrat_config_file

    run(["open", str(macrostrat_config_file)])


main.add_typer(cfg_app)


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

    subsystem_updates.append(update_weaver)
except ImportError as err:
    pass

try:
    from macrostrat_tileserver.cli import _cli as tileserver_cli
    from macrostrat_tileserver.cli import create_fixtures

    environ["DATABASE_URL"] = settings.pg_database
    main.add_typer(
        tileserver_cli,
        name="tileserver",
        rich_help_panel="Subsystems",
        short_help="Control Macrostrat's tileserver",
    )

    def update_tileserver():
        print("Creating models for [bold cyan]tileserver[/] subsystem")
        create_fixtures()

    subsystem_updates.append(update_tileserver)

except ImportError as err:
    print("Could not import tileserver subsystem")

try:
    environ["CORELLE_DB"] = settings.pg_database
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

    subsystem_updates.append(update_corelle)

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
