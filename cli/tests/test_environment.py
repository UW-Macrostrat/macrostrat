from pytest import mark


def test_database_connection(db):
    """Test that the database connection works."""
    res = db.run_query("SELECT 1").all()
    assert res[0][0] == 1


def test_columns_table_exists(db):
    """Check that the Macrostrat columns table exists and has more than 100 columns."""

    res = db.run_query("SELECT count(id) FROM macrostrat.cols").scalar()
    assert res > 100


col_ids = {500: "Piceance Basin", 1050: "Woodstock"}  # New Zealand


@mark.parametrize("col_id,col_name", col_ids.items())
def test_specific_column_identity(db, col_id, col_name):
    """Make sure identity is maintained for a specific column from Macrostrat's core dataset."""
    res = db.run_query(
        "SELECT col_name FROM macrostrat.cols WHERE id = :id",
        dict(id=col_id),
    ).scalar()
    assert res == col_name
