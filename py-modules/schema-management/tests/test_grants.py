"""Tests for the permission-rebuild category of `macrostrat schema sync`.

The sweep covers roles as well as grants: roles are cluster objects the schema
diff cannot see, so without them a diff-built database has none of the roles its
grants name.
"""

from psycopg.errors import DuplicateObject, InsufficientPrivilege
from sqlalchemy.exc import ProgrammingError

from macrostrat.schema_management.composer import SchemaDefinition
from macrostrat.schema_management.grants import (
    grant_statements_in,
    object_already_exists,
    rebuild_grants,
)

_PROBE_ROLE = "macrostrat_sync_probe"


def _role_exists(db, name: str) -> bool:
    return bool(
        db.run_query(
            "SELECT 1 FROM pg_roles WHERE rolname = :name", dict(name=name)
        ).scalar()
    )


def test_grant_statements_in_filters_and_strips_comments():
    sql = """
    -- a table (not a grant)
    CREATE TABLE s.t (id int);

    GRANT SELECT ON s.t TO web_anon;

    -- revoke something
    REVOKE INSERT ON s.t FROM web_anon;

    ALTER DEFAULT PRIVILEGES IN SCHEMA s GRANT SELECT ON TABLES TO web_anon;

    ALTER TABLE s.t ADD COLUMN y int;   -- not a grant

    CREATE VIEW s.v AS SELECT id FROM s.t;
    """
    found = list(grant_statements_in(sql))
    assert len(found) == 3
    assert found[0].upper().startswith("GRANT SELECT")
    assert found[1].upper().startswith("REVOKE INSERT")
    assert found[2].upper().startswith("ALTER DEFAULT PRIVILEGES")


def test_role_creation_is_swept_in_declared_order():
    """Roles and grants come back interleaved, as `0000-roles.sql` writes them.

    Each `GRANT` there follows the role it names, so preserving file order is what
    makes the sweep applicable; a roles-first pass would reorder them.
    """
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
    found = [
        f.split()[0].upper() + " " + f.split()[1].upper()
        for f in grant_statements_in(sql)
    ]
    assert found == [
        "CREATE ROLE",
        "GRANT MACROSTRAT_ADMIN",
        "CREATE ROLE",
        "CREATE USER",
    ]


def test_object_already_exists_reads_the_drivers_sqlstate():
    """Against the real driver exception, not a stand-in.

    psycopg 3 spells the code `sqlstate` (psycopg 2 `pgcode`), so a check written
    for one attribute silently classifies every duplicate as a failure.
    """

    def wrapped(err):
        return ProgrammingError("CREATE ROLE x", {}, err)

    assert object_already_exists(wrapped(DuplicateObject("role x already exists")))
    assert not object_already_exists(
        wrapped(InsufficientPrivilege("permission denied"))
    )
    assert not object_already_exists(RuntimeError("something else"))


def test_sync_creates_a_missing_role(schema_harness, tmp_path):
    """A declared role absent from the cluster is created; a second pass skips it.

    The role is declared by a chunk this test owns rather than by dropping a real
    one: declared roles accumulate grants across the shared cluster (dropping
    `rockd_reader` fails on its privileges for `audit.record_history`), so
    removing one to manufacture the "missing" case is neither reliable nor safe.

    Not wrapped in `db.transaction`: `run_sql` gives a statement its own
    transaction only when the session isn't already in one, so a tolerated
    failure inside one would roll back the caller's transaction instead.
    """
    db = schema_harness.load_schema(target="macrostrat")
    sql = tmp_path / "01-roles.sql"
    sql.write_text(
        f"CREATE ROLE {_PROBE_ROLE} NOLOGIN;\n" f"GRANT {_PROBE_ROLE} TO macrostrat;\n"
    )
    chunks = [SchemaDefinition(name="probe-roles", provides=[sql])]

    assert not _role_exists(db, _PROBE_ROLE)
    try:
        created = rebuild_grants(db, chunks)
        assert (created.total, created.applied) == (2, 2)  # the role and its grant
        assert created.skipped == [] and created.failed == []
        assert _role_exists(db, _PROBE_ROLE)

        # Applied again, the role is already there: noted, not failed. The grant
        # is idempotent and simply re-applies.
        again = rebuild_grants(db, chunks)
        assert again.failed == []
        assert len(again.skipped) == 1
    finally:
        db.run_sql(f"DROP ROLE IF EXISTS {_PROBE_ROLE}", raise_errors=False)


def test_sync_reports_no_duplicate_role_failures(schema_harness):
    """Against a provisioned database, no declared role lands in the failures.

    This is the invariant the no-guard design rests on: duplicates are recognized
    by SQLSTATE and stepped over. Grants can legitimately fail here (an object
    absent in this environment), so only role creation is asserted on.
    """
    db = schema_harness.load_schema(target="macrostrat")
    chunks = schema_harness.chunks()

    report = rebuild_grants(db, chunks)

    creations = [s for s in report.failed if s.lower().startswith("create ")]
    assert creations == []
    assert len(report.skipped) > 0  # the declared roles were all already present
