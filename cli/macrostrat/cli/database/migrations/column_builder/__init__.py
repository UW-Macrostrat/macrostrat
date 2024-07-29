from macrostrat.database import Database
from ..base import Migration, schema_exists

class ColumnBuilderMigration(Migration):
    name = "column-builder"
    subsystem = "core"
    description = """
    Starting from a Macrostrat v1 map database (burwell), create the macrostrat_api schema,
    then populate a number of views into the schema.
    """

    depends_on = ['macrostrat-core-v2']

    postconditions = [schema_exists('macrostrat_api')]
