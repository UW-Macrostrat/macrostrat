"""Units at a location, resolved through the compilation system.

Written against whatever the test database happens to hold. A database with no
topology solved answers with an empty list, and every invariant below is stated
so that it holds for that case too -- what is being tested is the shape of the
answer and the compilation bookkeeping, not the map data.
"""

from types import SimpleNamespace

from fastapi.testclient import TestClient
from sqlalchemy.exc import DBAPIError

from api.map import LEGACY_CARTO, MAX_BOUNDS_SPAN, MAX_LIMIT, _is_timeout

from .test_database import TEST_SOURCE_TABLE, api_client

# The face layer `carto` answers from at each zoom: its own, for the zoom's band
# per `map_bounds.scale_band` (tiny below 3, then small / medium / large at 3 / 6
# / 9) -- the same table the tiles read, so a point query here agrees with what
# is drawn.
CARTO_LAYER_FOR_ZOOM = {
    2: "carto@tiny",
    5: "carto@small",
    8: "carto@medium",
    14: "carto@large",
}

# South Dakota, where the carto layers have something to say.
SOMEWHERE = {"lng": -99, "lat": 43.5}


class TestMapUnits:
    def test_carto_answers_from_the_band_for_the_zoom(self, api_client: TestClient):
        """`carto` is multiscale: its faces are one layer per band, and the zoom
        picks the band, in the database."""
        for zoom, layer in CARTO_LAYER_FOR_ZOOM.items():
            response = api_client.get(
                "/map/carto/units", params={**SOMEWHERE, "zoom": zoom}
            )
            assert response.status_code == 200
            for unit in response.json():
                assert unit["map_layer"] == layer
                assert unit["map_layer_id"] is not None

    def test_zoom_is_the_only_thing_that_changes_the_answer(
        self, api_client: TestClient
    ):
        """`lng`/`lat` means the point, not the tile around it, so asking twice
        at one zoom is the same answer."""
        params = {**SOMEWHERE, "zoom": 8}
        once = api_client.get("/map/carto/units", params=params).json()
        twice = api_client.get("/map/carto/units", params=params).json()

        ids = [unit["map_id"] for unit in once]
        assert ids == [unit["map_id"] for unit in twice]

    def test_the_legacy_build_is_addressable(self, api_client: TestClient):
        """`sys:carto-legacy` reads `carto.polygons` through the same route, so
        the two builds can be compared with nothing but the name changing. It
        is not a `maps.sources` row, so it carries no compilation bookkeeping."""
        response = api_client.get(
            f"/map/{LEGACY_CARTO}/units", params={**SOMEWHERE, "zoom": 8}
        )
        assert response.status_code == 200
        for unit in response.json():
            assert unit["map_layer"] is None
            assert unit["map_face_id"] is None
            assert unit["priority_path"] == []

    def test_units_carry_where_they_came_from(self, api_client: TestClient):
        """The part the materialized carto tables cannot answer."""
        response = api_client.get("/map/carto/units", params={**SOMEWHERE, "zoom": 14})
        assert response.status_code == 200

        for unit in response.json():
            # The map that owns the polygon, which for a mosaic member is not
            # the member itself.
            assert unit["source_id"] is not None
            assert unit["map_id"] is not None
            # A layer answer always comes through a solved face.
            assert unit["map_face_id"] is not None

    def test_a_map_resolves_without_a_layer(self, api_client: TestClient):
        """Asked directly, a map answers for itself -- no faces involved."""
        response = api_client.get(
            f"/map/{TEST_SOURCE_TABLE.slug}/units", params=SOMEWHERE
        )
        assert response.status_code == 200

        for unit in response.json():
            assert unit["map_layer"] is None
            assert unit["map_face_id"] is None

    def test_an_unknown_map_is_not_an_empty_answer(self, api_client: TestClient):
        """A typo should say so rather than look like open ocean."""
        response = api_client.get("/map/not-a-map-at-all/units", params=SOMEWHERE)
        assert response.status_code == 404

    def test_somewhere_with_no_maps(self, api_client: TestClient):
        """Mid-Atlantic: a real answer that happens to be empty."""
        response = api_client.get(
            "/map/carto/units", params={"lng": -30, "lat": 0, "zoom": 8}
        )
        assert response.status_code == 200
        assert response.json() == []

    def test_bounds_are_accepted_too(self, api_client: TestClient):
        """The same location parameters as `/{compilation}/legend`."""
        response = api_client.get(
            "/map/carto/units", params={"bounds": "-99.1,43.4,-98.9,43.6"}
        )
        assert response.status_code == 200

    def test_a_location_is_required(self, api_client: TestClient):
        assert api_client.get("/map/carto/units").status_code == 400

    def test_a_continent_sized_bounds_is_refused(self, api_client: TestClient):
        """Refused up front, not after the statement timeout has burned ten
        seconds finding out."""
        response = api_client.get(
            "/map/carto/units", params={"bounds": "-180,-85,180,85"}
        )
        assert response.status_code == 400
        assert "bounds" in response.json()["detail"]

    def test_a_bounds_at_the_limit_is_accepted(self, api_client: TestClient):
        """The guard is on the span, not on where the box happens to sit.

        A tile-based measure would reject a tiny box that straddles a tile
        boundary, which is the wrong answer for the right-sized request.
        """
        half = MAX_BOUNDS_SPAN / 2
        bounds = f"{-half},{-half},{half},{half}"
        response = api_client.get("/map/carto/units", params={"bounds": bounds})
        assert response.status_code == 200

    def test_limit_caps_the_response(self, api_client: TestClient):
        response = api_client.get(
            "/map/carto/units",
            params={"bounds": "-99.1,43.4,-98.9,43.6", "limit": 1},
        )
        assert response.status_code == 200
        assert len(response.json()) <= 1

    def test_limit_is_bounded(self, api_client: TestClient):
        """An unbounded `limit` would undo the point of having one."""
        for limit in (0, MAX_LIMIT + 1):
            response = api_client.get(
                "/map/carto/units", params={**SOMEWHERE, "limit": limit}
            )
            assert response.status_code == 422

    def test_a_statement_timeout_is_recognized(self):
        """The guard against a runaway `bounds` only helps if the error it
        raises is told apart from every other driver error -- by SQLSTATE,
        since psycopg and asyncpg spell the exception class differently."""

        def error(**orig):
            return DBAPIError("SELECT 1", {}, SimpleNamespace(**orig))

        assert _is_timeout(error(sqlstate="57014"))  # asyncpg
        assert _is_timeout(error(pgcode="57014"))  # psycopg
        assert not _is_timeout(error(sqlstate="42P01"))  # undefined table
        assert not _is_timeout(error())
