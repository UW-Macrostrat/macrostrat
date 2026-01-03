import asyncio
from datetime import datetime
from pathlib import Path
from sys import exit, stderr
from typing import Callable

import click
import typer
from macrostrat.database import Database
from macrostrat.database.transfer import pg_dump_to_file
from macrostrat.database.transfer.utils import raw_database_url
from macrostrat.utils import get_logger
from macrostrat.utils.shell import run
from results import db as results_db
from results.dbdiff import Migration
from rich import print
from typer import Argument
from typer import Option

from macrostrat.core.config import settings
from macrostrat.core.database import get_database
from macrostrat.core.exc import MacrostratError
from macrostrat.core.migrations import run_migrations
from .defs import (
    get_inspector,
    managed_schemas,
    planning_database,
    StatementCounter,
    is_unsafe_statement,
)
# First, register all migrations
# NOTE: right now, this is quite implicit.
from .migration_system import load_migrations
from ..database.utils import engine_for_db_name

log = get_logger(__name__)

__here__ = Path(__file__).parent
fixtures_dir = __here__.parent / "fixtures"


DBCallable = Callable[[Database], None]


schema_app = typer.Typer(no_args_is_help=True)


@schema_app.command()
def plan():
    """Compare schema with target database"""

    # TODO: enable single-schema diffs
    db = get_database()
    url = db.engine.url
    env = settings.env

    outdir = settings.srcroot / "schema"
    outdir.mkdir(exist_ok=True)
    out_file = outdir / f"{env}.plan.sql"

    with planning_database(env) as plan_db:
        from_db = results_db(raw_database_url(url))
        target_db = results_db(raw_database_url(plan_db.engine.url))

        m = Migration(
            from_db,
            target_db,
        )
        m.changes.i_from = get_inspector(from_db)
        m.changes.i_target = get_inspector(target_db)

        m.set_safety(False)
        m.add_all_changes(privileges=True)

        unsafe_statements = [s for s in m.statements if is_unsafe_statement(s)]
        n_unsafe = len(unsafe_statements)

        if n_unsafe > 0:
            print(f"[red dim]{n_unsafe} unsafe statements in diff")

        print(
            f"[dim]Writing {len(m.statements)} proposed changes to [bold]{out_file}[/]"
        )

        with open(out_file, "w") as f:
            f.write("\n".join(m.statements))


@schema_app.command()
def review(edit=False):
    """Review the latest migration plan"""
    dumpdir = settings.srcroot / "schema"
    environment = settings.env

    pending_plan = dumpdir / f"{environment}.plan.sql"

    if not pending_plan.exists():
        raise MacrostratError(
            "[yellow]No plan found. Please run [cyan]macrostrat schema plan[/cyan] to generate one."
        )

    if edit:
        click.edit(filename=pending_plan)
        print(f"[dim]Updated plan saved to [bold]{pending_plan}[/]")
    else:
        plan_sql = pending_plan.read_text()
        print(plan_sql)


@schema_app.command()
def apply(
    plan_file: Path | None = Argument(None),
    safe: bool = Option(True, "--safe/--unsafe"),
):
    """Apply automated migrations"""
    db = get_database()

    dumpdir = settings.srcroot / "schema"
    environment = settings.env

    if plan_file is not None:
        pending_plan = plan_file
    else:
        pending_plan = dumpdir / f"{environment}.plan.sql"

    if not pending_plan.exists():
        raise MacrostratError(
            "[yellow]No plan found. Please run [cyan]macrostrat schema plan[/cyan] to generate one."
        )

    counter = StatementCounter(safe=safe)

    db.run_fixtures(pending_plan, statement_filter=counter.filter)
    db.run_sql("NOTIFY pgrst, 'reload schema';")

    counter.print_report()

    # If we applied the plan, move it to the applied plans location
    applied_dir = dumpdir / "_plans"
    applied_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    applied_file = applied_dir / f"{timestamp}-{pending_plan.name}"
    pending_plan.rename(applied_file)
    print(f"[dim]Moved applied plan to [bold]{applied_file}[/]")


@schema_app.command(name="scripts", rich_help_panel="Utils")
def run_scripts(migration: str = Argument(None)):
    """Ad-hoc database management scripts

    These will be integrated with the migration system in the future.
    """
    pth = Path(__file__).parent.parent / "data-scripts"
    files = list(pth.glob("*.sql")) + list(pth.glob("*.sh")) + list(pth.glob("*.py"))
    files.sort()
    if migration is None:
        print("[yellow bold]No script specified\n", file=stderr)
        print("[bold]Available scripts:", file=stderr)
        for f in files:
            print(f"  {f.stem}[dim]{f.suffix}", file=stderr)
        exit(1)
    matching_migrations = [
        f for f in files if f.stem == migration or str(f) == migration
    ]
    if len(matching_migrations) == 0:
        print(f"Script {migration} does not exist", file=stderr)
        exit(1)
    if len(matching_migrations) > 1:
        print(
            f"Ambiguous script name: {migration}",
            file=stderr,
        )
        print("Please specify the full file name")
        exit(1)
    migration = matching_migrations[0]
    if migration.suffix == ".py":
        run("python", str(migration))
    if migration.suffix == ".sh":
        run(str(migration))
    if migration.suffix == ".sql":
        db = get_database()
        db.run_sql(migration)


@schema_app.command(name="migrate")
def _run_migrations(*, apply: bool = Option(False, "--apply/--no-apply")):
    # TODO: we could import and load subsystem migrations here too.
    load_migrations()
    run_migrations(apply=apply)


@schema_app.command("dump", rich_help_panel="Utils")
def dump_schema(schema: str = Argument(None)):
    """Dump managed schemas using [cyan]pg_dump[/]"""

    engine = engine_for_db_name("macrostrat")

    dumpdir = settings.srcroot / "schema"
    env = settings.env

    schemas_to_dump = managed_schemas
    if schema is not None:
        schemas_to_dump = [schema]

    for _schema in schemas_to_dump:
        dumpfile = dumpdir / env / f"0999-{_schema}.sql"
        print(f"[dim]Dumping schema [bold cyan]{_schema}[/] to [bold]{dumpfile}[/]")
        task = pg_dump_to_file(
            engine,
            dumpfile,
            custom_format=False,
            args=["--schema-only", "--schema", _schema],
        )
        asyncio.run(task)
