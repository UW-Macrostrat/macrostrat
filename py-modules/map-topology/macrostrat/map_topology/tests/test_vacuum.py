from pytest import fixture

from macrostrat.database.utils import temporary_database
from macrostrat.map_topology.vacuum import (
    list_tables,
    resolve_tables,
    vacuum_tables,
)


@fixture
def vacuum_engine(empty_db):
    """A database of this test's own, on the shared cluster.

    VACUUM FULL carries over every tuple still visible to an open snapshot,
    and the session-scoped fixtures leave connections idle in transactions on
    the shared database (`run_query` never commits), so a rewrite there keeps
    the rows this test deletes and the size does not move. Only backends on
    the same database hold back that horizon, so a fresh database on the same
    cluster is enough; it costs a CREATE DATABASE, not a cluster.
    """
    url = empty_db.engine.url.set(database="macrostrat_vacuum_test")
    with temporary_database(
        url.render_as_string(hide_password=False), ensure_empty=True
    ) as engine:
        yield engine


def test_vacuum_full_reports_returned_space(vacuum_engine):
    engine = vacuum_engine
    with engine.begin() as conn:
        conn.exec_driver_sql(
            "CREATE TABLE vacuum_test AS"
            " SELECT g AS id, repeat('x', 500) AS pad FROM generate_series(1, 20000) g"
        )
        conn.exec_driver_sql("DELETE FROM vacuum_test WHERE id > 100")
    [res] = vacuum_tables(engine, resolve_tables(engine, ["vacuum_test"]), full=True)
    assert res.error is None
    assert res.after < res.before / 10


def test_sweep_lists_tables_by_schema(empty_db):
    engine = empty_db.engine
    with engine.begin() as conn:
        conn.exec_driver_sql("CREATE TABLE vacuum_test AS SELECT 1 AS id")
    try:
        assert "public.vacuum_test" in list_tables(engine, "public")
        assert "public.vacuum_test" not in list_tables(engine, "pg_catalog")
        results = list(vacuum_tables(engine, list_tables(engine, "public")))
        assert all(r.error is None for r in results)
    finally:
        with engine.begin() as conn:
            conn.exec_driver_sql("DROP TABLE vacuum_test")
