from ..database import db
from rich import print
from psycopg2.sql import Identifier, SQL


def prepare_fields(source_prefix: str):
    """Prepare empty fields for manual cleaning."""
    schema = "sources"

    source_id = get_sources_record(source_prefix)

    for table_suffix in ("_polygons", ""):
        # The old format didn't specify the 'polygons' suffix
        # but the new one does.
        table = f"{source_prefix}{table_suffix}"
        add_polygon_columns(schema, table)
        add_primary_key_column(schema, table)
        _set_source_id(schema, table, source_id)

    linework_table = f"{source_prefix}_linestrings"
    add_linework_columns(schema, linework_table)
    add_primary_key_column(schema, linework_table)
    _set_source_id(schema, linework_table, source_id)

    print(
        f"\n[bold green]Source [bold cyan]{source_prefix}[green] prepared for manual cleaning!\n"
    )


def get_sources_record(source_prefix):
    """Insert a record into the sources table."""
    return db.session.execute(
        """
        INSERT INTO maps.sources (primary_table)
        VALUES (:source_name)
        ON CONFLICT (primary_table)
        DO UPDATE SET primary_table = :source_name
        RETURNING source_id
        """,
        params=dict(source_name=source_prefix),
    ).scalar()


common_columns = {
    "source_id": "integer",
    "orig_id": "integer",
    "descrip": "text",
    "ready": "boolean",  # Ready to be inserted?
}


def add_linework_columns(schema, table_name):
    columns = {
        **common_columns,
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
        "comments": "text",
        "t_interval": "integer",
        "b_interval": "integer",
    }
    _apply_column_mapping(schema, table_name, columns)


def _apply_column_mapping(schema, table_name, columns, rename_geometry=True):
    table = Identifier(schema, table_name)

    sql = "ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {column} {type}"
    for name, type in columns.items():
        db.run_sql(
            sql, params=dict(table=table, column=Identifier(name), type=SQL(type))
        )

    # Rename the geometry column if necessary
    if not rename_geometry:
        return

    db.run_sql(
        "ALTER TABLE {table} RENAME COLUMN geometry TO geom",
        params=dict(table=table),
    )


def add_primary_key_column(schema, table_name, column_name=None):
    if column_name is None:
        column_name = "_pkid"

    db.run_sql(
        "ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {column} SERIAL PRIMARY KEY",
        params=dict(
            table=Identifier(schema, table_name), column=Identifier(column_name)
        ),
    )


def _set_source_id(schema, table, source_id):
    db.run_sql(
        "UPDATE {table} SET source_id = :source_id",
        params=dict(table=Identifier(schema, table), source_id=source_id),
    )
