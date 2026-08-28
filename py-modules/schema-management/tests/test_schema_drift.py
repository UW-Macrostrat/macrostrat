"""Plan-fidelity test for the schema diff.

``plan`` must report nothing between two databases that are structurally identical.
The two sides here are a declarative build and a ``CREATE DATABASE … TEMPLATE``
clone of it — identical by construction — so any statement in the plan is a false
positive in the diff machinery, which is what a user of ``macrostrat db plan`` would
see as phantom drift.

This replaced a build-vs-build comparison. Both of that test's sides went through
``build_schema`` (``apply_schema_for_environment`` is a thin wrapper over it), so it
could only ever catch non-determinism between two runs — and it paid two clusters
and two full builds for it. The clone cannot catch that, but it does exercise the
diff against every object class the schema actually defines.

The build is deliberately *unoptimized* rather than reusing ``schema_harness``: the
harness skips indexes and grants, and those (partial and expression indexes
especially) are the objects most likely to round-trip badly through the diff.

``template_database`` copies the source's database-level settings (macrostrat.database
>= 4.6.0). Without that the clone loses the ``search_path`` PostGIS sets for
``topology``, and the diff reports 19 statements of drift between databases that are
otherwise identical.
"""

from pytest import fixture, mark
from results.dbdiff import Migration as DiffMigration

from macrostrat.database import Database
from macrostrat.database.utils import template_database
from macrostrat.schema_management import _get_results_db, get_all_schemas, get_inspector
from macrostrat.schema_management.composer import build_schema
from macrostrat.schema_management.defs import temporary_database_cluster

_EXCLUDED_SCHEMAS = ["sources", "tiger", "tiger_data"]
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


@fixture(scope="module")
def built_schema():
    """One full, unoptimized declarative build for this module."""
    with temporary_database_cluster(username="macrostrat_admin") as db:
        build_schema(db, _ENV)
        yield db


@mark.docker
@mark.slow
def test_plan_is_empty_between_identical_databases(built_schema):
    """Empty plan both ways between a build and a clone of it."""
    source_url = built_schema.engine.url
    with template_database(source_url, close_source_connections=True) as clone_engine:
        # Reconnect the source rather than reusing the fixture's Database: cloning
        # evicts the source's sessions, leaving its pool and session dead.
        source = Database(source_url)
        clone = Database(clone_engine.url)

        forward = _plan(source, clone)
        reverse = _plan(clone, source)

    assert forward == [], f"phantom drift (built → clone): {forward}"
    assert reverse == [], f"phantom drift (clone → built): {reverse}"
