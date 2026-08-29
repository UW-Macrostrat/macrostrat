"""Change-tracking (audit) subsystem: roster attached, capture works, noise suppressed.

The schema diff self-heals audit triggers (it emits creates as well as drops), but
silently — a migration that recreates an audited table drops its trigger and nothing
complains until the next apply. These tests are the complaint.

The roster is parsed out of the SQL rather than restated here, so the tests cannot
disagree with the declaration about which tables are audited.
"""

import re

from pytest import fixture, mark

from macrostrat.core.config import settings
from macrostrat.schema_management.chunks import all_chunks
from macrostrat.schema_management.composer import order_chunks

_ROSTER_FILE = settings.srcroot / "schema" / "_definitions" / "audit" / "20-enable.sql"
_ENABLE_RE = re.compile(r"audit\.enable\(\s*'([^']+)'\s*\)", re.IGNORECASE)

# API roles that may read the trail but never write it.
_READONLY_ROLES = ("web_anon", "web_user", "web_admin")

# Tables carrying suppress_redundant_updates_trigger (schema/core/.../05-triggers.sql).
_SUPPRESSED_TABLES = ("units", "unit_liths", "unit_boundaries")
_SUPPRESS_TRIGGER = "a_suppress_noop_updates"


def audited_tables() -> list[str]:
    """The schema-qualified tables named by the roster, ignoring commented-out lines."""
    tables = []
    for line in _ROSTER_FILE.read_text().splitlines():
        if line.strip().startswith("--"):
            continue
        tables.extend(_ENABLE_RE.findall(line))
    return tables


@fixture(scope="module")
def audit_schema(schema_harness):
    """Audit subsystem and its dependencies, built on the session's shared cluster."""
    return schema_harness.load_schema(target="audit")


@fixture
def audit_db(audit_schema):
    """`audit_schema` in a transaction rolled back after each test, so probe tables
    and history rows don't leak into a database other modules share."""
    with audit_schema.transaction(rollback=True):
        yield audit_schema


def test_roster_is_not_empty():
    """A roster parsing to nothing would make the assertions below vacuous."""
    tables = audited_tables()
    assert tables
    assert all("." in t for t in tables), f"roster entries must be qualified: {tables}"


def test_audit_applies_in_every_environment():
    """Living in _definitions rather than development/ is what puts it in production."""
    chunks = {c.name: c for c in all_chunks()}
    assert "audit" in chunks, "audit subsystem was not discovered"
    assert chunks["audit"].environments is None, chunks["audit"].environments


def test_audit_is_ordered_after_the_tables_it_audits():
    """enable() needs its target tables to exist."""
    order = [c.name for c in order_chunks(all_chunks())]
    assert order.index("audit") > order.index("core")
    assert order.index("audit") > order.index("macrostrat")


@mark.docker
def test_roster_triggers_are_attached(audit_schema):
    attached = {
        (row.schema, row.table, row.trigger)
        for row in audit_schema.run_query(
            """
            SELECT n.nspname AS schema, c.relname AS table, t.tgname AS trigger
            FROM pg_catalog.pg_trigger t
            JOIN pg_catalog.pg_class c ON c.oid = t.tgrelid
            JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
            WHERE NOT t.tgisinternal
              AND t.tgname IN ('zzz_audit_row', 'zzz_audit_truncate')
            """
        )
    }
    missing = [
        f"{qualified}:{trigger}"
        for qualified in audited_tables()
        for trigger in ("zzz_audit_row", "zzz_audit_truncate")
        if (*qualified.split(".", 1), trigger) not in attached
    ]
    assert not missing, f"rostered tables missing audit triggers: {missing}"


@mark.docker
def test_audit_captures_changes_with_an_actor(audit_db):
    """Attribution, normalized pk, and read-time diffing.

    Uses a probe table because every curated table sits behind a FK chain
    (col_groups -> projects -> timescales) that is empty in a fresh schema.
    """
    audit_db.run_sql(
        """
        CREATE TABLE macrostrat.audit_smoke (id bigint primary key, label text);
        SELECT audit.enable('macrostrat.audit_smoke');
        SELECT audit.set_context('orcid:0000-0002-1234-5678', 'test-batch');
        INSERT INTO macrostrat.audit_smoke (id, label) VALUES (1, 'Original');
        UPDATE macrostrat.audit_smoke SET label = 'Renamed' WHERE id = 1;
        DELETE FROM macrostrat.audit_smoke WHERE id = 1;
        """,
        raise_errors=True,
    )

    rows = audit_db.run_query(
        """
        SELECT action, actor_id, batch_id, record_pk, changed FROM audit.changes
        WHERE table_name = 'audit_smoke' ORDER BY id
        """
    ).all()

    assert [r.action for r in rows] == ["INSERT", "UPDATE", "DELETE"]
    assert all(r.record_pk == {"id": 1} for r in rows)
    assert all(r.actor_id == "orcid:0000-0002-1234-5678" for r in rows), [
        r.actor_id for r in rows
    ]
    assert all(r.batch_id == "test-batch" for r in rows)
    # UPDATE records only what moved; INSERT/DELETE carry the whole row.
    assert rows[0].changed == {"id": 1, "label": "Original"}
    assert rows[1].changed == {"label": {"old": "Original", "new": "Renamed"}}
    assert rows[2].changed == {"id": 1, "label": "Renamed"}


@mark.docker
def test_actor_falls_back_to_the_postgrest_jwt(audit_db):
    """API writes are attributed without the app calling set_context()."""
    audit_db.run_sql(
        """
        CREATE TABLE macrostrat.audit_jwt (id bigint primary key, label text);
        SELECT audit.enable('macrostrat.audit_jwt');
        SELECT set_config('request.jwt.claims',
                          '{"sub":"0000-0002-1234-5678","role":"web_user"}', true);
        INSERT INTO macrostrat.audit_jwt (id, label) VALUES (1, 'via api');
        """,
        raise_errors=True,
    )
    actor = audit_db.run_query(
        "SELECT actor_id FROM audit.record_history WHERE table_name = 'audit_jwt'"
    ).scalar()
    assert actor == "orcid:0000-0002-1234-5678", f"JWT fallback did not fire: {actor!r}"


@mark.docker
def test_history_is_append_only_for_api_roles(audit_db, schema_harness):
    """API roles read the trail but cannot rewrite it."""
    # The harness skips GRANT statements for speed, so re-apply the chunk
    # unoptimized. Rolled back with the rest of the test.
    audit_chunk = next(c for c in schema_harness.chunks() if c.name == "audit")
    audit_chunk.apply(audit_db, transform_statement=None)

    for role in _READONLY_ROLES:
        privs = audit_db.run_query(
            """
            SELECT
              pg_catalog.has_schema_privilege(:role, 'audit', 'USAGE') AS usage,
              pg_catalog.has_table_privilege(:role, 'audit.record_history', 'SELECT') AS sel,
              pg_catalog.has_table_privilege(:role, 'audit.record_history', 'INSERT') AS ins,
              pg_catalog.has_table_privilege(:role, 'audit.record_history', 'UPDATE') AS upd,
              pg_catalog.has_table_privilege(:role, 'audit.record_history', 'DELETE') AS dlt
            """,
            {"role": role},
        ).one()
        assert privs.usage and privs.sel, f"{role} cannot read the trail: {privs}"
        assert not (privs.ins or privs.upd or privs.dlt), f"{role} can rewrite: {privs}"


@mark.docker
def test_suppress_trigger_sorts_before_row_stamping_triggers(audit_schema):
    """BEFORE triggers fire in name order and on_update_current_timestamp sets
    date_mod = now(), so suppressing after it suppresses nothing — silently."""
    rows = audit_schema.run_query(
        """
        SELECT c.relname AS table, t.tgname AS trigger
        FROM pg_catalog.pg_trigger t
        JOIN pg_catalog.pg_class c ON c.oid = t.tgrelid
        JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'macrostrat' AND NOT t.tgisinternal
          AND (t.tgtype::int & 2) > 0 AND (t.tgtype::int & 16) > 0  -- BEFORE UPDATE
        ORDER BY c.relname, t.tgname
        """
    ).all()

    by_table: dict[str, list[str]] = {}
    for row in rows:
        by_table.setdefault(row.table, []).append(row.trigger)

    for table in _SUPPRESSED_TABLES:
        triggers = by_table.get(table, [])
        assert _SUPPRESS_TRIGGER in triggers, f"{table} lost its suppressor: {triggers}"
        assert triggers[0] == _SUPPRESS_TRIGGER, f"{table} order: {triggers}"


@mark.docker
def test_noop_update_writes_no_history_even_with_a_stamping_trigger(audit_db):
    """Probe wired exactly like `units`: suppressor plus a date_mod stamper."""
    audit_db.run_sql(
        """
        CREATE TABLE macrostrat.suppress_probe (
          id bigint primary key, label text, date_mod timestamptz
        );
        CREATE TRIGGER on_update_current_timestamp BEFORE UPDATE
          ON macrostrat.suppress_probe FOR EACH ROW
          EXECUTE FUNCTION macrostrat.on_update_current_timestamp_units();
        CREATE TRIGGER a_suppress_noop_updates BEFORE UPDATE
          ON macrostrat.suppress_probe FOR EACH ROW
          EXECUTE FUNCTION suppress_redundant_updates_trigger();
        SELECT audit.enable('macrostrat.suppress_probe');
        INSERT INTO macrostrat.suppress_probe (id, label) VALUES (1, 'Original');
        """,
        raise_errors=True,
    )

    def updates():
        return audit_db.run_query(
            """
            SELECT changed FROM audit.changes
            WHERE table_name = 'suppress_probe' AND action = 'UPDATE' ORDER BY id
            """
        ).all()

    audit_db.run_sql(
        "UPDATE macrostrat.suppress_probe SET label = 'Original' WHERE id = 1",
        raise_errors=True,
    )
    assert updates() == [], "a no-op UPDATE was written to the audit log"

    audit_db.run_sql(
        "UPDATE macrostrat.suppress_probe SET label = 'Changed' WHERE id = 1",
        raise_errors=True,
    )
    changed = updates()
    assert len(changed) == 1, f"a real UPDATE was lost: {changed}"
    assert {"label", "date_mod"} <= set(changed[0].changed), changed[0].changed


@mark.docker
def test_set_audit_context_scopes(audit_schema):
    """`set_audit_context`, used by both machine writers: session scope (rebuild
    scripts, autocommit) vs transaction scope (column ingestion). Picking the wrong
    one fails silently — rows land with a null actor rather than raising.

    Runs outside a rolled-back transaction on purpose, since the distinction only
    shows across real statement boundaries. Cleans up after itself.
    """
    from macrostrat.core.database import set_audit_context

    db = audit_schema
    try:
        db.run_sql(
            """
            CREATE TABLE macrostrat.ctx_probe (id bigint primary key, label text);
            SELECT audit.enable('macrostrat.ctx_probe');
            """,
            raise_errors=True,
        )

        # Session scope: survives to the next autocommit statement.
        assert set_audit_context(db, "system:rebuild", "rebuild:probe", local=False)
        db.run_sql(
            "INSERT INTO macrostrat.ctx_probe (id, label) VALUES (1, 'a')",
            raise_errors=True,
        )
        row = db.run_query(
            "SELECT actor_id, batch_id FROM audit.record_history"
            " WHERE table_name = 'ctx_probe' AND record_pk = '{\"id\": 1}'::jsonb"
        ).one()
        assert (row.actor_id, row.batch_id) == ("system:rebuild", "rebuild:probe"), row

        # Transaction scope: reaches writes sharing its transaction.
        set_audit_context(db, "", None, local=False)  # clear the session setting
        with db.transaction():
            set_audit_context(db, "system:column-ingest", "ingest:probe")
            db.run_sql(
                "INSERT INTO macrostrat.ctx_probe (id, label) VALUES (2, 'b')",
                raise_errors=True,
            )
        row = db.run_query(
            "SELECT actor_id, batch_id FROM audit.record_history"
            " WHERE table_name = 'ctx_probe' AND record_pk = '{\"id\": 2}'::jsonb"
        ).one()
        assert (row.actor_id, row.batch_id) == (
            "system:column-ingest",
            "ingest:probe",
        ), row
    finally:
        set_audit_context(db, "", None, local=False)
        db.run_sql("DROP TABLE IF EXISTS macrostrat.ctx_probe")
        db.run_sql("DELETE FROM audit.record_history WHERE table_name = 'ctx_probe'")
