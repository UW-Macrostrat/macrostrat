"""Change-tracking (audit) subsystem: roster is attached, and capture works.

The audit roster (``schema/_definitions/audit/20-enable.sql``) is a list of
``audit.enable()`` calls, so the triggers it attaches are part of the declarative
build and therefore part of the ideal schema the diff compares against. That
makes the diff self-healing — ``db apply`` re-creates a trigger that went missing
— but it also makes drift *silent* until the next apply: a migration that
recreates an audited table drops its trigger, and nothing complains. These tests
are the complaint.

The roster is parsed out of the SQL rather than restated here, so the test cannot
disagree with the declaration about which tables are audited.
"""

import re

from pytest import mark
from sqlalchemy import text

from macrostrat.core.config import settings
from macrostrat.schema_management.chunks import all_chunks
from macrostrat.schema_management.composer import build_schema, order_chunks
from macrostrat.schema_management.defs import test_database_cluster

_ENV = "development"

# Built as a target: audit's dependency closure, not the whole schema.
_TARGET = "audit"

_ROSTER_FILE = settings.srcroot / "schema" / "_definitions" / "audit" / "20-enable.sql"

_ENABLE_RE = re.compile(r"audit\.enable\(\s*'([^']+)'\s*\)", re.IGNORECASE)

# API roles that may read the trail but never write it.
_READONLY_ROLES = ("web_anon", "web_user", "web_admin")


def audited_tables() -> list[str]:
    """The schema-qualified tables named by the roster, ignoring commented-out lines."""
    tables = []
    for line in _ROSTER_FILE.read_text().splitlines():
        if line.strip().startswith("--"):
            continue
        tables.extend(_ENABLE_RE.findall(line))
    return tables


def test_roster_is_not_empty():
    """A roster that parses to nothing would make every assertion below vacuous."""
    tables = audited_tables()
    assert tables, f"no audit.enable() calls parsed from {_ROSTER_FILE}"
    assert all("." in t for t in tables), f"roster entries must be schema-qualified: {tables}"


def test_audit_applies_in_every_environment():
    """The point of living in _definitions rather than development/.

    ``discover_chunks`` on ``_definitions`` passes no ``environments``, so the
    chunk applies everywhere. If this ever regresses to a dev-only chunk,
    provenance silently stops existing in production.
    """
    chunks = {c.name: c for c in all_chunks()}
    assert "audit" in chunks, "audit subsystem was not discovered"
    assert chunks["audit"].environments is None, (
        "audit must apply in every environment; got "
        f"{chunks['audit'].environments}"
    )


def test_audit_is_ordered_after_the_tables_it_audits():
    """enable() needs its target tables to exist, so audit must sort after them."""
    order = [c.name for c in order_chunks(all_chunks())]
    assert order.index("audit") > order.index("core")
    assert order.index("audit") > order.index("macrostrat")


@mark.docker
@mark.slow
def test_roster_triggers_are_attached():
    with test_database_cluster(username="macrostrat_admin") as db:
        build_schema(db, _ENV, target=_TARGET)

        attached = {
            (row.schema, row.table, row.trigger)
            for row in db.run_query(
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

        missing = []
        for qualified in audited_tables():
            schema, table = qualified.split(".", 1)
            for trigger in ("zzz_audit_row", "zzz_audit_truncate"):
                if (schema, table, trigger) not in attached:
                    missing.append(f"{qualified}:{trigger}")
        assert not missing, f"rostered tables missing audit triggers: {missing}"


@mark.docker
@mark.slow
def test_audit_captures_changes_with_an_actor():
    """The capture machinery: attribution, normalized pk, and read-time diffing.

    Deliberately exercised on a purpose-built table rather than a rostered one.
    Every curated table sits behind a foreign-key chain (col_groups -> projects ->
    timescales) that is empty in a freshly built schema, so inserting into one
    would test seed data rather than the audit layer. That the roster's real
    tables are wired up is ``test_roster_triggers_are_attached``'s job.
    """
    with test_database_cluster(username="macrostrat_admin") as db:
        build_schema(db, _ENV, target=_TARGET)

        # raise_errors so a failed statement fails the test here, rather than
        # surfacing later as a confusingly empty trail.
        db.run_sql(
            """
            CREATE TABLE macrostrat.audit_smoke (id bigint primary key, label text);
            SELECT audit.enable('macrostrat.audit_smoke');
            """,
            raise_errors=True,
        )

        # One real transaction, via the engine rather than run_sql: run_sql
        # executes statement-by-statement, so a transaction-local GUC set in one
        # call is already gone by the next -- which is the whole point of the
        # assertion below.
        with db.engine.begin() as conn:
            conn.execute(
                text("SELECT audit.set_context('orcid:0000-0002-1234-5678', 'test-batch')")
            )
            conn.execute(
                text("INSERT INTO macrostrat.audit_smoke (id, label) VALUES (1, 'Original')")
            )
            conn.execute(
                text("UPDATE macrostrat.audit_smoke SET label = 'Renamed' WHERE id = 1")
            )
            conn.execute(text("DELETE FROM macrostrat.audit_smoke WHERE id = 1"))

        rows = db.run_query(
            """
            SELECT action, actor_id, batch_id, record_pk, changed
            FROM audit.changes
            WHERE schema_name = 'macrostrat' AND table_name = 'audit_smoke'
            ORDER BY id
            """
        ).all()

        assert [r.action for r in rows] == ["INSERT", "UPDATE", "DELETE"]
        assert all(r.record_pk == {"id": 1} for r in rows)

        # set_context uses a transaction-local GUC, so attribution only survives
        # if the writes share its transaction. A writer in autocommit gets a trail
        # with null actors -- silently useless -- which is what this pins down.
        assert all(r.actor_id == "orcid:0000-0002-1234-5678" for r in rows), (
            "actor did not survive into the trail: "
            f"{[r.actor_id for r in rows]}"
        )
        assert all(r.batch_id == "test-batch" for r in rows)

        # The UPDATE records only what moved; INSERT/DELETE carry the whole row.
        assert rows[1].changed == {"label": {"old": "Original", "new": "Renamed"}}
        assert rows[0].changed == {"id": 1, "label": "Original"}
        assert rows[2].changed == {"id": 1, "label": "Renamed"}


@mark.docker
@mark.slow
def test_actor_falls_back_to_the_postgrest_jwt():
    """API writes are attributed without the app calling set_context()."""
    with test_database_cluster(username="macrostrat_admin") as db:
        build_schema(db, _ENV, target=_TARGET)

        db.run_sql(
            """
            CREATE TABLE macrostrat.audit_jwt (id bigint primary key, label text);
            SELECT audit.enable('macrostrat.audit_jwt');
            """,
            raise_errors=True,
        )

        # PostgREST sets this GUC per request, inside the request's transaction;
        # mirror that rather than relying on statement-at-a-time execution.
        with db.engine.begin() as conn:
            conn.execute(
                text(
                    "SELECT set_config('request.jwt.claims',"
                    """ '{"sub":"0000-0002-1234-5678","role":"web_user"}', true)"""
                )
            )
            conn.execute(
                text("INSERT INTO macrostrat.audit_jwt (id, label) VALUES (1, 'via api')")
            )

        actor = db.run_query(
            """
            SELECT actor_id FROM audit.record_history
            WHERE table_name = 'audit_jwt' ORDER BY id LIMIT 1
            """
        ).scalar()
        assert actor == "orcid:0000-0002-1234-5678", f"JWT fallback did not fire: {actor!r}"


@mark.docker
@mark.slow
def test_history_is_append_only_for_api_roles():
    """The API roles can read the trail but must not be able to rewrite it."""
    with test_database_cluster(username="macrostrat_admin") as db:
        build_schema(db, _ENV, target=_TARGET)

        for role in _READONLY_ROLES:
            privs = db.run_query(
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
            assert privs.usage and privs.sel, f"{role} cannot read the audit trail: {privs}"
            assert not (
                privs.ins or privs.upd or privs.dlt
            ), f"{role} can rewrite the audit trail: {privs}"
