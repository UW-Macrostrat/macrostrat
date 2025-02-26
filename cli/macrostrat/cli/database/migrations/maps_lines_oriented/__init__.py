"""
Macrostrat line orientation management
"""

from macrostrat.database import Database

from macrostrat.core.migrations import Migration, has_columns


class MapsLinesOriented(Migration):
    name = "maps-lines-oriented"
    subsystem = "maps"
    description = "Create a flag for line orientations in maps.sources table."

    depends_on = ["baseline"]

    postconditions = [has_columns("maps", "sources", "lines_oriented")]

    def apply(self, db: Database):
        db.run_sql("ALTER TABLE maps.sources ADD COLUMN lines_oriented boolean")


# Legacy maps with consistently-oriented linework that does not need to be reversed
valid_maps = [4]

# Legacy maps with consistently-oriented linework that needs to be reversed
reversed_maps = [229, 210, 74, 75, 40, 205, 154]
