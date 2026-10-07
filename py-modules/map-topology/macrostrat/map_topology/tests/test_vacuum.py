from macrostrat.map_topology.vacuum import (
    list_tables,
    resolve_tables,
    vacuum_tables,
)


def test_vacuum_full_reports_returned_space(empty_db):
    engine = empty_db.engine
    with engine.begin() as conn:
        conn.exec_driver_sql(
            "CREATE TABLE vacuum_test AS"
            " SELECT g AS id, repeat('x', 500) AS pad FROM generate_series(1, 20000) g"
        )
        conn.exec_driver_sql("DELETE FROM vacuum_test WHERE id > 100")
    try:
        [res] = vacuum_tables(
            engine, resolve_tables(engine, ["vacuum_test"]), full=True
        )
        assert res.error is None
        assert res.after < res.before / 10
    finally:
        with engine.begin() as conn:
            conn.exec_driver_sql("DROP TABLE vacuum_test")


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
