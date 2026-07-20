from psycopg.sql import Identifier
from pytest import mark

from macrostrat.schema_management import ReadinessState
from macrostrat.schema_management.migrations import _run_migrations_in_database


@mark.docker
def test_database_migrations(test_db_base):
    """Test that no database migrations are needed to reach the optimal database state."""

    # NOTE: we need to use readiness_level=ReadinessState.GA here because when running
    # in CI, we don't preload the development schema adjustments. We could potentially change
    # this.
    res = _run_migrations_in_database(
        test_db_base, legacy=False, raise_errors=True, readiness_level=ReadinessState.GA
    )
    assert res.n_migrations == 0
    assert res.n_remaining == 0


def test_maps_tables_exist(test_db_full):
    """Test that the tables exist in the database."""

    for table in ["polygons", "lines", "points"]:
        res = test_db_full.run_query(
            "SELECT * FROM {table}", dict(table=Identifier("maps", table))
        ).all()

        assert len(res) == 0
