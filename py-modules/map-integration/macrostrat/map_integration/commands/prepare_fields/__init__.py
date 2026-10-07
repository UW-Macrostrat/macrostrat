from pathlib import Path
from typing import Annotated

from rich import print
from sqlalchemy.exc import NoSuchTableError
from typer import Option

from macrostrat.core.exc import MacrostratError
from macrostrat.map_utils.slugs import staging_table

from ...database import get_database
from ...utils import MapInfo, create_sources_record, get_map_info
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
        return create_sources_record(get_database(), identifier)
    except ValueError:
        print(f"[bold red]Failed to recover source record for [bold cyan]{identifier}")


def _prepare_fields(
    info: MapInfo | None, recover: bool = False, identifier: str | None = None
):
    """Prepare empty fields for manual cleaning; `identifier` names a map with no record."""
    identifier = identifier or info.slug
    print(f"[bold]Preparing fields for source [cyan]{identifier}")

    schema = "sources"
    if info is None and recover:
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
            updater(db, staging_table(slug, table_type), schema).run(source_id)
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
    # A candidate read off a table name is a prefix; `get_map_info` also tries it hyphenated.
    for slug in sorted({row.slug for row in db.run_query(sql)}):
        try:
            info = get_map_info(db, slug)
        except MacrostratError:
            info = None
        _prepare_fields(info, recover=recover, identifier=slug)


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
