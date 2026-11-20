"""Route tests for the gateway image, run against tests/compose.yaml."""

import json
import os
import time
import unittest
import uuid
from http.client import HTTPConnection

API = int(os.environ.get("GATEWAY_TEST_API_PORT", 18080))
TILES = int(os.environ.get("GATEWAY_TEST_TILES_PORT", 18081))


def request(port, path, method="GET", headers=None):
    conn = HTTPConnection("127.0.0.1", port, timeout=10)
    conn.request(method, path, headers=headers or {})
    res = conn.getresponse()
    body = res.read()
    conn.close()
    return res, body


def echoed(port, path, **kwargs):
    res, body = request(port, path, **kwargs)
    assert res.status == 200, (path, res.status, body)
    return res, json.loads(body)


def unique(path):
    """A fresh URL, so no earlier test's cached response answers it."""
    sep = "&" if "?" in path else "?"
    return f"{path}{sep}n={uuid.uuid4().hex}"


def setUpModule():
    # Varnish marks Caddy healthy only after its first probe succeeds
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        try:
            if request(API, "/api/health")[0].status == 200:
                if request(TILES, "/legacy/version")[0].status == 200:
                    return
        except OSError:
            pass
        time.sleep(1)
    raise RuntimeError("gateway did not become ready")


class APIRoutes(unittest.TestCase):
    def test_v3(self):
        _, data = echoed(API, "/api/v3/columns?id=1")
        self.assertEqual(data["service"], "api_v3")
        self.assertEqual(data["path"], "/columns?id=1")

    def test_v2(self):
        _, data = echoed(API, "/api/v2/units")
        self.assertEqual((data["service"], data["path"]), ("api_v2", "/units"))

    def test_unmatched_falls_back_to_v2(self):
        _, data = echoed(API, "/api/defs/intervals")
        self.assertEqual((data["service"], data["path"]), ("api_v2", "/defs/intervals"))

    def test_knowledge_graph(self):
        _, data = echoed(API, "/api/v3/knowledge-graph/search")
        self.assertEqual((data["service"], data["path"]), ("kg", "/search"))

    def test_health(self):
        res, body = request(API, "/api/health")
        self.assertEqual((res.status, body), (200, b"OK"))

    def test_version(self):
        res, data = echoed(API, "/api/gateway/version")
        self.assertEqual(data["service"], "api-gateway")
        self.assertEqual(res.getheader("Cache-Control"), "no-store")

    def test_legacy_raster_tiles(self):
        _, data = echoed(API, "/api/v2/maps/burwell/emphasized/12/986/1435/tile.png")
        self.assertEqual(data["service"], "tilehost")
        self.assertEqual(data["path"], "/carto/12/986/1435.png")
        self.assertEqual(data["headers"]["host"], "tilehost:8000")

    def test_task_routes_bypass_cache(self):
        res, _ = echoed(API, "/api/v3/tasks/list")
        self.assertEqual(res.getheader("X-Cache"), "bypass")

    def test_responses_are_cached(self):
        path = unique("/api/v3/columns")
        first, _ = echoed(API, path)
        second, _ = echoed(API, path)
        self.assertEqual(first.getheader("X-Cache"), "miss")
        self.assertEqual(second.getheader("X-Cache"), "hit")

    def test_v2_cookies_dropped(self):
        _, data = echoed(API, "/api/v2/units", headers={"Cookie": "access_token=abc"})
        self.assertNotIn("cookie", data["headers"])

    def test_cors_and_server_headers(self):
        res, _ = echoed(API, unique("/api/v3/columns"))
        self.assertEqual(res.getheader("Access-Control-Allow-Origin"), "*")
        self.assertIsNone(res.getheader("Server"))


class PostgRESTRoutes(unittest.TestCase):
    def test_schema_profiles(self):
        for path, schema in [
            ("/api/v3/macrostrat/pg/units", "macrostrat_api"),
            ("/api/v3/map-ingestion/pg/sources", "map_ingestion_api"),
            ("/api/v3/knowledge-graph/pg/runs", "macrostrat_api"),
            ("/api/pg/units", "macrostrat_api"),
        ]:
            with self.subTest(path=path):
                _, data = echoed(API, unique(path))
                self.assertEqual(data["service"], "postgrest")
                self.assertTrue(data["path"].startswith("/" + path.split("/")[-1]))
                self.assertEqual(data["headers"]["accept-profile"], schema)
                self.assertEqual(data["headers"]["content-profile"], schema)

    def test_content_range_renamed(self):
        # Varnish drops Content-Range from a 200, as deployed; clients read X-Data-Range
        res, _ = echoed(API, unique("/api/v3/macrostrat/pg/units"))
        self.assertEqual(res.getheader("X-Data-Range"), "0-9/100")

    def test_cookie_becomes_authorization(self):
        _, data = echoed(
            API, "/api/v3/macrostrat/pg/units", headers={"Cookie": "access_token=abc"}
        )
        self.assertEqual(data["headers"]["authorization"], "abc")
        self.assertNotIn("cookie", data["headers"])

    def test_authorization_header_wins(self):
        _, data = echoed(
            API,
            "/api/v3/macrostrat/pg/units",
            headers={"Cookie": "access_token=abc", "Authorization": "Bearer xyz"},
        )
        self.assertEqual(data["headers"]["authorization"], "Bearer xyz")

    def test_trailing_slash_redirect_keeps_api_prefix(self):
        res, _ = request(API, "/api/v3/macrostrat/pg")
        self.assertEqual(res.status, 301)
        # Relative, so it resolves to /api/v3/macrostrat/pg/
        self.assertEqual(res.getheader("Location"), "pg/")


class TileCache(unittest.TestCase):
    def test_mvt_goes_to_core_without_extension(self):
        _, data = echoed(TILES, "/map/carto/3/2/1.mvt?x=1")
        self.assertEqual(data["service"], "tileserver_core")
        self.assertEqual(data["path"], "/map/carto/3/2/1?x=1")

    def test_png_goes_to_legacy(self):
        _, data = echoed(TILES, unique("/carto/3/2/1.png"))
        self.assertEqual(data["service"], "tileserver_legacy")

    def test_raster_png_goes_to_core(self):
        _, data = echoed(TILES, unique("/rasters/relief/3/2/1.png"))
        self.assertEqual(data["service"], "tileserver_core")

    def test_index_goes_to_legacy(self):
        _, data = echoed(TILES, "/")
        self.assertEqual(data["service"], "tileserver_legacy")

    def test_legacy_status_routes(self):
        _, data = echoed(TILES, "/legacy/version")
        self.assertEqual(
            (data["service"], data["path"]), ("tileserver_legacy", "/version")
        )

    def test_cache_management_hidden(self):
        self.assertEqual(request(TILES, "/cache/clear")[0].status, 403)
        _, data = echoed(TILES, unique("/cache/footprints/1/1/1"))
        self.assertEqual(data["service"], "tileserver_core")

    def test_high_zoom_bypasses_cache(self):
        # tiles.vcl reports a pass as a miss, so a repeat must not hit
        path = unique("/carto/15/2/1.png")
        echoed(TILES, path)
        res, _ = echoed(TILES, path)
        self.assertEqual(res.getheader("X-Cache"), "miss")

    def test_tiles_are_cached(self):
        path = unique("/carto/3/2/1.png")
        echoed(TILES, path)
        res, _ = echoed(TILES, path)
        self.assertEqual(res.getheader("X-Cache"), "hit")

    def test_cors_restated_on_delivery(self):
        res, _ = echoed(
            TILES, unique("/carto/3/2/1.png"), headers={"Origin": "https://x.org"}
        )
        self.assertEqual(res.getheader("Access-Control-Allow-Origin"), "*")

    def test_relayed_ban_refused(self):
        res, _ = request(
            TILES, "/", method="BAN", headers={"X-Forwarded-For": "203.0.113.1"}
        )
        self.assertEqual(res.status, 403)


def client_ipv4():
    n = uuid.uuid4().int
    return f"198.18.{n % 256}.{(n >> 8) % 256}"


def client_ipv6_net():
    n = uuid.uuid4().hex
    return f"2001:db8:{n[:4]}:{n[4:8]}"


def throttle(path, client):
    """The X-Throttle mark on a tile, as relayed by an edge proxy for `client`."""
    res, _ = echoed(TILES, path, headers={"X-Forwarded-For": client})
    return res.getheader("X-Throttle")


class RenderThrottle(unittest.TestCase):
    """TILE_THROTTLE_BURST is 5 in tests/compose.yaml."""

    def test_sixth_miss_is_marked(self):
        client = client_ipv4()
        marks = [throttle(unique("/carto/3/2/1.png"), client) for _ in range(6)]
        self.assertEqual(marks[:5], [None] * 5)
        self.assertEqual(marks[5], "would-deny")

    def test_report_only_still_serves(self):
        client = client_ipv4()
        for _ in range(6):
            res, body = echoed(
                TILES, unique("/carto/3/2/1.png"), headers={"X-Forwarded-For": client}
            )
        self.assertEqual(res.getheader("X-Throttle"), "would-deny")
        self.assertEqual(body["service"], "tileserver_legacy")
        self.assertNotIn("x-throttle-client", body["headers"])

    def test_clients_are_counted_apart(self):
        busy = client_ipv4()
        for _ in range(6):
            throttle(unique("/carto/3/2/1.png"), busy)
        self.assertIsNone(throttle(unique("/carto/3/2/1.png"), client_ipv4()))

    def test_cache_hits_are_not_counted(self):
        client = client_ipv4()
        path = unique("/carto/3/2/1.png")
        marks = [throttle(path, client) for _ in range(10)]
        self.assertEqual(marks, [None] * 10)

    def test_ipv6_counts_by_64(self):
        net = client_ipv6_net()
        marks = [
            throttle(unique("/carto/3/2/1.png"), f"{net}:{i:x}:0:0:{i + 1:x}")
            for i in range(6)
        ]
        self.assertEqual(marks[5], "would-deny")

    def test_forged_entries_do_not_reset_the_count(self):
        client = client_ipv4()
        marks = [
            throttle(unique("/carto/3/2/1.png"), f"{client_ipv4()}, {client}")
            for _ in range(6)
        ]
        self.assertEqual(marks[5], "would-deny")

    def test_direct_internal_calls_are_exempt(self):
        marks = [
            echoed(TILES, unique("/carto/3/2/1.png"))[0].getheader("X-Throttle")
            for _ in range(6)
        ]
        self.assertEqual(marks, [None] * 6)

    def test_client_cannot_set_the_mark(self):
        res, _ = echoed(
            TILES,
            unique("/carto/3/2/1.png"),
            headers={"X-Forwarded-For": client_ipv4(), "X-Throttle": "deny"},
        )
        self.assertIsNone(res.getheader("X-Throttle"))


if __name__ == "__main__":
    unittest.main()
