"""A schema-diff plan applies as `macrostrat`, escalating only where it must.

The plan is a flat statement list, so it can't take an owner per chunk the way
`build_schema` does. Instead it runs under `SET ROLE macrostrat` and reacts to
`42501` — the only reliable signal that a statement needs the connector — rather
than trying to classify statements in advance.
"""

from sqlalchemy import create_engine

from macrostrat.core.database import _role_pins
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
        # Never connects; only carries the pool listeners `pin_role` installs.
        self.engine = create_engine("postgresql+psycopg://")

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
        # Dropped to the connector to re-run the statement, then took the role
        # back so the rest of the plan is still applied as macrostrat.
        assert db.roles == [
            "SET ROLE {role}",
            "RESET ROLE",
            ctx.query,
            "SET ROLE {role}",
        ]
        assert _role_pins[db.engine].role == "macrostrat"
    assert recovery == []  # handled, nothing left for the loop to run
    assert db.engine not in _role_pins


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
    assert db.engine not in _role_pins


def test_migrations_apply_as_their_owner():
    """A migration is applied as `macrostrat` by default, with the hook that
    retries refused statements; `owner = None` applies it as the connector."""
    from macrostrat.schema_management.migrations import Migration, _apply_as_owner

    seen = []

    class AsOwner(Migration):
        name = "as-owner"

        def apply(self, db):
            seen.append((self.name, db.roles[-1], self.on_error is not None))

    class AsConnector(AsOwner):
        name = "as-connector"
        owner = None

    db = FakeDB()
    _apply_as_owner(db, AsOwner())
    _apply_as_owner(db, AsConnector())
    assert seen == [
        ("as-owner", "SET ROLE {role}", True),
        ("as-connector", "RESET ROLE", False),
    ]
    assert db.engine not in _role_pins


def test_apply_skips_the_plans_own_role_statements():
    """A plan names the role it applies as, for applying it by hand; `apply`
    manages the role itself, so those lines are neither run nor counted."""
    from macrostrat.schema_management.defs import StatementCounter

    counter = StatementCounter()
    kept = [
        s
        for s in ["SET ROLE macrostrat;", "CREATE TABLE maps.t ();", "RESET ROLE"]
        if counter.filter(s, None)
    ]
    assert kept == ["CREATE TABLE maps.t ();"]
    assert counter.total == 1
