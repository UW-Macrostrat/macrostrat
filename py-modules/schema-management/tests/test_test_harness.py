"""Tests for the progressive, chunk-based test harness.

The key acceptance check: the harness's minimal build reproduces the legacy
"macrostrat schema only" behavior (``target="macrostrat"`` with the optimize
transform), and can then be grown to a full build in place.
"""

from types import SimpleNamespace

from pytest import mark
from results.dbdiff import Migration as DiffMigration

from macrostrat.schema_management import (
    _get_results_db,
    apply_schema_for_environment,
    get_all_schemas,
    get_inspector,
)
from macrostrat.schema_management.defs import (
    SCHEMA_FILTERED_QUERIES,
    SYSTEM_SCHEMAS,
    OurPostgreSQL,
    temporary_database_cluster,
)
from macrostrat.schema_management.test_harness import (
    DatabaseTestHarness,
    optimize_transform,
)

# Excluded from schema comparison exactly as the `plan` command does.
_EXCLUDED_SCHEMAS = ["sources", "tiger", "tiger_data"]

# Topology is local-only; "development" gives a full-but-topology-free build.
_ENV = "development"


def _diff_statements(from_db, target_db) -> list[str]:
    """Statements to turn ``from_db`` into ``target_db`` (empty if equal)."""
    schemas = get_all_schemas(target_db, excluded_schemas=_EXCLUDED_SCHEMAS)
    r_from = _get_results_db(from_db)
    r_target = _get_results_db(target_db)

    m = DiffMigration(get_inspector(r_from, schemas), get_inspector(r_target, schemas))
    m.changes.ignore_extension_versions = True
    m.set_safety(False)
    m.add_all_changes(privileges=True)
    return list(m.statements)


@mark.docker
@mark.slow
def test_harness_replicates_macrostrat_schema_only():
    with (
        temporary_database_cluster(username="macrostrat_admin") as db_legacy,
        temporary_database_cluster(username="macrostrat_admin") as db_harness,
    ):
        # Legacy minimal build via the public API, with the optimize transform.
        apply_schema_for_environment(
            db_legacy,
            _ENV,
            target="macrostrat",
            transform_statement=optimize_transform,
        )

        # Harness minimal build.
        harness = DatabaseTestHarness(db_harness, env=_ENV, optimize=True)
        harness.load_schema(target="macrostrat")

        # 1. The harness minimal build equals the legacy minimal build.
        assert _diff_statements(db_legacy, db_harness) == []
        assert _diff_statements(db_harness, db_legacy) == []

        # 2. It really built the macrostrat schema (and cut before the rest).
        minimal_schemas = set(get_all_schemas(db_harness))
        assert "macrostrat" in minimal_schemas

        # 3. Progressive continuation in place: completing the build adds schema
        #    without re-running the already-applied core files.
        harness.load_schema()
        full_schemas = set(get_all_schemas(db_harness))
        assert minimal_schemas < full_schemas


# Stand-ins for the two connections the inspector takes; it builds its queries
# as `text()` clauses over SQLAlchemy and as strings over psycopg.
_CONNECTIONS = {
    "sqlalchemy": SimpleNamespace(dialect=SimpleNamespace(server_version_info=(17,))),
    "psycopg": SimpleNamespace(
        connection=SimpleNamespace(pgconn=SimpleNamespace(server_version=170000))
    ),
}


class _QueriesOnly(OurPostgreSQL):
    """The inspector's catalog queries, without running them."""

    def load_all(self):
        pass


@mark.parametrize("connection", _CONNECTIONS)
def test_catalog_queries_can_exclude_schemas(connection):
    """`results` keeps the system-schema list the exclusion is spliced into.

    If an upgrade rewords it, inspection silently reads every schema again.
    """
    inspector = _QueriesOnly(_CONNECTIONS[connection])

    def sql(attr):
        return str(getattr(inspector, attr))

    for attr in SCHEMA_FILTERED_QUERIES:
        assert SYSTEM_SCHEMAS in sql(attr), attr

    inspector.exclude_schemas(["sources", "o'brien"])
    for attr in SCHEMA_FILTERED_QUERIES:
        assert f"{SYSTEM_SCHEMAS}, 'sources', 'o''brien'" in sql(attr), attr
