from macrostrat.core.migrations import Migration, exists


class StrabospotBaseSchema(Migration):
    name = "strabospot-integration"
    subsystem = "strabospot-integration"
    description = """ Create tables for StraboSpot integration."""

    postconditions = [exists("strabospot", "featured_spots")]
