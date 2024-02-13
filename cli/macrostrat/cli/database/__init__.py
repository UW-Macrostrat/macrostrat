from os import environ
from pathlib import Path
from sys import exit, stderr, stdin
from typing import Any, Callable
from urllib.parse import quote

import typer
from macrostrat.app_frame import compose
from macrostrat.database import Database
from macrostrat.utils.shell import run
from pydantic import BaseModel
from rich import print
from sqlalchemy import create_engine, text
from sqlalchemy_utils import create_database
from typer import Argument, Option

from macrostrat.core import MacrostratSubsystem, app
from macrostrat.core.utils import is_pg_url

from .._dev.utils import (
    _create_database_if_not_exists,
    _docker_local_run_args,
    raw_database_url,
)
from ._legacy import *

__here__ = Path(__file__).parent
fixtures_dir = __here__.parent / "fixtures"


def run_sql(db, f: Path, params, match: str = None):
    if match is not None and match not in str(f):
        return
    print(f"[cyan bold]{f}[/]")
    db.run_sql(f)
    print()


def run_all_sql(db, dir: Path, match: str = None):
    schema_files = list(dir.glob("*.sql"))
    for f in sorted(schema_files):
        if not f.is_file():
            continue
        run_sql(db, f, match)


class SubsystemSchemaDefinition(BaseModel):
    """A schema definition managed by a Macrostrat subsystem"""

    class Config:
        arbitrary_types_allowed = True

    name: str
    version: str = "0.0.0"
    depends_on: list[str] = []
    fixtures: list[Path] = []
    params: dict[str, Any] | None = None
    callback: Callable[[Database], None] | None = None

    def _run_sql(self, db, f: Path, match: str = None):
        if match is not None and match not in str(f):
            return
        print(f"[cyan bold]{f}[/]")
        db.run_sql(f, self.params)
        print()

    def _run_all_sql(self, db, dir: Path, match: str = None):
        schema_files = list(dir.glob("*.sql"))
        for f in sorted(schema_files):
            print(f)
            if not f.is_file():
                continue
            self._run_sql(db, f, match)

    def apply(self, db, match: str = None):
        print(self.fixtures)
        for f in self.fixtures:
            print(f)
            if f.is_file():
                self._run_sql(db, f, match)
            elif f.is_dir():
                self._run_all_sql(db, f, match)

        if self.callback is not None:
            self.callback(db)


# The core hunk contains all of Macrostrat's core schema


class DatabaseSubsystem(MacrostratSubsystem):
    # Additional functions to run when updating schema
    name = "database"

    schema_hunks: list[SubsystemSchemaDefinition]

    def __init__(self, app):
        super().__init__(app)
        self.schema_hunks = []

    def register_schema_part(
        self,
        *,
        name: str,
        version: str = "0.0.0",
        depends_on: list[str] = [],
        fixtures: list[Path] = [],
        params: dict[str, any] = None,
        callback: Callable[[Database], None] | None = None,
    ):
        hunk = SubsystemSchemaDefinition(
            name=name,
            version=version,
            depends_on=depends_on,
            fixtures=fixtures,
            params=params,
            callback=callback,
        )

        self.schema_hunks.append(hunk)


db_subsystem = DatabaseSubsystem(app)


db_subsystem.register_schema_part(
    name="core",
    fixtures=[fixtures_dir],
)


def update_schema(match: str = Option(None), subsystems: list[str] = Option(None)):
    """Update the database schema"""
    from macrostrat.database import Database

    from macrostrat.core.config import PG_DATABASE

    """Create schema additions"""
    schema_dir = fixtures_dir
    # Loaded from env file
    db = Database(PG_DATABASE)

    # Run subsystem updates
    for hunk in db_subsystem.schema_hunks:
        if (
            subsystems is not None
            and len(subsystems) != 0
            and hunk.name not in subsystems
        ):
            continue
        hunk.apply(db)

    app.subsystems.run_hook("schema-update")

    # Reload the postgrest schema cache
    if app.settings.get("compose_root", None) is not None:
        compose("kill -s SIGUSR1 postgrest")
    else:
        db.run_sql("NOTIFY pgrst, 'reload schema';")


db_app = db_subsystem.control_command()
db_app.command(name="update-schema")(update_schema)

# Pass through arguments


@db_app.command(
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True}
)
def psql(ctx: typer.Context, database: str = None):
    """Run psql in the database container"""
    from macrostrat.core.config import PG_DATABASE_DOCKER

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
    ctx: typer.Context, dumpfile: Path, database: str = None, schema: bool = False
):
    """Dump the database to a file"""
    from .._dev.dump_database import pg_dump

    db_container = app.settings.get("pg_database_container", "postgres:15")

    engine = _engine_for_db_name(database)

    args = ctx.args
    custom_format = True
    if schema:
        args.append("--schema-only")
        custom_format = False

    pg_dump(
        dumpfile,
        engine,
        postgres_container=db_container,
        args=ctx.args,
        custom_format=custom_format,
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
        result = conn.execute(text(sql), kwargs)
        for row in result:
            print(f"{row.table_schema}.{row.table_name}")


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

    pod = getattr(app.settings, "pg_database_pod", None)
    if pod is None:
        raise Exception("No pod specified.")
    port = environ.get("PGPORT", "5432")
    run("kubectl", "port-forward", pod, f"{port}:5432")


@db_app.command(name="import-mariadb")
def import_legacy():
    """Import legacy MariaDB database to PostgreSQL using pgloader"""
    # Run pgloader in docker

    cfg = app.settings

    args = _docker_local_run_args(postgres_container="dimitri/pgloader")

    # Get the database URL
    db = get_db()
    url = db.engine.url
    url = url.set(database="macrostrat_v1")

    _create_database_if_not_exists(url, create=True)

    pg_url = str(url)
    # Repl

    pg_url = cfg.get("pg_database", None)

    url = pg_url + "_v1"

    dburl = cfg.get("mysql_database", None)
    if dburl is None:
        raise Exception("No MariaDB database URL available in configuration")

    run(
        *args,
        "pgloader",
        "--with",
        "prefetch rows = 1000",
        str(dburl),
        str(url),
    )


keys = ["username", "host", "port", "password", "database"]


@db_app.command(name="connection-details")
def connection_details():
    """Print the database connection details"""
    db = get_db()
    url = raw_database_url(db.engine.url)
    for key in keys:
        print(
            field_title(key.capitalize()),
            f"[dim bold green]{getattr(db.engine.url, key)}",
        )
    print(field_title("URL"), f"[dim white]{url}")


def field_title(name):
    title = name + ":"
    # expand the title to 20 characters
    title = title.ljust(12)
    return "[dim]" + title + "[/]" + " "
