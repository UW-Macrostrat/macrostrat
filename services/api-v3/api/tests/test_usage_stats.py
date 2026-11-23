"""The usage-stats routes. The test database holds no harvested logs, so these pin
the admin gate and the shape of the responses rather than their contents."""

import pytest
from fastapi.testclient import TestClient

from api.app import app
from api.routes.security import TokenData, require_admin

from .test_database import api_client


@pytest.fixture
def admin_api(api_client: TestClient):
    app.dependency_overrides[require_admin] = lambda: TokenData(
        sub="0000-0000-0000-0001", role="web_admin"
    )
    yield api_client
    app.dependency_overrides.pop(require_admin, None)


@pytest.mark.parametrize(
    "path",
    ["/usage-stats/status", "/usage-stats/tiles/requests", "/usage-stats/tiles/maps"],
)
def test_requires_a_session(api_client: TestClient, path):
    assert api_client.get(path).status_code == 401


@pytest.mark.parametrize(
    "path",
    [
        "/usage-stats/status",
        "/usage-stats/tiles/requests",
        "/usage-stats/tiles/cache",
        "/usage-stats/tiles/layers",
        "/usage-stats/tiles/maps/-1",
        "/usage-stats/tiles/throttled",
    ],
)
def test_series_are_lists(admin_api: TestClient, path):
    response = admin_api.get(path, params={"start": "2026-01-01", "end": "2026-01-31"})
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_referrers_shape(admin_api: TestClient):
    response = admin_api.get("/usage-stats/tiles/referrers", params={"bots": "only"})
    assert response.status_code == 200
    assert {"total_requests", "n_referrers", "referrers"} <= set(response.json())


def test_maps_shape(admin_api: TestClient):
    response = admin_api.get("/usage-stats/tiles/maps", params={"limit": 5})
    assert response.status_code == 200
    body = response.json()
    assert {"n_maps", "first_date", "last_date", "maps"} <= set(body)
    assert len(body["maps"]) <= 5


def test_rejects_unknown_options(admin_api: TestClient):
    assert (
        admin_api.get("/usage-stats/tiles/requests", params={"bin": "year"}).status_code
        == 422
    )
    assert (
        admin_api.get("/usage-stats/tiles/layers", params={"bots": "some"}).status_code
        == 422
    )
