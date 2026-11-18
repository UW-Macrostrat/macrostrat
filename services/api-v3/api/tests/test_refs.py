"""The reference routes: metadata at `/refs`, geometries at `/refs.geojson`."""

from fastapi.testclient import TestClient

from .test_database import api_client


class TestRefs:
    def test_list_has_no_geometry(self, api_client: TestClient):
        response = api_client.get("/refs")
        assert response.status_code == 200
        refs = response.json()
        assert refs
        assert all("geometry" not in r for r in refs)

    def test_geojson(self, api_client: TestClient):
        response = api_client.get("/refs.geojson", params={"has_geom": True})
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/geo+json"
        collection = response.json()
        assert collection["type"] == "FeatureCollection"
        for feature in collection["features"]:
            props = feature["properties"]
            assert feature["id"] == props["id"]
            assert feature["geometry"]["type"].upper() == props["geom_type"]
            assert "geom" not in props

    def test_geojson_empty(self, api_client: TestClient):
        response = api_client.get("/refs.geojson", params={"ref_id": [-1]})
        assert response.json() == {"type": "FeatureCollection", "features": []}

    def test_filter_by_id(self, api_client: TestClient):
        first = api_client.get("/refs").json()[0]
        response = api_client.get("/refs", params={"ref_id": [first["id"]]})
        assert [r["id"] for r in response.json()] == [first["id"]]

    def test_single(self, api_client: TestClient):
        first = api_client.get("/refs").json()[0]
        response = api_client.get(f"/refs/{first['id']}")
        assert response.status_code == 200
        assert response.json()["id"] == first["id"]

    def test_unknown(self, api_client: TestClient):
        assert api_client.get("/refs/-1").status_code == 404
