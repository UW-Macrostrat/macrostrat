"""One indexed raster, served by id at `/rasters/raster/{raster_id}`.

How a raster with no layer is previewed: the mosaic routes never select it.
"""

import pytest

pytest.importorskip("macrostrat.raster_layers")

from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from macrostrat.raster_index.testing import create_test_rasters  # noqa: E402
from macrostrat.tileserver.rasters import (  # noqa: E402
    SINGLE_RASTER_PREFIX,
    _single_raster_router,
    raster_layer_configs,
)


@pytest.fixture(scope="module")
def rasters(tmp_path_factory):
    files = create_test_rasters(tmp_path_factory.mktemp("rasters"))
    return {1: str(files["fine"])}


@pytest.fixture
def client(rasters):
    app = FastAPI()
    app.include_router(
        _single_raster_router(rasters.get, SINGLE_RASTER_PREFIX),
        prefix=SINGLE_RASTER_PREFIX,
    )
    return TestClient(app)


def test_an_unknown_id_is_not_found(client):
    response = client.get("/rasters/raster/99/info")
    assert response.status_code == 404
    assert "99" in response.json()["detail"]


def test_reads_the_indexed_file(client):
    info = client.get("/rasters/raster/1/info")
    assert info.status_code == 200
    assert len(info.json()["bounds"]) == 4


def test_tilejson_addresses_this_raster(client):
    tilejson = client.get("/rasters/raster/1/WebMercatorQuad/tilejson.json")
    assert tilejson.status_code == 200
    assert "/rasters/raster/1/tiles/WebMercatorQuad/" in tilejson.json()["tiles"][0]


def test_no_address_can_be_supplied(client):
    paths = client.app.openapi()["paths"]
    info = paths["/rasters/raster/{raster_id}/info"]["get"]
    assert "url" not in {p["name"] for p in info["parameters"]}


def test_no_configured_layer_takes_the_reserved_slug():
    assert "raster" not in {config.slug for config in raster_layer_configs()}
