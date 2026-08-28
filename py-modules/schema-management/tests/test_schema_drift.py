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
"""

from pytest import fixture, mark
from results.dbdiff import Migration as DiffMigration

from sqlalchemy import create_engine, text

from macrostrat.database import Database
from macrostrat.schema_management import _get_results_db, get_all_schemas, get_inspector
from macrostrat.schema_management.composer import build_schema
from macrostrat.schema_management.defs import temporary_database_cluster

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


def _clone_database(db: Database) -> Database:
    """A ``CREATE DATABASE … TEMPLATE`` copy of ``db``, on the same cluster.

    Deliberately not ``macrostrat.database.utils.template_database``: its teardown
    force-drops through an engine built with ``database=None``, which in this
    environment resolves to a database that doesn't exist and raises. Nothing here
    needs dropping — the clone goes away with the throwaway cluster.

    Postgres refuses to copy a template that has other sessions attached, so the
    copy is issued from ``template1`` after releasing this process's pool and
    evicting whatever else is still on the source.
    """
    url = db.engine.url
    clone_name = f"{url.database}_clone"

    db.session.close()
    db.engine.dispose()

    admin = create_engine(
        url.set(database="template1"),
        execution_options={"isolation_level": "AUTOCOMMIT"},
    )
    with admin.connect() as conn:
        conn.execute(
            text(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity"
                " WHERE datname = :db AND pid <> pg_backend_pid()"
            ),
            {"db": url.database},
        )
        conn.execute(
            text(f'CREATE DATABASE "{clone_name}" TEMPLATE "{url.database}"')
        )

        # CREATE DATABASE … TEMPLATE does not copy per-database settings, and
        # `CREATE EXTENSION postgis_topology` sets one: search_path gains
        # `topology, tiger`. Without it the clone resolves topogeometry columns and
        # topology-referencing views differently, and the diff reports 19
        # statements of phantom drift on a database that is otherwise identical.
        for setting in conn.execute(
            text(
                "SELECT unnest(setconfig) FROM pg_db_role_setting"
                " WHERE setdatabase = (SELECT oid FROM pg_database WHERE datname = :db)"
                "   AND setrole = 0"
            ),
            {"db": url.database},
        ).scalars():
            key, _, value = setting.partition("=")
            conn.execute(text(f'ALTER DATABASE "{clone_name}" SET {key} = {value}'))
    admin.dispose()

    return Database(url.set(database=clone_name))


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
    clone = _clone_database(built_schema)
    # Reconnect the source: cloning closed its connections.
    source = Database(built_schema.engine.url)

    forward = _plan(source, clone)
    reverse = _plan(clone, source)

    assert forward == [], f"phantom drift (built → clone): {forward}"
    assert reverse == [], f"phantom drift (clone → built): {reverse}"
