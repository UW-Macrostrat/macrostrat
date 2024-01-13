from ._legacy import *

from pathlib import Path
from os import environ
from sys import stderr, stdin
from rich import print
import typer
from macrostrat.utils.shell import run
from typer import Argument, Option
from ..utils import is_pg_url
from ..core import MacrostratSubsystem, app
from sqlalchemy import create_engine, text

from macrostrat.app_frame import compose


from sys import exit


__here__ = Path(__file__).parent
fixtures_dir = __here__.parent / "fixtures"
# macrostrat_root = Path(settings.macrostrat_root)


# Manage as a docker-compose application


def run_all_sql(db, dir: Path):
    schema_files = list(dir.glob("*.sql"))
    schema_files.sort()
    for f in schema_files:
        print(f"[cyan bold]{f}[/]")
        db.run_sql(f)
        print()


class DatabaseSubsystem(MacrostratSubsystem):
    # Additional functions to run when updating schema
    _queued_updates = []


db_subsystem = DatabaseSubsystem(app)


def update_schema(match: str = Argument(None)):
    """Update the database schema"""
    from ..config import PG_DATABASE
    from macrostrat.database import Database

    """Create schema additions"""
    schema_dir = fixtures_dir
    # Loaded from env file
    db = Database(PG_DATABASE)

    subdirs = [d for d in schema_dir.iterdir()]
    subdirs.sort()
    for f in subdirs:
        if f.is_file() and f.suffix == ".sql":
            if match is not None and match not in str(f):
                continue

            print(f"[cyan bold]{f}[/]")
            db.run_sql(f)
            print()
        elif f.is_dir():
            run_all_sql(db, f)

    # Run subsystem updates
    for func in db_subsystem._queued_updates:
        func()

    # Reload the postgrest schema cache
    compose("kill -s SIGUSR1 postgrest")


db_app = db_subsystem.control_command()
db_app.command(name="update-schema")(update_schema)

# Pass through arguments


@db_app.command(
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True}
)
def psql(ctx: typer.Context, database: str = None):
    """Run psql in the database container"""
    from ..config import PG_DATABASE_DOCKER

    _database = PG_DATABASE_DOCKER
    if database is not None:
        if is_pg_url(database):
            _database = database
        else:
            _database = database

    flags = [
        "-i",
        "--rm",
        "--network",
        "host",
    ]
    if len(ctx.args) == 0 and stdin.isatty():
        flags.append("-t")

    run("docker", "run", *flags, "postgres:15", "psql", _database, *ctx.args)


@db_app.command(
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True}
)
def dump(
    ctx: typer.Context,
    dumpfile: Path,
    database: str = None,
):
    """Dump the database to a file"""
    from .._dev.dump_database import pg_dump

    db_container = app.settings.get("pg_database_container", "postgres:15")

    engine = _engine_for_db_name(database)

    pg_dump(
        dumpfile,
        engine,
        postgres_container=db_container,
        args=ctx.args,
    )


@db_app.command()
def restore(
    dumpfile: Path,
    database: str = Argument(None),
    *,
    create: bool = False,
    jobs: int = Option(None, "--jobs", "-j"),
):
    """Restore the database from a dump file"""
    from .._dev.restore_database import pg_restore

    db_container = app.settings.get("pg_database_container", "postgres:15")

    engine = _engine_for_db_name(database)

    args = []
    if jobs is not None:
        args.extend(["--jobs", str(jobs)])

    pg_restore(
        dumpfile,
        engine,
        postgres_container=db_container,
        create=create,
        args=args,
    )


def _engine_for_db_name(name: str | None):
    engine = get_db().engine
    if name is None:
        return engine
    url = engine.url.set(database=name)
    return create_engine(url)


@db_app.command(name="tables")
def list_tables(ctx: typer.Context, database: str = Argument(None), schema: str = None):
    sql = """SELECT table_schema, table_name
    FROM information_schema.tables
    WHERE table_schema != 'pg_catalog' AND table_schema != 'information_schema'
    """

    kwargs = {}
    if schema is not None:
        sql += f"\nAND table_schema = :schema"
        kwargs["schema"] = schema

    sql += "\nORDER BY table_schema, table_name;"

    engine = _engine_for_db_name(database)

    print(
        f"[dim]Tables in database: [bold cyan]{engine.url.database}[/]\n", file=stderr
    )

    with engine.connect() as conn:
        result = conn.execute(text(sql), **kwargs)
        for row in result:
            print(f"{row.table_schema}.{row.table_name}")


@db_app.command(name="sql")
def run_migration(migration: str = Argument(None)):
    """Run an ad-hoc migration"""
    pth = Path(__file__).parent.parent.parent / "ad-hoc-migrations"
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

    pod = getattr(app.settings, "pg_database_pod", None)
    if pod is None:
        raise Exception("No pod specified.")
    port = environ.get("PGPORT", "5432")
    run("kubectl", "port-forward", pod, f"{port}:5432")
