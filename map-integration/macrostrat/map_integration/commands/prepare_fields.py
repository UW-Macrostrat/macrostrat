from pathlib import Path

from psycopg2.sql import SQL, Identifier
from rich import print
from sqlalchemy.exc import NoResultFound
from typer import Argument, Option

from ..database import db
from ..utils import create_sources_record, get_map_info


def prepare_fields(
    identifier: str = Argument(None),
    all: bool = False,
    recover: bool = Option(False, "--recover", help="Recover sources records"),
):
    """Prepare empty fields for manual cleaning."""
    if all:
        prepare_fields_for_all_sources(recover=recover)
        return

    if identifier is None:
        raise ValueError("You must specify a slug or pass --all")

    _prepare_fields(identifier, recover=recover)


def _prepare_fields(identifier: str, recover: bool = False):
    """Prepare empty fields for manual cleaning."""

    print(f"[bold]Preparing fields for source [cyan]{identifier}")

    schema = "sources"
    info = None
    try:
        info = get_map_info(db, identifier)
    except NoResultFound:
        print(f"[bold red]No source found with slug [bold cyan]{identifier}")
        print(
            f"[gray dim]Use [bold]--recover[/] to attempt to recover the record in the [bold]maps.sources[/] table."
        )
        if recover:
            print(
                f"[bold yellow]Attempting to recover source record for [bold cyan]{identifier}"
            )
            try:
                info = create_sources_record(db, identifier)
            except ValueError:
                print(
                    f"[bold red]Failed to recover source record for [bold cyan]{identifier}"
                )
    if info is None:
        return

    slug = info.slug
    source_id = info.id

    # The old format didn't specify the 'polygons' suffix
    # but the new one does.
    poly_table = f"{slug}_polygons"
    add_polygon_columns(schema, poly_table)
    add_primary_key_column(schema, poly_table)
    _set_source_id(schema, poly_table, source_id)

    update_legacy_table_columns(schema, f"{slug}_polygons")

    linework_table = f"{slug}_lines"
    add_linework_columns(schema, linework_table)
    add_primary_key_column(schema, linework_table)
    _set_source_id(schema, linework_table, source_id)

    points_table = f"{slug}_points"
    add_points_columns(schema, points_table)
    add_primary_key_column(schema, points_table)
    _set_source_id(schema, points_table, source_id)

    print(
        f"\n[bold green]Source [bold cyan]{slug}[green] prepared for manual cleaning!\n"
    )


def prepare_fields_for_all_sources(recover=False):
    # Run prepare fields for all legacy map tables that don't have a _pkid column
    sql = Path(__file__).parent.parent / "procedures" / "all-candidate-source-slugs.sql"
    for table in db.run_query(sql):
        prepare_fields(table.slug, recover=recover)


def get_sources_record(slug):
    """Insert a record into the sources table."""
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


common_columns = {
    "source_id": "integer",
    "orig_id": "integer",
    "omit": "boolean",
    # "ready": "boolean",  # Ready to be inserted?
}


def add_linework_columns(schema, table_name):
    columns = {
        **common_columns,
        "descrip": "text",
        "name": "character varying(255)",
        "type": "character varying(100)",
        "direction": "character varying(20)",
    }
    _apply_column_mapping(schema, table_name, columns)


def add_polygon_columns(schema, table_name):
    """Add columns to the polygons table that are required for homogenization."""

    columns = {
        **common_columns,
        "name": "text",
        "strat_name": "text",
        "age": "text",
        "lith": "text",
        "descrip": "text",
        "comments": "text",
        "t_interval": "integer",
        "b_interval": "integer",
    }
    _apply_column_mapping(schema, table_name, columns)


def add_points_columns(schema, table_name):
    """Add columns to the points table that are required for homogenization."""
    columns = {
        **common_columns,
        "comments": "text",
        "strike": "integer",
        "dip": "integer",
        "dip_dir": "integer",
        "point_type": "character varying(100)",
        "certainty": "character varying(100)",
    }
    _apply_column_mapping(schema, table_name, columns)


def _apply_column_mapping(schema, table_name, columns, rename_geometry=True):
    table = Identifier(schema, table_name)

    sql = "ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {column} {type}"
    for name, type in columns.items():
        db.run_sql(sql, dict(table=table, column=Identifier(name), type=SQL(type)))

    # Rename the geometry column if necessary
    if not rename_geometry:
        return

    db.run_sql(
        "ALTER TABLE {table} RENAME COLUMN geometry TO geom",
        dict(table=table),
    )


def add_primary_key_column(schema, table_name, column_name=None):
    if column_name is None:
        column_name = "_pkid"

    params = dict(table=Identifier(schema, table_name), column=Identifier(column_name))

    db.run_sql(
        "ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {column} SERIAL PRIMARY KEY",
        params=params,
    )


def update_legacy_table_columns(schema, table_name):
    """Legacy tables had different standard names for several columns."""

    db.run_sql(
        """
    ALTER TABLE {table} RENAME COLUMN gid TO _pkid;
    UPDATE {table} SET  t_interval = late_id, b_interval = early_id;
    UPDATE {table} SET omit = not ready WHERE ready IS NOT NULL;  
    """,
        params=dict(table=Identifier(schema, table_name)),
    )


def _set_source_id(schema, table, source_id):
    db.run_sql(
        "UPDATE {table} SET source_id = :source_id",
        params=dict(table=Identifier(schema, table), source_id=source_id),
    )
