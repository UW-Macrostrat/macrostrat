from psycopg2.sql import Identifier

from macrostrat.core.migrations import Migration, _not, custom_type_exists
from macrostrat.database import Database


class MeasurementClassCustomTypeMigration(Migration):
    name = "measurement-class-custom-type"
    description = """
    Relocate custom type that drives the maps schema
    """

    readiness_state = "ga"

    postconditions = [
        custom_type_exists("macrostrat", "measurement_class"),
        _not(custom_type_exists("public", "measurement_class")),
    ]

    preconditions = [custom_type_exists("macrostrat", "measurement_class")]
