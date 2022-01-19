
project_id = 1
column_group_id = 1
col_id = 112
section_id = 871
unit_id = 5071

def test_root(client, db): # keep db here! So it builds the db to begin!
    res = client.get("/")
    assert res.status_code == 200
    assert res.json() == {"Welcome": "Docs Future"}


def test_projects(client):
    title = "North America"
    res = client.get(f"/projects/{project_id}")
    assert res.status_code == 200
    assert res.json().get("project", False) == title

    res = client.get("/projects/")
    assert res.status_code == 200
    assert isinstance(res.json(), list)
    assert res.json()[0].get("project") == title

def test_column_groups(client):
    name_long = "Atlantic Coastal Plain"

    res = client.get(f"/groups/{column_group_id}")
    assert res.status_code == 200
    assert res.json().get("col_group_long") == name_long

    res = client.get("/groups/")
    assert res.status_code == 200
    assert isinstance(res.json(), list)
    assert res.json()[-1].get("col_group_long") == name_long

    res = client.get(f"/groups?project_id={project_id}")
    assert res.status_code == 200
    assert isinstance(res.json(), list)
    names = [group['col_group_long'] for group in res.json()]
    assert name_long in names

def test_cols(client):
    res = client.get(f"/columns?col_group_id={column_group_id}")
    assert res.status_code == 200
    assert len(res.json()) > 0

    res = client.get(f"/columns?project_id={project_id}")
    assert res.status_code == 200
    assert len(res.json()) > 0

def test_units(client):
    res = client.get(f"/units?project_id={project_id}")
    assert res.status_code == 200
    assert len(res.json()) > 0
    
    res = client.get(f"/units?col_group_id={column_group_id}")
    assert res.status_code == 200
    assert len(res.json()) > 0
    
    res = client.get(f"/units?col_id={col_id}")
    assert res.status_code == 200
    assert len(res.json()) > 0
    
    res = client.get(f"/units?section_id={section_id}")
    assert res.status_code == 200
    assert len(res.json()) > 0

def test_def_routes(client):
    res = client.get(f"/defs/environs?unit_id={unit_id}")
    assert res.status_code == 200
    assert len(res.json()) > 0
    
    res = client.get(f"/defs/environs?like=b")
    assert res.status_code == 200
    assert len(res.json()) > 0
    
    res = client.get(f"/defs/liths?unit_id={unit_id}")
    assert res.status_code == 200
    assert len(res.json()) > 0
    
    res = client.get(f"/defs/liths?like=s")
    assert res.status_code == 200
    assert len(res.json()) > 0