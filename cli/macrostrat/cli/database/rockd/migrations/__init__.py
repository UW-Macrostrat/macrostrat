from macrostrat.core.migrations import Migration, exists


class InitialSchema(Migration):
    name = "rockd_initial_schema"
    description = "Initial schema and core tables"
    subsystem = "rockd"
    preconditions = [lambda db: True]
    postconditions = [exists("rockd", "users")]
