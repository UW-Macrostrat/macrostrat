"""Record how the ground corroborates a name match, not just whether."""

from macrostrat.database import Database
from macrostrat.schema_management import ApplicationStatus, Migration


def _has_column(db: Database, table: str, column: str) -> bool:
    return (
        db.run_query(
            """
        SELECT true FROM information_schema.columns
        WHERE table_schema = 'maps'
          AND table_name = :table AND column_name = :column
        """,
            dict(table=table, column=column),
        ).scalar()
        is not None
    )


class StratNameLocationBasisMigration(Migration):
    name = "strat-name-location-basis"
    subsystem = "maps"
    description = """
    Replace `maps.legend_strat_names.in_footprint` with `location_basis`, a
    four-value scale running column unit -> adjacent column -> footprint -> none.
    The boolean could say only whether a footprint was reached; the scale records
    which evidence was found, and the two precedence ladders order on it
    directly.

    Only reaches a database that applied `legend-strat-names` before the column
    was renamed. A database built from the current definitions already has it.
    """
    depends_on = []
    readiness_state = "ga"

    # Drops a column whose content is carried into the new one first.
    destructive = True

    def should_apply(self, db: Database) -> ApplicationStatus:
        """Preconditions checked here, not through `super()`.

        The base implementation tests postconditions first, and `all([])` is
        true, so a migration declaring none reports applied without looking.
        """
        if not _has_column(db, "legend_strat_names", "in_footprint"):
            # Either already converted, or the table predates this work.
            if _has_column(db, "legend_strat_names", "location_basis"):
                return ApplicationStatus.APPLIED
            return ApplicationStatus.CANT_APPLY
        return ApplicationStatus.CAN_APPLY
