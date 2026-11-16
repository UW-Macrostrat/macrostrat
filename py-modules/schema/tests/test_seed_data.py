"""Tests for seed-data detection and re-application."""

from pytest import raises
from sqlalchemy.exc import IntegrityError

from macrostrat.schema_management.seed_data import (
    _is_non_idempotent_insert,
    data_statements_in,
    rebuild_seed_data,
)


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
    expected = {
        "user": "web_user",
        "authorized": "web_authorized",
        "admin": "web_admin",
        "test": "web_user",
    }

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
