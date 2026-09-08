"""Tests for seed-data detection and re-application."""

from pytest import raises
from sqlalchemy.exc import IntegrityError

from macrostrat.schema_management.seed_data import (
    _is_non_idempotent_insert,
    data_statements_in,
    rebuild_seed_data,
)


def test_seed_statements_in_detects_data_dml_only():
    sql = """
    CREATE TABLE s.t (id int);
    INSERT INTO s.t (id) VALUES (1) ON CONFLICT DO NOTHING;
    UPDATE s.t SET x = 1 WHERE id = 1;
    WITH cte AS (SELECT 1 AS id)
        INSERT INTO s.t (id) SELECT id FROM cte ON CONFLICT (id) DO NOTHING;
    WITH cte AS (SELECT 1) SELECT * FROM cte;   -- read-only, not seed
    DELETE FROM s.t WHERE id = 99;
    CREATE VIEW s.v AS SELECT 1;
    GRANT SELECT ON s.t TO web_anon;
    """
    found = list(data_statements_in(sql))
    # INSERT, UPDATE, WITH…INSERT, DELETE — but not WITH…SELECT, CREATE*, GRANT.
    assert len(found) == 4
    assert any(f.upper().startswith("WITH") for f in found)  # WITH … INSERT swept in
    assert not any(f.upper().startswith(("CREATE", "GRANT")) for f in found)


def test_setval_selects_are_swept_in_but_plain_selects_are_not():
    """`SELECT setval(…)` writes, even though sqlparse types it as a SELECT."""
    sql = """
    INSERT INTO s.t (id) VALUES (1) ON CONFLICT DO NOTHING;
    SELECT setval('s.t_id_seq', (SELECT max(id) FROM s.t));
    SELECT pg_catalog.setval('s.other_seq', 10);
    SELECT max(id) FROM s.t;   -- read-only, not seed
    """
    found = list(data_statements_in(sql))
    assert len(found) == 3
    assert sum("setval" in f for f in found) == 2
    assert not any(f.strip().upper().startswith("SELECT MAX") for f in found)


def test_non_idempotent_insert_detection():
    assert _is_non_idempotent_insert("INSERT INTO s.t (id) VALUES (1)") is True
    assert (
        _is_non_idempotent_insert(
            "INSERT INTO s.t (id) VALUES (1) ON CONFLICT DO NOTHING"
        )
        is False
    )
    # WITH … INSERT without ON CONFLICT is still flagged.
    assert (
        _is_non_idempotent_insert("WITH c AS (SELECT 1) INSERT INTO s.t SELECT 1")
        is True
    )
    # Non-INSERT DML isn't an ON CONFLICT concern.
    assert _is_non_idempotent_insert("UPDATE s.t SET x = 1") is False


def test_sync_reapplies_seed_data(schema_harness):
    """After provisioning, `sync`'s data category restores wiped seed rows."""
    # `core` includes maps_metadata and its ingest_state seed insert.
    db = schema_harness.load_schema(target="core")
    chunks = schema_harness.chunks()

    with db.transaction(rollback=True):

        def states():
            return set(
                db.run_query("SELECT id FROM maps_metadata.ingest_state")
                .scalars()
                .all()
            )

        seeded = states()
        assert {"pending", "ingested", "ready"} <= seeded  # provision seeded them
        assert len(seeded) == 11

        # Wipe the seed rows, then let sync's data category restore them.
        db.run_sql("DELETE FROM maps_metadata.ingest_state", raise_errors=True)
        assert states() == set()

        rebuild_seed_data(db, chunks)
        assert states() == seeded  # sync re-applied the seed INSERT


def test_auth_roles_are_seeded_and_resynced(schema_harness):
    """`macrostrat_auth.role` is seeded by the build, and sync converges it.

    `user.role` is a string FK with no database default, so a database whose role
    table is empty cannot create a user at all. The seed is `ON CONFLICT ... DO
    UPDATE`, so sync owns the postgres_role mapping and not just the keys.
    """
    db = schema_harness.load_schema(target="macrostrat")
    chunks = schema_harness.chunks()
    expected = {"user": "web_user", "admin": "web_admin", "test": "web_user"}

    with db.transaction(rollback=True):

        def roles():
            return dict(
                db.run_query("SELECT id, postgres_role FROM macrostrat_auth.role").all()
            )

        assert roles() == expected

        db.run_sql(
            "UPDATE macrostrat_auth.role SET postgres_role = 'web_anon'",
            raise_errors=True,
        )
        db.run_sql(
            "DELETE FROM macrostrat_auth.role WHERE id = 'test'", raise_errors=True
        )

        rebuild_seed_data(db, chunks)
        assert roles() == expected


def test_postgres_role_must_be_a_web_role(schema_harness):
    """The mapping column is free text, so a check constraint guards it.

    Without it a typo is stored happily and only shows up as a session that
    silently falls back to the default role — `role_claim` rejects anything
    outside `POSTGREST_ROLES`, so a bad mapping fails quietly rather than loudly.
    """
    db = schema_harness.load_schema(target="macrostrat")

    # Not wrapped in `db.transaction`: the insert is rejected, so it writes
    # nothing to roll back, and a failing statement inside one would roll back
    # the caller's transaction rather than its own.
    with raises(IntegrityError):
        db.run_sql(
            "INSERT INTO macrostrat_auth.role (id, postgres_role) "
            "VALUES ('bogus', 'web_amdin')",
            raise_errors=True,
        )
