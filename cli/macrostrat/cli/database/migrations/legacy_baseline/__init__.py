from macrostrat.core.migrations import Migration, exists


class LegacyBaselineMigration(Migration):
    name = "legacy-baseline"
    subsystem = "core"
    description = """
    Starting from an empty database, create the baseline macrostrat schemas as of 2023-08-29.
    """
    legacy = True

    # Basic sanity check, just confirm that the first table created in the migration is present
    postconditions = [exists("maps", "sources")]