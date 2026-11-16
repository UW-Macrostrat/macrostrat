"""Object selection for `schema sync --object`: what each statement names, and matching."""

from pytest import fixture, mark

from macrostrat.schema_management import SchemaDefinition
from macrostrat.schema_management.grants import grant_objects
from macrostrat.schema_management.procedures import procedure_objects
from macrostrat.schema_management.seed_data import data_objects
from macrostrat.schema_management.selection import ObjectName, ObjectSelector
from macrostrat.schema_management.views import rebuild_views, view_objects

# --- a selected view's recreate cascades past the selection (database) ----

SCHEMA = "sync_selection_test"


@fixture
def scratch_schema(empty_db):
    empty_db.run_sql(f"CREATE SCHEMA {SCHEMA}", raise_errors=True)
    try:
        yield empty_db
    finally:
        empty_db.run_sql(f"DROP SCHEMA {SCHEMA} CASCADE", raise_errors=True)


@mark.docker
def test_cascade_dropped_dependents_are_restored(scratch_schema, tmp_path):
    db = scratch_schema
    db.run_sql(f"CREATE VIEW {SCHEMA}.base AS SELECT 1 AS a", raise_errors=True)
    db.run_sql(
        f"CREATE VIEW {SCHEMA}.dep AS SELECT a FROM {SCHEMA}.base", raise_errors=True
    )
    db.run_sql(f"CREATE VIEW {SCHEMA}.other AS SELECT 1 AS x", raise_errors=True)

    # `base` loses its column, so it can only be dropped and recreated.
    (tmp_path / "f.sql").write_text(
        f"CREATE VIEW {SCHEMA}.base AS SELECT 1 AS a0, 2 AS a;\n"
        f"CREATE VIEW {SCHEMA}.dep AS SELECT a FROM {SCHEMA}.base;\n"
        f"CREATE VIEW {SCHEMA}.other AS SELECT 2 AS x;\n"
    )
    chunk = SchemaDefinition(name="t", provides=[tmp_path])
    report = rebuild_views(db, [chunk], ObjectSelector.parse([f"{SCHEMA}.base"]))

    assert report.total == 1
    assert report.recreated == [f"{SCHEMA}.base"]
    assert report.restored == [f"{SCHEMA}.dep"]
    assert db.run_query(f"SELECT a FROM {SCHEMA}.dep").scalar() == 2
    # Outside the selection and never dropped, so left as it was.
    assert db.run_query(f"SELECT x FROM {SCHEMA}.other").scalar() == 1
