import importlib
from os import environ

import typer
from sqlalchemy import text

from macrostrat.core.migrations import _run_migrations
from macrostrat.database import Database


def get_rockd_db() -> Database:
    """
    Return a Database instance that talks to the Rockd cluster.
    The URL can live in .env / docker-compose.yml as ROCKD_DATABASE.
    """
    url = environ.get("ROCKD_DATABASE")
    if url is None:
        raise RuntimeError("Set ROCKD_DATABASE in your environment")
    return Database(url)


cli = typer.Typer(help="Rockd database tools")


@cli.command()
def migrations(
    apply: bool = typer.Option(False, "--apply", help="Actually run them"),
    name: str | None = None,
    force: bool = False,
    data_changes: bool = False,
):
    """
    List or apply Rockd migrations.
    """
    importlib.import_module(".migrations", __package__)
    db = get_rockd_db()

    with db.engine.connect() as conn:
        row = (
            conn.execute(
                text(
                    """
            select current_database() as db,
                   current_user     as usr,
                   inet_server_addr() as host,
                   inet_server_port() as port,
                   to_regclass('public.people') as ppl,
                   to_regclass('public.checkins') as chk
        """
                )
            )
            .mappings()
            .one()
        )
        print(
            f"Preflight -> db={row['db']} user={row['usr']} server={row['host']}:{row['port']} people={row['ppl']} checkins={row['chk']}"
        )
    _run_migrations(
        db,
        apply=apply,
        name=name,
        force=force,
        data_changes=data_changes,
        subsystem="rockd",
    )
