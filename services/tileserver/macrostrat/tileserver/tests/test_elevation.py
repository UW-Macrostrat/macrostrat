"""The elevation service, end to end against tiny generated rasters.

Two layers in the shape of the real arrangement: a fine int16 land tile whose
sea is stored as 0 (SRTM GL1) over a coarse float32 global layer with NaN
nodata (SRTM15+). What is asserted is which raster answers and that water
falls through — the sampling arithmetic itself is tested in
`macrostrat.raster_layers`.
"""

import math

import pytest

pytest.importorskip("macrostrat.raster_layers.sampling")

# Nothing from `macrostrat.tileserver` is imported at module level: importing
# any of its subpackages builds the whole app, and that must not happen before
# the `app` fixture has pointed `DATABASE_URL` at the test database.

# The two layer slugs the service composites, finest first — mirrored from
# `macrostrat.tileserver.elevation.ELEVATION_LAYERS` and asserted equal below.
ELEVATION_LAYERS = ["srtm-gl1", "srtm15plus"]

FINE_BOUNDS = (-105.0, 40.0, -104.9, 40.1)
FINE_OCEAN = (-105.0, 40.0, -104.97, 40.1)
COARSE_BOUNDS = (-105.5, 39.5, -104.5, 40.5)

LAND = (-104.92, 40.05)
SEA = (-104.99, 40.05)
NOWHERE = (10.0, 10.0)


@pytest.fixture(scope="module")
def elevation_app(app, test_database_url):
    """The app with the elevation routes mounted against the test database.

    They mount at import when `DATABASE_URL` is set; when the package was
    imported earlier (another test module at collection time) they are added
    here, against the same database the fixtures fill.
    """
    from macrostrat.tileserver.elevation import ELEVATION_LAYERS as declared
    from macrostrat.tileserver.elevation import (
        ELEVATION_PREFIX,
        register_elevation_routes,
    )

    assert declared == ELEVATION_LAYERS
    mounted = any(
        getattr(r, "path", "").startswith(ELEVATION_PREFIX + "/") for r in app.routes
    )
    if not mounted:
        assert register_elevation_routes(app, database_url=test_database_url)
    return app


@pytest.fixture(scope="module")
def elevation_data(db, tmp_path_factory):
    """Register the two test layers under the slugs the service composites."""
    from macrostrat.raster_index import RasterIndex
    from macrostrat.raster_index.testing import create_test_dem

    directory = tmp_path_factory.mktemp("dems")
    fine = create_test_dem(
        directory / "fine.tif",
        FINE_BOUNDS,
        size=128,
        dtype="int16",
        nodata=-32768,
        base=1000,
        ocean=FINE_OCEAN,
        ocean_value=0,
    )
    coarse = create_test_dem(
        directory / "coarse.tif",
        COARSE_BOUNDS,
        size=64,
        dtype="float32",
        nodata=math.nan,
        base=-4000,
        step=10,
    )
    index = RasterIndex(db.engine)
    if not index.schema_exists():
        index.create_schema()
    land, global_ = ELEVATION_LAYERS
    index.register_layer(land, name="Fine land tiles")
    index.register_layer(global_, name="Coarse global layer")
    index.add_raster(fine, layer=land, slug="fine")
    index.add_raster(coarse, layer=global_, slug="coarse")
    index.set_nodata(land, 0)
    return index


class TestMounting:
    def test_routes_are_registered(self, elevation_app):
        paths = {getattr(r, "path", "") for r in elevation_app.routes}
        assert "/elevation/point/{lng},{lat}" in paths
        assert "/elevation/profile" in paths

    def test_the_raster_view_is_declared(self, elevation_app):
        """The same layers are also a mosaic under `/rasters/elevation`."""
        from macrostrat.tileserver.rasters import raster_layer_configs

        config = next(c for c in raster_layer_configs() if c.slug == "elevation")
        assert config.layer_slugs == ELEVATION_LAYERS
        assert config.resampling == "bilinear"
        assert config.class_filtering is False
        assert config.backend_options == {"scale_aware": True}

    def test_routes_are_public(self, client, elevation_app, elevation_data):
        """Public data, public route — unlike the `/rasters/*` mosaics."""
        response = client.get("/elevation/point/{},{}".format(*LAND))
        assert response.status_code == 200


class TestPoint:
    def test_land(self, client, elevation_app, elevation_data):
        data = client.get("/elevation/point/{},{}".format(*LAND)).json()
        assert 1000 <= data["elevation"] <= 1127
        assert data["source"]["layer"] == ELEVATION_LAYERS[0]
        assert data["source"]["raster"] == "fine"
        assert data["source"]["resolution"] > 0

    def test_sea_falls_through_to_bathymetry(
        self, client, elevation_app, elevation_data
    ):
        data = client.get("/elevation/point/{},{}".format(*SEA)).json()
        assert data["elevation"] < 0
        assert data["source"]["layer"] == ELEVATION_LAYERS[1]

    def test_nothing_there_is_null_not_an_error(
        self, client, elevation_app, elevation_data
    ):
        response = client.get("/elevation/point/{},{}".format(*NOWHERE))
        assert response.status_code == 200
        data = response.json()
        assert data["elevation"] is None
        assert data["source"] is None

    def test_a_coarse_resolution_reads_the_coarse_product(
        self, client, elevation_app, elevation_data
    ):
        data = client.get(
            "/elevation/point/{},{}".format(*LAND), params={"resolution": 5000}
        ).json()
        assert data["source"]["raster"] == "coarse"

    def test_out_of_range_coordinates(self, client, elevation_app):
        assert client.get("/elevation/point/200,40").status_code == 422


class TestProfile:
    def test_across_the_coast(self, client, elevation_app, elevation_data):
        response = client.get(
            "/elevation/profile",
            params=dict(
                start_lng=-104.995, start_lat=40.05, end_lng=-104.905, end_lat=40.05
            ),
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["samples"]) == 201
        assert data["samples"][0]["distance"] == 0
        assert data["samples"][-1]["distance"] == data["length"]
        assert all(s["elevation"] is not None for s in data["samples"])
        assert data["samples"][0]["source"]["raster"] == "coarse"
        assert data["samples"][-1]["source"]["raster"] == "fine"
        assert {s["layer"] for s in data["sources"]} == set(ELEVATION_LAYERS)

    def test_order_is_preserved(self, client, elevation_app, elevation_data):
        """East to west stays east to west; the legacy API reorders, this does not."""
        data = client.get(
            "/elevation/profile",
            params=dict(
                start_lng=-104.905,
                start_lat=40.05,
                end_lng=-104.995,
                end_lat=40.05,
                samples=5,
            ),
        ).json()
        assert data["samples"][0]["lng"] == -104.905

    def test_sample_count_is_bounded(self, client, elevation_app):
        params = dict(start_lng=0, start_lat=0, end_lng=1, end_lat=1)
        assert (
            client.get(
                "/elevation/profile", params={**params, "samples": 1}
            ).status_code
            == 422
        )
        assert (
            client.get(
                "/elevation/profile", params={**params, "samples": 5000}
            ).status_code
            == 422
        )

    def test_a_coarse_profile_only_opens_the_coarse_product(
        self, client, elevation_app, elevation_data
    ):
        data = client.get(
            "/elevation/profile",
            params=dict(
                start_lng=-105.45,
                start_lat=39.55,
                end_lng=-104.55,
                end_lat=40.45,
                samples=20,
            ),
        ).json()
        assert [s["raster"] for s in data["sources"]] == ["coarse"]
