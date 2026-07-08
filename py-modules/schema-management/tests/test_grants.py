"""Unit tests for grant-rebuild parsing (no database required)."""

from macrostrat.schema_management.grants import grant_statements_in


def test_grant_statements_in_filters_and_strips_comments():
    sql = """
    -- a table (not a grant)
    CREATE TABLE s.t (id int);

    GRANT SELECT ON s.t TO web_anon;

    -- revoke something
    REVOKE INSERT ON s.t FROM web_anon;

    ALTER DEFAULT PRIVILEGES IN SCHEMA s GRANT SELECT ON TABLES TO web_anon;

    ALTER TABLE s.t ADD COLUMN y int;   -- not a grant

    CREATE VIEW s.v AS SELECT id FROM s.t;
    """
    found = list(grant_statements_in(sql))
    assert len(found) == 3
    assert found[0].upper().startswith("GRANT SELECT")
    assert found[1].upper().startswith("REVOKE INSERT")
    assert found[2].upper().startswith("ALTER DEFAULT PRIVILEGES")
