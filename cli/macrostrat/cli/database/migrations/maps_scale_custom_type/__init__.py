from macrostrat.database import Database
from psycopg2.sql import Identifier

from macrostrat.core.migrations import Migration, custom_type_exists, _not, _any


class MapsScaleCustomTypeMigration(Migration):
    name = "maps-scale-type"
    subsystem = "maps"
    description = """
    Relocate custom type that drives the maps schema
    """

    depends_on = ["baseline", "macrostrat-mariadb"]

    postconditions = [
        custom_type_exists("maps", "map_scale"),
        _not(custom_type_exists("public", "map_scale")),
    ]

    preconditions = [
        _any(
            custom_type_exists(s, "map_scale")
            for s in ["macrostrat_backup", "macrostrat", "public"]
        )
    ]

    def apply(self, db: Database):
        # Handle edge case where the MariaDB migration has already been applied
        db.run_sql("ALTER TYPE macrostrat_backup.map_scale SET SCHEMA macrostrat")
        db.run_sql("ALTER TYPE macrostrat.map_scale SET SCHEMA maps")
        db.run_sql("ALTER TYPE public.map_scale SET SCHEMA maps")
        for schema in ["macrostrat_backup", "macrostrat", "public"]:
            db.run_sql(
                "DROP TYPE IF EXISTS {schema}.map_scale",
                dict(schema=Identifier(schema)),
            )
