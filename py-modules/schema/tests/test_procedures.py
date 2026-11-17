"""Procedure rebuild: statement parsing, and recreating what CREATE OR REPLACE refuses."""

from pytest import fixture, mark

from macrostrat.schema_management import SchemaDefinition
from macrostrat.schema_management.sync.procedures import (
    _as_create_or_replace,
    procedure_statements_in,
    rebuild_procedures,
)

# --- drop-and-recreate (database) -----------------------------------------

SCHEMA = "sync_recreate_test"


@fixture
def scratch_schema(empty_db):
    """A throwaway schema in the shared test database, dropped afterwards so the
    harness's drift comparison never sees it."""
    empty_db.run_sql(f"CREATE SCHEMA {SCHEMA}", raise_errors=True)
    try:
        yield empty_db
    finally:
        empty_db.run_sql(f"DROP SCHEMA {SCHEMA} CASCADE", raise_errors=True)


def _sync(db, tmp_path, sql: str):
    (tmp_path / "f.sql").write_text(sql)
    chunk = SchemaDefinition(name="t", provides=[tmp_path])
    return rebuild_procedures(db, [chunk])


def _scalar(db, sql: str):
    return db.run_query(sql).scalar()


@mark.docker
def test_a_renamed_parameter_is_recreated_with_its_grants(scratch_schema, tmp_path):
    db = scratch_schema
    db.run_sql(
        f"CREATE FUNCTION {SCHEMA}.f(_a integer) RETURNS integer"
        " LANGUAGE sql AS $$ SELECT _a $$",
        raise_errors=True,
    )
    db.run_sql(
        f"REVOKE ALL ON FUNCTION {SCHEMA}.f(integer) FROM PUBLIC", raise_errors=True
    )
    db.run_sql(
        f"GRANT EXECUTE ON FUNCTION {SCHEMA}.f(integer) TO pg_read_all_data",
        raise_errors=True,
    )

    report = _sync(
        db,
        tmp_path,
        f"CREATE OR REPLACE FUNCTION {SCHEMA}.f(_b integer) RETURNS integer"
        " LANGUAGE sql AS $$ SELECT _b + 1 $$;",
    )

    assert report.failures == [] and len(report.recreated) == 1
    assert _scalar(db, f"SELECT {SCHEMA}.f(1)") == 2
    assert _scalar(
        db, f"SELECT proargnames FROM pg_proc WHERE oid = '{SCHEMA}.f'::regproc"
    ) == ["_b"]
    granted = "SELECT has_function_privilege('{}', '{}.f(integer)', 'EXECUTE')"
    assert _scalar(db, granted.format("pg_read_all_data", SCHEMA)) is True
    assert _scalar(db, granted.format("pg_monitor", SCHEMA)) is False


@mark.docker
def test_a_function_with_dependents_keeps_its_old_definition(scratch_schema, tmp_path):
    db = scratch_schema
    db.run_sql(
        f"CREATE FUNCTION {SCHEMA}.f(_a integer) RETURNS integer"
        " LANGUAGE sql AS $$ SELECT _a $$",
        raise_errors=True,
    )
    db.run_sql(f"CREATE VIEW {SCHEMA}.v AS SELECT {SCHEMA}.f(1)", raise_errors=True)

    report = _sync(
        db,
        tmp_path,
        f"CREATE OR REPLACE FUNCTION {SCHEMA}.f(_b integer) RETURNS integer"
        " LANGUAGE sql AS $$ SELECT _b + 1 $$;",
    )

    assert report.recreated == [] and len(report.failures) == 1
    assert "depend" in report.failures[0].message
    assert _scalar(db, f"SELECT {SCHEMA}.f(1)") == 1


@mark.docker
def test_an_overloaded_name_is_not_guessed_at(scratch_schema, tmp_path):
    db = scratch_schema
    for args in ("_a integer", "_a text"):
        db.run_sql(
            f"CREATE FUNCTION {SCHEMA}.f({args}) RETURNS integer"
            " LANGUAGE sql AS $$ SELECT 1 $$",
            raise_errors=True,
        )

    report = _sync(
        db,
        tmp_path,
        f"CREATE OR REPLACE FUNCTION {SCHEMA}.f(_b integer) RETURNS integer"
        " LANGUAGE sql AS $$ SELECT 2 $$;",
    )

    assert report.recreated == [] and len(report.failures) == 1
    assert "2 signatures" in report.failures[0].message
    assert _scalar(db, f"SELECT {SCHEMA}.f(1)") == 1
