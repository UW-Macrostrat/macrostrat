from ..database import db
from pathlib import Path
from psycopg2.sql import Identifier


def change_legacy_table_names():
    """
    Change polygon table names to match new names, and then run the "prepare-fields" command. This will allow previously-imported
    maps to be shown in new manual cleaning interfaces, for debugging purposes.
    """
    sql = """SELECT table_name, source_id
            FROM information_schema.tables
            JOIN maps.sources ON slug = table_name
            WHERE table_schema = 'sources'"""

    for table_name, source_id in db.session.execute(sql):
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
            params=dict(new_table_name=new_table_name, source_id=source_id),
        )


def change_column_names():
    sql = Path(__file__).parent / "change-column-names.sql"
    db.run_sql(sql)


def run_migrations():
    """Run database migrations for map ingestion."""
    change_column_names()
    change_legacy_table_names()
