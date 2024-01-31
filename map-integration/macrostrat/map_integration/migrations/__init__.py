from pathlib import Path

from macrostrat.database import Database
from macrostrat.utils import get_logger
from psycopg2.sql import Identifier

log = get_logger(__name__)


def change_legacy_table_names(db: Database):
    """
    Change polygon table names to match new names, and then run the "prepare-fields" command. This will allow previously-imported
    maps to be shown in new manual cleaning interfaces, for debugging purposes.
    """
    sql = """SELECT table_name, source_id
            FROM information_schema.tables
            JOIN maps.sources ON slug = table_name
            WHERE table_schema = 'sources'"""

    for table_name, source_id in db.run_query(sql):
        new_table_name = table_name + "_polygons"
        db.run_sql(
            "ALTER TABLE sources.{table_name} RENAME TO {new_table_name}",
            params=dict(
                table_name=Identifier(table_name),
                new_table_name=Identifier(new_table_name),
            ),
        )

        # Update the sources table to reflect the new table name
        db.run_sql(
            "UPDATE maps.sources SET primary_table = :new_table_name WHERE source_id = :source_id",
            dict(new_table_name=new_table_name, source_id=source_id),
        )
        db.session.commit()


def add_missing_table_names(db: Database):
    """For each source, check that the primary_table and primary_line_table are populated if
    the relevant tables exist."""
    all_tables = db.run_query(
        "SELECT slug, primary_table, primary_line_table FROM maps.sources WHERE slug IS NOT NULL"
    ).fetchall()

    for row in all_tables:
        _add_missing_table_name(db, row, "primary_table", row.slug + "_polygons")
        _add_missing_table_name(
            db, row, "primary_line_table", row.slug + "_linestrings"
        )

        db.session.commit()


# TODO: integrate this with the Macrostrat database module.
def table_exists(db: Database, table_name: str, schema: str = "public") -> bool:
    """Check if a table exists in a PostgreSQL database."""
    sql = """SELECT EXISTS (
        SELECT FROM information_schema.tables 
        WHERE table_schema = :schema
          AND table_name = :table_name
    );"""

    return db.run_query(sql, dict(schema=schema, table_name=table_name)).scalar()


def _add_missing_table_name(
    db: Database, row: object, column_name: str, new_table_name: str
):
    slug = row.slug
    table_name = getattr(row, column_name)

    if table_name == new_table_name:
        return

    if table_exists(db, new_table_name, schema="sources"):
        print(f"Updating {slug} {column_name} to {new_table_name}")
        db.run_sql(
            "UPDATE maps.sources SET {column_name} = :table_name WHERE slug = :slug",
            params=dict(
                table_name=new_table_name,
                slug=slug,
                column_name=Identifier(column_name),
            ),
        )
    else:
        log.warning(
            f"Expected {column_name} to be {new_table_name}, but was {table_name}"
        )


def change_column_names(db: Database):
    sql = Path(__file__).parent / "change-column-names.sql"
    db.run_sql(sql)


def run_migrations(db: Database):
    """Run database migrations for map ingestion."""
    change_column_names(db)
    change_legacy_table_names(db)
    add_missing_table_names(db)
