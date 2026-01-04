import asyncio
from datetime import datetime
from pathlib import Path
from sys import exit, stderr
from typing import Callable

import click
from macrostrat.app_frame import CommandBase
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

from macrostrat.core import app as macrostrat_app
from macrostrat.core.config import settings
from macrostrat.core.database import get_database
from macrostrat.core.exc import MacrostratError
from macrostrat.core.migrations import run_migrations
from .defs import (
    get_inspector,
    planning_database,
    StatementCounter,
    is_unsafe_statement,
    get_all_schemas,
    apply_schema_for_environment,
)
# First, register all migrations
# NOTE: right now, this is quite implicit.
from .migration_system import load_migrations
from ..database.utils import engine_for_db_name

log = get_logger(__name__)

__here__ = Path(__file__).parent
fixtures_dir = __here__.parent / "fixtures"


DBCallable = Callable[[Database], None]


schema_app = CommandBase()


@schema_app.command(name="plan", rich_help_panel="Automated migrations")
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

        schemas = get_all_schemas(
            plan_db,
            excluded_schemas=["topology", "sources", "tiger", "tiger_data"],
        )

        m = Migration(
            from_db,
            target_db,
        )
        # Subsitute inspectors for ones that support multiple schemas
        m.changes.i_from = get_inspector(from_db, schemas)
        m.changes.i_target = get_inspector(target_db, schemas)
        # Extension versions are not important
        m.changes.ignore_extension_versions = True

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


@schema_app.command(rich_help_panel="Automated migrations")
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


@schema_app.command(rich_help_panel="Automated migrations")
def apply(
    plan_file: Path | None = Argument(None),
    safe: bool = Option(True, "--safe/--unsafe"),
    archive: bool = Option(True, "--archive/--no-archive"),
):
    """Apply migration plan to database"""
    db = get_database()

    dumpdir = settings.srcroot / "schema"
    environment = settings.env

    if plan_file is not None:
        pending_plan = plan_file
    else:
        pending_plan = dumpdir / f"{environment}.plan.sql"

    if not pending_plan.exists():
        raise MacrostratError(
            "No plan found. Please run [item]macrostrat schema plan[/item] to generate one."
        )

    counter = StatementCounter(safe=safe)

    db.run_fixtures(
        pending_plan, statement_filter=counter.filter, console=macrostrat_app.console
    )
    db.run_sql("NOTIFY pgrst, 'reload schema';")

    counter.print_report()

    statements_to_log = counter.schema_log_entries()

    if not archive:
        print("[dim]Skipping archive step.")
        return

    if len(statements_to_log) == 0:
        print("[dim]No statements to log, skipping archive step.")
        return

    n_ignored = len(counter.statements) - len(statements_to_log)

    # If we applied the plan, move it to the applied plans location
    applied_dir = dumpdir / "_changelog"
    applied_dir.mkdir(exist_ok=True)

    _now = datetime.now()
    date = _now.strftime("%Y-%m-%d")
    applied_file = applied_dir / f"{date}-{environment}.applied.sql"

    time_applied = _now.strftime("%Y-%m-%d %H:%M:%S")

    cwd = Path.cwd()

    with applied_file.open("a") as f:
        # TODO: include user info, mark failing statements
        f.write(f"\n-- {time_applied}\n")
        f.write(f"-- Environment: {environment}\n")
        counter.print_report(file=f, prefix="-- ")
        if n_ignored > 0:
            f.write(f"-- {n_ignored} statements were not logged\n")

        f.write("\n")
        f.write("\n".join(statements_to_log) + "\n\n")
        # Write newlines to separate from next log entry

    print(
        f"[dim]Logged statements to [bold]{applied_file.relative_to(cwd, walk_up=True)}[/]"
    )


@schema_app.command(name="migrate", rich_help_panel="Manual migrations")
def migrate(
    name: str = Argument(None),
    *,
    apply: bool = Option(False, "--apply/--no-apply"),
    force: bool = Option(False, "--force/--no-force"),
    data: bool = Option(False, "--data/--no-data"),
):
    """Run all pending migrations"""
    load_migrations()
    run_migrations(apply=apply, name=name, force=force, data_changes=data)


@schema_app.command(name="scripts", rich_help_panel="Utils")
def run_scripts(migration: str = Argument(None)):
    """Run ad-hoc data management scripts

    These will be integrated with the migration system in the future.
    """
    pth = settings.srcroot / "schema" / "_data_scripts"
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


@schema_app.command("dump", rich_help_panel="Utils")
def dump_schema(schema: str):
    """Dump managed schemas using [cyan]pg_dump[/]"""

    engine = engine_for_db_name("macrostrat")

    dumpdir = settings.srcroot / "schema"
    env = settings.env

    dumpfile = dumpdir / env / f"0999-{schema}.sql"
    print(f"[dim]Dumping schema [bold cyan]{schema}[/] to [bold]{dumpfile}[/]")
    task = pg_dump_to_file(
        engine,
        dumpfile,
        custom_format=False,
        args=["--schema-only", "--schema", schema],
    )
    asyncio.run(task)


@schema_app.command(rich_help_panel="Utils")
def provision():
    """Apply all schema objects to the database

    TODO: filter out non-idempotent statements (table creation, etc.)
    """
    db = get_database()

    environment = settings.env

    counter = StatementCounter(safe=True)
    apply_schema_for_environment(db, environment, statement_filter=counter.filter)
    db.run_sql("NOTIFY pgrst, 'reload schema';")
    counter.print_report()
