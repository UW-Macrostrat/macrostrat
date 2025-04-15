from psycopg2.sql import Identifier


def test_maps_tables_exist(db):
    """Test that the tables exist in the database."""

    for table in ["polygons", "lines", "points"]:
        res = db.run_query(
            "SELECT * FROM {table}", dict(table=Identifier("maps", table))
        ).all()

        assert len(res) == 0


def test_get_database(db):
    from macrostrat.core.database import db_ctx

    db_ctx.set(db)
    from macrostrat.map_integration.database import get_database

    db1 = get_database()

    assert db1 is db
