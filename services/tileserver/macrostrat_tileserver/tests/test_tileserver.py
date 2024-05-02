"""
Tests for Macrostrat's tileserver v2
"""

import pytest


@pytest.mark.legacy_raster
def test_mapnik_available():
    import mapnik

    assert mapnik


# x: 1554 y: 3078 z: 13
# x: 194 y: 384 z: 10
# source id: 251
# large

# tile 0, 0, 1
# North america


def test_database(db):
    assert db
    assert db.engine
    assert db.engine.url


def test_get_tile(client):
    res = client.get("/carto/13/1554/3078")
    assert res.status_code == 200
    assert res.headers["Content-Type"] == "application/x-protobuf"
