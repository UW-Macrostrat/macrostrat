from urvogel.database.queries import get_sql, add_sql_clause, add_where_clause
from urvogel.database import Database
from urvogel.models import Project
from psycopg.sql import SQL, Identifier, Literal


sql = """ SELECT * FROM macrostrat.projects; """
    
def test_db_exists(db: Database):
    
    res = db.query(sql).fetchall()
    for project in res:
        assert project.get('project', False)
        assert project.get('descrip', False)

    assert len(res) > 0

def test_db_utils(db:Database):
    addition = "WHERE {col} = {id}"
    sql = get_sql("get-cols-by.sql")
    sql = add_sql_clause(sql, addition)

    assert addition in sql

    sql = "SELECT * FROM cols;"
    sql = add_where_clause(sql, "id", 3)
    assert sql.as_string(db.conn) == 'SELECT * FROM cols WHERE "id" = 3;'

def test_db_posting_sql(db: Database):
    sql = """INSERT INTO {table} ({columns})
                    VALUES ({values})"""
    
    project = Project(id=2, project = "test1", descrip="A test project", timescale_id=1)
    
    fields, values = zip(*[(k,v) for k,v in project if v is not None])

    fields = SQL(',').join([Identifier(field) for field in fields])
    values= SQL(",").join([Literal(v) for v in values])

    sql = SQL(sql).format(table=Identifier('macrostrat','projects'), columns = fields, values=values)
    
    db.query(sql)

    sql = """SELECT * from macrostrat.projects WHERE project = 'test1'"""
    row = db.query(sql).fetchone()
    
    assert row.get('project') == project.project
    assert row.get('descrip') == project.descrip

def test_db_insert_method(db):
    project = Project(id=3, project = "test2", descrip="Another test project", timescale_id=1)
    id_ = db.insert(project, "projects", "macrostrat")
    assert id_ == project.id

    sql = """SELECT * from macrostrat.projects WHERE project = 'test2'"""
    row = db.query(sql).fetchone()
    
    assert row.get('project') == project.project
    assert row.get('descrip') == project.descrip


def test_db_editing_sql(db:Database):
    """ grab a project from the db and serialize as a Project.
        then edit it and re-commit it to the db as an UPDATE.

        UPDATE macrostrat.projects SET id = 2, project = 'test1', descrip = 'descrip', timescale_id = 1
    """
    sql = """ SELECT * FROM macrostrat.projects WHERE id=2 """
    res = db.query(sql).fetchone()
    project = Project(**res)

    project.project = 'test1_edits'
    project.descrip = "An edited project description"

    sql = """UPDATE {table} SET {setters} WHERE id={id}"""

    setters = [SQL('{column}={value}').format(column = Identifier(k), value=Literal(v)) for k,v in project if v is not None]
    
    table = Identifier('macrostrat', 'projects')

    sql = SQL(sql).format(table=table, setters = SQL(",").join(setters), id=project.id)
    db.query(sql)

    sql = """SELECT * from macrostrat.projects WHERE id = 2"""
    row = db.query(sql).fetchone()
    
    assert row.get('project') == project.project
    assert row.get('descrip') == project.descrip

def test_db_update_method(db: Database):
    sql = """ SELECT * FROM macrostrat.projects WHERE id=2 """
    res = db.query(sql).fetchone()
    project = Project(**res)

    project.project = "test1_update_method"
    project.descrip = "this description has been updated using the db update method"

    id_ = db.update(project, "projects", "macrostrat")
    assert id_ == project.id

    row = db.query(f"SELECT * FROM macrostrat.projects WHERE id={id_}").fetchone()
    assert row.get('project') == project.project
    assert row.get('descrip') == project.descrip
    