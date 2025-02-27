from macrostrat.core.migrations import Migration, exists


class IntegrationsBaseSchema(Migration):
    name = "integrations-tables"
    subsystem = "integrations"
    description = """ Create tables for StraboSpot integration."""

    postconditions = [
        exists("integrations", "dataset", "dataset_type"),
        exists("macrostrat_api", "dataset", "dataset_type"),
    ]
