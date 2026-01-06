from macrostrat.core.migrations import Migration, exists, view_exists


class PointsMigration(Migration):
    name = "points"
    subsystem = "core"
    description = """ Move the points table to schema maps """
    readiness_state = "ga"
    depends_on = ["baseline"]

    postconditions = [exists("maps", "points"), view_exists("points", "points")]
