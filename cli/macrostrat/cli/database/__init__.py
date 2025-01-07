import asyncio
from pathlib import Path
from sys import exit, stderr, stdin, stdout
from typing import Any, Callable, Iterable

import typer
from macrostrat.database import Database
from macrostrat.database.transfer import pg_dump_to_file, pg_restore_from_file
from macrostrat.database.transfer.utils import raw_database_url
from macrostrat.database.utils import get_sql_files
from macrostrat.utils import get_logger
from macrostrat.utils.shell import run
from pydantic import BaseModel
from rich import print
from sqlalchemy import make_url, text
from typer import Argument, Option

from macrostrat.core import MacrostratSubsystem, app
from macrostrat.core.migrations import run_migrations
from ._legacy import get_db
# First, register all migrations
# NOTE: right now, this is quite implicit.
from .migrations import load_migrations
from .utils import engine_for_db_name, setup_postgrest_access

log = get_logger(__name__)

__here__ = Path(__file__).parent
fixtures_dir = __here__.parent / "fixtures"


DBCallable = Callable[[Database], None]


load_migrations()


class SubsystemSchemaDefinition(BaseModel):
    """A schema definition managed by a Macrostrat subsystem"""

    # TODO: These could be recast as "idempotent migrations" that can be run at any time
    # and integrated with the migrations system
    model_config = dict(
        arbitrary_types_allowed=True,
    )

    name: str
    version: str = "0.0.0"
    depends_on: list[str] = []
    fixtures: list[Path | DBCallable] = []
    params: dict[str, Any] | None = None
    callback: DBCallable | None = None

    def apply(self, db, match: str = None):
        for f in self.fixtures:
            if callable(f):
                f(db)
                continue
            # This does the same as the upstream "Apply fixtures" function
            # but it has support for a 'match' parameter
            files = _match_paths(get_sql_files(f), match)
            db.run_fixtures(files)

        if self.callback is not None:
            self.callback(db)


def _match_paths(paths: Iterable[Path], match: str | None):
    for path in paths:
        if match is not None and match not in str(path):
            continue
        yield path


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


@db_app.command(
    context_settings={
        "allow_extra_args": True,
        "ignore_unknown_options": True,
        "help_option_names": [],
    },
)
def psql(
    ctx: typer.Context,
):
    """Explore a database using [cyan]psql[/cyan]"""
    from macrostrat.core.config import PG_DATABASE_DOCKER

    # Clumsy way to get the correct host for Docker
    url = make_url(PG_DATABASE_DOCKER)

    # Set default arguments
    env_flags = [
        "-e",
        "PGDATABASE",
        "-e",
        "PGUSER",
        "-e",
        "PGPASSWORD",
        "-e",
        f"PGHOST={url.host}",
        "-e",
        "PGPORT",
    ]

    flags = [
        "-i",
        "--rm",
        "--network",
        "host",
        *env_flags,
    ]
    if stdin.isatty():
        flags.append("-t")

    db_container = app.settings.get("pg_database_container", "postgres:15")

    run("docker", "run", *flags, db_container, "psql", *ctx.args)


@db_app.command(
    context_settings={
        "allow_extra_args": True,
        "ignore_unknown_options": True,
    }
)
def dump(
    ctx: typer.Context,
    dumpfile: Path = Argument("-", help="Output file"),
    database: str = Option(
        None,
        "--database",
    ),
    schema: bool = False,
):
    """Export a database using [cyan]pg_dump[/]"""

    db_container = app.settings.get("pg_database_container", "postgres:15")

    engine = engine_for_db_name(database)

    if dumpfile == "-":
        dumpfile = stdout

    args = ctx.args
    custom_format = True
    if schema:
        args.append("--schema-only")
        custom_format = False

    task = pg_dump_to_file(
        engine,
        dumpfile,
        args=args,
        postgres_container=db_container,
        custom_format=custom_format,
    )
    asyncio.run(task)


@db_app.command()
def restore(
    dumpfile: Path,
    database: str = Argument(None),
    *,
    create: bool = False,
    jobs: int = Option(None, "--jobs", "-j"),
    version: str = Option(
        None,
        "--version",
        "-v",
        help="Postgres version or docker container to restore with",
    ),
):
    """Load a database using [cyan]pg_restore[/]"""

    db_container = app.settings.get("pg_database_container", "postgres:15")
    if version is not None:
        if ":" in version:
            db_container = version
        else:
            db_container = f"postgres:{version}"

    engine = engine_for_db_name(database)

    args = []
    if jobs is not None:
        args.extend(["--jobs", str(jobs)])

    task = pg_restore_from_file(
        dumpfile,
        engine,
        args=args,
        postgres_container=db_container,
        create=create,
    )
    asyncio.run(task)


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
    pth = Path(__file__).parent.parent / "sql-scripts"
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


def update_permissions():
    """Setup permissions for the PostgREST API.

    NOTE: This is a stopgap until we have a better permssions system.
    """
    db = get_db()
    setup_postgrest_access("macrostrat_api")(db)
    db.run_sql("NOTIFY pgrst, 'reload schema';")


db_app.command(name="permissions", rich_help_panel="Helpers")(update_permissions)


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
