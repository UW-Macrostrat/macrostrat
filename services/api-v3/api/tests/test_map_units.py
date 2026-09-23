"""Units at a location, resolved through the compilation system.

Written against whatever the test database happens to hold. A database with no
topology solved answers with an empty list, and every invariant below is stated
so that it holds for that case too -- what is being tested is the shape of the
answer and the layer bookkeeping, not the map data.
"""

from types import SimpleNamespace

from fastapi.testclient import TestClient
from sqlalchemy.exc import DBAPIError

from api.map import (
    LAYER_STACKS,
    MAX_BOUNDS_SPAN,
    MAX_LIMIT,
    _is_timeout,
    layer_for_zoom,
)

from .test_database import TEST_SOURCE_TABLE, api_client

# The dynamic layers, not the materialized `carto.polygons` that
# `/{compilation}/legend` answers from -- see `LAYER_STACKS`.
CARTO_STACK = LAYER_STACKS["carto-v2"]
CARTO_LAYERS = [slug for _, slug in CARTO_STACK]

# South Dakota, where the carto layers have something to say.
SOMEWHERE = {"lng": -99, "lat": 43.5}


class TestMapUnits:
    def test_layer_for_zoom_matches_the_tile_query(self):
        """The thresholds `carto-dynamic.sql` buckets a tile `z` with.

        A point query that disagreed with the tiles would be useless for
        checking them, so these are pinned rather than derived from
        `map_layer`'s own zoom ranges, which differ.
        """
        assert layer_for_zoom(CARTO_STACK, 0) == "tiny"
        assert layer_for_zoom(CARTO_STACK, 2) == "tiny"
        assert layer_for_zoom(CARTO_STACK, 3) == "carto-small"
        assert layer_for_zoom(CARTO_STACK, 5) == "carto-small"
        assert layer_for_zoom(CARTO_STACK, 6) == "carto-medium"
        assert layer_for_zoom(CARTO_STACK, 8) == "carto-medium"
        assert layer_for_zoom(CARTO_STACK, 9) == "carto-large"
        assert layer_for_zoom(CARTO_STACK, 18) == "carto-large"

    def test_a_stack_answers_for_every_layer(self, api_client: TestClient):
        """Nothing is chosen server-side: each layer's answer comes back, and
        the flag says which one the zoom would have drawn."""
        for zoom in (2, 5, 8, 14):
            response = api_client.get(
                "/map/carto-v2/units", params={**SOMEWHERE, "zoom": zoom}
            )
            assert response.status_code == 200

            current = layer_for_zoom(CARTO_STACK, zoom)
            for unit in response.json():
                assert unit["map_layer"] in CARTO_LAYERS
                assert unit["is_current_layer"] == (unit["map_layer"] == current)

    def test_zoom_only_chooses_the_current_layer(self, api_client: TestClient):
        """`lng`/`lat` means the point, not the tile around it.

        Sizing the query from the tile makes a low zoom an area scan of a
        quarter of a hemisphere, which is what this route is not for. The row
        set must therefore not depend on the zoom -- only which row is marked.
        """
        params = {**SOMEWHERE, "zoom": 2}
        coarse = api_client.get("/map/carto-v2/units", params=params).json()
        params = {**SOMEWHERE, "zoom": 14}
        fine = api_client.get("/map/carto-v2/units", params=params).json()

        assert [unit["map_id"] for unit in coarse] == [unit["map_id"] for unit in fine]

    def test_units_carry_where_they_came_from(self, api_client: TestClient):
        """The part the materialized carto tables cannot answer."""
        response = api_client.get(
            "/map/carto-v2/units", params={**SOMEWHERE, "zoom": 14}
        )
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
            assert not unit["is_current_layer"]

    def test_an_unknown_map_is_not_an_empty_answer(self, api_client: TestClient):
        """A typo should say so rather than look like open ocean."""
        response = api_client.get("/map/not-a-map-at-all/units", params=SOMEWHERE)
        assert response.status_code == 404

    def test_somewhere_with_no_maps(self, api_client: TestClient):
        """Mid-Atlantic: a real answer that happens to be empty."""
        response = api_client.get(
            "/map/carto-v2/units", params={"lng": -30, "lat": 0, "zoom": 8}
        )
        assert response.status_code == 200
        assert response.json() == []

    def test_bounds_are_accepted_too(self, api_client: TestClient):
        """The same location parameters as `/{compilation}/legend`."""
        response = api_client.get(
            "/map/carto-v2/units", params={"bounds": "-99.1,43.4,-98.9,43.6"}
        )
        assert response.status_code == 200

    def test_a_location_is_required(self, api_client: TestClient):
        assert api_client.get("/map/carto-v2/units").status_code == 400

    def test_a_continent_sized_bounds_is_refused(self, api_client: TestClient):
        """Refused up front, not after the statement timeout has burned ten
        seconds finding out."""
        response = api_client.get(
            "/map/carto-v2/units", params={"bounds": "-180,-85,180,85"}
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
        response = api_client.get("/map/carto-v2/units", params={"bounds": bounds})
        assert response.status_code == 200

    def test_limit_caps_the_response(self, api_client: TestClient):
        response = api_client.get(
            "/map/carto-v2/units",
            params={"bounds": "-99.1,43.4,-98.9,43.6", "limit": 1},
        )
        assert response.status_code == 200
        assert len(response.json()) <= 1

    def test_limit_is_bounded(self, api_client: TestClient):
        """An unbounded `limit` would undo the point of having one."""
        for limit in (0, MAX_LIMIT + 1):
            response = api_client.get(
                "/map/carto-v2/units", params={**SOMEWHERE, "limit": limit}
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
