"""A schema-diff plan applies as `macrostrat`, escalating only where it must.

The plan is a flat statement list, so it can't take an owner per chunk the way
`build_schema` does. Instead it runs under `SET ROLE macrostrat` and reacts to
`42501` — the only reliable signal that a statement needs the connector — rather
than trying to classify statements in advance.
"""

from macrostrat.schema_management.ownership import applied_as_app_owner


class FakeError(Exception):
    """A SQLAlchemy-style wrapper around a driver error carrying a SQLSTATE."""

    def __init__(self, sqlstate):
        super().__init__(sqlstate)
        self.orig = type("Orig", (), {"sqlstate": sqlstate})()


class FakeContext:
    def __init__(self, sql="CREATE TABLE maps.t ()"):
        self.query = sql
        self.sql_text = sql
        self.params = None


class FakeDB:
    """Records role directives; optionally refuses to take the application role."""

    def __init__(self, can_set_role: bool = True):
        self.roles: list[str] = []
        self.can_set_role = can_set_role

    def run_sql(self, sql, params=None, **kwargs):
        if sql == "SET ROLE {role}" and not self.can_set_role:
            raise PermissionError("not a member of macrostrat")
        self.roles.append(sql)


def test_plan_applies_as_the_app_owner_and_resets():
    db = FakeDB()
    with applied_as_app_owner(db) as escalate:
        assert escalate is not None
        assert db.roles == ["SET ROLE {role}"]
    assert db.roles == ["SET ROLE {role}", "RESET ROLE"]


def test_privilege_error_is_retried_as_the_connector():
    db = FakeDB()
    ctx = FakeContext()
    with applied_as_app_owner(db) as escalate:
        recovery = escalate(ctx, FakeError("42501"), None)

    # Drop to the connector, re-run the statement, then take the role back so the
    # rest of the plan is still applied as macrostrat.
    assert [d.query for d in recovery] == [
        "RESET ROLE",
        ctx.query,
        "SET ROLE {role}",
    ]


def test_other_errors_are_left_to_normal_handling():
    db = FakeDB()
    with applied_as_app_owner(db) as escalate:
        # 42P07 (duplicate_table) is a real failure, not a privilege boundary.
        assert escalate(FakeContext(), FakeError("42P07"), None) is None


def test_falls_back_to_the_connector_when_the_role_is_unavailable():
    """A connector outside macrostrat's membership keeps the previous behaviour."""
    db = FakeDB(can_set_role=False)
    with applied_as_app_owner(db) as escalate:
        assert escalate is None
    assert db.roles == []  # never masqueraded, so nothing to reset
