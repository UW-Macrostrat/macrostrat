"""The boundary-operation routes.

Writes are admin-only, so these check only that they are closed; the edits
themselves are tested in the library (`map-integration/tests/test_bounds_edit.py`).
"""

from fastapi.testclient import TestClient

from .test_database import TEST_SOURCE_TABLE, api_client


class TestOperations:
    def test_catalog(self, api_client: TestClient):
        response = api_client.get("/bounds/operations")
        assert response.status_code == 200
        ops = {o["op_id"]: o for o in response.json()}
        # Openings are set from the CLI, never appended.
        assert "union" not in ops and "adopt" not in ops
        assert ops["add"]["geometry"] and not ops["fill_holes"]["geometry"]
        assert "max_area" in ops["fill_holes"]["parameters"]["properties"]

    def test_unknown_map(self, api_client: TestClient):
        assert api_client.get("/bounds/no-such-map-slug").status_code == 404


class TestEditing:
    def test_anonymous_append_is_refused(self, api_client: TestClient):
        response = api_client.post(
            f"/bounds/{TEST_SOURCE_TABLE.slug}/operations",
            json={"operation": "fill_holes", "parameters": {"max_area": "1km2"}},
        )
        assert response.status_code == 401

    def test_anonymous_build_is_refused(self, api_client: TestClient):
        response = api_client.post(f"/bounds/{TEST_SOURCE_TABLE.slug}/build")
        assert response.status_code == 401

    def test_anonymous_remove_is_refused(self, api_client: TestClient):
        response = api_client.delete(f"/bounds/{TEST_SOURCE_TABLE.slug}/operations/1")
        assert response.status_code == 401
