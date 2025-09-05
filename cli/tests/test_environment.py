def test_database_connection(env_db):
    """Test that the database connection works."""
    res = env_db.run_query("SELECT 1").all()
    assert res[0][0] == 1


def test_columns_table_exists(env_db):
    """Check that the Macrostrat columns table exists and has more than 100 columns."""

    res = env_db.run_query("SELECT count(id) FROM macrostrat.cols").scalar()
    assert res > 100
