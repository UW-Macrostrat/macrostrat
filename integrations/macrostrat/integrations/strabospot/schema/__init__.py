from macrostrat.core.migrations import Migration, exists


class StrabospotBaseSchema(Migration):
    name = "integrations-tables"
    subsystem = "integrations"
    description = """ Create tables for StraboSpot integration."""

    postconditions = [exists("integrations", "dataset", "dataset_type")]
