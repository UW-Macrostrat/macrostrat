from macrostrat.database import Database
from ..base import Migration

from psycopg2.sql import Identifier

MATCHES_SLUG_SQL = """
SELECT table_name
FROM information_schema.tables
JOIN maps.sources ON slug = table_name
WHERE table_schema = 'sources'"""

class ColumnBuilderMigration(Migration):
    name = "column-builder"
    subsystem = "core"
    description = """
    Starting from a Macrostrat v1 map database (burwell), create the macrostrat_api schema,
    then populate a number of views into the schema.
    """

    depends_on = ['macrostrat-core-v2']

    def should_apply(self, db: Database):
        return not db.inspector.has_schema('macrostrat_api')
