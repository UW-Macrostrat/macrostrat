"""Fill the flattened rank tree, which the lexicon rebuild maintains thereafter."""

from macrostrat.database import Database
from macrostrat.schema_management import ApplicationStatus, Migration, exists


class StratNameTreeMigration(Migration):
    name = "strat-name-tree"
    subsystem = "core"
    description = """
    Populate `macrostrat.lookup_strat_name_tree` from the current lexicon.

    The table is declarative, so a schema apply creates it empty, and unit
    matching and the legend lookup both join it — so until it holds rows they
    match nothing. The lexicon rebuild repopulates it from then on; this is the
    one fill an existing database needs.
    """

    depends_on = []
    readiness_state = "ga"
    destructive = False

    preconditions = [
        exists("macrostrat", "lookup_strat_name_tree", "lookup_strat_names")
    ]

    def should_apply(self, db: Database) -> ApplicationStatus:
        if not all(cond(db) for cond in self.preconditions):
            return ApplicationStatus.CANT_APPLY
        counts = db.run_query(
            """
            SELECT
              (SELECT count(*) FROM macrostrat.lookup_strat_name_tree) AS tree,
              (SELECT count(*) FROM macrostrat.lookup_strat_names) AS lexicon
            """
        ).one()
        if counts.lexicon == 0 or counts.tree == counts.lexicon:
            return ApplicationStatus.APPLIED
        return ApplicationStatus.CAN_APPLY
