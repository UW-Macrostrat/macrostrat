from requests import get, post, patch, put
from urvogel.database.fixtures import get_sql
import time

base= "http://127.0.0.1:3001"

username = "cidzikowski"
password = "gniessrocks"

auth = get_sql("02-auth.sql")

def login(username, password):
    res = post(base+"/rpc/login", data={"username": username, "pass": password})
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
        assert row.get('rolname') in ['api_views_owner','anon','authenticator','anon_test','authenticator_test', 'api_user']
    
def test_pg_extensions(db):
    sql = """ select extname from pg_extension; """
    res = db.query(sql).fetchall()
    extensions = [r.get('extname') for r in res]
    assert 'pgcrypto' in extensions
    assert 'pgjwt' in extensions
    
def test_add_user(db):
    time.sleep(10) # if I don't wait it all fails. As if the sql is still being run....
    params = {"firstname": "Casey", "lastname": "Idzikowski", "pass": password, "username": username}
    res = post(base+"/rpc/create_user", data=params)

    assert res.status_code == 200

    sql = """ 
        SELECT username from auth.users;
         """
    res = db.query(sql).fetchone()
    assert res.get('username') is not None

def test_login(db):

    res = post(base+"/rpc/login", data={"username": username, "pass": password})

    assert res.status_code == 200

    token = res.json().get('token')
    assert token is not None
    headers = {"Prefer": "return=representation", "Authorization": f'bearer {token}'}

    res = post(base + "/rpc/get_username", headers=headers)

    assert res.json() == username

    res = get(base + "/projects", headers=headers)
    data = res.json()

    assert len(data) == 0

    # make the user an owner
    sql = """ insert into auth.user_projects(user_, project, role_id) 
                values(1, 1, 4) """

    with db.conn.cursor() as cur:
        cur.execute(sql)
    
    res = post(base + '/rpc/current_user_projects', headers=headers)
    assert len(res.json()) == 1 and res.json()[0].get('project') == 1

    res = get(base + "/projects", headers={"Prefer": "return=representation", "Authorization": f'bearer {token}'})
    data = res.json()

    assert len(data) == 1 and data[0].get('id') == 1

def test_project_create(db):
    res = post(base+"/rpc/login", data={"username": username, "pass": password})

    assert res.status_code == 200

    token = res.json().get('token')
    assert token is not None
    headers = {"Prefer": "return=representation", "Authorization": f'bearer {token}'}

    res = post(base + "/projects", headers=headers, data={"project":"CFP1", "descrip":"fake project owned by casey", "timescale_id": 1})

    assert res.status_code == 201
    res = get(base + "/projects", headers=headers)
    data = res.json()

    assert len(data) == 2

    res = patch(base + "/projects?id=eq.13", headers={"Authorization": f'bearer {token}','Prefer': 'return=minimal'}, data={"project": "CFP2"})
    assert res.status_code != 404

def test_child_data(db):
    """ add some col-group, col and unit and see that we can access it """
    headers = login(username, password)

    col_group = {"col_group": "CG1", "col_group_long": "Casey's first fake column group", "project_id":13}
    res = post(base+"/col_groups", data=col_group, headers=headers)

    assert res.status_code == 201

    res = get(base + "/col_groups", headers=headers)
    assert len(res.json()) == 1

def test_rls(db):
    """ 
        create a new user with read only access to casey's project,
        As owner I should be able to configure user privileges
    """
    username = 'app_user@gmail.com'
    password = 'appuser1'
    params = {'firstname': 'appuser','lastname':'lastnameApp',"username": username, "pass": password}

    res = post(base+"/rpc/create_user", data=params)

    headers = login('app_user@gmail.com', 'appuser1')


    res = get(base + "/projects", headers=headers)
    data = res.json()

    assert len(data) == 0

    res = post(base + "/projects", headers=headers, data={"project":"app1", "descrip":"fake project created and owned by app", "timescale_id": 1})

    assert res.status_code == 201
    res = get(base + "/projects", headers=headers)
    data = res.json()

    assert len(data) == 1


def test_user_management():
    """  """
    headers = login(username,password)

    res = get(base + "/user_projects", headers=headers)

    assert len(res.json()) == 2

    headers_ = login('app_user@gmail.com', 'appuser1')
    res = get(base + "/user_projects", headers=headers_)
    assert len(res.json()) == 1

    # make app_user a reader for project 13
    data = {"user_":2, "project":13, "role_id": 1 }
    res = post(base + "/user_projects", data=data, headers=headers)

    assert res.status_code == 201
    
    res = get(base + "/projects", headers=headers_)
    data = res.json()
    assert len(data) == 2
    assert data[0].get('id') == 13 