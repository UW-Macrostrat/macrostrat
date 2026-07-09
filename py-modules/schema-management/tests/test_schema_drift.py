"""Structural-drift test for the declarative schema.

Asserts the "empty-build → empty-plan" invariant: a freshly built declarative
schema matches its own ideal, i.e. ``plan`` produces no statements in either
direction. A stray statement means the build is non-deterministic or an object
exists that isn't reproducible from the declarative source.

(Migration no-op-ness on a fresh build is covered separately by
``test_database_migrations``.)
"""

from pytest import mark
from results.dbdiff import Migration as DiffMigration

from macrostrat.schema_management import _get_results_db, get_all_schemas, get_inspector
from macrostrat.schema_management.composer import build_schema
from macrostrat.schema_management.defs import planning_database, test_database_cluster

_EXCLUDED_SCHEMAS = ["sources", "tiger", "tiger_data"]
# Topology is local-only and function-built; "development" is a full,
# topology-free declarative build.
_ENV = "development"


def _plan(from_db, target_db) -> list[str]:
    """Statements to turn ``from_db`` into ``target_db`` — the same machinery as
    the ``macrostrat schema plan`` command."""
    schemas = get_all_schemas(target_db, excluded_schemas=_EXCLUDED_SCHEMAS)
    r_from = _get_results_db(from_db)
    r_target = _get_results_db(target_db)

    m = DiffMigration(r_from, r_target)
    m.changes.i_from = get_inspector(r_from, schemas)
    m.changes.i_target = get_inspector(r_target, schemas)
    m.changes.ignore_extension_versions = True
    m.set_safety(False)
    m.add_all_changes(privileges=True)
    return list(m.statements)


@mark.docker
@mark.slow
def test_declarative_build_has_no_drift():
    """A declarative build matches a fresh ideal — empty plan both ways."""
    with (
        test_database_cluster(username="macrostrat_admin") as built,
        planning_database(_ENV) as ideal,
    ):
        build_schema(built, _ENV)

        forward = _plan(built, ideal)
        reverse = _plan(ideal, built)

        assert forward == [], f"drift (built → ideal): {forward}"
        assert reverse == [], f"drift (ideal → built): {reverse}"
