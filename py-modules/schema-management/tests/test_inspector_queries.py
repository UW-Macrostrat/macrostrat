"""The schema inspector's catalog queries, checked without a database."""

from types import SimpleNamespace

from pytest import mark

from macrostrat.schema_management.defs import (
    SCHEMA_FILTERED_QUERIES,
    SYSTEM_SCHEMAS,
    OurPostgreSQL,
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
