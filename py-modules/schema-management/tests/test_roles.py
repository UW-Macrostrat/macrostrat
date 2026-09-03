"""Tests for the role-rebuild category of `macrostrat schema sync`.

Database roles are cluster objects, so the schema diff cannot see them; without
this category, a diff-built database has none of the roles its grants name.
"""

from psycopg.errors import DuplicateObject, InsufficientPrivilege
from sqlalchemy.exc import ProgrammingError

from macrostrat.schema_management.composer import SchemaDefinition
from macrostrat.schema_management.roles import (
    iter_role_statements,
    rebuild_roles,
    role_already_exists,
    role_statements_in,
)

_PROBE_ROLE = "macrostrat_sync_probe"


def _role_exists(db, name: str) -> bool:
    return bool(
        db.run_query(
            "SELECT 1 FROM pg_roles WHERE rolname = :name", dict(name=name)
        ).scalar()
    )


def test_role_statements_in_finds_role_creation_only():
    sql = """
    CREATE ROLE macrostrat_admin;
    GRANT macrostrat_admin TO "macrostrat-admin";
    -- a login role
    CREATE ROLE postgrest LOGIN NOINHERIT NOCREATEDB NOCREATEROLE NOSUPERUSER;
    CREATE USER logs_writer;
    CREATE TABLE s.t (id int);
    CREATE SCHEMA s;
    ALTER ROLE web_anon NOLOGIN;   -- an alteration, not a creation
    """
    found = list(role_statements_in(sql))
    assert len(found) == 3
    assert found[0].startswith("CREATE ROLE macrostrat_admin")
    assert found[2].startswith("CREATE USER logs_writer")


def test_role_already_exists_reads_the_drivers_sqlstate():
    """Against the real driver exception, not a stand-in.

    psycopg 3 spells the code `sqlstate` (psycopg 2 `pgcode`), so a check written
    for one attribute silently classifies every duplicate as a failure.
    """

    def wrapped(err):
        return ProgrammingError("CREATE ROLE x", {}, err)

    assert role_already_exists(wrapped(DuplicateObject("role x already exists")))
    assert not role_already_exists(wrapped(InsufficientPrivilege("permission denied")))
    assert not role_already_exists(RuntimeError("something else"))


def test_sync_creates_a_missing_role(schema_harness, tmp_path):
    """A declared role absent from the cluster is created; a second pass skips it.

    The role is declared by a chunk this test owns rather than by dropping a real
    one: declared roles accumulate grants across the shared cluster (dropping
    `rockd_reader` fails on its privileges for `audit.record_history`), so
    removing one to manufacture the "missing" case is neither reliable nor safe.
    """
    db = schema_harness.load_schema(target="macrostrat")
    sql = tmp_path / "01-roles.sql"
    sql.write_text(
        f"CREATE ROLE {_PROBE_ROLE} NOLOGIN;\n"
        f"GRANT {_PROBE_ROLE} TO macrostrat;  -- a grant, not a creation\n"
    )
    chunks = [SchemaDefinition(name="probe-roles", provides=[sql])]

    assert not _role_exists(db, _PROBE_ROLE)
    try:
        created = rebuild_roles(db, chunks)
        assert (created.total, created.applied) == (1, 1)
        assert created.skipped == [] and created.failed == []
        assert _role_exists(db, _PROBE_ROLE)

        # Applied again, the role is already there: noted, not failed.
        again = rebuild_roles(db, chunks)
        assert (again.total, again.applied, again.failed) == (1, 0, [])
        assert len(again.skipped) == 1
    finally:
        db.run_sql(f"DROP ROLE IF EXISTS {_PROBE_ROLE}", raise_errors=False)


def test_sync_steps_over_roles_the_build_already_created(schema_harness):
    """Against a provisioned database the sweep is a whole-cluster no-op.

    Each statement gets its own transaction and is rolled back on failure, so the
    duplicates neither abort the run nor land in the failure report. Nothing is
    written, so there is nothing to roll back — and a sweep must not be wrapped
    in `db.transaction` anyway: with the session already in a transaction,
    `_execute_one` cannot open its own and rolls back the caller's instead.
    """
    db = schema_harness.load_schema(target="macrostrat")
    chunks = schema_harness.chunks()

    report = rebuild_roles(db, chunks)

    assert report.total == len(list(iter_role_statements(chunks)))
    assert report.total > 0
    assert report.failed == []
    assert len(report.skipped) == report.total
