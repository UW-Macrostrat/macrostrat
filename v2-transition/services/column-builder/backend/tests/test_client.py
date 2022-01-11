

def test_root(client):
    res = client.get("/")
    assert res.status_code == 200
    assert res.json() == {"Welcome": "Docs Future"}


def test_projects(client):
    project_id = 10
    title = "North American Ediacaran"
    res = client.get(f"/projects/{project_id}")
    assert res.status_code == 200
    assert res.json().get("project", False) == title

    res = client.get("/projects/")
    assert res.status_code == 200
    assert isinstance(res.json(), list)
    assert res.json()[0].get("project") == title

def test_column_groups(client):
    column_group_id = 66
    name_long = "Avalonia"

    res = client.get(f"/groups/{column_group_id}")
    assert res.status_code == 200
    assert res.json().get("col_group_long") == name_long

    res = client.get("/groups/")
    assert res.status_code == 200
    assert isinstance(res.json(), list)
    assert res.json()[-1].get("col_group_long") == name_long

    res = client.get("/groups?project_id=10")
    assert res.status_code == 200
    assert isinstance(res.json(), list)
    names = [group['col_group_long'] for group in res.json()]
    assert name_long in names

def test_cols(client):
    project_id = 10
    col_group_id = 66

    res = client.get(f"/columns?col_group_id={col_group_id}")
    assert res.status_code == 200
    assert len(res.json()) > 0

    res = client.get(f"/columns?project_id={project_id}")
    assert res.status_code == 200
    assert len(res.json()) > 0

