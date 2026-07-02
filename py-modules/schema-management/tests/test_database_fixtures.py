def test_database_fixtures(empty_db):
    """Test that the test database works and can be stood up in a timely manner"""

    empt = empty_db.run_query("SELECT 1").scalar()
    assert empt == 1
