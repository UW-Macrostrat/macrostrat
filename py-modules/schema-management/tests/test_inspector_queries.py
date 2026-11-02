"""The schema inspector's catalog queries, checked without a database."""

from types import SimpleNamespace

from pytest import mark

from macrostrat.schema_management.defs import (
    SCHEMA_FILTERED_QUERIES,
    SYSTEM_SCHEMAS,
    TYPES_QUERY_FIXES,
    OurPostgreSQL,
    _types_off_search_path,
)

# Stand-ins for the two connections the inspector takes; it builds its queries
# as `text()` clauses over SQLAlchemy and as strings over psycopg.
_CONNECTIONS = {
    "sqlalchemy": SimpleNamespace(dialect=SimpleNamespace(server_version_info=(17,))),
    "psycopg": SimpleNamespace(
        connection=SimpleNamespace(pgconn=SimpleNamespace(server_version=170000))
    ),
}


class _QueriesOnly(OurPostgreSQL):
    """The inspector's catalog queries, without running them."""

    def load_all(self):
        pass


@mark.parametrize("connection", _CONNECTIONS)
def test_catalog_queries_can_exclude_schemas(connection):
    """`results` keeps the system-schema list the exclusion is spliced into.

    If an upgrade rewords it, inspection silently reads every schema again.
    """
    inspector = _QueriesOnly(_CONNECTIONS[connection])

    def sql(attr):
        return str(getattr(inspector, attr))

    for attr in SCHEMA_FILTERED_QUERIES:
        assert SYSTEM_SCHEMAS in sql(attr), attr

    inspector.exclude_schemas(["sources", "o'brien"])
    for attr in SCHEMA_FILTERED_QUERIES:
        assert f"{SYSTEM_SCHEMAS}, 'sources', 'o''brien'" in sql(attr), attr


@mark.parametrize("connection", _CONNECTIONS)
def test_types_query_reads_types_off_the_search_path(connection):
    """`results` keeps the wording the types-query fixes replace.

    If an upgrade rewords it, composite types outside the search path drop out
    of the diff again.
    """
    query = str(_QueriesOnly(_CONNECTIONS[connection]).TYPES_QUERY)
    for old in TYPES_QUERY_FIXES:
        assert old in query, old

    fixed = str(_types_off_search_path(query))
    assert "pg_type_is_visible" not in fixed
    assert "t.typname AS name" in fixed
