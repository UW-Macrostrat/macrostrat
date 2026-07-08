"""Unit tests for view-rebuild parsing (no database required)."""

from types import SimpleNamespace

from pytest import mark, raises

from macrostrat.schema_management.views import (
    _as_create_or_replace,
    _is_replace_conflict,
    _view_name,
    view_statements_in,
)


@mark.parametrize(
    "stmt, expected",
    [
        ("CREATE VIEW macrostrat_api.cols AS SELECT 1", "macrostrat_api.cols"),
        ("create or replace view lines.small as select 1", "lines.small"),
        ("CREATE VIEW IF NOT EXISTS a.b AS SELECT 1", "a.b"),
        ('CREATE VIEW "weird schema"."v" AS SELECT 1', '"weird'),  # best-effort
    ],
)
def test_view_name(stmt, expected):
    assert _view_name(stmt) == expected


def test_view_name_unparseable():
    with raises(ValueError):
        _view_name("SELECT 1")


@mark.parametrize(
    "stmt, expected_prefix",
    [
        ("CREATE VIEW a.b AS SELECT 1", "CREATE OR REPLACE VIEW"),
        ("create   view a.b as select 1", "CREATE OR REPLACE VIEW"),
        ("CREATE OR REPLACE VIEW a.b AS SELECT 1", "CREATE OR REPLACE VIEW"),
    ],
)
def test_as_create_or_replace(stmt, expected_prefix):
    out = _as_create_or_replace(stmt)
    assert out.upper().startswith(expected_prefix)
    # Rewriting is idempotent and never doubles the clause.
    assert out.upper().count("OR REPLACE") == 1
    # The body after the view keyword is preserved.
    assert out.rstrip().endswith("SELECT 1")


def test_view_statements_in_filters_and_strips_comments():
    sql = """
    -- a leading comment
    CREATE TABLE t (id int);

    -- the view we care about
    CREATE VIEW s.v AS SELECT id FROM t;

    GRANT SELECT ON s.v TO web_anon;

    CREATE OR REPLACE VIEW s.w AS SELECT 1;
    """
    found = list(view_statements_in(sql))
    assert len(found) == 2
    assert found[0].startswith("CREATE VIEW s.v")
    assert found[1].startswith("CREATE OR REPLACE VIEW s.w")


@mark.parametrize(
    "sqlstate, pgcode, expected",
    [
        ("42P16", None, True),   # invalid_table_definition (psycopg3)
        (None, "42P16", True),   # pgcode fallback (psycopg2-style)
        ("42804", None, False),  # datatype_mismatch — not a replace conflict
        (None, None, False),
    ],
)
def test_is_replace_conflict(sqlstate, pgcode, expected):
    orig = SimpleNamespace(sqlstate=sqlstate, pgcode=pgcode)
    err = SimpleNamespace(orig=orig)
    assert _is_replace_conflict(err) is expected
