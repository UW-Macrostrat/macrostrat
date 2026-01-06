from psycopg2.sql import Identifier

from macrostrat.core.migrations import ApplicationStatus, Migration
from macrostrat.database import Database

MATCHES_SLUG_SQL = """
SELECT table_name
FROM information_schema.tables
JOIN maps.sources ON slug = table_name
WHERE table_schema = 'sources'"""


class MapSourceSlugsMigration(Migration):
    name = "map-source-slug"
    subsystem = "core"
    description = """
    Starting from a Macrostrat v1 map database (burwell), create the maps.sources.slugs column,
    then add a '_polygons' suffix to the associated primary table name in the sources schema.
    """

    depends_on = ["baseline"]
    readiness_state = "ga"

    destructive = True

    def apply(self, db: Database):
        # First, run sql migrations to add the slugs column and rename primary_table
        super().apply(db)

        # Then, manually rename all primary_tables
        self._rename_primary_tables(db)

    def _rename_primary_tables(self, db: Database):
        for (table_name,) in db.run_query(MATCHES_SLUG_SQL):
            new_table_name = table_name + "_polygons"
            db.run_sql(
                "ALTER TABLE sources.{table_name} RENAME TO {new_table_name}",
                params=dict(
                    table_name=Identifier(table_name),
                    new_table_name=Identifier(new_table_name),
                ),
            )

    def should_apply(self, db: Database):
        insp = db.inspector

        # Check that maps.sources exists, and has a 'slug' column
        if not insp.has_table("sources", "maps"):
            return ApplicationStatus.CANT_APPLY

        col_names = [c["name"] for c in insp.get_columns("sources", "maps")]
        if not "slug" in col_names:
            return ApplicationStatus.CAN_APPLY

        # Check that the primary_table column has appropriate values
        non_polygon_table_names = db.run_query(
            "SELECT primary_table FROM maps.sources WHERE primary_table NOT LIKE '%_polygons' AND primary_table != 'unknown'"
        )
        if non_polygon_table_names.first() is not None:
            return ApplicationStatus.CAN_APPLY

        # Check that tables in sources match primary_table instead of slug
        non_polygon_tables = db.run_query(MATCHES_SLUG_SQL)
        if non_polygon_tables.first() is not None:
            return ApplicationStatus.CAN_APPLY

        return ApplicationStatus.APPLIED
