"""The region routes. The test database may hold no regions, so these pin the
shape of the responses rather than their contents."""

from fastapi.testclient import TestClient

from .test_database import api_client


def test_list(api_client: TestClient):
    response = api_client.get("/regions")
    assert response.status_code == 200
    for region in response.json():
        assert {"region_id", "source_id", "region_class", "bounds"} <= set(region)


def test_list_by_source(api_client: TestClient):
    response = api_client.get("/regions", params={"source_id": -1})
    assert response.status_code == 200
    assert response.json() == []


def test_sources_is_not_read_as_an_id(api_client: TestClient):
    response = api_client.get("/regions/sources")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_unknown_region(api_client: TestClient):
    assert api_client.get("/regions/-1").status_code == 404
