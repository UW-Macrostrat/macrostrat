from macrostrat.schema_management import Migration, view_exists


class UsageStatsConsolidationMigration(Migration):
    name = "usage-stats-consolidation"
    subsystem = "core"
    readiness_state = "beta"
    description = """
    Move the tileserver request indexes into the consolidated `usage_stats`
    schema, renaming them with a `tileserver_` prefix so the schema can host
    other usage pipelines alongside them.
    """

    # The pre-2026-03 legacy lineage (~93k day rows back to 2018, ~1.25M
    # location rows) has no surviving source logs and cannot be re-derived,
    # so this moves the tables rather than rebuilding them.
    destructive = True

    # Applied once the old names resolve to *views* over the new tables.
    #
    # Deliberately not keyed on the new tables existing: the declarative
    # `usage-stats` chunk also creates them, so an out-of-order apply
    # (chunk before migration) would otherwise look "already migrated" and
    # strand the legacy rows in the old schema. The view only appears once
    # the rename has actually happened.
    postconditions = [view_exists("tileserver_stats", "day_index", "location_index")]
