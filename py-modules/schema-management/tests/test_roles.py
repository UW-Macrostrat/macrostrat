"""Tests for the role-rebuild category of `macrostrat schema sync`.

Database roles are cluster objects, so the schema diff cannot see them; without
this category, a diff-built database has none of the roles its grants name.
"""

from macrostrat.schema_management.roles import (
    iter_role_statements,
    rebuild_roles,
    role_statements_in,
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


def test_sync_restores_a_dropped_role(schema_harness):
    """A role missing from the cluster is re-created; the rest are stepped over."""
    db = schema_harness.load_schema(target="macrostrat")
    chunks = schema_harness.chunks()

    def exists(name: str) -> bool:
        return bool(
            db.run_query(
                "SELECT 1 FROM pg_roles WHERE rolname = :name", dict(name=name)
            ).scalar()
        )

    assert exists("rockd_reader")  # the declarative build created it
    db.run_sql("DROP ROLE rockd_reader", raise_errors=True)
    assert not exists("rockd_reader")

    report = rebuild_roles(db, chunks)
    assert exists("rockd_reader")
    assert report.failed == []
    # Everything else was already there: noted as skipped, not failed.
    assert len(report.skipped) == report.total - 1
    assert report.total == len(list(iter_role_statements(chunks)))
