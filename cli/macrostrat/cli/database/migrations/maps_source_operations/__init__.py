from ..base import Migration, exists, view_exists

class BaselineMigration(Migration):
    name = "maps-source-operations"
    subsystem = "core"
    description = """ Create table for tracking map management operations """

    depends_on = ["baseline"]

    postconditions = [ exists("maps", "source_operations") ]
