"""The management-task routes.

Every route is admin-only, so these check that they are closed, that the
catalog carries the topology update, and that the event framing survives the
control characters a terminal stream is made of.
"""

import json

from fastapi.testclient import TestClient

from api.routes import tasks
from macrostrat.task_runner import load_registry

from .test_database import api_client  # noqa: F401


class TestAccess:
    def test_catalog_is_admin_only(self, api_client: TestClient):
        assert api_client.get("/tasks").status_code == 401

    def test_runs_are_admin_only(self, api_client: TestClient):
        assert api_client.get("/tasks/runs").status_code == 401
        response = api_client.post("/tasks/runs", json={"task": "topology.update"})
        assert response.status_code == 401
        run = "00000000-0000-0000-0000-000000000000"
        assert api_client.get(f"/tasks/runs/{run}").status_code == 401
        assert api_client.get(f"/tasks/runs/{run}/output").status_code == 401
        assert api_client.post(f"/tasks/runs/{run}/cancel").status_code == 401
        assert api_client.post(f"/tasks/runs/{run}/kill").status_code == 401


class TestCatalog:
    def test_topology_update_is_registered(self):
        spec = load_registry()["topology.update"]
        schema = spec.schema()
        assert set(schema["properties"]) >= {"maps", "build_bounds", "bulk"}
        params = spec.parse({"maps": ["ngs-*"], "piece_timeout": 30})
        assert params.maps == ["ngs-*"] and params.build_bounds

    def test_parameters_are_validated(self):
        spec = load_registry()["topology.update"]
        try:
            spec.parse({"bulk": "sometimes"})
        except Exception as err:
            assert "bulk" in str(err)
        else:
            raise AssertionError("a bad parameter must be refused")


class TestFraming:
    def test_control_characters_survive_an_event(self):
        chunk = "\x1b[1A\rNoding pieces \x1b[32m━━━\x1b[0m 50%\n"
        event = tasks._event("17-0", chunk)
        assert event.startswith("id: 17-0\ndata: ")
        payload = event[len("id: 17-0\ndata: ") :].rstrip("\n")
        assert "\r" not in payload and "\x1b" not in payload
        assert json.loads(payload) == {"d": chunk}
        assert tasks._end("cancelled") == 'event: end\ndata: {"state": "cancelled"}\n\n'
