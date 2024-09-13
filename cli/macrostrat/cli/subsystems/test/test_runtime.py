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
website = "https://dev2.macrostrat.org"


# Exponential backoff for up to 20 seconds
def exponential_backoff(url):
    for i in range(5):
        res = client.get(url)
        if res.status_code == 200:
            yield res
        sleep(2**i)
    yield res


def test_tile_cache():
    # Get a random tile
    url = tileserver + "/carto-slim/3/1/2"

    for res in exponential_backoff(url):
        if res.headers.get("x-cache") == "hit":
            return
    assert False, "Tile cache did not work"


def test_web_unknown_page():
    url = website + "/this-is-a-404"

    res = client.get(url)

    assert res.status_code == 404
