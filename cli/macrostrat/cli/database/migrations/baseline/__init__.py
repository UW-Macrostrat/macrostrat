from ..base import Migration

class BaselineMigration(Migration):
    name = "00-baseline"
    subsystem = "core"
    description = """
    Starting from an empty database, create the baseline macrostrat schemas as of 2023-08-29. 
    """
    # Basic sanity check, just confirm that the first table created in the migration is present
    expected_tables = ["carto.flat_large"]
