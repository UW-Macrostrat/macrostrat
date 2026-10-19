"""`apply_reconciliation` sends one statement per batch, not one per row."""

from contextlib import contextmanager

from sqlalchemy import MetaData, Table, event, text

from macrostrat.column_ingestion.reconciliation import reconcile


@contextmanager
def counted(db):
    """Collect the INSERT and UPDATE statements sent to the test table."""
    sent = []

    def record(conn, cursor, statement, params, context, executemany):
        if "recon_batch" in statement and statement.lstrip()[:6] in (
            "INSERT",
            "UPDATE",
        ):
            sent.append(statement.lstrip()[:6])

    event.listen(db.engine, "before_cursor_execute", record)
    try:
        yield sent
    finally:
        event.remove(db.engine, "before_cursor_execute", record)


def fetch(db) -> list[dict]:
    rows = db.session.execute(text("SELECT id, name, value, note FROM recon_batch"))
    return [dict(row._mapping) for row in rows]


def reflected_table(db) -> Table:
    """A table shaped like the macrostrat ones: reflected, `id` defaulting to `nextval`.

    The default draws from a sequence the column does not own, as `units_sections`
    does, so ids must come from the default rather than `pg_get_serial_sequence`.
    """
    db.session.execute(text("CREATE TEMP SEQUENCE recon_batch_draw_seq"))
    db.session.execute(
        text(
            "CREATE TEMP TABLE recon_batch ("
            " id integer PRIMARY KEY DEFAULT nextval('recon_batch_draw_seq'),"
            " name text, value float, note text)"
        )
    )
    return Table("recon_batch", MetaData(), autoload_with=db.session.connection())


class TestBatchedWrites:
    def test_inserts_and_updates_are_batched(self, db):
        try:
            table = reflected_table(db)
            desired = [
                {"name": "a", "value": 1.0},
                {"name": "b", "value": 2.0, "note": "set"},
                {"name": "c", "value": 3.0},
                {"name": "d", "value": 4.0, "note": "set"},
                {"name": "e", "value": 5.0},
            ]
            with counted(db) as sent:
                _, ids = reconcile(
                    db,
                    table,
                    existing=[],
                    desired=desired,
                    key=["name"],
                    owned_columns=["value"],
                )
            # Two batches, because two rows also set `note`
            assert sent == ["INSERT", "INSERT"]
            by_id = {row["id"]: row for row in fetch(db)}
            assert [by_id[i]["name"] for i in ids] == ["a", "b", "c", "d", "e"]
            drawn = db.session.execute(
                text("SELECT last_value FROM recon_batch_draw_seq")
            ).scalar()
            assert max(ids) == drawn

            moved = [dict(row, value=row["value"] * 10) for row in desired]
            with counted(db) as sent:
                plan, again = reconcile(
                    db,
                    table,
                    existing=fetch(db),
                    desired=moved,
                    key=["name"],
                    owned_columns=["value"],
                )
            assert sent == ["UPDATE"]
            assert again == ids
            assert len(plan.updates) == 5
            assert {r["name"]: r["value"] for r in fetch(db)} == {
                "a": 10.0,
                "b": 20.0,
                "c": 30.0,
                "d": 40.0,
                "e": 50.0,
            }
        finally:
            db.session.rollback()
