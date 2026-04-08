from psycopg2.sql import Identifier

from macrostrat.database import Database
from macrostrat.schema_management import Migration, exists


class UserSavedLocationsMigration(Migration):
    name = "user-saved-locations"
    subsystem = "user_features"
    description = """
    Create user-saved-locations db schema, permissions, and views.
    """

    # depends_on = ["baseline", "macrostrat-mariadb"]
    preconditions = [exists("macrostrat_auth", "user")]

    postconditions = [
        exists("user_features", "user_locations"),
        exists("user_features", "location_tags"),
        exists("user_features", "location_tags_intersect"),
    ]
