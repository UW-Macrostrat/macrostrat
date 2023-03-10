from ..database import db
from sqlalchemy.exc import ProgrammingError
from rich import print


def prepare_fields(source_prefix: str):
    """Prepare empty fields for manual cleaning."""
    schema = "sources"

    source_id = get_sources_record(source_prefix)

    for table_suffix in ("_polygons", ""):
        # The old format didn't specify the 'polygons' suffix
        # but the new one does.
        table = f"{source_prefix}{table_suffix}"
        add_polygon_columns(schema, table)
        _set_source_id(schema, table, source_id)

    linework_table = f"{source_prefix}_linestrings"
    add_linework_columns(schema, linework_table)
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
    for name, type in columns.items():
        add_column(schema=schema, table_name=table_name, name=name, type=type)

    # Rename the geometry column if necessary
    if not rename_geometry:
        return

    sql = "ALTER TABLE {schema}.{table_name} RENAME COLUMN geometry TO geom".format(
        schema=schema, table_name=table_name
    )
    exec_sql(sql)


# Use dirty string formatting for now
def add_column(**kwargs):
    sql = "ALTER TABLE {schema}.{table_name} ADD COLUMN IF NOT EXISTS {name} {type}".format(
        **kwargs
    )

    exec_sql(sql)


def _set_source_id(schema, table, source_id):
    exec_sql(
        f"UPDATE {schema}.{table} SET source_id = :source_id", dict(source_id=source_id)
    )


def exec_sql(sql, params=None):
    try:
        db.session.execute(sql, params)
        db.session.commit()
        print("[dim]" + sql)
    except ProgrammingError as e:
        print("[dim red]" + str(sql))
        db.session.rollback()
