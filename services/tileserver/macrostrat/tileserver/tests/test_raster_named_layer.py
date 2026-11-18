"""Any indexed layer, served by name at `/rasters/layer/{layer}`.

Configured mounts cover the layers Macrostrat curates; this route is how a
layer created in the admin interface is looked at without a code change.
"""

import pytest

pytest.importorskip("macrostrat.raster_layers")

from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from macrostrat.tileserver.rasters import (  # noqa: E402
    NAMED_LAYER_PREFIX,
    _named_layer_router,
    raster_layer_configs,
)


class FakeIndex:
    def __init__(self):
        self.asked = []

    def layer(self, slug):
        self.asked.append(slug)
        return None


@pytest.fixture
def index():
    return FakeIndex()


@pytest.fixture
def client(index):
    app = FastAPI()
    app.include_router(
        _named_layer_router(index, NAMED_LAYER_PREFIX), prefix=NAMED_LAYER_PREFIX
    )
    return TestClient(app)


def test_the_path_names_the_layer(client, index):
    response = client.get("/rasters/layer/aviris-2024/layer")
    assert index.asked == ["aviris-2024"]
    assert response.status_code == 404
    assert "aviris-2024" in response.json()["detail"]


def test_serves_the_full_mosaic_route_set(client):
    paths = client.app.openapi()["paths"]
    prefix = "/rasters/layer/{layer}"
    assert f"{prefix}/tiles/{{tileMatrixSetId}}/{{z}}/{{x}}/{{y}}" in paths
    assert f"{prefix}/footprints" in paths
    tile = paths[f"{prefix}/tiles/{{tileMatrixSetId}}/{{z}}/{{x}}/{{y}}"]["get"]
    assert {"layer", "classes", "resampling"} <= {p["name"] for p in tile["parameters"]}


def test_no_configured_layer_takes_the_reserved_slug():
    assert "layer" not in {config.slug for config in raster_layer_configs()}


def test_registration_requires_the_admin_scope(index, monkeypatch):
    """Every route under the prefix refuses a request with no token."""
    from macrostrat.tileserver import rasters

    monkeypatch.setattr(rasters, "sync_engine", lambda url: url)
    monkeypatch.setattr("macrostrat.raster_index.RasterIndex", lambda engine: index)
    app = FastAPI()
    assert rasters.register_raster_routes(app, "postgresql://unused/unused")

    response = TestClient(app).get("/rasters/layer/anything/layer")
    assert response.status_code == 401
    assert rasters.NAMED_LAYER_SCOPE in response.json()["detail"]
