"""Tests for seed-data detection and re-application."""

from pytest import mark

from macrostrat.schema_management.composer import build_schema, selected_chunks
from macrostrat.schema_management.defs import test_database_cluster
from macrostrat.schema_management.seed_data import (
    _is_non_idempotent_insert,
    rebuild_seed_data,
    data_statements_in,
)

_ENV = "development"


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


@mark.docker
@mark.slow
def test_sync_reapplies_seed_data():
    """After provisioning, `sync`'s data category restores wiped seed rows."""
    with test_database_cluster(username="macrostrat_admin") as db:
        # `core` includes maps_metadata and its ingest_state seed insert.
        chunks = selected_chunks(_ENV, target="core")
        build_schema(db, _ENV, chunks=chunks)

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
