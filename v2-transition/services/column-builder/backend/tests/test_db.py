
sql = """ SELECT * FROM macrostrat.projects; """
    
def test_db_exists(db):
    
    res = db.execute(sql).fetchall()
    for project in res:
        assert project.get('project', False)
        assert project.get('descrip', False)

    assert len(res) > 0

