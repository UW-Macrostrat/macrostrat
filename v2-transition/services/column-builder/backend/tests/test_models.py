import pytest
from urvogel.models import Project, Column, Unit, Environ, Lith
from urvogel.database.queries import get_sql

sql = """ SELECT * FROM macrostrat.projects; """

def test_project_model(db):
    res  = db.execute(sql).fetchall()
    new_projects = []
    for project in res:
        new_project = Project
        for k,v in project.items():
            setattr(new_project, k, v)
        new_projects.append(new_project)
    
    assert len(res) == len(new_projects)

@pytest.mark.skip(reason="strange postgis function error that works in other test")
def test_geom_values(db):
    """ asserts the usage of pydantic models for geometry types! 
        also assert the Columns pydantic model
    """
    sql = get_sql("get-cols-by.sql")
    res = db.execute(sql).fetchall()
    columns = []
    for column in res:
        columns.append(Column(**column))

def test_units_model(db):
    """ assert the unit model works correctly """
    sql = """ SELECT * FROM macrostrat.units; """
    res = db.execute(sql).fetchall()
    units = [Unit(**unit) for unit in res]

def test_environ_model(db):
    sql = """ SELECT * FROM macrostrat.environs; """
    res = db.execute(sql).fetchall()
    envs = [Environ(**env) for env in res]

def test_lith_model(db):
    sql = """ SELECT * FROM macrostrat.liths; """
    res = db.execute(sql).fetchall()
    liths = [Lith(**lith) for lith in res]