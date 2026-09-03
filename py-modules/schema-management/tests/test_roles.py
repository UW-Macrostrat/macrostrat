"""Tests for the role-rebuild category of `macrostrat schema sync`.

Database roles are cluster objects, so the schema diff cannot see them; without
this category, a diff-built database has none of the roles its grants name.
"""

from pytest import mark

from macrostrat.schema_management.composer import build_schema, selected_chunks
from macrostrat.schema_management.defs import temporary_database_cluster
from macrostrat.schema_management.roles import (
    guard_existing,
    rebuild_roles,
    role_name_in,
    role_statements_in,
)

_ENV = "development"


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
    assert [role_name_in(f) for f in found] == [
        "macrostrat_admin",
        "postgrest",
        "logs_writer",
    ]


def test_role_name_in_unquotes_dashed_roles():
    # The Postgres operator creates dash-named roles, which the schema shadows.
    assert role_name_in('CREATE ROLE "macrostrat-admin";') == "macrostrat-admin"
    assert role_name_in("CREATE TABLE s.t (id int);") is None


def test_guard_existing_wraps_creation_in_an_existence_check():
    guarded = guard_existing("CREATE ROLE web_anon NOLOGIN;")
    assert "pg_roles" in guarded
    assert "'web_anon'" in guarded
    assert "CREATE ROLE web_anon NOLOGIN" in guarded
    # No `%`-style formatting: a bare % is read as a bind parameter downstream.
    assert "%" not in guarded


@mark.docker
@mark.slow
def test_sync_creates_missing_roles():
    """A role dropped from the cluster is re-created by sync's role category."""
    with temporary_database_cluster(username="macrostrat_admin") as db:
        chunks = selected_chunks(_ENV, target="core")
        build_schema(db, _ENV, chunks=chunks)

        def exists(name: str) -> bool:
            return bool(
                db.run_query(
                    "SELECT 1 FROM pg_roles WHERE rolname = :name", dict(name=name)
                ).scalar()
            )

        assert exists("logs_writer")
        db.run_sql("DROP ROLE logs_writer", raise_errors=True)
        assert not exists("logs_writer")

        report = rebuild_roles(db, chunks)
        assert report.failed == []
        assert exists("logs_writer")
        # Re-applying is a no-op rather than a duplicate-object error.
        assert rebuild_roles(db, chunks).failed == []
