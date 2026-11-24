"""Which request hosts each pipeline counts."""

from macrostrat.usage_stats_capture import get_pipelines
from macrostrat.usage_stats_capture.pipelines import API_HOSTS, TILE_HOSTS

TILE = {
    "RequestMethod": "GET",
    "RequestPath": "/carto/4/12/5.mvt",
    "StartUTC": "2026-10-07T12:00:00.123456789Z",
    "ClientHost": "203.0.113.5",
}
DASHBOARD = {
    "RequestMethod": "GET",
    "RequestPath": "/api/v2/mobile/dashboard?lng=-89.4&lat=43.07&app=rockd&version=4.2.0",
    "StartUTC": "2026-10-07T12:00:00.123456789Z",
    "ClientHost": "203.0.113.5",
    "DownstreamStatus": 200,
}


def pipelines(**hosts):
    tiles, rockd = get_pipelines(
        ["tileserver", "rockd-dashboard"], client_salt=b"salt", **hosts
    )
    return tiles, rockd


def test_production_by_default():
    tiles, rockd = pipelines()
    assert (tiles.hosts, rockd.hosts) == (TILE_HOSTS, API_HOSTS)
    assert tiles.parse({**TILE, "RequestHost": "tiles.macrostrat.org"})
    assert tiles.parse({**TILE, "RequestHost": "tiles.dev.macrostrat.org"}) is None
    assert rockd.parse({**DASHBOARD, "RequestHost": "macrostrat.org"})
    assert rockd.parse({**DASHBOARD, "RequestHost": "dev.macrostrat.org"}) is None


def test_configured_hosts_replace_production():
    tiles, rockd = pipelines(
        tile_hosts=["tiles.dev.macrostrat.org", "tiles.staging.macrostrat.org"],
        api_hosts=["dev.macrostrat.org"],
    )
    assert tiles.parse({**TILE, "RequestHost": "tiles.staging.macrostrat.org"})
    assert tiles.parse({**TILE, "RequestHost": "tiles.macrostrat.org"}) is None
    assert rockd.parse({**DASHBOARD, "RequestHost": "dev.macrostrat.org"})
    assert rockd.parse({**DASHBOARD, "RequestHost": "macrostrat.org"}) is None
