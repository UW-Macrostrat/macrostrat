from psycopg2.sql import Identifier

from macrostrat.core.migrations import Migration, exists
from macrostrat.database import Database


class UserSavedLocationsMigration(Migration):
    name = "user-saved-locations"
    subsystem = "user_features"
    description = """
    Create user-saved-locations db schema, permissions, and views.
    """

    # depends_on = ["baseline", "macrostrat-mariadb"]

    preconditions = [exists("macrostrat_auth", "user")]

    postconditions = [
        exists(
            "user_features", "user_locations, location_tags, location_tags_intersect"
        ),
    ]
