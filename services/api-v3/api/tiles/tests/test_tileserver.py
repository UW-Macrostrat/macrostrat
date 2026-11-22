"""
Tests for Macrostrat's tileserver v2
"""

import pytest
from mapbox_vector_tile import decode
from sqlalchemy import text


@pytest.fixture
def carto_layers(db):
    """Skip unless the test database actually has the carto tile functions.

    The committed dump (`test-fixtures/tileserver-test.pg-dump`) predates the
    current `tile_layers.carto` stack, so these assertions can't run against it.
    Regenerating the dump lights them up again — they are skipped rather than
    deleted so that stays visible.
    """
    with db.engine.connect() as conn:
        exists = conn.execute(
            text(
                "SELECT to_regprocedure('tile_layers.carto(integer,integer,integer,json)')"
                " IS NOT NULL"
            )
        ).scalar()
    if not exists:
        pytest.skip("test database predates tile_layers.carto; regenerate the dump")


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


@pytest.mark.parametrize(
    "source_id,z,x,y",
    [
        (251, 13, 1554, 3078),
        (251, 10, 194, 384),
        (154, 1, 0, 0),
    ],
)
def test_get_tile(client, carto_layers, source_id, z, x, y):
    res = client.get(f"/carto/{z}/{x}/{y}")
    assert res.status_code == 200
    assert res.headers["Content-Type"] == "application/x-protobuf"
    # Get the tile
    tile = res.content
    # Check that there are features
    assert len(tile) > 0

    res = decode(tile=tile)
    features = res["units"]["features"]
    assert len(features) > 0
    for feature in features:
        assert feature["properties"]["source_id"] == source_id

    if source_id == 154:
        return

    features = res["lines"]["features"]
    assert len(features) > 0
    for feature in features:
        assert feature["properties"]["source_id"] == source_id


def test_get_empty_tile(client, carto_layers):
    res = client.get("/carto/10/321/354")
    assert res.status_code == 200
    assert res.headers["Content-Type"] == "application/x-protobuf"
    # Get the tile
    tile = res.content
    # Check that there are features
    assert len(tile) == 0
