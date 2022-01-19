from urvogel.models import Project, Column, Unit, Environ, Lith
from requests import get, post, patch, put

""" A testing suite to test some postgrest functionlity """


base= "http://127.0.0.1:3000"

def test_projects():
    res = get(base + "/projects")

    data = res.json()
    assert len(data) == 3

def test_units_query():
    section_id=884
    col_id=112

    res = get(base + f"/units?col_id=eq.{col_id}&section_id=eq.{section_id}")
    data = res.json()
    assert len(data) > 0

    for col in data:
        assert col.get("section_id") == section_id
        assert col.get("col_id") == col_id

def test_units_metadata():
    """ test getting data from 1-many join tables """
    unit_id = 4575
    unit_envs = ["non-marine","fluvial indet."]
    res = get(base + f"/units?id=eq.{unit_id}")
    unit = res.json()

    assert len(unit) == 1
    unit = unit[0]

    res = get(base + f"/environ_unit?unit_id=eq.{unit['id']}")

    envs = res.json()
    assert len(envs) > 0


    for env in envs:
        assert env.get('unit_id') == unit_id
        assert env.get("environ") in unit_envs

def test_create_environ_add_to_unit():
    unit_id = 4575
    headers={"Prefer": "return=representation"}

    env = Environ(environ="test-env",environ_class="marine", environ_color="#669900")
    # try inserting directly into the environ_unit
    data = env.dict()
    res = post(base + "/environs", data, headers=headers)
    environ_id = res.json()[0].get('id')
    assert environ_id is not None

    data = {"environ_id": environ_id, "unit_id": unit_id}
    res = post(base + "/unit_environs", data, headers=headers)

    data = res.json()[0]
    assert data.get('id') is not None
    assert data.get('environ_id') == environ_id
    assert data.get('unit_id') == unit_id

def test_edit_unit():
    unit_id = 4575
    headers={"Prefer": "return=representation"}

    data = {"min_thick": 50, "max_thick": 500, "color": "gray light"}

    res = patch(base + f"/units?id=eq.{unit_id}", data, headers=headers)

    unit_res = res.json()[0]
    assert unit_res.get('id') == unit_id
    assert unit_res.get('min_thick') == data['min_thick']
    assert unit_res.get('max_thick') == data['max_thick']

