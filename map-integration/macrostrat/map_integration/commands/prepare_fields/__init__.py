from pathlib import Path
from typing import Annotated

from rich import print
from sqlalchemy.exc import NoSuchTableError
from typer import Option

from ...database import get_database
from ...utils import MapInfo, create_sources_record
from .utils import LineworkTableUpdater, PointsTableUpdater, PolygonTableUpdater


def prepare_fields(
    map: MapInfo,
    all: bool = False,
    recover: Annotated[
        bool, Option("--recover", help="Recover sources records")
    ] = False,
):
    """Prepare empty fields for manual cleaning."""
    identifier = map.slug
    if all:
        prepare_fields_for_all_sources(recover=recover)
        return

    if identifier is None:
        raise ValueError("You must specify a slug or pass --all")

    _prepare_fields(map, recover=recover)


def _recover_sources_row(identifier):
    print(
        f"[bold yellow]Attempting to recover source record for [bold cyan]{identifier}"
    )
    try:
        return create_sources_record(db, identifier)
    except ValueError:
        print(f"[bold red]Failed to recover source record for [bold cyan]{identifier}")


def _prepare_fields(map: MapInfo | None, recover: bool = False):
    """Prepare empty fields for manual cleaning."""
    identifier = map.slug

    print(f"[bold]Preparing fields for source [cyan]{identifier}")

    schema = "sources"
    info = map
    # print(
    #     f"[gray dim]Use [bold]--recover[/] to attempt to recover the record in the [bold]maps.sources[/] table."
    # )
    if recover:
        info = _recover_sources_row(identifier)
    if info is None:
        print()
        return

    slug = info.slug
    source_id = info.id

    update_tables(source_id, slug, schema)

    print(
        f"\n[bold green]Source [bold cyan]{slug}[green] prepared for manual cleaning!\n"
    )


updaters = {
    "polygons": PolygonTableUpdater,
    "lines": LineworkTableUpdater,
    "points": PointsTableUpdater,
}


def update_tables(source_id, slug, schema):
    db = get_database()
    for table_type, updater in updaters.items():
        try:
            updater(db, f"{slug}_{table_type}", schema).run(source_id)
        except NoSuchTableError:
            print(f"[bold orange]No {table_type} table found for [bold cyan]{slug}")


def prepare_fields_for_all_sources(recover=False):
    # Run prepare fields for all legacy map tables that don't have a _pkid column
    db = get_database()
    sql = (
        Path(__file__).parent.parent.parent
        / "procedures"
        / "all-candidate-source-slugs.sql"
    )
    for table in db.run_query(sql):
        prepare_fields(table.slug, recover=recover)


def get_sources_record(slug):
    """Insert a record into the sources table."""
    db = get_database()
    return db.run_query(
        """
        INSERT INTO maps.sources (slug)
        VALUES (:source_name)
        ON CONFLICT (slug)
        DO NOTHING
        RETURNING source_id
        """,
        dict(source_name=slug),
    ).scalar()
