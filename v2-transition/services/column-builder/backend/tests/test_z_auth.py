from requests import get, post, patch, put
from urvogel.database.fixtures import get_sql
from psycopg.sql import SQL, Literal


base= "http://127.0.0.1:3001"

auth = get_sql("auth.sql")
auth_inserts = get_sql("test_auth_inserts.sql")

def test_create_auth(db):
    with db.conn.cursor() as cur:
        cur.execute(auth)
        ##cur.execute(auth_inserts)

    sql =""" SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE  table_schema = 'auth'
            AND    table_name   = 'users'
            ); """

    res = db.query(sql).fetchone()
    assert res.get("exists") == True

    sql = """ 
    SELECT rolname FROM pg_catalog.pg_roles WHERE rolinherit = FALSE;
     """
    res = db.query(sql).fetchall()

    for row in res:
        assert row.get('rolname') in ['reader', 'writer', 'deleter', 'owner_']