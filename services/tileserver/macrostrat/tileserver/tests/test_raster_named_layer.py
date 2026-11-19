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


def test_serves_wmts(client):
    paths = client.app.openapi()["paths"]
    assert "/rasters/layer/{layer}/WMTSCapabilities.xml" in paths


def test_wmts_classes_come_from_the_named_layer():
    """Each by-name layer advertises its own vocabulary, not a configured one."""
    from macrostrat.tileserver.rasters import _class_renders

    class Category:
        label = "Alunite"

    class Index:
        def get_categories(self, slug):
            return [Category()] if slug == "aviris" else []

    class Backend:
        input = ["aviris"]

    assert _class_renders(Index())(Backend) == {"Alunite": {"classes": "Alunite"}}


def _registered(index, monkeypatch, configs):
    from macrostrat.tileserver import rasters

    monkeypatch.setattr(rasters, "sync_engine", lambda url: url)
    monkeypatch.setattr("macrostrat.raster_index.RasterIndex", lambda engine: index)
    monkeypatch.setattr(rasters, "raster_layer_configs", lambda: configs)
    app = FastAPI()
    assert rasters.register_raster_routes(app, "postgresql://unused/unused")
    return app


def _first_match(app, path):
    from starlette.routing import Match

    scope = {"type": "http", "path": path, "method": "GET"}
    for route in app.routes:
        match, _ = route.matches(scope)
        if match == Match.FULL:
            return route.path
    return None


def test_a_configured_layer_overrides_the_defaults(index, monkeypatch):
    """Its own router answers for its slug; every other slug falls through."""
    from macrostrat.raster_layers import RasterLayerConfig

    override = RasterLayerConfig(
        slug="smooth", resampling="bilinear", class_filtering=False
    )
    app = _registered(index, monkeypatch, [override])
    tile = "/tiles/WebMercatorQuad/4/3/5@1x.png"

    assert _first_match(app, "/rasters/layer/smooth" + tile).startswith(
        "/rasters/layer/smooth/"
    )
    assert _first_match(app, "/rasters/layer/aviris" + tile).startswith(
        "/rasters/layer/{layer}/"
    )


def test_an_override_takes_the_same_scopes(index, monkeypatch):
    from macrostrat.raster_layers import RasterLayerConfig

    override = RasterLayerConfig(slug="smooth", class_filtering=False)
    app = _registered(index, monkeypatch, [override])
    detail = TestClient(app).get("/rasters/layer/smooth/layer").json()["detail"]
    assert "tiles:map" in detail
    assert "rasters:smooth" in detail


def test_registration_requires_the_tile_scope(index, monkeypatch):
    """Refused with no token; the website's tile token is the one that works."""
    from macrostrat.tileserver import rasters
    from macrostrat.tileserver.map_tiles import SCOPE

    assert rasters.NAMED_LAYER_SCOPE == SCOPE
    monkeypatch.setattr(rasters, "sync_engine", lambda url: url)
    monkeypatch.setattr("macrostrat.raster_index.RasterIndex", lambda engine: index)
    app = FastAPI()
    assert rasters.register_raster_routes(app, "postgresql://unused/unused")

    response = TestClient(app).get("/rasters/layer/anything/layer")
    assert response.status_code == 401
    assert "tiles:map" in response.json()["detail"]
