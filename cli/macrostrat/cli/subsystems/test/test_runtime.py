"""
Runtime tests for the Macrostrat system.

These tests are designed to run against a deployed instance
of Macrostrat to ensure that the system is functioning as expected.

Unlike unit or integration tests, these tests depend on the state
of the deployed system and can depend on specific data being present.
As such, they may need to evolve with Macrostrat's data holdings.
"""

from time import sleep

from requests import Session

client = Session()

tileserver = "https://tileserver.development.svc.macrostrat.org"


def test_tile_cache():
    # Get a random tile
    url = tileserver + "/carto-slim/3/1/2"

    res = client.get(url)

    assert res.status_code == 200

    xcache = res.headers.get("x-cache")

    if xcache == "miss":
        # Try again, the cache may need to be warmed
        # TODO: we could add a backoff here
        sleep(1)
        res = client.get(url)
        assert res.status_code == 200
        xcache = res.headers.get("x-cache")

    assert xcache == "hit"
