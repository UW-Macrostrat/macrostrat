"""
Macrostrat line orientation management
"""

from macrostrat.core.migrations import Migration, has_columns
from macrostrat.database import Database

_has_column = has_columns("maps", "sources", "lines_oriented")


class MapsLinesOriented(Migration):
    name = "maps-lines-oriented"
    subsystem = "maps"
    description = "Create a flag for line orientations in maps.sources table."

    depends_on = ["baseline", "map-source-slug"]

    postconditions = [_has_column]

    def apply(self, db: Database):
        db.run_sql("ALTER TABLE maps.sources ADD COLUMN lines_oriented boolean")
