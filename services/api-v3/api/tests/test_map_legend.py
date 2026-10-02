"""The legend of a source, resolved through the compilation system.

Written against whatever the test database happens to hold: what is tested is
which requests are answered and which are refused, not the map data.
"""

from types import SimpleNamespace

from fastapi.testclient import TestClient
from sqlalchemy.exc import DBAPIError

from api.map import _is_timeout, max_bounds_span

from .test_database import api_client

# South Dakota, where the carto layers have something to say.
LNG, LAT = -99, 43.5


def box(span: float) -> str:
    half = span / 2
    return f"{LNG - half},{LAT - half},{LNG + half},{LAT + half}"


class TestMapLegend:
    def test_an_unknown_map_is_not_an_empty_answer(self, api_client: TestClient):
        """A typo should say so rather than look like open ocean."""
        response = api_client.get("/map/not-a-map-at-all/legend")
        assert response.status_code == 404

    def test_bounds_without_a_zoom_are_answered_at_their_own(
        self, api_client: TestClient
    ):
        """A box with no zoom is read at the zoom it fills, so a view is always
        within the limit."""
        response = api_client.get("/map/carto/legend", params={"bounds": box(0.2)})
        assert response.status_code == 200

    def test_a_continent_sized_bounds_is_refused(self, api_client: TestClient):
        """A continent at zoom 11 is not a view. Refused up front, not after the
        statement timeout has burned ten seconds finding out."""
        response = api_client.get(
            "/map/carto/legend", params={"bounds": box(10), "zoom": 11}
        )
        assert response.status_code == 400
        assert "bounds" in response.json()["detail"]

    def test_a_bounds_at_the_limit_is_accepted(self, api_client: TestClient):
        """The guard is on the span at the zoom, not on where the box happens
        to sit."""
        zoom = 11
        response = api_client.get(
            "/map/carto/legend",
            params={"bounds": box(max_bounds_span(zoom)), "zoom": zoom},
        )
        assert response.status_code == 200

    def test_a_zoom_below_the_drawn_range_is_refused(self, api_client: TestClient):
        """`large` is drawn from zoom 9; below that its tiles hold nothing, and
        neither does its legend."""
        refused = api_client.get("/map/large/legend", params={"zoom": 1})
        assert refused.status_code == 400
        assert "zoom" in refused.json()["detail"]

        drawn = api_client.get(
            "/map/large/legend", params={"bounds": box(0.2), "zoom": 9}
        )
        assert drawn.status_code == 200

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
