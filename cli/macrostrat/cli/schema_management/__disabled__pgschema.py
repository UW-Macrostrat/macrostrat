from json import loads
from pathlib import Path
from typing import Callable

import docker
import typer
from macrostrat.database import Database
from macrostrat.dinosaur.upgrade_cluster.utils import database_cluster
from macrostrat.utils import get_logger, working_directory
from macrostrat.utils.shell import run
from rich import print
from typer import Argument

from macrostrat.core import app
from macrostrat.core.config import settings
from macrostrat.core.database import get_database
from macrostrat.core.migrations import _run_migrations_in_database
from ..database.utils import engine_for_db_name

log = get_logger(__name__)

__here__ = Path(__file__).parent
fixtures_dir = __here__.parent / "fixtures"


DBCallable = Callable[[Database], None]


@db_app.command("dump-canonical", deprecated=True)
def dump_managed(schema: str = Argument(None)):
    """Export managed schemas from the Macrostrat database using [cyan]pg_dump[/]"""

    db_container = app.settings.get("pg_database_container", "postgres:15")
    engine = engine_for_db_name("macrostrat")

    dumpdir = settings.srcroot / "schema"

    db = get_db()
    url = db.engine.url

    dbargs = [
        "--db",
        url.database,
        "--host",
        url.host,
        "--port",
        str(url.port or 5432),
        "--user",
        url.username,
        "--password",
        url.password,
    ]

    schemas_to_dump = managed_schemas
    if schema is not None:
        schemas_to_dump = [schema]

    # Use the dump directory as the working directory
    # to pull in the pgschemaignore file
    with working_directory(str(dumpdir)):
        args = []
        for schema in schemas_to_dump:
            dumpfile = f"{schema}.sql"
            with open(dumpfile, "w") as f:
                print(
                    f"[dim]Dumping schema [bold cyan]{schema}[/] to [bold]{dumpfile}[/]"
                )
                run(
                    "pgschema",
                    "dump",
                    *dbargs,
                    "--schema",
                    schema,
                    stdout=f,
                )


@db_app.command("plan")
def plan():
    """Plan updates to managed schemas in the Macrostrat database using [cyan]pgschema[/cyan]"""
    db = get_database()
    url = db.engine.url

    image = settings.get("pg_database_container", "postgres:15")

    client = docker.from_env()

    img_root = settings.srcroot / "base-images" / "database"

    # Build postgres pgaudit image
    img_tag = "macrostrat.local/database:latest"

    client.images.build(path=str(img_root), tag=img_tag)

    dumpdir = settings.srcroot / "schema"

    # Spin up an image with this container
    port = 54884
    with planning_database(db) as plan_db:
        out_dir = dumpdir / "plans"
        out_dir.mkdir(exist_ok=True)
        for _schema in managed_schemas:
            plan_file = dumpdir / f"{_schema}.sql"

            out_file = out_dir / f"{_schema}_plan.sql"

            human_readable = out_file.with_suffix(".txt")
            machine_readable = out_file.with_suffix(".json")

            print(f"[dim]Planning schema [bold cyan]{_schema}[/]")

            _pgschema(
                db,
                [
                    "plan",
                    "--schema",
                    _schema,
                    "--file",
                    str(plan_file),
                    "--output-sql",
                    str(out_file),
                    "--output-json",
                    str(machine_readable),
                ],
                plan_db=plan_db,
            )

            # Read the plan
            plan_data = loads(machine_readable.read_text())
            n_changes = plan_data.get("groups", None)
            if n_changes is None:
                print(f"[green]No changes planned for schema [bold cyan]{_schema}[/]")
                out_file.unlink(missing_ok=True)
                human_readable.unlink(missing_ok=True)
                machine_readable.unlink(missing_ok=True)
            else:
                n_changes = sum([len(g.get("steps", [])) for g in plan_data["groups"]])
                print(
                    f"[yellow bold]{n_changes} changes planned for schema [bold cyan]{_schema}[/]"
                )


@db_app.command(deprecated=True)
def apply_pgschema(schema: str = Argument(None)):
    """Apply planned updates to managed schemas in the Macrostrat database using [cyan]pgschema[/cyan]"""
    db = get_database()
    url = db.engine.url

    dumpdir = settings.srcroot / "schema"
    out_dir = dumpdir / "plans"

    if schema is not None:
        schemas_to_apply = [schema]
    else:
        schemas_to_apply = managed_schemas

    with working_directory(str(dumpdir)):
        for _schema in schemas_to_apply:
            plan_file = out_dir / f"{_schema}_plan.json"
            if not plan_file.exists():
                print(
                    f"[dim]No plan found for schema [bold cyan]{_schema}[/], skipping"
                )
                continue

            print(f"[dim]Applying plan for schema [bold cyan]{_schema}[/]")

            res = _pgschema(
                db,
                ["apply", "--schema", _schema, "--plan", str(plan_file)],
            )

            if res.returncode != 0:
                print(
                    f"[red bold]Failed to apply plan for schema [bold cyan]{_schema}[/]"
                )
                return

            print(
                f"[green bold]Successfully applied plan for schema [bold cyan]{_schema}[/]"
            )

            # Remove plan files
            plan_file.with_suffix(".sql").unlink(missing_ok=True)
            plan_file.with_suffix(".txt").unlink(missing_ok=True)
            plan_file.unlink(missing_ok=True)

            # Dump the updated schema
            dumpfile = f"{_schema}.sql"
            with open(dumpfile, "w") as f:
                print(
                    f"[dim]Dumping updated schema [bold cyan]{_schema}[/] to [bold]{dumpfile}[/]"
                )
                _pgschema(db, ["dump", "--schema", _schema], stdout=f)


@db_app.command(
    context_settings={
        "allow_extra_args": True,
        "ignore_unknown_options": True,
        "help_option_names": [],
    }
)
def pgschema(
    ctx: typer.Context,
):
    """Explore a database using [cyan]pgschema[/cyan]"""
    db = get_database()
    url = db.engine.url

    dbargs = [
        "--db",
        url.database,
        "--host",
        url.host,
        "--port",
        str(url.port or 5432),
        "--user",
        url.username,
        "--password",
        url.password,
    ]

    if ctx.args[0] == "dump":
        _pgschema(db, ctx.args)
        return

    # Otherwise we

    image = settings.get("pg_database_container", "postgres:15")

    client = docker.from_env()

    img_root = settings.srcroot / "base-images" / "database"

    # Build postgres pgaudit image
    img_tag = "macrostrat.local/database:latest"

    client.images.build(path=str(img_root), tag=img_tag)

    # Spin up an image with this container
    port = 54884
    with database_cluster(client, img_tag, port=port) as container:
        _url = f"postgresql://postgres@localhost:{port}/postgres"
        plan_db = Database(_url)
        plan_db.run_sql('CREATE ROLE "macrostrat-admin"')

        _run_migrations_in_database(plan_db, legacy=False)

        _pgschema(db, ctx.args, plan_db=plan_db)


def _pgschema(db: Database, args: list[str], plan_db: Database = None):
    """Run pgschema with the given arguments"""
    url = db.engine.url

    dbargs = [
        "--db",
        url.database,
        "--host",
        url.host,
        "--port",
        str(url.port or 5432),
        "--user",
        url.username,
    ]

    if url.password is not None:
        dbargs.extend(["--password", url.password])

    if plan_db is not None:
        plan_url = plan_db.engine.url
        dbargs += [
            "--plan-db",
            plan_url.database,
            "--plan-host",
            plan_url.host,
            "--plan-port",
            str(plan_url.port or 5432),
            "--plan-user",
            plan_url.username,
        ]

        if plan_url.password is not None:
            dbargs.extend(["--plan-password", plan_url.password])

    return run("pgschema", *dbargs, *args)
