from email import header
from requests import get, post, patch, put
from urvogel.database.fixtures import get_sql
from psycopg.sql import SQL, Literal

base= "http://127.0.0.1:3001"

auth = get_sql("auth.sql")
auth_inserts = get_sql("test_auth_inserts.sql")
email = "cidzikowski@wisc.edu"
password = "gniessrocks"

def login():
    res = post(base+"/rpc/login", data={"email": email, "pass": password})
    token = res.json().get('token')
    headers = {"Prefer": "return=representation", "Authorization": f'bearer {token}'}

    return headers

def test_create_auth(db):
    with db.conn.cursor() as cur:
        cur.execute(auth)

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
        assert row.get('rolname') in ['reader', 'writer', 'deleter', 'owner_','anon','authenticator', 'new_user']
    
def test_pg_extensions(db):
    sql = """ select extname from pg_extension; """
    res = db.query(sql).fetchall()
    extensions = [r.get('extname') for r in res]
    assert 'pgcrypto' in extensions
    assert 'pgjwt' in extensions
    
def test_add_user(db):

    params = {"email": email, "pass": password}
    res = post(base+"/rpc/create_user", data=params)

    assert res.status_code == 200

    sql = """ 
        SELECT email from auth.users;
         """
    res = db.query(sql).fetchone()
    assert res.get('email') is not None

def test_login(db):

    res = post(base+"/rpc/login", data={"email": email, "pass": password})

    assert res.status_code == 200

    token = res.json().get('token')
    assert token is not None
    headers = {"Prefer": "return=representation", "Authorization": f'bearer {token}'}

    res = post(base + "/rpc/get_email", headers=headers)

    assert res.json() == email

    res = get(base + "/projects", headers=headers)
    data = res.json()

    assert len(data) == 0

    # make the user an owner
    sql = """ insert into auth.user_projects(user_, project, role) 
                values(1, 1, 'owner_') """

    with db.conn.cursor() as cur:
        cur.execute(sql)
    
    res = post(base + '/rpc/current_user_projects', headers=headers)
    assert len(res.json()) == 1 and res.json()[0].get('id') == 1

    res = get(base + "/projects", headers={"Prefer": "return=representation", "Authorization": f'bearer {token}'})
    data = res.json()

    assert len(data) == 1 and data[0].get('id') == 1

def test_project_create(db):
    res = post(base+"/rpc/login", data={"email": email, "pass": password})

    assert res.status_code == 200

    token = res.json().get('token')
    assert token is not None
    headers = {"Prefer": "return=representation", "Authorization": f'bearer {token}'}

    res = post(base + "/projects", headers=headers, data={"project":"CFP1", "descrip":"fake project owned by casey", "timescale_id": 1})

    assert res.status_code == 201
    res = get(base + "/projects", headers=headers)
    data = res.json()

    assert len(data) == 2

def test_child_data(db):
    """ add some col-group, col and unit and see that we can access it """
    headers = login()

    col_group = {"col_group": "CG1", "col_group_long": "Casey's first fake column group", "project_id":13}
    res = post(base+"/col_groups", data=col_group, headers=headers)

    assert res.status_code == 201

    res = get(base + "/col_groups", headers=headers)
    assert len(res.json()) == 1


