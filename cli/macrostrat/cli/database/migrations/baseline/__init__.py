from ..base import Migration, exists, not_exists

class BaselineMigration(Migration):
    name = "baseline"
    subsystem = "core"
    description = """
    Starting from an empty database, create the baseline macrostrat schemas as of 2023-08-29. 
    """

    # Basic sanity check, just confirm that the first table created in the migration is present
    preconditions = [not_exists("carto", "flat_large")]
    postconditions = [exists("carto", "flat_large")]
