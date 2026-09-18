"""The rebuild sweeps apply each chunk's statements as that chunk's owner.

`sync` re-applies the same SQL `build_schema` does, so it has to use the same role:
`CREATE OR REPLACE VIEW` keeps an existing view's owner, but the drop-and-recreate
fallback (and anything cascaded with it) creates the view afresh, under whichever
role is connected. Running the sweep as the connector is how application objects
end up owned by it — which is what `ownership-unification` then has to undo.
"""

from macrostrat.core import SchemaDefinition
from macrostrat.schema_management.rebuild import (
    ChunkStatement,
    apply_statements,
    iter_chunk_statements,
)
from macrostrat.schema_management.views import rebuild_views


class FakeDB:
    """Records role directives and applied SQL instead of touching a database."""

    def __init__(self, fail_on: str | None = None):
        self.roles: list[str] = []
        self.applied: list[str] = []
        self.fail_on = fail_on

    def run_sql(self, sql, params=None, **kwargs):
        if sql in ("RESET ROLE", "SET ROLE {role}"):
            self.roles.append(sql)
            return
        self.applied.append(sql)
        if self.fail_on is not None and self.fail_on in sql:
            raise RuntimeError("statement exploded")


def _statements(*pairs):
    return iter(ChunkStatement(owner, sql) for owner, sql in pairs)


def test_iter_chunk_statements_carries_the_chunk_owner(tmp_path):
    (tmp_path / "a.sql").write_text("SELECT 1;")
    chunk = SchemaDefinition(name="app", provides=[tmp_path], owner="macrostrat")

    found = list(iter_chunk_statements([chunk], lambda text: iter([text.strip()])))
    assert found == [ChunkStatement("macrostrat", "SELECT 1;")]


def test_apply_statements_sets_role_per_chunk_and_resets():
    db = FakeDB()
    apply_statements(
        db,
        _statements(
            (None, "CREATE EXTENSION postgis"),  # foundational → connector
            ("macrostrat", "CREATE VIEW a AS SELECT 1"),
            ("macrostrat", "CREATE VIEW b AS SELECT 1"),  # same owner → no re-SET
            (None, "GRANT USAGE ON SCHEMA public TO web_anon"),
        ),
    )
    assert db.roles == [
        "RESET ROLE",
        "SET ROLE {role}",
        "RESET ROLE",  # back to the connector for the grants chunk
        "RESET ROLE",  # final reset on exit
    ]


def test_apply_statements_resets_role_after_a_failed_statement():
    """A recorded failure still leaves the session unmasked."""
    db = FakeDB(fail_on="CREATE VIEW b")
    report = apply_statements(
        db,
        _statements(("macrostrat", "CREATE VIEW a"), ("macrostrat", "CREATE VIEW b")),
    )
    assert report.failed == ["CREATE VIEW b"]
    assert db.roles == ["SET ROLE {role}", "RESET ROLE"]


def test_rebuild_views_applies_each_view_as_its_chunk_owner(tmp_path):
    (tmp_path / "app.sql").write_text("CREATE VIEW app.v AS SELECT 1;")
    public = tmp_path / "public"
    public.mkdir()
    (public / "public.sql").write_text("CREATE VIEW public.v AS SELECT 1;")

    chunks = [
        SchemaDefinition(name="public", provides=[public]),
        SchemaDefinition(
            name="app", provides=[tmp_path / "app.sql"], owner="macrostrat"
        ),
    ]
    db = FakeDB()
    report = rebuild_views(db, chunks)

    assert report.total == 2
    assert db.roles == ["RESET ROLE", "SET ROLE {role}", "RESET ROLE"]
