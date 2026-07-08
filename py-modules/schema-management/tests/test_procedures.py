"""Unit tests for procedure-rebuild parsing (no database required)."""

from pytest import mark

from macrostrat.schema_management.procedures import (
    _as_create_or_replace,
    procedure_statements_in,
)


def test_procedure_statements_in_filters():
    sql = """
    CREATE TABLE s.t (id int);
    CREATE FUNCTION s.f() RETURNS int LANGUAGE sql AS $$ SELECT 1 $$;
    CREATE OR REPLACE PROCEDURE s.p() LANGUAGE sql AS $$ SELECT 1 $$;
    CREATE VIEW s.v AS SELECT 1;
    GRANT SELECT ON s.v TO web_anon;
    """
    found = list(procedure_statements_in(sql))
    assert len(found) == 2
    assert found[0].upper().startswith("CREATE FUNCTION")
    assert found[1].upper().startswith("CREATE OR REPLACE PROCEDURE")


@mark.parametrize(
    "stmt, expected_prefix",
    [
        ("CREATE FUNCTION s.f() RETURNS int AS $$x$$", "CREATE OR REPLACE FUNCTION"),
        ("create   procedure s.p() AS $$x$$", "CREATE OR REPLACE PROCEDURE"),
        ("CREATE OR REPLACE FUNCTION s.f() AS $$x$$", "CREATE OR REPLACE FUNCTION"),
    ],
)
def test_as_create_or_replace(stmt, expected_prefix):
    out = _as_create_or_replace(stmt)
    assert out.upper().startswith(expected_prefix)
    # Idempotent — never doubles the clause, body preserved.
    assert out.upper().count("OR REPLACE") == 1
    assert out.rstrip().endswith("$$x$$")
