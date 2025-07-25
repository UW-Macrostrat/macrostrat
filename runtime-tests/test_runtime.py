"""
Simple tests for the Macrostrat system.

These tests are designed to run against a deployed instance
of Macrostrat to ensure that the system is functioning as expected.

Unlike unit or integration tests, these tests depend on the state
of the deployed system and can depend on specific data being present.
As such, they may need to evolve with Macrostrat's data holdings.
"""

from pytest import mark
from requests import Session
from time import sleep

client = Session()

tileserver = "https://tileserver.development.svc.macrostrat.org"
website = "https://dev2.macrostrat.org"


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


valid_urls = ["/", "/api/v2", "/api/columns", "/columns", "/projects", "/docs", "/map"]


@mark.parametrize("url", valid_urls)
def test_web_pages(url):
    res = client.get(website + url)
    assert res.status_code == 200


# Exponential backoff for up to 20 seconds
def exponential_backoff(url):
    for i in range(5):
        res = client.get(url)
        if res.status_code == 200:
            yield res
        sleep(2**i)
    yield res


# Tile server should return an image for a legacy tile request
def test_legacy_tile():
    # TODO: modify this for dev URLs
    url = "https://macrostrat.org/api/v2/maps/burwell/emphasized/1/0/1/tile.png"
    res = client.get(url)
    assert res.status_code == 200
    assert res.headers["Content-Type"] == "image/png"
    assert len(res.content) > 0, "Tile content should not be empty"
