"""`apply_reconciliation` sends one statement per batch, not one per row."""

from contextlib import contextmanager

from sqlalchemy import Column, Float, Integer, MetaData, Table, Text, event, text

from macrostrat.column_ingestion.reconciliation import reconcile

TABLE = Table(
    "recon_batch",
    MetaData(),
    Column("id", Integer, primary_key=True),
    Column("name", Text),
    Column("value", Float),
    Column("note", Text),
)


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


class TestBatchedWrites:
    def test_inserts_and_updates_are_batched(self, db):
        db.session.execute(
            text(
                "CREATE TEMP TABLE recon_batch "
                "(id serial PRIMARY KEY, name text, value float, note text)"
            )
        )
        try:
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
                    TABLE,
                    existing=[],
                    desired=desired,
                    key=["name"],
                    owned_columns=["value"],
                )
            # Two batches, because two rows also set `note`
            assert sent == ["INSERT", "INSERT"]
            by_id = {row["id"]: row for row in fetch(db)}
            assert [by_id[i]["name"] for i in ids] == ["a", "b", "c", "d", "e"]

            moved = [dict(row, value=row["value"] * 10) for row in desired]
            with counted(db) as sent:
                plan, again = reconcile(
                    db,
                    TABLE,
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
