from macrostrat.core.migrations import Migration, exists


class MapsSoureOperationsMigration(Migration):
    name = "maps-source-operations"
    subsystem = "core"
    description = """ Create table for tracking map management operations """

    depends_on = ["api-v3"]

    postconditions = [exists("maps", "source_operations")]
