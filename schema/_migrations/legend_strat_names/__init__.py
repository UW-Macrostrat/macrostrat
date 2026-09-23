"""Move stratigraphic-name matches onto legend grain."""

from macrostrat.database import Database
from macrostrat.schema_management import ApplicationStatus, Migration


def _relkind(db: Database, schema: str, name: str) -> str | None:
    """`r` for an ordinary table, `v` for a view, None when absent.

    `exists()` from `inspect_utils` cannot carry this migration: the relation
    keeps its name across the switchover, so existence says nothing about whether
    the work has been done.
    """
    return db.run_query(
        """
        SELECT c.relkind FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = :schema AND c.relname = :name
        """,
        dict(schema=schema, name=name),
    ).scalar()


class LegendStratNamesMigration(Migration):
    name = "legend-strat-names"
    subsystem = "maps"
    description = """
    Move stratigraphic-name matches onto `maps.legend_strat_names`, at legend
    grain with structured evidence, leaving `maps.map_strat_names` as a view
    under its old name so the v2 API and the precedence ladders are untouched.
    Carries the manual matches; the rest is matcher output.

    Run before `schema apply` on an existing database -- a plan taken while
    `map_strat_names` is still a table cannot create the view beside it.
    """
    # Deliberately empty: `depends_on` is matched against migrations completed in
    # the same run, so naming one that is not loaded means this never applies.
    depends_on = []
    readiness_state = "ga"

    # Renames a table and moves 152 rows. Nothing is dropped and no row is lost,
    # so this does not need `--data`.
    destructive = False

    def should_apply(self, db: Database) -> ApplicationStatus:
        """Applied once `maps.map_strat_names` is a view.

        Preconditions are checked here rather than through `super()`: the base
        implementation tests postconditions first, and `all([])` is true, so a
        migration that declares none is reported applied without anything being
        looked at.
        """
        kind = _relkind(db, "maps", "map_strat_names")
        if kind == "v":
            return ApplicationStatus.APPLIED
        if kind != "r":
            # Absent entirely: not a database this applies to.
            return ApplicationStatus.CANT_APPLY
        # Still a table. The SQL clears any debris from a run that failed partway
        # before doing the work, so this is safe to report even mid-recovery.
        for required in ("legend", "map_legend"):
            if _relkind(db, "maps", required) is None:
                return ApplicationStatus.CANT_APPLY
        return ApplicationStatus.CAN_APPLY
