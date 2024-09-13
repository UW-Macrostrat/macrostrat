from os import environ
from pathlib import Path
from sys import exit, stderr, stdin
from typing import Any, Callable

import typer
from pydantic import BaseModel
from rich import print
from sqlalchemy import text
from typer import Argument, Option

from macrostrat.core import MacrostratSubsystem, app
from macrostrat.core.utils import is_pg_url
from macrostrat.database import Database
from macrostrat.utils.shell import run

from .._dev.utils import (
    _create_database_if_not_exists,
    _docker_local_run_args,
    raw_database_url,
)
from ._legacy import get_db
from .migrations import run_migrations
from .utils import engine_for_db_name

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

    # TODO: These could also be recast as "idempotent migrations" that can be run at any time
    model_config = dict(
        arbitrary_types_allowed=True,
    )

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
            if not f.is_file():
                continue
            self._run_sql(db, f, match)

    def apply(self, db, match: str = None):
        for f in self.fixtures:
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

    def initialize(self):
        self.register_schema_part(
            name="core",
            fixtures=[fixtures_dir],
        )


db_subsystem = DatabaseSubsystem(app)

db_app = typer.Typer(no_args_is_help=True)


def update_schema(
    match: str = Option(None),
    subsystems: list[str] = Option(None),
    _all: bool = Option(None, "--all"),
):
    """Update the database schema"""
    from macrostrat.core.config import PG_DATABASE
    from macrostrat.database import Database

    db_subsystem = app.subsystems.get("database")

    if subsystems is None:
        subsystems = []

    """Create schema additions"""
    schema_dir = fixtures_dir
    # Loaded from env file
    db = Database(PG_DATABASE)

    if match is not None and len(subsystems) == 0:
        # core is implicit
        subsystems = ["core"]

    if not _all and len(subsystems) == 0:
        print("Please specify --all or --subsystems to update the schema")
        print("Available subsystems:")
        for hunk in db_subsystem.schema_hunks:
            print(f"  {hunk.name}")
        return

    # Run subsystem updates
    for hunk in db_subsystem.schema_hunks:
        if (
            subsystems is not None
            and len(subsystems) != 0
            and hunk.name not in subsystems
        ):
            continue
        hunk.apply(db, match=match)

    app.subsystems.run_hook("schema-update")


db_app = db_subsystem.control_command()
db_app.command(name="update", rich_help_panel="Schema management")(update_schema)

# Pass through arguments


@db_app.command(
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True}
)
def psql(ctx: typer.Context, database: str = None):
    """Explore a database using [cyan]psql[/cyan]"""
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
    ctx: typer.Context,
    dumpfile: Path,
    database: str = Option(
        None,
        "--database",
    ),
    schema: bool = False,
):
    """Export a database using [cyan]pg_dump[/]"""
    from .._dev.dump_database import pg_dump

    db_container = app.settings.get("pg_database_container", "postgres:15")

    engine = engine_for_db_name(database)

    args = ctx.args
    custom_format = True
    if schema:
        args.append("--schema-only")
        custom_format = False

    pg_dump(
        dumpfile,
        engine,
        *args,
        postgres_container=db_container,
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
    """Load a database using [cyan]pg_restore[/]"""
    from .._dev.restore_database import pg_restore

    db_container = app.settings.get("pg_database_container", "postgres:15")

    engine = engine_for_db_name(database)

    args = []
    if jobs is not None:
        args.extend(["--jobs", str(jobs)])

    pg_restore(
        dumpfile,
        engine,
        *args,
        postgres_container=db_container,
        create=create,
    )


@db_app.command(name="tables", rich_help_panel="Helpers")
def list_tables(ctx: typer.Context, database: str = Argument(None), schema: str = None):
    """List tables in the database"""
    sql = """SELECT table_schema, table_name
    FROM information_schema.tables
    WHERE table_schema != 'pg_catalog' AND table_schema != 'information_schema'
    """

    kwargs = {}
    if schema is not None:
        sql += f"\nAND table_schema = :schema"
        kwargs["schema"] = schema

    sql += "\nORDER BY table_schema, table_name;"

    engine = engine_for_db_name(database)

    print(
        f"[dim]Tables in database: [bold cyan]{engine.url.database}[/]\n", file=stderr
    )

    with engine.connect() as conn:
        result = conn.execute(text(sql), kwargs)
        for row in result:
            print(f"{row.table_schema}.{row.table_name}")


class TableInspector:
    def __init__(self, db: Database, table, schema=None):
        self.db = db
        self.table = table
        self.schema = schema
        self._insp = db.inspector

    def __getattr__(self, name, **kwargs):
        return getattr(self.insp, name)(self.table, schema=self.schema, **kwargs)

    @property
    def foreign_keys(self):
        return self._insp.get_foreign_keys(self.table, schema=self.schema)

    @property
    def indexes(self):
        return self._insp.get_indexes(self.table, schema=self.schema)

    @property
    def columns(self):
        return self._insp.get_columns(self.table, schema=self.schema)

    @property
    def pk_constraint(self):
        return self._insp.get_pk_constraint(self.table, schema=self.schema)

    @property
    def unique_constraints(self):
        return self._insp.get_unique_constraints(self.table, schema=self.schema)

    @property
    def check_constraints(self):
        return self._insp.get_check_constraints(self.table, schema=self.schema)


@db_app.command(name="inspect", rich_help_panel="Helpers")
def inspect_table(table: str):
    """Inspect a table in the database"""
    db = get_db()

    schema = None
    if "." in table:
        schema, table = table.split(".")

    if not db.inspector.has_table(table, schema=schema):
        print(f"Table {table} does not exist", file=stderr)
        exit(1)

    insp = TableInspector(db, table, schema=schema)

    print(f"[dim]Inspecting table: [bold cyan]{table}[/]\n", file=stderr)
    from IPython import embed

    embed(
        header=f"""Inspecting table {table} in database {db.engine.url.database}.
        Use the 'db' object to interact with the database and 'insp' to interact with the inspector."""
    )


@db_app.command(name="scripts", rich_help_panel="Schema management")
def run_scripts(migration: str = Argument(None)):
    """Ad-hoc database management scripts"""
    pth = Path(__file__).parent.parent / "ad-hoc-migrations"
    files = list(pth.glob("*.sql"))
    files.sort()
    if migration is None:
        print("[yellow bold]No script specified\n", file=stderr)
        print("[bold]Available scripts:", file=stderr)
        for f in files:
            print(f"  {f.stem}", file=stderr)
        exit(1)
    migration = pth / (migration + ".sql")
    if not migration.exists():
        print(f"Script {migration} does not exist", file=stderr)
        exit(1)

    db = get_db()
    db.run_sql(migration)


db_app.command(name="migrations", rich_help_panel="Schema management")(run_migrations)


@db_app.command(
    name="import-mariadb", rich_help_panel="Schema management", deprecated=True
)
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


### Helpers


keys = ["username", "host", "port", "password", "database"]


@db_app.command(name="credentials", rich_help_panel="Helpers")
def connection_details():
    """Show PostgreSQL connection credentials"""
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


@db_app.command(name="tunnel", deprecated=True, rich_help_panel="Helpers")
def db_tunnel():
    """Kubernetes port-forward to a remote database"""
    # TODO: Check if we are running in a Kubernetes environment

    pod = getattr(app.settings, "pg_database_pod", None)
    if pod is None:
        raise Exception("No pod specified.")
    port = environ.get("PGPORT", "5432")
    run("kubectl", "port-forward", pod, f"{port}:5432")
